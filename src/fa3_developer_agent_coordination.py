#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

RUNTIME_ID = "FA3-DEVELOPER-AGENT-COORDINATION-REF-RUNTIME-001"
RUNTIME_VERSION = "0.1.0"
FIXTURE_PROVIDER_ID = "FA3-BUILTIN-DETERMINISTIC-FIXTURE-ADAPTER-001"
INTEGRATION_ACTOR = "FA3_INTEGRATION"


class CoordinationDenied(RuntimeError):
    pass


class ConflictDetected(CoordinationDenied):
    pass


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    agent_id: str
    provider_id: str
    relative_path: str
    content: str
    max_message_hops: int = 4
    risk_class: str = "LOW"


@dataclass(frozen=True)
class AgentDelegation:
    task_id: str
    agent_id: str
    caller_identity: str
    workspace_id: str
    capability_scope: tuple[str, ...]
    expires_at: str


@dataclass(frozen=True)
class WorkspaceLease:
    workspace_id: str
    agent_id: str
    branch: str
    base_commit: str


@dataclass(frozen=True)
class AgentMessage:
    message_id: str
    task_id: str
    sender: str
    recipient: str
    act: str
    hop: int
    max_hops: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class AgentResult:
    task_id: str
    agent_id: str
    provider_id: str
    status: str
    changed_paths: tuple[str, ...]
    result_sha256: str


@dataclass(frozen=True)
class HumanEscalation:
    task_id: str
    risk_class: str
    required: bool
    approved: bool
    approval_id: str | None = None


@dataclass(frozen=True)
class CircuitBreakerAction:
    task_id: str
    state: str
    reason: str


@dataclass(frozen=True)
class IntegrationIntent:
    task_id: str
    actor: str
    target_branch: str
    patch_sha256: str


@dataclass(frozen=True)
class ExecutionEvidence:
    runtime_id: str
    runtime_version: str
    task_ids: tuple[str, ...]
    integration_commit: str
    integration_author: str
    event_log_sha256: str
    status: str


class ProviderAdapter(Protocol):
    provider_id: str

    def spawn(
        self,
        *,
        task: AgentTask,
        workspace: Path,
        request_path: Path,
        result_path: Path,
    ) -> subprocess.Popen[str]:
        ...


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_within(root: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise CoordinationDenied("workspace path must be non-empty and relative")
    normalized = Path(relative_path)
    if ".." in normalized.parts:
        raise CoordinationDenied("workspace path traversal denied")
    root_resolved = root.resolve()
    target = (root_resolved / normalized).resolve(strict=False)
    if target == root_resolved or root_resolved not in target.parents:
        raise CoordinationDenied("workspace escape denied")
    parent = target.parent.resolve(strict=False)
    if parent != root_resolved and root_resolved not in parent.parents:
        raise CoordinationDenied("workspace parent escape denied")
    if target.exists() and target.is_symlink():
        raise CoordinationDenied("symlink target mutation denied")
    return target


def workspace_plan_valid(workspace_by_agent: dict[str, str], mutating_agents: list[str]) -> bool:
    if any(not workspace_by_agent.get(agent) for agent in mutating_agents):
        return False
    values = [workspace_by_agent[a] for a in mutating_agents]
    return len(values) == len(set(values))


def commit_intent_allowed(*, actor_role: str, target_branch: str) -> bool:
    if target_branch == "main":
        return actor_role == INTEGRATION_ACTOR
    return actor_role != "UNAUTHORIZED"


def message_hop_action(*, hop: int, max_hops: int, act: str) -> str:
    if max_hops <= 0 or hop < 0:
        return "TERMINATE"
    if act in {"done", "inform"} and hop <= max_hops:
        return "ALLOW"
    return "ALLOW" if hop < max_hops else "TERMINATE"


def mutation_allowed(*, risk_class: str, approved: bool) -> bool:
    critical = {"DESTRUCTIVE", "SPEND", "SCOPE_CHANGE", "UNRESOLVED_CONFLICT", "RELEASE", "CREDENTIAL"}
    return approved if risk_class in critical else True


def cleanup_state_valid(*, live_processes: int, worktrees: int, active_leases: int, pending_messages: int) -> bool:
    return live_processes == 0 and worktrees == 0 and active_leases == 0 and pending_messages == 0


def provider_authority_assignment_allowed(*, provider_id: str, authority_owner: str) -> bool:
    return bool(provider_id and authority_owner and provider_id != authority_owner)


class BuiltinDeterministicAdapter:
    provider_id = FIXTURE_PROVIDER_ID

    def __init__(self, module_path: Path | None = None):
        self.module_path = (module_path or Path(__file__)).resolve()

    def spawn(
        self,
        *,
        task: AgentTask,
        workspace: Path,
        request_path: Path,
        result_path: Path,
    ) -> subprocess.Popen[str]:
        _json_write(
            request_path,
            {
                "schema": "fa3.developer-agent-fixture-request.v1",
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "provider_id": task.provider_id,
                "workspace": str(workspace.resolve()),
                "relative_path": task.relative_path,
                "content": task.content,
            },
        )
        return subprocess.Popen(
            [
                sys.executable,
                str(self.module_path),
                "worker",
                "--request",
                str(request_path),
                "--result",
                str(result_path),
            ],
            cwd=str(workspace),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
        )


class Coordinator:
    def __init__(self, repo: Path, control_root: Path, *, max_message_hops: int = 4):
        self.repo = repo.resolve()
        self.control_root = control_root.resolve()
        self.control_root.mkdir(parents=True, exist_ok=True)
        self.max_message_hops = max_message_hops
        self.base_commit = self.git(self.repo, "rev-parse", "HEAD").strip()
        self.event_log = self.control_root / "events.jsonl"
        self.workspaces: dict[str, Path] = {}
        self.leases: dict[str, WorkspaceLease] = {}
        self.processes: dict[str, subprocess.Popen[str]] = {}

    @staticmethod
    def git(repo: Path, *args: str, input_text: str | None = None) -> str:
        cp = subprocess.run(
            ["git", "-C", str(repo), *args],
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
        if cp.returncode != 0:
            raise CoordinationDenied(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
        return cp.stdout

    def event(self, event_type: str, **fields: Any) -> None:
        record = {
            "event_type": event_type,
            "runtime_id": RUNTIME_ID,
            **fields,
        }
        with self.event_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    def allocate_worktree(self, task: AgentTask) -> WorkspaceLease:
        if task.agent_id in self.workspaces:
            raise CoordinationDenied("agent already has a workspace")
        workspace_id = f"ws-{task.agent_id}"
        workspace = self.control_root / "worktrees" / task.agent_id
        branch = f"fa3-dac/{task.agent_id}-{task.task_id.lower()}"
        workspace.parent.mkdir(parents=True, exist_ok=True)
        self.git(self.repo, "worktree", "add", "-b", branch, str(workspace), self.base_commit)
        lease = WorkspaceLease(workspace_id, task.agent_id, branch, self.base_commit)
        self.workspaces[task.agent_id] = workspace
        self.leases[task.agent_id] = lease
        self.event("WORKSPACE_ALLOCATED", agent_id=task.agent_id, workspace_id=workspace_id, branch=branch)
        return lease

    def publish_message(self, message: AgentMessage) -> Path:
        action = message_hop_action(hop=message.hop, max_hops=message.max_hops, act=message.act)
        if action != "ALLOW":
            self.event("CIRCUIT_BREAKER", task_id=message.task_id, state="TERMINATE", reason="MESSAGE_HOP_BUDGET")
            raise CoordinationDenied("message hop budget exceeded")
        mailbox = self.control_root / "mailboxes" / message.recipient
        mailbox.mkdir(parents=True, exist_ok=True)
        final = mailbox / f"{message.message_id}.json"
        temp = mailbox / f".{message.message_id}.tmp"
        _json_write(temp, asdict(message))
        os.replace(temp, final)
        self.event("MESSAGE_PUBLISHED", message_id=message.message_id, recipient=message.recipient)
        return final

    def consume_message(self, recipient: str, message_id: str) -> str:
        cursor_path = self.control_root / "cursors" / f"{recipient}.json"
        cursor = {"processed": []}
        if cursor_path.exists():
            cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
        processed = set(cursor.get("processed", []))
        if message_id in processed:
            self.event("MESSAGE_REPLAY_NOOP", message_id=message_id, recipient=recipient)
            return "NOOP"
        path = self.control_root / "mailboxes" / recipient / f"{message_id}.json"
        if not path.exists():
            raise CoordinationDenied("message missing before first consumption")
        json.loads(path.read_text(encoding="utf-8"))
        processed.add(message_id)
        _json_write(cursor_path, {"processed": sorted(processed)})
        path.unlink()
        self.event("MESSAGE_CONSUMED", message_id=message_id, recipient=recipient)
        return "PROCESS"

    def spawn_workers(self, tasks: list[AgentTask], adapter: ProviderAdapter) -> None:
        for task in tasks:
            if task.provider_id != adapter.provider_id:
                raise CoordinationDenied("task/provider adapter identity mismatch")
            workspace = self.workspaces[task.agent_id]
            req = self.control_root / "requests" / f"{task.task_id}.json"
            result = self.control_root / "results" / f"{task.task_id}.json"
            proc = adapter.spawn(task=task, workspace=workspace, request_path=req, result_path=result)
            self.processes[task.agent_id] = proc
            self.event("WORKER_SPAWNED", task_id=task.task_id, agent_id=task.agent_id, provider_id=task.provider_id)

    def collect_workers(self, tasks: list[AgentTask]) -> list[AgentResult]:
        results: list[AgentResult] = []
        for task in tasks:
            proc = self.processes[task.agent_id]
            stdout, stderr = proc.communicate(timeout=30)
            if proc.returncode != 0:
                raise CoordinationDenied(f"worker {task.agent_id} failed: {stderr.strip() or stdout.strip()}")
            result_path = self.control_root / "results" / f"{task.task_id}.json"
            if not result_path.exists():
                raise CoordinationDenied("worker result missing")
            raw = json.loads(result_path.read_text(encoding="utf-8"))
            if raw.get("status") != "PASS" or raw.get("task_id") != task.task_id:
                raise CoordinationDenied("worker result invalid")
            if self.git(self.workspaces[task.agent_id], "rev-parse", "HEAD").strip() != self.base_commit:
                raise CoordinationDenied("worker committed instead of returning a diff")
            changed = tuple(
                x for x in self.git(self.workspaces[task.agent_id], "diff", "--name-only", "HEAD", "--").splitlines() if x
            )
            if not changed:
                raise CoordinationDenied("worker produced no diff")
            results.append(
                AgentResult(
                    task_id=task.task_id,
                    agent_id=task.agent_id,
                    provider_id=task.provider_id,
                    status="PASS",
                    changed_paths=changed,
                    result_sha256=_sha256_file(result_path),
                )
            )
            self.event("WORKER_RESULT_COLLECTED", task_id=task.task_id, agent_id=task.agent_id, changed_paths=list(changed))
        return results

    @staticmethod
    def assert_no_path_conflicts(results: list[AgentResult]) -> None:
        owners: dict[str, str] = {}
        for result in results:
            for path in result.changed_paths:
                prior = owners.get(path)
                if prior is not None and prior != result.agent_id:
                    raise ConflictDetected(f"path conflict: {path} by {prior} and {result.agent_id}")
                owners[path] = result.agent_id

    def integrate(self, tasks: list[AgentTask], results: list[AgentResult]) -> tuple[str, str, list[str]]:
        self.assert_no_path_conflicts(results)
        if not commit_intent_allowed(actor_role=INTEGRATION_ACTOR, target_branch="main"):
            raise CoordinationDenied("integration actor cannot commit main")
        applied_hashes: list[str] = []
        for task in tasks:
            patch = self.git(self.workspaces[task.agent_id], "diff", "--binary", "HEAD", "--")
            if not patch.strip():
                raise CoordinationDenied("empty worker patch")
            patch_hash = _sha256_bytes(patch.encode("utf-8"))
            applied_hashes.append(patch_hash)
            self.git(self.repo, "apply", "--check", "-", input_text=patch)
            self.git(self.repo, "apply", "--index", "-", input_text=patch)
            self.event("PATCH_CHECKED_AND_APPLIED", task_id=task.task_id, patch_sha256=patch_hash)
        status = self.git(self.repo, "status", "--porcelain").strip()
        if not status:
            raise CoordinationDenied("integration has no staged changes")
        cp = subprocess.run(
            [
                "git", "-C", str(self.repo),
                "-c", "user.name=FA3 Integration",
                "-c", "user.email=fa3-integration@localhost",
                "commit", "-m", "FA3 reference multi-agent integration",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if cp.returncode != 0:
            raise CoordinationDenied(f"integration commit failed: {cp.stderr.strip()}")
        commit = self.git(self.repo, "rev-parse", "HEAD").strip()
        author = self.git(self.repo, "show", "-s", "--format=%an", commit).strip()
        self.event("INTEGRATION_COMMITTED", commit=commit, actor=INTEGRATION_ACTOR, author=author)
        return commit, author, applied_hashes

    def cleanup(self) -> dict[str, int]:
        for proc in self.processes.values():
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
        for workspace in list(self.workspaces.values()):
            try:
                self.git(self.repo, "worktree", "remove", "--force", str(workspace))
            except CoordinationDenied:
                pass
        try:
            self.git(self.repo, "worktree", "prune")
        except CoordinationDenied:
            pass
        pending = 0
        mailbox_root = self.control_root / "mailboxes"
        if mailbox_root.exists():
            pending = sum(1 for p in mailbox_root.rglob("*.json") if p.is_file())
        live = sum(1 for proc in self.processes.values() if proc.poll() is None)
        state = {
            "live_processes": live,
            "worktrees": sum(1 for p in (self.control_root / "worktrees").glob("*") if p.exists()) if (self.control_root / "worktrees").exists() else 0,
            "active_leases": 0,
            "pending_messages": pending,
        }
        self.leases.clear()
        self.event("CLEANUP_COMPLETE", **state)
        return state

    def run(self, tasks: list[AgentTask], adapter: ProviderAdapter) -> dict[str, Any]:
        if len(tasks) < 2:
            raise CoordinationDenied("multi-agent reference flow requires at least two workers")
        if len({t.agent_id for t in tasks}) != len(tasks):
            raise CoordinationDenied("duplicate agent identity")
        positive: dict[str, Any] = {}
        cleanup_state: dict[str, int] | None = None
        try:
            for task in tasks:
                self.allocate_worktree(task)
            if not workspace_plan_valid(
                {agent: str(path) for agent, path in self.workspaces.items()},
                [t.agent_id for t in tasks],
            ):
                raise CoordinationDenied("workspace isolation invariant failed")

            for index, task in enumerate(tasks):
                message = AgentMessage(
                    message_id=f"msg-{task.task_id}",
                    task_id=task.task_id,
                    sender="coordinator",
                    recipient=task.agent_id,
                    act="request",
                    hop=0,
                    max_hops=min(task.max_message_hops, self.max_message_hops),
                    payload={"objective": "execute delegated developer task"},
                )
                self.publish_message(message)
                first = self.consume_message(task.agent_id, message.message_id)
                replay = self.consume_message(task.agent_id, message.message_id)
                if first != "PROCESS" or replay != "NOOP":
                    raise CoordinationDenied("idempotent mailbox invariant failed")
                if index == 0:
                    positive["mailbox_first"] = first
                    positive["mailbox_replay"] = replay

            self.spawn_workers(tasks, adapter)
            results = self.collect_workers(tasks)
            commit, author, patch_hashes = self.integrate(tasks, results)
            positive.update(
                {
                    "worker_count": len(tasks),
                    "workspace_count": len(self.workspaces),
                    "result_count": len(results),
                    "worker_heads_unchanged": True,
                    "integration_commit": commit,
                    "integration_author": author,
                    "patch_sha256": patch_hashes,
                    "changed_paths": sorted({p for r in results for p in r.changed_paths}),
                }
            )
        finally:
            cleanup_state = self.cleanup()

        if cleanup_state is None or not cleanup_state_valid(**cleanup_state):
            raise CoordinationDenied(f"cleanup invariant failed: {cleanup_state}")
        if positive.get("integration_author") != "FA3 Integration":
            raise CoordinationDenied("single integration committer identity drift")
        event_hash = _sha256_file(self.event_log)
        positive["cleanup"] = cleanup_state
        positive["event_log_sha256"] = event_hash
        positive["status"] = "PASS"
        return positive


def _init_fixture_repo(path: Path, files: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(path), "checkout", "-b", "main"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "FA3 Fixture"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "fa3-fixture@localhost"], check=True)
    for rel, content in files.items():
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "baseline"], check=True, capture_output=True, text=True)


def _positive_reference_flow(base: Path) -> dict[str, Any]:
    repo = base / "positive-repo"
    _init_fixture_repo(
        repo,
        {
            "work/architecture.txt": "baseline architecture\n",
            "work/tests.txt": "baseline tests\n",
            "work/security.txt": "baseline security\n",
        },
    )
    tasks = [
        AgentTask("TASK-ARCH", "architecture-agent", FIXTURE_PROVIDER_ID, "work/architecture.txt", "architecture-result\n"),
        AgentTask("TASK-TEST", "test-agent", FIXTURE_PROVIDER_ID, "work/tests.txt", "test-result\n"),
        AgentTask("TASK-SEC", "security-agent", FIXTURE_PROVIDER_ID, "work/security.txt", "security-result\n"),
    ]
    coordinator = Coordinator(repo, base / "positive-control")
    return coordinator.run(tasks, BuiltinDeterministicAdapter())


def _overlap_negative_flow(base: Path) -> bool:
    repo = base / "conflict-repo"
    _init_fixture_repo(repo, {"work/shared.txt": "baseline\n"})
    tasks = [
        AgentTask("TASK-A", "agent-a", FIXTURE_PROVIDER_ID, "work/shared.txt", "a\n"),
        AgentTask("TASK-B", "agent-b", FIXTURE_PROVIDER_ID, "work/shared.txt", "b\n"),
    ]
    coordinator = Coordinator(repo, base / "conflict-control")
    try:
        coordinator.run(tasks, BuiltinDeterministicAdapter())
    except ConflictDetected:
        return True
    return False


def run_reference_e2e() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="fa3-dac-e2e-") as td:
        base = Path(td)
        positive = _positive_reference_flow(base)
        negatives = {
            "duplicate_mutating_workspace_denied": not workspace_plan_valid(
                {"agent-a": "same", "agent-b": "same"}, ["agent-a", "agent-b"]
            ),
            "worker_direct_main_commit_denied": not commit_intent_allowed(
                actor_role="WORKER", target_branch="main"
            ),
            "message_hop_budget_overflow_terminates": message_hop_action(
                hop=4, max_hops=4, act="request"
            ) == "TERMINATE",
            "destructive_without_human_approval_denied": not mutation_allowed(
                risk_class="DESTRUCTIVE", approved=False
            ),
            "cleanup_leak_fails": not cleanup_state_valid(
                live_processes=1, worktrees=0, active_leases=0, pending_messages=0
            ),
            "provider_authority_assignment_denied": not provider_authority_assignment_allowed(
                provider_id="provider-x", authority_owner="provider-x"
            ),
            "overlapping_worker_diffs_denied": _overlap_negative_flow(base),
        }
        status = "PASS" if positive.get("status") == "PASS" and all(negatives.values()) else "FAIL"
        runtime_sha = _sha256_file(Path(__file__).resolve())
        return {
            "schema": "fa3.developer-agent-coordination-e2e.v1",
            "runtime_id": RUNTIME_ID,
            "runtime_version": RUNTIME_VERSION,
            "status": "CI_REFERENCE_RUNTIME_E2E_PASS" if status == "PASS" else "FAIL",
            "result": status,
            "evidence_scope": "REFERENCE_RUNTIME_ONLY_NOT_CURRENT_HOST_PROVIDER_PROMOTION",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "runtime_sha256": runtime_sha,
            "positive_flow": positive,
            "negative_cases": negatives,
            "external_provider_credentials_used": False,
            "current_host_production_claim": False,
        }


def worker_main(request_path: Path, result_path: Path) -> int:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    workspace = Path(request["workspace"]).resolve()
    target = _resolve_within(workspace, str(request["relative_path"]))
    if not target.exists():
        raise CoordinationDenied("fixture worker only modifies pre-existing files")
    target.write_text(str(request["content"]), encoding="utf-8")
    _json_write(
        result_path,
        {
            "schema": "fa3.developer-agent-fixture-result.v1",
            "task_id": request["task_id"],
            "agent_id": request["agent_id"],
            "provider_id": request["provider_id"],
            "status": "PASS",
            "target_sha256": _sha256_file(target),
        },
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    worker = sub.add_parser("worker")
    worker.add_argument("--request", required=True)
    worker.add_argument("--result", required=True)
    sub.add_parser("e2e")
    args = ap.parse_args()
    if args.command == "worker":
        return worker_main(Path(args.request), Path(args.result))
    report = run_reference_e2e()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
