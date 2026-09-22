#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

BROKER_ID = "FA3-INTEGRATION-BROKER-001"
PROPOSAL_SCHEMA = "fa3.agent-task-proposal.v1"
EVENT_SCHEMA = "fa3.agent-integration-event.v1"
APPROVED = "APPROVED_BY_HUMAN"
PROPOSAL_ID_RE = re.compile(r"^prop-[0-9]{8}-[0-9]{3,6}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

PROTECTED_PATHS = (
    "bin/fa3-enforce",
    "bin/fa3-integration-committer.py",
    "src/fa3_enforce.py",
    "src/fa3_integration_broker.py",
    "src/fa3_integration_broker_gate.py",
    "src/fa3_podman_secret_negative_gate.py",
    "canonical/enforcement-policy.json",
    "canonical/integration-broker-enforcement.json",
    "canonical/FA3-GATE-INTEGRATION-BROKER-001.json",
    "canonical/FA3-PODMAN-SECRET-ISOLATION-CURRENT-HOST-CONFORMANCE-001.json",
    "canonical/FA3-GATE-PODMAN-SECRET-ISOLATION-CURRENT-HOST-001.json",
    "canonical/schemas/",
    ".github/workflows/fa3-integration-broker.yml",
)


class IntegrationDenied(RuntimeError):
    pass


def _safe_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS", "SSH_ASKPASS",
        "SSH_AUTH_SOCK", "GIT_SSH_COMMAND",
    ):
        env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "Never"
    if extra:
        env.update(extra)
    return env


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        env=_safe_env(env),
    )
    if check and cp.returncode != 0:
        msg = cp.stderr.strip() or cp.stdout.strip() or f"exit={cp.returncode}"
        raise IntegrationDenied(f"{' '.join(argv)} failed: {msg[:2000]}")
    return cp


def _git(repo: Path, *args: str, input_text: str | None = None) -> str:
    return _run(["git", "-C", str(repo), *args], input_text=input_text).stdout


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def proposal_digest(proposal: dict[str, Any]) -> str:
    value = copy.deepcopy(proposal)
    approval = value.get("approval_state")
    if isinstance(approval, dict):
        approval.pop("proposal_digest_sha256", None)
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def validate_approval(proposal: dict[str, Any]) -> tuple[bool, str]:
    if proposal.get("schema") != PROPOSAL_SCHEMA:
        return False, "proposal schema mismatch"
    prop_id = proposal.get("proposal_id")
    if not isinstance(prop_id, str) or not PROPOSAL_ID_RE.fullmatch(prop_id):
        return False, "proposal_id invalid"
    approval = proposal.get("approval_state")
    if not isinstance(approval, dict) or approval.get("status") != APPROVED:
        return False, "human approval missing"
    base = approval.get("approved_base_sha")
    if not isinstance(base, str) or not SHA_RE.fullmatch(base):
        return False, "approved_base_sha invalid"
    expected = approval.get("proposal_digest_sha256")
    if not isinstance(expected, str) or not DIGEST_RE.fullmatch(expected):
        return False, "proposal digest invalid"
    if expected != proposal_digest(proposal):
        return False, "proposal digest does not match approved content"
    if not str(approval.get("approved_by", "")).strip():
        return False, "approved_by missing"
    if not str(approval.get("approved_at", "")).strip():
        return False, "approved_at missing"
    mutations = proposal.get("mutations")
    if not isinstance(mutations, list) or not mutations:
        return False, "mutations missing"
    context = proposal.get("context")
    if not isinstance(context, dict):
        return False, "context missing"
    if context.get("base_commit") != base:
        return False, "context base_commit does not match approved_base_sha"
    target = context.get("target_capability")
    if not isinstance(target, str) or not re.fullmatch(r"CAP-[0-9]{3}", target):
        return False, "target_capability invalid"
    write_set = context.get("declared_write_set")
    if not isinstance(write_set, list) or not write_set or not all(isinstance(x, str) for x in write_set):
        return False, "declared_write_set missing"
    test_plan = context.get("test_plan")
    if not isinstance(test_plan, list) or not test_plan or not all(isinstance(x, str) and x.strip() for x in test_plan):
        return False, "test_plan missing"
    limits = proposal.get("circuit_breaker_limits")
    if not isinstance(limits, dict):
        return False, "circuit_breaker_limits missing"
    return True, "PASS"


def normalize_repo_path(repo: Path, value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise IntegrationDenied("invalid repository path")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        raise IntegrationDenied(f"path traversal denied: {value}")
    normalized = p.as_posix()
    if normalized == ".git" or normalized.startswith(".git/"):
        raise IntegrationDenied(".git mutation denied")
    cursor = repo.resolve()
    for part in p.parts[:-1]:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise IntegrationDenied(f"symlink parent mutation denied: {value}")
    target = repo / normalized
    if target.exists() and target.is_symlink():
        raise IntegrationDenied(f"symlink target mutation denied: {value}")
    return normalized


def protected_path(path: str) -> bool:
    for protected in PROTECTED_PATHS:
        if protected.endswith("/"):
            if path.startswith(protected):
                return True
        elif path == protected:
            return True
    return False


def patch_paths(diff_text: str) -> set[str]:
    if not isinstance(diff_text, str) or not diff_text.strip():
        raise IntegrationDenied("empty patch denied")
    joined = "\n" + diff_text
    if "\nrename from " in joined or "\nrename to " in joined:
        raise IntegrationDenied("rename patches require separate reviewed migration")
    paths: set[str] = set()
    for raw in diff_text.splitlines():
        if raw.startswith("--- ") or raw.startswith("+++ "):
            token = raw[4:].split("\t", 1)[0]
            if token == "/dev/null":
                continue
            if token.startswith("a/") or token.startswith("b/"):
                token = token[2:]
            if token.startswith('"'):
                raise IntegrationDenied("quoted patch path denied")
            paths.add(token)
    if not paths:
        raise IntegrationDenied("patch contains no repository path")
    return paths


def validate_mutations(repo: Path, proposal: dict[str, Any]) -> list[str]:
    declared: list[str] = []
    for mutation in proposal.get("mutations", []):
        if not isinstance(mutation, dict):
            raise IntegrationDenied("mutation must be object")
        path = normalize_repo_path(repo, mutation.get("file_path", ""))
        if protected_path(path):
            raise IntegrationDenied(f"trusted integration surface is protected: {path}")
        touched = {normalize_repo_path(repo, p) for p in patch_paths(mutation.get("diff", ""))}
        if touched != {path}:
            raise IntegrationDenied(
                f"declared path {path!r} does not exactly match patch paths {sorted(touched)!r}"
            )
        declared.append(path)
    if len(declared) != len(set(declared)):
        raise IntegrationDenied("duplicate mutation path denied")
    write_set = proposal.get("context", {}).get("declared_write_set", [])
    normalized_write_set = [normalize_repo_path(repo, value) for value in write_set]
    if len(normalized_write_set) != len(set(normalized_write_set)):
        raise IntegrationDenied("duplicate declared_write_set path denied")
    if set(normalized_write_set) != set(declared):
        raise IntegrationDenied(
            f"declared_write_set differs from mutation set: {sorted(normalized_write_set)} != {sorted(declared)}"
        )
    return declared


def _write_event(ledger_root: Path, proposal: dict[str, Any], event: dict[str, Any]) -> Path:
    bucket = "prepared" if event["status"] == "PR_READY" else "failed"
    target_dir = ledger_root / bucket
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = target_dir / f"{proposal['proposal_id']}-{stamp}.json"
    payload = {
        "schema": EVENT_SCHEMA,
        "broker_id": BROKER_ID,
        "proposal_id": proposal["proposal_id"],
        "proposal_digest_sha256": proposal_digest(proposal),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with target.open("x", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, sort_keys=True, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    return target


def _lock_path(repo: Path) -> Path:
    common = _git(repo, "rev-parse", "--git-common-dir").strip()
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = (repo / common_path).resolve()
    return common_path / "fa3-integration-broker.lock"


def _main_preconditions(repo: Path, approved_base: str) -> None:
    branch = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD").strip()
    if branch != "main":
        raise IntegrationDenied("broker requires the primary working tree to be on main")
    if _git(repo, "status", "--porcelain").strip():
        raise IntegrationDenied("main working tree must be clean")
    current = _git(repo, "rev-parse", "refs/heads/main").strip()
    if current != approved_base:
        raise IntegrationDenied(
            f"approved base is stale: approved={approved_base} current={current}"
        )


class FA3IntegrationBroker:
    def __init__(
        self,
        repo_dir: str | Path = ".",
        inbox_dir: str | Path = "_agent-inbox/approved",
        ledger_dir: str | Path = "_agent-ledger",
    ):
        self.repo = Path(repo_dir).resolve()
        inbox = Path(inbox_dir)
        ledger = Path(ledger_dir)
        self.inbox = inbox if inbox.is_absolute() else self.repo / inbox
        self.ledger = ledger if ledger.is_absolute() else self.repo / ledger

    def integrate(self, proposal_path: Path) -> dict[str, Any]:
        proposal_bytes = proposal_path.read_bytes()
        proposal = json.loads(proposal_bytes.decode("utf-8"))
        valid, reason = validate_approval(proposal)
        if not valid:
            raise IntegrationDenied(reason)
        declared = validate_mutations(self.repo, proposal)
        approval = proposal["approval_state"]
        base = approval["approved_base_sha"]
        prop_id = proposal["proposal_id"]
        branch = f"fa3/integration/{prop_id}"
        if _run(
            ["git", "-C", str(self.repo), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            check=False,
        ).returncode == 0:
            raise IntegrationDenied(f"candidate branch already exists: {branch}")
        lock_path = _lock_path(self.repo)
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        with lock_path.open("a+", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            _main_preconditions(self.repo, base)
            with tempfile.TemporaryDirectory(prefix=f"fa3-integration-{prop_id}-") as td:
                temp = Path(td)
                candidate = temp / "candidate"
                trusted = temp / "trusted-base"
                prepared = False
                try:
                    _git(self.repo, "worktree", "add", "--detach", str(trusted), base)
                    _git(self.repo, "worktree", "add", "-b", branch, str(candidate), base)

                    for mutation in proposal["mutations"]:
                        diff_text = mutation["diff"]
                        _git(candidate, "apply", "--check", "--whitespace=error-all", "-", input_text=diff_text)
                        _git(candidate, "apply", "--index", "--whitespace=error-all", "-", input_text=diff_text)

                    staged = {
                        x for x in _git(candidate, "diff", "--cached", "--name-only", "--").splitlines() if x
                    }
                    if staged != set(declared):
                        raise IntegrationDenied(
                            f"staged path set differs from approved set: {sorted(staged)} != {sorted(declared)}"
                        )

                    trusted_gate = _run(
                        [
                            sys.executable,
                            str(trusted / "src/fa3_enforce.py"),
                            "--root",
                            str(candidate),
                            "static",
                        ],
                        cwd=trusted,
                        env={"PYTHONPATH": str(trusted / "src")},
                    )
                    trusted_gate_sha = hashlib.sha256(
                        (trusted_gate.stdout + trusted_gate.stderr).encode("utf-8")
                    ).hexdigest()

                    candidate_gate = _run(
                        [str(candidate / "bin/fa3-enforce"), "static"],
                        cwd=candidate,
                    )
                    candidate_gate_sha = hashlib.sha256(
                        (candidate_gate.stdout + candidate_gate.stderr).encode("utf-8")
                    ).hexdigest()

                    scope = " ".join(str(proposal.get("context", {}).get("task_scope", "approved agent change")).split())[:160]
                    origin = " ".join(str(proposal.get("origin_agent", "unknown")).split())[:128]
                    _run(
                        [
                            "git", "-C", str(candidate),
                            "-c", "user.name=FA3 Integration",
                            "-c", "user.email=fa3-integration@localhost",
                            "-c", "core.hooksPath=/dev/null",
                            "commit", "-m",
                            f"integration({prop_id}): {scope} [attributable: {origin}]",
                        ]
                    )
                    result_sha = _git(candidate, "rev-parse", "HEAD").strip()

                    if proposal_path.read_bytes() != proposal_bytes:
                        raise IntegrationDenied("approved proposal changed during integration")
                    if proposal_digest(proposal) != approval["proposal_digest_sha256"]:
                        raise IntegrationDenied("approved proposal digest changed during integration")

                    _main_preconditions(self.repo, base)
                    if _git(self.repo, "rev-parse", "refs/heads/main").strip() != base:
                        raise IntegrationDenied("protected main changed during candidate preparation")

                    event_path = _write_event(
                        self.ledger,
                        proposal,
                        {
                            "status": "PR_READY",
                            "approved_base_sha": base,
                            "candidate_branch": branch,
                            "result_sha": result_sha,
                            "changed_paths": sorted(declared),
                            "trusted_gate_output_sha256": trusted_gate_sha,
                            "candidate_gate_output_sha256": candidate_gate_sha,
                            "proposal_mutated": False,
                            "main_mutated": False,
                            "protected_branch_submission_required": True,
                        },
                    )
                    prepared = True
                    return {
                        "result": "PASS",
                        "status": "PR_READY",
                        "proposal_id": prop_id,
                        "candidate_branch": branch,
                        "result_sha": result_sha,
                        "event_path": str(event_path),
                        "protected_branch_submission_required": True,
                    }
                finally:
                    for worktree in (candidate, trusted):
                        if worktree.exists():
                            _run(
                                ["git", "-C", str(self.repo), "worktree", "remove", "--force", str(worktree)],
                                check=False,
                            )
                    _run(["git", "-C", str(self.repo), "worktree", "prune"], check=False)
                    if not prepared:
                        _run(["git", "-C", str(self.repo), "branch", "-D", branch], check=False)

    def process_once(self) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        if not self.inbox.exists():
            return {"result": "PASS", "processed": 0, "items": []}
        for proposal_path in sorted(self.inbox.glob("*.json")):
            try:
                results.append(self.integrate(proposal_path))
            except Exception as exc:
                try:
                    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
                    event_path = _write_event(
                        self.ledger,
                        proposal,
                        {
                            "status": "INTEGRATION_FAILED",
                            "error_class": type(exc).__name__,
                            "error": str(exc)[:2000],
                            "proposal_mutated": False,
                        },
                    )
                    event = str(event_path)
                    prop_id = proposal.get("proposal_id")
                except Exception:
                    event = None
                    prop_id = proposal_path.stem
                results.append(
                    {
                        "result": "FAIL",
                        "status": "INTEGRATION_FAILED",
                        "proposal_id": prop_id,
                        "error": str(exc)[:2000],
                        "event_path": event,
                    }
                )
        ok = all(item["result"] == "PASS" for item in results)
        return {
            "result": "PASS" if ok else "FAIL",
            "processed": len(results),
            "items": results,
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 human-approved agent change integration broker")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--inbox", default="_agent-inbox/approved")
    ap.add_argument("--ledger", default="_agent-ledger")
    ap.add_argument("--digest-proposal", default=None)
    args = ap.parse_args()
    if args.digest_proposal:
        proposal = json.loads(Path(args.digest_proposal).read_text(encoding="utf-8"))
        print(proposal_digest(proposal))
        return 0
    report = FA3IntegrationBroker(args.repo, args.inbox, args.ledger).process_once()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
