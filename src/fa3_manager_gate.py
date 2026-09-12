#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from fa3_manager import ManagerInputError, build_management_projection, self_check

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "profile": ROOT / "canonical/profiles/FA3-MANAGER-001.json",
    "contracts": ROOT / "canonical/contracts/FA3-MANAGER-CONTRACTS-001.json",
    "provider": ROOT / "canonical/providers/FA3-PROVIDER-MANAGER-LOCAL-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-MANAGER-2026-09-12.json",
    "enforcement": ROOT / "canonical/manager-enforcement.json",
    "conformance": ROOT / "canonical/FA3-MANAGER-CONFORMANCE-MATRIX-001.json",
    "runtime": ROOT / "canonical/FA3-MANAGER-RUNTIME-CONFORMANCE-001.json",
    "gate": ROOT / "canonical/FA3-GATE-MANAGER-001.json",
    "implementation": ROOT / "src/fa3_manager.py",
}
FORBIDDEN_IMPLEMENTATION_TOKENS = ["subprocess.", "os.system(", "os.popen(", "pty.spawn(", "sudo ", "pkexec"]
MANDATORY_RULES = {
    "MANAGER_PROVIDER_NEUTRAL_MANAGEMENT_OVERLAY",
    "MANAGER_NOT_ARCHITECTURAL_OR_EXECUTION_AUTHORITY",
    "MANAGER_DIRECT_TOOL_AND_AGENT_EXECUTION_FORBIDDEN",
    "MANAGER_TYPED_DELEGATION_REQUIRED_FOR_ACTIONABLE_WORK",
    "MANAGER_WORK_STATE_MACHINE_REQUIRED",
    "MANAGER_VERIFIED_REQUIRES_ACCEPTANCE_AND_EVIDENCE",
    "MANAGER_DONE_WITHOUT_EVIDENCE_FORBIDDEN",
    "MANAGER_DEPENDENCY_GRAPH_MUST_BE_ACYCLIC",
    "MANAGER_BLOCKED_STATE_MUST_PRESERVE_BLOCKER_PROVENANCE",
    "MANAGER_CAPABILITY_PROVIDER_RESOLUTION_IS_PROJECTION_ONLY",
    "MANAGER_KNOWLEDGE_GAPS_DELEGATE_TO_MENTOR",
    "MANAGER_COACHING_DELEGATES_TO_COACH",
    "MANAGER_HUMAN_APPROVAL_BOUNDARIES_PRESERVED",
    "MANAGER_CANONICAL_REGISTRY_AND_DECISION_AUTHORITY_UNCHANGED",
    "MANAGER_CURRENT_HOST_PROMOTION_REQUIRES_FRESH_EVIDENCE",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    failures: list[str] = []
    for name, path in REQUIRED.items():
        if not path.exists():
            failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures:
        return failures

    profile = load_json(REQUIRED["profile"])
    contracts = load_json(REQUIRED["contracts"])
    provider = load_json(REQUIRED["provider"])
    decision = load_json(REQUIRED["decision"])
    enforcement = load_json(REQUIRED["enforcement"])
    conformance = load_json(REQUIRED["conformance"])
    runtime = load_json(REQUIRED["runtime"])
    gate = load_json(REQUIRED["gate"])

    checks = [
        (profile.get("id") == "FA3-MANAGER-001", "profile-id"),
        (profile.get("priority") == "P0" and profile.get("requirement") == "MUST", "profile-p0-must"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        (profile.get("role_boundaries", {}).get("knowledge_gap_delegation") == "FA3-MENTOR-001", "mentor-boundary"),
        (profile.get("role_boundaries", {}).get("coaching_delegation") == "FA3-COACH-001", "coach-boundary"),
        (contracts.get("provider_neutral") is True, "contracts-provider-neutral"),
        (contracts.get("execution_model", {}).get("direct_tool_execution") == "FORBIDDEN", "contracts-no-direct-tool-exec"),
        (contracts.get("execution_model", {}).get("direct_agent_execution") == "FORBIDDEN", "contracts-no-direct-agent-exec"),
        (contracts.get("state_model", {}).get("implicit_done") == "FORBIDDEN", "contracts-no-implicit-done"),
        (contracts.get("state_model", {}).get("verified_requires_evidence_reference") is True, "contracts-evidence-closure"),
        (provider.get("architectural_authority") is False, "provider-no-authority"),
        (provider.get("current_host_promotion_claimed") is False, "provider-no-runtime-claim"),
        (decision.get("new_capabilities") == 0, "decision-no-new-capability"),
        (decision.get("new_architectural_authorities") == 0, "decision-no-new-authority"),
        (decision.get("capability_count_after") == 143, "decision-capability-count"),
        (decision.get("conformance_matrix_id") == "FA3-MANAGER-CONFORMANCE-MATRIX-001", "decision-conformance-link"),
        (enforcement.get("fail_closed") is True, "enforcement-fail-closed"),
        (enforcement.get("mandatory_rule_count") == 15, "enforcement-rule-count"),
        (set(enforcement.get("rules", [])) == MANDATORY_RULES, "enforcement-rule-set"),
        (conformance.get("decision_ref") == "FA3-DEC-MANAGER-2026-09-12", "conformance-decision-link"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-not-falsely-promoted"),
        (runtime.get("production_admitted") is False, "runtime-production-not-admitted"),
        (runtime.get("evidence_present") is False, "runtime-evidence-not-fabricated"),
        (gate.get("fail_closed") is True and gate.get("rule_count") == 15, "gate-fail-closed"),
        (gate.get("current_host_runtime_required_for_runtime_promotion") is True, "gate-runtime-evidence-required"),
        (gate.get("capability_count_after") == 143, "gate-capability-count"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    implementation = REQUIRED["implementation"].read_text(encoding="utf-8")
    for token in FORBIDDEN_IMPLEMENTATION_TOKENS:
        if token in implementation:
            failures.append(f"implementation-forbidden-token:{token}")

    try:
        self_check()
        projection = build_management_projection({
            "mode": "PLAN",
            "objective": "Verify Manager authority boundaries",
            "work_items": [{"id": "w1", "title": "Action", "state": "READY"}],
            "knowledge_gap": True,
            "coaching_needed": True,
            "actionable_request": True,
        })
        if projection.get("status") != "MANAGEMENT_PROJECTION_ONLY":
            failures.append("runtime-projection-only")
        if projection.get("authority", {}).get("direct_execution_allowed") is not False:
            failures.append("runtime-direct-execution-denial")
        kinds = {item.get("kind") for item in projection.get("delegations", [])}
        if kinds != {"MENTOR", "COACH", "ACTION"}:
            failures.append("runtime-delegation-boundary")
        try:
            build_management_projection({
                "mode": "VERIFY_CLOSURE",
                "objective": "Reject false closure",
                "work_items": [{"id": "w1", "title": "No evidence", "state": "VERIFIED", "acceptance_criteria": ["done"], "acceptance_met": True}],
            })
            failures.append("runtime-verified-without-evidence-accepted")
        except ManagerInputError:
            pass
        try:
            build_management_projection({
                "mode": "PLAN",
                "objective": "Reject cycle",
                "work_items": [
                    {"id": "a", "title": "A", "depends_on": ["b"]},
                    {"id": "b", "title": "B", "depends_on": ["a"]},
                ],
            })
            failures.append("runtime-dependency-cycle-accepted")
        except ManagerInputError:
            pass
    except Exception as exc:
        failures.append(f"runtime-self-check:{type(exc).__name__}:{exc}")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 Manager gate: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("FA3 Manager gate: PASS")
    print("profile=FA3-MANAGER-001 capabilities=143 new_authorities=0 runtime=PENDING_CURRENT_HOST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
