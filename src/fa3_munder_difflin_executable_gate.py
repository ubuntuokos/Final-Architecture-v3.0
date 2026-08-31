#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

EXECUTABLE_GATE_ID = "FA3-GATE-MUNDER-DIFFLIN-001"
GATESET_ID = "FA3-MUNDER-DIFFLIN-GATESET-001"
PROVIDER_ID = "FA3-PROVIDER-MUNDER-DIFFLIN-001"
CAPABILITY_COUNT = 143

CASE_IDS = [
    "MD-001", "MD-002", "MD-003", "MD-004", "MD-005",
    "MD-006", "MD-007", "MD-008", "MD-009", "MD-010",
    "MD-011", "MD-012", "MD-013", "MD-014", "MD-015",
    "MD-016", "MD-017", "MD-018", "MD-019", "MD-020",
]

TELEMETRY_ALLOWLIST = {"event", "provider", "app_version", "status", "duration_ms"}
SENSITIVE_TELEMETRY_KEYS = {
    "prompt", "transcript", "file_path", "repo_name", "hostname",
    "email", "api_key", "token", "secret", "message_text",
}
CRITICAL_RISKS = {"DESTRUCTIVE", "SPEND", "SCOPE_CHANGE", "RELEASE", "CREDENTIAL", "UNRESOLVED_CONFLICT"}


class GateDenied(RuntimeError):
    pass


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _result(case_id: str, name: str, positive: bool, negative: bool, **evidence: Any) -> dict[str, Any]:
    ok = bool(positive and negative)
    return {
        "case_id": case_id,
        "name": name,
        "status": "PASS" if ok else "FAIL",
        "positive_case": bool(positive),
        "negative_case": bool(negative),
        "evidence": evidence,
    }


def provider_cannot_be_authority(provider_id: str, authority_owner: str) -> bool:
    return bool(provider_id and authority_owner and provider_id != authority_owner)


def worker_direct_shared_commit_allowed(actor: str, designated_committer: str) -> bool:
    return bool(actor and actor == designated_committer)


def atomic_publish(mailbox: Path, message_id: str, payload: dict[str, Any]) -> Path:
    if not message_id or "/" in message_id or ".." in message_id:
        raise GateDenied("invalid message id")
    mailbox.mkdir(parents=True, exist_ok=True)
    final = mailbox / f"{message_id}.json"
    temp = mailbox / f".{message_id}.{os.getpid()}.tmp"
    if final.exists():
        raise GateDenied("duplicate publication")
    temp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temp, final)
    return final


@dataclass
class ConsumerState:
    cursor: int = 0
    processed: set[str] | None = None

    def __post_init__(self) -> None:
        if self.processed is None:
            self.processed = set()

    def consume(self, message_id: str, sequence: int) -> str:
        assert self.processed is not None
        if not message_id or sequence < 0:
            return "DENY"
        if message_id in self.processed:
            return "NOOP"
        if sequence < self.cursor:
            return "DENY"
        self.processed.add(message_id)
        self.cursor = sequence + 1
        return "PROCESS"


def cursor_isolation_valid(a: ConsumerState, b: ConsumerState) -> bool:
    return a is not b and a.processed is not b.processed


def resolve_workspace_path(root: Path, requested: str, *, allow_missing_leaf: bool = True) -> Path:
    if not requested or Path(requested).is_absolute():
        raise GateDenied("path must be relative")
    rel = Path(requested)
    if ".." in rel.parts:
        raise GateDenied("path traversal denied")
    canonical_root = root.resolve(strict=True)
    candidate = canonical_root / rel
    parent = candidate.parent.resolve(strict=True)
    resolved = parent / candidate.name
    if resolved != canonical_root and canonical_root not in resolved.parents:
        raise GateDenied("workspace escape denied")
    if candidate.exists() or not allow_missing_leaf:
        actual = candidate.resolve(strict=True)
        if actual != canonical_root and canonical_root not in actual.parents:
            raise GateDenied("symlink escape denied")
        return actual
    return resolved


def renderer_host_call_allowed(*, direct_node_access: bool, through_typed_broker: bool, capability_scoped: bool) -> bool:
    return not direct_node_access and through_typed_broker and capability_scoped


def human_gate_allows(risk_class: str, approved: bool) -> bool:
    return approved if risk_class in CRITICAL_RISKS else True


@dataclass
class BudgetCircuitBreaker:
    budget: int
    used: int = 0
    state: str = "RUN"

    def charge(self, amount: int) -> str:
        if self.budget < 0 or amount < 0:
            self.state = "TERMINATE"
            return self.state
        self.used += amount
        ratio = self.used / max(self.budget, 1)
        if self.used > self.budget:
            self.state = "TERMINATE"
        elif ratio >= 0.9:
            self.state = "CONSTRAIN"
        elif ratio >= 0.75:
            self.state = "STEER"
        return self.state


def deterministic_stop(proc: subprocess.Popen[str], timeout: float = 2.0) -> bool:
    if proc.poll() is not None:
        return True
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)
    return proc.poll() is not None


def context_can_grant_capability(*, trust_class: str, requested_capability: str, delegated_capabilities: set[str]) -> bool:
    if trust_class not in {"UNTRUSTED_SCOPED_CONTEXT", "PROVIDER_LOCAL_WORKING_MEMORY"}:
        return False
    return requested_capability in delegated_capabilities


def telemetry_valid(payload: dict[str, Any]) -> bool:
    keys = set(payload)
    return keys <= TELEMETRY_ALLOWLIST and not (keys & SENSITIVE_TELEMETRY_KEYS)


def workspace_assignment_valid(mutating_agents: list[str], assignments: dict[str, str]) -> bool:
    roots = [assignments.get(agent, "") for agent in mutating_agents]
    return all(roots) and len(set(roots)) == len(roots)


def orchestrator_survives_provider_failure(providers: dict[str, Callable[[], str]]) -> dict[str, str]:
    results: dict[str, str] = {}
    for provider, callback in providers.items():
        try:
            results[provider] = callback()
        except Exception:
            results[provider] = "FAILED_ISOLATED"
    return results


def cleanup_ephemeral_worker(proc: subprocess.Popen[str], workspace: Path, pending_messages: list[str]) -> bool:
    stopped = deterministic_stop(proc)
    pending_messages.clear()
    if workspace.exists():
        for child in sorted(workspace.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        workspace.rmdir()
    return stopped and not workspace.exists() and not pending_messages


def capability_state_valid(state: str, *, implementation_present: bool, executable_evidence: bool) -> bool:
    if state == "DESIGNED":
        return True
    if state == "PLANNED":
        return not executable_evidence
    if state == "IMPLEMENTED":
        return implementation_present
    if state == "VERIFIED":
        return implementation_present and executable_evidence
    return False


def transition_evidence_valid(*, implementation_present: bool, transition_exercised: bool, evidence_status: str) -> bool:
    return implementation_present and transition_exercised and evidence_status == "PASS"


def fault_injection_valid(*, critical_path: bool, nominally_reachable: bool, fault_injected: bool, evidence_status: str) -> bool:
    if evidence_status != "PASS":
        return False
    if critical_path and not nominally_reachable:
        return fault_injected
    return True


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    cases.append(_result(
        "MD-001", "provider-cannot-be-authority",
        provider_cannot_be_authority(PROVIDER_ID, "FA3-AUTH-SECURITY-GOV-001"),
        not provider_cannot_be_authority(PROVIDER_ID, PROVIDER_ID),
    ))
    cases.append(_result(
        "MD-002", "agent-cannot-directly-commit-shared-state",
        worker_direct_shared_commit_allowed("FA3 Integration", "FA3 Integration"),
        not worker_direct_shared_commit_allowed("munder-agent-a", "FA3 Integration"),
    ))

    with tempfile.TemporaryDirectory(prefix="fa3-munder-mailbox-") as td:
        mailbox = Path(td)
        final = atomic_publish(mailbox, "msg-001", {"id": "msg-001", "body": "hello"})
        positive = final.is_file() and not list(mailbox.glob("*.tmp")) and json.loads(final.read_text())["id"] == "msg-001"
        try:
            atomic_publish(mailbox, "../escape", {"bad": True})
            negative = False
        except GateDenied:
            negative = True
        cases.append(_result("MD-003", "cross-agent-message-atomicity", positive, negative, published=str(final.name)))

    consumer = ConsumerState()
    first = consumer.consume("m1", 0)
    duplicate = consumer.consume("m1", 0)
    cases.append(_result(
        "MD-004", "duplicate-message-idempotency",
        first == "PROCESS" and duplicate == "NOOP",
        consumer.consume("", 1) == "DENY",
        cursor=consumer.cursor,
    ))

    a, b = ConsumerState(), ConsumerState()
    a.consume("a1", 0)
    independent = cursor_isolation_valid(a, b) and a.cursor == 1 and b.cursor == 0 and "a1" not in b.processed
    shared = ConsumerState()
    bad_a = bad_b = shared
    cases.append(_result(
        "MD-005", "consumer-cursor-isolation",
        independent,
        not cursor_isolation_valid(bad_a, bad_b),
    ))

    with tempfile.TemporaryDirectory(prefix="fa3-munder-workspace-") as td:
        root = Path(td)
        (root / "safe").mkdir()
        positive = resolve_workspace_path(root, "safe/file.txt") == (root / "safe/file.txt").resolve(strict=False)
        try:
            resolve_workspace_path(root, "../outside.txt")
            negative = False
        except GateDenied:
            negative = True
        cases.append(_result("MD-006", "workspace-root-escape-denied", positive, negative))

    with tempfile.TemporaryDirectory(prefix="fa3-munder-symlink-") as td:
        root = Path(td) / "root"
        outside = Path(td) / "outside"
        root.mkdir()
        outside.mkdir()
        (root / "inside").mkdir()
        os.symlink(outside, root / "link")
        positive = resolve_workspace_path(root, "inside/new.txt").parent == (root / "inside").resolve()
        try:
            resolve_workspace_path(root, "link/secret.txt")
            negative = False
        except GateDenied:
            negative = True
        cases.append(_result("MD-007", "symlink-path-revalidation", positive, negative))

    cases.append(_result(
        "MD-008", "renderer-direct-host-access-denied",
        renderer_host_call_allowed(direct_node_access=False, through_typed_broker=True, capability_scoped=True),
        not renderer_host_call_allowed(direct_node_access=True, through_typed_broker=False, capability_scoped=False),
    ))

    cases.append(_result(
        "MD-009", "destructive-operation-human-gate",
        human_gate_allows("READ_ONLY", approved=False) and human_gate_allows("DESTRUCTIVE", approved=True),
        not human_gate_allows("DESTRUCTIVE", approved=False),
    ))

    breaker = BudgetCircuitBreaker(100)
    state1, state2, state3 = breaker.charge(76), breaker.charge(15), breaker.charge(15)
    bad_breaker = BudgetCircuitBreaker(10)
    bad_breaker.charge(-1)
    cases.append(_result(
        "MD-010", "budget-overrun-circuit-breaker",
        (state1, state2, state3) == ("STEER", "CONSTRAIN", "TERMINATE"),
        bad_breaker.state == "TERMINATE",
        states=[state1, state2, state3],
    ))

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    stopped = deterministic_stop(proc)
    cases.append(_result(
        "MD-011", "deterministic-agent-stop",
        stopped and proc.poll() is not None,
        not (proc.poll() is None),
        returncode=proc.returncode,
    ))

    delegated = {"read_repo"}
    cases.append(_result(
        "MD-012", "untrusted-memory-cannot-grant-capabilities",
        context_can_grant_capability(
            trust_class="UNTRUSTED_SCOPED_CONTEXT",
            requested_capability="read_repo",
            delegated_capabilities=delegated,
        ),
        not context_can_grant_capability(
            trust_class="UNTRUSTED_SCOPED_CONTEXT",
            requested_capability="shell_root",
            delegated_capabilities=delegated,
        ),
    ))

    cases.append(_result(
        "MD-013", "secret-material-not-exported-to-telemetry",
        telemetry_valid({"event": "agent.completed", "provider": "codex", "status": "PASS"}),
        not telemetry_valid({"event": "agent.completed", "api_key": "secret"}),
    ))

    cases.append(_result(
        "MD-014", "telemetry-unknown-field-rejected",
        telemetry_valid({"event": "agent.started", "duration_ms": 12}),
        not telemetry_valid({"event": "agent.started", "arbitrary_free_form": "x"}),
    ))

    cases.append(_result(
        "MD-015", "concurrent-agent-workspace-collision-test",
        workspace_assignment_valid(["a", "b"], {"a": "wt-a", "b": "wt-b"}),
        not workspace_assignment_valid(["a", "b"], {"a": "shared", "b": "shared"}),
    ))

    results = orchestrator_survives_provider_failure({
        "good": lambda: "PASS",
        "bad": lambda: (_ for _ in ()).throw(RuntimeError("provider failed")),
        "later": lambda: "PASS",
    })
    cases.append(_result(
        "MD-016", "provider-failure-does-not-collapse-orchestrator",
        results == {"good": "PASS", "bad": "FAILED_ISOLATED", "later": "PASS"},
        results.get("later") != "FAILED_ISOLATED",
        provider_results=results,
    ))

    with tempfile.TemporaryDirectory(prefix="fa3-munder-cleanup-parent-") as td:
        workspace = Path(td) / "worker"
        workspace.mkdir()
        (workspace / "artifact.tmp").write_text("temporary", encoding="utf-8")
        messages = ["pending"]
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        cleaned = cleanup_ephemeral_worker(proc, workspace, messages)
        cases.append(_result(
            "MD-017", "ephemeral-worker-cleanup",
            cleaned and proc.poll() is not None,
            not workspace.exists() and not messages,
        ))

    cases.append(_result(
        "MD-018", "planned-capability-cannot-pass-as-implemented",
        capability_state_valid("IMPLEMENTED", implementation_present=True, executable_evidence=False),
        not capability_state_valid("IMPLEMENTED", implementation_present=False, executable_evidence=True)
        and not capability_state_valid("VERIFIED", implementation_present=True, executable_evidence=False),
    ))

    cases.append(_result(
        "MD-019", "update-transition-evidence-required",
        transition_evidence_valid(implementation_present=True, transition_exercised=True, evidence_status="PASS"),
        not transition_evidence_valid(implementation_present=True, transition_exercised=False, evidence_status="PASS"),
    ))

    cases.append(_result(
        "MD-020", "critical-error-path-fault-injection",
        fault_injection_valid(critical_path=True, nominally_reachable=False, fault_injected=True, evidence_status="PASS"),
        not fault_injection_valid(critical_path=True, nominally_reachable=False, fault_injected=False, evidence_status="PASS"),
    ))

    ids = [case["case_id"] for case in cases]
    passed = sum(case["status"] == "PASS" for case in cases)
    return {
        "schema": "fa3.munder-difflin-executable-regression-report.v1",
        "gate_id": EXECUTABLE_GATE_ID,
        "gateset_id": GATESET_ID,
        "provider_id": PROVIDER_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ids == CASE_IDS and passed == len(CASE_IDS) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "case_ids_exact": ids == CASE_IDS,
        "cases": cases,
    }


def canonical_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    record_path = root / "canonical/FA3-GATE-MUNDER-DIFFLIN-001.json"
    enforcement_path = root / "canonical/munder-difflin-enforcement.json"
    policy_path = root / "canonical/enforcement-policy.json"
    for path in (record_path, enforcement_path, policy_path):
        if not path.is_file():
            findings.append({"code": "MD-CANON-001", "message": f"missing {path.relative_to(root)}"})
    if findings:
        return {"result": "FAIL", "findings": findings}
    record = json.loads(record_path.read_text(encoding="utf-8"))
    enforcement = json.loads(enforcement_path.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if not (
        record.get("id") == EXECUTABLE_GATE_ID
        and record.get("gateset_id") == GATESET_ID
        and record.get("provider_id") == PROVIDER_ID
        and record.get("fail_closed") is True
        and record.get("case_ids") == CASE_IDS
        and record.get("regression_case_count") == 20
        and record.get("new_capability") is False
        and record.get("new_architectural_authority") is False
        and record.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append({"code": "MD-CANON-002", "message": "executable gate canonical record drift"})
    if not (
        enforcement.get("executable_gate_id") == EXECUTABLE_GATE_ID
        and enforcement.get("regression_case_count") == 20
        and enforcement.get("executable_case_ids") == CASE_IDS
    ):
        findings.append({"code": "MD-CANON-003", "message": "enforcement executable binding drift"})
    if policy.get("munder_difflin_executable_gate_id") != EXECUTABLE_GATE_ID:
        findings.append({"code": "MD-CANON-004", "message": "global policy executable gate binding drift"})
    if policy.get("munder_difflin_executable_case_ids") != CASE_IDS:
        findings.append({"code": "MD-CANON-005", "message": "global policy executable case set drift"})
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    canonical = canonical_check(root)
    regressions = run_regressions()
    ok = canonical["result"] == "PASS" and regressions["result"] == "PASS"
    report = {
        "schema": "fa3.munder-difflin-executable-gate-report.v1",
        "gate_id": EXECUTABLE_GATE_ID,
        "gateset_id": GATESET_ID,
        "provider_id": PROVIDER_ID,
        "result": "PASS" if ok else "FAIL",
        "canonical": canonical,
        "regressions": regressions,
        "current_host_provider_runtime_claim": False,
        "promotion_effect": "EXECUTABLE_COORDINATION_AND_SECURITY_INVARIANT_EVIDENCE_ONLY",
    }
    _write_json(root / "reports/munder-difflin-executable-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3-GATE-MUNDER-DIFFLIN-001 executable regression gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
