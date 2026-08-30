#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_developer_agent_coordination import (
    RUNTIME_ID,
    RUNTIME_VERSION,
    cleanup_state_valid,
    commit_intent_allowed,
    message_hop_action,
    mutation_allowed,
    provider_authority_assignment_allowed,
    run_reference_e2e,
    workspace_plan_valid,
)

GATE_ID = "FA3-DEVELOPER-AGENT-COORDINATION-GATESET-001"
PROFILE_ID = "FA3-AGENT-EXEC-001"
CONTRACT_ID = "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
CONFORMANCE_ID = "FA3-DEVELOPER-AGENT-COORDINATION-RUNTIME-CONFORMANCE-001"
DECISION_ID = "FA3-DEC-DEVELOPER-AGENT-COORDINATION-2026-08-30"
CAPABILITY_COUNT = 143

P0_RULES = [
    "DAC_EXPLICIT_TYPED_TASK_AND_DELEGATION",
    "DAC_ISOLATED_MUTATING_WORKSPACES",
    "DAC_SINGLE_WRITER_COORDINATION_STATE",
    "DAC_SINGLE_INTEGRATION_COMMITTER",
    "DAC_ATOMIC_IDEMPOTENT_MESSAGING",
    "DAC_BOUNDED_MESSAGE_HOPS",
    "DAC_PROVIDER_ADAPTER_NON_AUTHORITY",
    "DAC_CRITICAL_ACTION_HUMAN_ESCALATION",
    "DAC_STEER_CONSTRAIN_TERMINATE",
    "DAC_READ_DIFF_CHECK_BEFORE_INTEGRATION",
    "DAC_WORKER_DIRECT_MAIN_COMMIT_DENIED",
    "DAC_CONFLICT_DETECTION_FAIL_CLOSED",
    "DAC_EXECUTION_EVIDENCE_ATTRIBUTABLE",
    "DAC_EPHEMERAL_WORKER_CLEANUP_REQUIRED",
    "DAC_REFERENCE_E2E_POSITIVE_AND_NEGATIVE_PASS",
    "DAC_REFERENCE_E2E_NOT_CURRENT_HOST_PROVIDER_PROMOTION",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-AGENT-EXEC-001.json",
        "contracts": root / "canonical/contracts/FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001.json",
        "conformance": root / "canonical/FA3-DEVELOPER-AGENT-COORDINATION-RUNTIME-CONFORMANCE-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-DEVELOPER-AGENT-COORDINATION-2026-08-30.json",
        "enforcement": root / "canonical/developer-agent-coordination-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("DAC-REF-001", f"missing {name} artifact"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile = _load(paths["profile"])
    contracts = _load(paths["contracts"])
    conformance = _load(paths["conformance"])
    decision = _load(paths["decision"])
    enforcement = _load(paths["enforcement"])
    policy = _load(paths["policy"])

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("version") == "1.1.0"
        and CONTRACT_ID in profile.get("contracts", [])
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
    ):
        findings.append(_finding("DAC-REF-002", "Agent Execution profile extension drift"))

    required_contracts = {
        "AgentTask", "AgentDelegation", "WorkspaceLease", "AgentMessage", "AgentResult",
        "HumanEscalation", "CircuitBreakerAction", "IntegrationIntent", "ExecutionEvidence",
    }
    if not (
        contracts.get("id") == CONTRACT_ID
        and contracts.get("parent_profile") == PROFILE_ID
        and contracts.get("provider_neutral") is True
        and required_contracts.issubset(set(contracts.get("contracts", [])))
        and contracts.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(_finding("DAC-REF-003", "Coordination contract family drift"))

    e2e = conformance.get("executable_e2e", {})
    if not (
        conformance.get("id") == CONFORMANCE_ID
        and conformance.get("runtime_id") == RUNTIME_ID
        and conformance.get("runtime_version") == RUNTIME_VERSION
        and conformance.get("provider_neutral") is True
        and e2e.get("required") is True
        and e2e.get("current_host_production_claim") is False
        and e2e.get("pass_status") == "CI_REFERENCE_RUNTIME_E2E_PASS"
    ):
        findings.append(_finding("DAC-REF-004", "Reference runtime conformance drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("parent_profile") == PROFILE_ID
        and decision.get("contract_family") == CONTRACT_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("provider_dependency_created") is False
    ):
        findings.append(_finding("DAC-REF-005", "Canonical coordination decision drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("contract_family") == CONTRACT_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("p0_invariants") == P0_RULES
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and enforcement.get("current_host_production_promotion_claim") is False
    ):
        findings.append(_finding("DAC-REF-006", "Coordination enforcement drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("DAC-REF-007", "Coordination gate missing from global enforcement policy"))
    if policy.get("developer_agent_coordination_contract_id") != CONTRACT_ID:
        findings.append(_finding("DAC-REF-008", "Global coordination contract binding drift"))
    if policy.get("developer_agent_coordination_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("DAC-REF-009", "Global coordination P0 rules drift"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases = {
        "duplicate_mutating_workspace_denied": not workspace_plan_valid(
            {"a": "same", "b": "same"}, ["a", "b"]
        ),
        "worker_direct_main_commit_denied": not commit_intent_allowed(
            actor_role="WORKER", target_branch="main"
        ),
        "integration_main_commit_allowed": commit_intent_allowed(
            actor_role="FA3_INTEGRATION", target_branch="main"
        ),
        "hop_overflow_terminates": message_hop_action(
            hop=4, max_hops=4, act="request"
        ) == "TERMINATE",
        "destructive_without_approval_denied": not mutation_allowed(
            risk_class="DESTRUCTIVE", approved=False
        ),
        "cleanup_leak_denied": not cleanup_state_valid(
            live_processes=1, worktrees=0, active_leases=0, pending_messages=0
        ),
        "provider_cannot_own_authority": not provider_authority_assignment_allowed(
            provider_id="provider-x", authority_owner="provider-x"
        ),
    }
    passed = sum(cases.values())
    return {
        "schema": "fa3.developer-agent-coordination-regressions.v1",
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
    }


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    e2e = run_reference_e2e()
    _write(root / "reports/developer-agent-coordination-e2e-report.json", e2e)
    ok = (
        reference["result"] == "PASS"
        and regressions["result"] == "PASS"
        and e2e["result"] == "PASS"
        and e2e["status"] == "CI_REFERENCE_RUNTIME_E2E_PASS"
        and e2e["current_host_production_claim"] is False
    )
    report = {
        "schema": "fa3.developer-agent-coordination-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "runtime_id": RUNTIME_ID,
        "runtime_version": RUNTIME_VERSION,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "regressions": regressions,
        "e2e": {
            "result": e2e["result"],
            "status": e2e["status"],
            "runtime_sha256": e2e["runtime_sha256"],
            "negative_cases": e2e["negative_cases"],
            "positive_worker_count": e2e["positive_flow"].get("worker_count"),
            "integration_author": e2e["positive_flow"].get("integration_author"),
            "cleanup": e2e["positive_flow"].get("cleanup"),
            "current_host_production_claim": e2e["current_host_production_claim"],
        },
        "promotion_effect": "REFERENCE_RUNTIME_COORDINATION_EVIDENCE_ONLY_EXTERNAL_PROVIDER_PROMOTION_SEPARATE",
    }
    _write(root / "reports/developer-agent-coordination-gate-report.json", report)
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
