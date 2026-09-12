#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from fa3_coach import CoachInputError, build_proposal, self_check

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "profile": ROOT / "canonical/profiles/FA3-COACH-001.json",
    "contracts": ROOT / "canonical/contracts/FA3-COACH-CONTRACTS-001.json",
    "provider": ROOT / "canonical/providers/FA3-PROVIDER-COACH-LOCAL-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-COACH-2026-09-12.json",
    "enforcement": ROOT / "canonical/coach-enforcement.json",
    "conformance": ROOT / "canonical/FA3-COACH-CONFORMANCE-MATRIX-001.json",
    "runtime": ROOT / "canonical/FA3-COACH-RUNTIME-CONFORMANCE-001.json",
    "gate": ROOT / "canonical/FA3-GATE-COACH-001.json",
    "implementation": ROOT / "src/fa3_coach.py",
}
FORBIDDEN_IMPLEMENTATION_TOKENS = [
    "subprocess.",
    "os.system(",
    "os.popen(",
    "pty.spawn(",
    "sudo ",
    "pkexec",
]
MANDATORY_RULES = {
    "COACH_ADVISORY_AND_PROPOSAL_ONLY",
    "COACH_USER_GOAL_OWNERSHIP_REQUIRED",
    "COACH_EXPLICIT_COMMITMENT_REQUIRED_FOR_ACCOUNTABILITY_TRACKING",
    "COACH_DIRECT_TOOL_AND_AGENT_EXECUTION_FORBIDDEN",
    "COACH_TYPED_MCP_OR_AGENT_EXECUTION_DELEGATION_REQUIRED_FOR_ACTIONS",
    "COACH_KNOWLEDGE_AND_SKILL_GAPS_DELEGATE_TO_MENTOR",
    "COACH_FACT_EVIDENCE_INFERENCE_SEPARATION_REQUIRED",
    "COACH_COERCION_SHAMING_MANIPULATION_FORBIDDEN",
    "COACH_IDENTITY_SCORING_AND_SENSITIVE_TRAIT_INFERENCE_FORBIDDEN",
    "COACH_MEDICAL_THERAPY_DIAGNOSIS_AUTHORITY_FORBIDDEN",
    "COACH_SILENT_MEMORY_AND_CROSS_WORKSPACE_PERSISTENCE_FORBIDDEN",
    "COACH_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
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
        (profile.get("id") == "FA3-COACH-001", "profile-id"),
        (profile.get("priority") == "P0" and profile.get("requirement") == "MUST", "profile-p0-must"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        (profile.get("mentor_boundary", {}).get("knowledge_gap_delegation") == "FA3-MENTOR-001", "mentor-boundary"),
        (contracts.get("provider_neutral") is True, "contracts-provider-neutral"),
        (contracts.get("execution_model", {}).get("direct_tool_execution") == "FORBIDDEN", "contracts-no-direct-tool-exec"),
        (contracts.get("execution_model", {}).get("direct_agent_execution") == "FORBIDDEN", "contracts-no-direct-agent-exec"),
        (contracts.get("state_model", {}).get("goal_owner") == "USER", "contracts-user-goal-owner"),
        (provider.get("architectural_authority") is False, "provider-no-authority"),
        (provider.get("current_host_promotion_claimed") is False, "provider-no-runtime-claim"),
        (decision.get("new_capabilities") == 0, "decision-no-new-capability"),
        (decision.get("new_architectural_authorities") == 0, "decision-no-new-authority"),
        (decision.get("capability_count_after") == 143, "decision-capability-count"),
        (decision.get("conformance_matrix_id") == "FA3-COACH-CONFORMANCE-MATRIX-001", "decision-conformance-link"),
        (enforcement.get("fail_closed") is True, "enforcement-fail-closed"),
        (enforcement.get("mandatory_rule_count") == 12, "enforcement-rule-count"),
        (set(enforcement.get("rules", [])) == MANDATORY_RULES, "enforcement-rule-set"),
        (conformance.get("decision_ref") == "FA3-DEC-COACH-2026-09-12", "conformance-decision-link"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-not-falsely-promoted"),
        (runtime.get("production_admitted") is False, "runtime-production-not-admitted"),
        (runtime.get("evidence_present") is False, "runtime-evidence-not-fabricated"),
        (gate.get("fail_closed") is True and gate.get("rule_count") == 12, "gate-fail-closed"),
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
        proposal = build_proposal(
            {
                "mode": "PLAN",
                "goal": "Verify Coach delegation boundaries",
                "knowledge_gap": True,
                "actionable_request": True,
            }
        )
        if proposal.get("status") != "PROPOSAL_ONLY":
            failures.append("runtime-proposal-only")
        if proposal.get("goal", {}).get("owner") != "USER":
            failures.append("runtime-user-goal-owner")
        if proposal.get("authority", {}).get("direct_execution_allowed") is not False:
            failures.append("runtime-direct-execution-denial")
        kinds = {item.get("kind") for item in proposal.get("delegations", [])}
        if kinds != {"MENTOR", "ACTION"}:
            failures.append("runtime-delegation-boundary")
        try:
            build_proposal({"mode": "ACCOUNTABILITY", "goal": "Test commitment boundary"})
            failures.append("runtime-accountability-without-commitment-accepted")
        except CoachInputError:
            pass
    except Exception as exc:  # gate must fail closed on any unexpected reference-runtime error
        failures.append(f"runtime-self-check:{type(exc).__name__}:{exc}")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 Coach gate: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("FA3 Coach gate: PASS")
    print("profile=FA3-COACH-001 capabilities=143 new_authorities=0 runtime=PENDING_CURRENT_HOST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
