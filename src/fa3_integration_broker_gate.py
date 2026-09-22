#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_integration_broker import (
    FA3IntegrationBroker,
    IntegrationDenied,
    protected_path,
    proposal_digest,
    validate_approval,
    validate_mutations,
)

GATE_ID = "FA3-INTEGRATION-BROKER-GATESET-001"
BROKER_ID = "FA3-INTEGRATION-BROKER-001"
CONTRACT_ID = "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-INTEGRATION-BROKER-2026-09-19"
CAPABILITY_COUNT = module_active_capability_count(__file__)

P0_RULES = [
    "INTEGRATION_APPROVAL_REQUIRED_AND_DIGEST_BOUND",
    "APPROVED_PROPOSAL_IMMUTABLE",
    "APPROVED_BASE_SHA_PINNED",
    "ISOLATED_GIT_WORKTREE_REQUIRED",
    "PROPOSAL_PATCH_PATHS_DECLARED_AND_VALIDATED",
    "PATH_TRAVERSAL_AND_SYMLINK_ESCAPE_DENIED",
    "TRUSTED_GATE_EXECUTES_FROM_APPROVED_BASE",
    "CANDIDATE_GATE_ALSO_REQUIRED",
    "GATE_SELF_MODIFICATION_DENIED",
    "EXPLICIT_STAGING_ONLY_NO_GIT_ADD_DOT",
    "PROTECTED_MAIN_UPDATE_FORBIDDEN",
    "CANDIDATE_BRANCH_PR_SUBMISSION_REQUIRED",
    "REPOSITORY_INTEGRATION_LOCK_REQUIRED",
    "CLEAN_MAIN_WORKTREE_REQUIRED",
    "INTEGRATION_EVIDENCE_APPEND_ONLY",
    "FAILURE_DOES_NOT_MUTATE_PROPOSAL",
    "AGENT_GIT_CREDENTIALS_FORBIDDEN",
    "DIRECT_AGENT_MAIN_WRITE_FORBIDDEN",
    "CURRENT_HOST_SECRET_NEGATIVE_GATE_FAIL_CLOSED",
    "CAPABILITY_AND_AUTHORITY_COUNT_INVARIANT",
    "REFERENCE_E2E_POSITIVE_AND_NEGATIVE_REQUIRED",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    paths = {
        "record": root / "canonical/FA3-GATE-INTEGRATION-BROKER-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-INTEGRATION-BROKER-2026-09-19.json",
        "enforcement": root / "canonical/integration-broker-enforcement.json",
        "proposal_schema": root / "canonical/schemas/agent-task-proposal.v1.json",
        "event_schema": root / "canonical/schemas/agent-integration-event.v1.json",
        "contract": root / "canonical/contracts/FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001.json",
        "policy": root / "canonical/enforcement-policy.json",
        "broker": root / "src/fa3_integration_broker.py",
        "wrapper": root / "bin/fa3-integration-committer.py",
        "secret_gate": root / "src/fa3_podman_secret_negative_gate.py",
        "secret_gate_record": root / "canonical/FA3-GATE-PODMAN-SECRET-ISOLATION-CURRENT-HOST-001.json",
        "secret_conformance": root / "canonical/FA3-PODMAN-SECRET-ISOLATION-CURRENT-HOST-CONFORMANCE-001.json",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("IB-REF-001", f"missing {name} artifact"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    record = _load(paths["record"])
    decision = _load(paths["decision"])
    enforcement = _load(paths["enforcement"])
    contract = _load(paths["contract"])
    policy = _load(paths["policy"])
    proposal_schema = _load(paths["proposal_schema"])
    event_schema = _load(paths["event_schema"])
    secret_gate_record = _load(paths["secret_gate_record"])
    secret_conformance = _load(paths["secret_conformance"])
    source = paths["broker"].read_text(encoding="utf-8")

    if not (
        record.get("id") == "FA3-GATE-INTEGRATION-BROKER-001"
        and record.get("gateset_id") == GATE_ID
        and record.get("priority") == "P0"
        and record.get("fail_closed") is True
        and record.get("capability_count") == CAPABILITY_COUNT
        and record.get("new_capabilities") == 0
        and record.get("new_architectural_authorities") == 0
    ):
        findings.append(_finding("IB-REF-002", "integration broker gate record drift"))
    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("contract_family") == CONTRACT_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("capability_id") == "CAP-028"
    ):
        findings.append(_finding("IB-REF-003", "integration broker decision drift"))
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and enforcement.get("p0_invariants") == P0_RULES
    ):
        findings.append(_finding("IB-REF-004", "integration broker enforcement drift"))
    required_contracts = {
        "AgentChangeProposal", "HumanApprovalReceipt", "IntegrationEvidence", "IntegrationLedgerEvent"
    }
    if not required_contracts.issubset(set(contract.get("contracts", []))):
        findings.append(_finding("IB-REF-005", "developer-agent contract family missing broker contracts"))
    if not (
        policy.get("integration_broker_gate_id") == GATE_ID
        and policy.get("integration_broker_enforcement_class") == "P0_CROSS_CUTTING_STATIC_GATE"
        and policy.get("integration_broker_global_static_required") is True
    ):
        findings.append(_finding("IB-REF-006", "integration broker explicit global policy binding drift"))
    if policy.get("integration_broker_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("IB-REF-007", "global integration broker P0 rules drift"))
    if proposal_schema.get("$id") != "https://fa3.internal/schemas/agent-task-proposal.v1.json":
        findings.append(_finding("IB-REF-008", "proposal schema identity drift"))
    if event_schema.get("$id") != "https://fa3.internal/schemas/agent-integration-event.v1.json":
        findings.append(_finding("IB-REF-009", "event schema identity drift"))

    if not (
        secret_gate_record.get("gateset_id") == "FA3-PODMAN-SECRET-ISOLATION-CURRENT-HOST-GATESET-001"
        and secret_gate_record.get("capability_id") == "CAP-028"
        and secret_gate_record.get("fail_closed") is True
        and secret_gate_record.get("current_host_runner_required") is True
        and secret_gate_record.get("current_host_runtime_promotion_claim") is False
        and secret_conformance.get("id") == "FA3-PODMAN-SECRET-ISOLATION-CURRENT-HOST-CONFORMANCE-001"
        and secret_conformance.get("capability_id") == "CAP-028"
        and secret_conformance.get("status") == "EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING"
        and secret_conformance.get("missing_runtime_or_secret_precondition") == "BLOCKED_NOT_SKIP"
        and secret_conformance.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(_finding("IB-REF-012", "Podman secret-isolation current-host binding drift"))

    required_source_tokens = [
        "worktree", "apply", "--check", "PR_READY", "protected_branch_submission_required",
        "proposal_path.read_bytes() != proposal_bytes", "LOCK_EX",
        "GIT_TERMINAL_PROMPT", "core.hooksPath=/dev/null",
    ]
    if not all(token in source for token in required_source_tokens):
        findings.append(_finding("IB-REF-010", "broker hardening source invariants missing"))
    if '"git", "add", "."' in source:
        findings.append(_finding("IB-REF-011", "forbidden git add dot reintroduced"))
    if '"update-ref", "refs/heads/main"' in source or '"reset", "--hard", result_sha' in source:
        findings.append(_finding("IB-REF-013", "broker may not update the protected main ref"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def _init_repo(repo: Path) -> str:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "FA3 Fixture"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@localhost"], check=True)
    (repo / "work").mkdir()
    (repo / "work/item.txt").write_text("baseline\n", encoding="utf-8")
    (repo / ".gitignore").write_text("/_agent-inbox/\n/_agent-ledger/\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src/fa3_enforce.py").write_text(
        "#!/usr/bin/env python3\n"
        "import argparse, pathlib\n"
        "p=argparse.ArgumentParser(); p.add_argument('--root'); p.add_argument('command'); a=p.parse_args()\n"
        "ok=(pathlib.Path(a.root)/'work/item.txt').read_text()=='approved\\n' and a.command=='static'\n"
        "raise SystemExit(0 if ok else 2)\n",
        encoding="utf-8",
    )
    (repo / "bin").mkdir()
    executable = repo / "bin/fa3-enforce"
    executable.write_text(
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "[ \"$1\" = static ]\n"
        "[ \"$(cat work/item.txt)\" = approved ]\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    subprocess.run(["git", "-C", str(repo), "add", "--", ".gitignore", "work/item.txt", "src/fa3_enforce.py", "bin/fa3-enforce"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "baseline"], check=True, capture_output=True, text=True)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def run_reference_e2e() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="fa3-integration-broker-e2e-") as td:
        root = Path(td)
        repo = root / "repo"
        base = _init_repo(repo)
        approved = repo / "_agent-inbox/approved"
        approved.mkdir(parents=True)
        proposal = {
            "schema": "fa3.agent-task-proposal.v1",
            "proposal_id": "prop-20260919-001",
            "origin_agent": "FA3-PROVIDER-TEST-001",
            "context": {
                "task_scope": "reference broker integration",
                "target_capability": "CAP-028",
                "base_commit": base,
                "declared_write_set": ["work/item.txt"],
                "test_plan": ["trusted static gate", "candidate static gate"],
            },
            "approval_state": {
                "status": "APPROVED_BY_HUMAN",
                "approved_by": "reference-human",
                "approved_at": "2026-09-19T00:00:00Z",
                "approved_base_sha": base,
                "proposal_digest_sha256": "sha256:" + "0" * 64,
            },
            "mutations": [{
                "file_path": "work/item.txt",
                "diff": (
                    "diff --git a/work/item.txt b/work/item.txt\n"
                    "--- a/work/item.txt\n"
                    "+++ b/work/item.txt\n"
                    "@@ -1 +1 @@\n"
                    "-baseline\n"
                    "+approved\n"
                ),
            }],
            "circuit_breaker_limits": {
                "max_execution_seconds": 300,
                "max_file_mutations": 1,
            },
        }
        proposal["approval_state"]["proposal_digest_sha256"] = proposal_digest(proposal)
        path = approved / "prop-20260919-001.json"
        path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
        before = path.read_bytes()
        result = FA3IntegrationBroker(repo).process_once()
        after = path.read_bytes()
        candidate_branch = "fa3/integration/prop-20260919-001"
        candidate_text = subprocess.run(
            ["git", "-C", str(repo), "show", f"{candidate_branch}:work/item.txt"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        prepared = (
            result["result"] == "PASS"
            and result["items"][0]["status"] == "PR_READY"
            and (repo / "work/item.txt").read_text(encoding="utf-8") == "baseline\n"
            and candidate_text == "approved\n"
            and before == after
        )

        tampered = json.loads(json.dumps(proposal))
        tampered["context"]["task_scope"] = "tampered"
        tamper_denied = validate_approval(tampered)[0] is False
        protected_denied = protected_path("bin/fa3-enforce")
        mismatch_denied = False
        bad = json.loads(json.dumps(proposal))
        bad["mutations"][0]["file_path"] = "work/other.txt"
        try:
            validate_mutations(repo, bad)
        except IntegrationDenied:
            mismatch_denied = True
        negatives = {
            "digest_tamper_denied": tamper_denied,
            "trusted_gate_self_modification_denied": protected_denied,
            "declared_patch_path_mismatch_denied": mismatch_denied,
        }
        ok = prepared and all(negatives.values())
        return {
            "schema": "fa3.integration-broker-reference-e2e.v1",
            "result": "PASS" if ok else "FAIL",
            "status": "CI_REFERENCE_RUNTIME_E2E_PASS" if ok else "FAIL",
            "positive_flow": {
                "pr_ready": prepared,
                "main_unchanged": (repo / "work/item.txt").read_text(encoding="utf-8") == "baseline\n",
                "proposal_immutable": before == after,
            },
            "negative_cases": negatives,
            "current_host_production_claim": False,
        }


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    e2e = run_reference_e2e()
    ok = reference["result"] == "PASS" and e2e["result"] == "PASS"
    report = {
        "schema": "fa3.integration-broker-gate-report.v1",
        "gate_id": GATE_ID,
        "broker_id": BROKER_ID,
        "contract_id": CONTRACT_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "e2e": e2e,
        "current_host_secret_gate": "FA3-PODMAN-SECRET-ISOLATION-CURRENT-HOST-GATESET-001",
        "current_host_secret_pass_claimed": False,
        "promotion_effect": "REFERENCE_BROKER_INVARIANTS_ONLY_CURRENT_HOST_SECRET_PROOF_SEPARATE",
    }
    _write(root / "reports/integration-broker-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
