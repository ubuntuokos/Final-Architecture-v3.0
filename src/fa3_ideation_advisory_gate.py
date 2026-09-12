#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from fa3_ideation_advisory import build_projection, self_check

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "profile": ROOT / "canonical/profiles/FA3-IDEATION-ADVISORY-001.json",
    "contracts": ROOT / "canonical/contracts/FA3-IDEATION-ADVISORY-CONTRACTS-001.json",
    "provider": ROOT / "canonical/providers/FA3-PROVIDER-IDEATION-ADVISORY-LOCAL-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-IDEATION-ADVISORY-2026-09-12.json",
    "enforcement": ROOT / "canonical/ideation-advisory-enforcement.json",
    "conformance": ROOT / "canonical/FA3-IDEATION-ADVISORY-CONFORMANCE-MATRIX-001.json",
    "runtime": ROOT / "canonical/FA3-IDEATION-ADVISORY-RUNTIME-CONFORMANCE-001.json",
    "gate": ROOT / "canonical/FA3-GATE-IDEATION-ADVISORY-001.json",
    "implementation": ROOT / "src/fa3_ideation_advisory.py",
}
FORBIDDEN_IMPLEMENTATION_TOKENS = ["subprocess.", "os.system(", "os.popen(", "pty.spawn(", "sudo ", "pkexec"]
MANDATORY_RULES = {
    "IDEATION_ADVISORY_IDEA_NOT_FACT",
    "IDEATION_ADVISORY_HYPOTHESIS_NOT_EVIDENCE",
    "IDEATION_ADVISORY_RECOMMENDATION_NOT_DECISION",
    "IDEATION_ADVISORY_DECISION_NOT_AUTHORIZATION",
    "IDEATION_ADVISORY_AUTHORIZATION_NOT_EXECUTION",
    "IDEATION_ADVISORY_EXECUTION_NOT_VERIFIED_RESULT",
    "IDEATION_ADVISORY_DIRECT_EXECUTION_AND_REPOSITORY_WRITE_FORBIDDEN",
    "IDEATION_ADVISORY_VERIFIED_RECOMMENDATION_REQUIRES_EVIDENCE",
    "IDEATION_ADVISORY_MISSING_EVIDENCE_MARKED_UNVERIFIED",
    "IDEATION_ADVISORY_UNCERTAINTY_AND_CONFIDENCE_EXPLICIT",
    "IDEATION_ADVISORY_CONFLICTING_EVIDENCE_VISIBLE",
    "IDEATION_ADVISORY_RECOMMENDATION_TRACEABILITY_REQUIRED",
    "IDEATION_ADVISORY_DECISION_HANDOFF_REQUIRED",
    "IDEATION_ADVISORY_HIGH_IMPACT_INDEPENDENT_VERIFICATION_REQUIRED",
    "IDEATION_ADVISORY_SILENT_MEMORY_AND_CROSS_WORKSPACE_PERSISTENCE_FORBIDDEN",
    "IDEATION_ADVISORY_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
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
    subprofiles = profile.get("subprofiles", {})

    checks = [
        (profile.get("id") == "FA3-IDEATION-ADVISORY-001", "profile-id"),
        (profile.get("priority") == "P0" and profile.get("requirement") == "MUST", "profile-p0-must"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        (subprofiles.get("ideator", {}).get("id") == "FA3-IDEATOR-001", "ideator-subprofile"),
        (subprofiles.get("advisor", {}).get("id") == "FA3-ADVISOR-001", "advisor-subprofile"),
        (subprofiles.get("ideator", {}).get("priority") == "P1", "ideator-p1"),
        (subprofiles.get("advisor", {}).get("priority") == "P0", "advisor-p0"),
        (contracts.get("provider_neutral") is True, "contracts-provider-neutral"),
        (contracts.get("execution_model", {}).get("direct_tool_execution") == "FORBIDDEN", "contracts-no-direct-tool-exec"),
        (contracts.get("execution_model", {}).get("direct_agent_execution") == "FORBIDDEN", "contracts-no-direct-agent-exec"),
        (contracts.get("execution_model", {}).get("direct_repository_write") == "FORBIDDEN", "contracts-no-direct-repo-write"),
        (provider.get("architectural_authority") is False, "provider-no-authority"),
        (provider.get("current_host_promotion_claimed") is False, "provider-no-runtime-claim"),
        (decision.get("new_capabilities") == 0, "decision-no-new-capability"),
        (decision.get("new_architectural_authorities") == 0, "decision-no-new-authority"),
        (decision.get("capability_count_after") == 143, "decision-capability-count"),
        (decision.get("conformance_matrix_id") == "FA3-IDEATION-ADVISORY-CONFORMANCE-MATRIX-001", "decision-conformance-link"),
        (enforcement.get("fail_closed") is True, "enforcement-fail-closed"),
        (enforcement.get("mandatory_rule_count") == 16, "enforcement-rule-count"),
        (set(enforcement.get("rules", [])) == MANDATORY_RULES, "enforcement-rule-set"),
        (conformance.get("decision_ref") == "FA3-DEC-IDEATION-ADVISORY-2026-09-12", "conformance-decision-link"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-not-falsely-promoted"),
        (runtime.get("production_admitted") is False, "runtime-production-not-admitted"),
        (runtime.get("evidence_present") is False, "runtime-evidence-not-fabricated"),
        (gate.get("fail_closed") is True and gate.get("rule_count") == 16, "gate-fail-closed"),
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
        idea = build_projection({"mode": "IDEATE", "problem": "Generate bounded candidates", "candidates": ["A", "B"]})
        if any(c.get("semantic_status") != "HYPOTHESIS" for c in idea.get("candidates", [])):
            failures.append("runtime-idea-not-hypothesis")
        advice = build_projection({
            "mode": "RECOMMEND", "problem": "Recommend with verified evidence",
            "evidence": [{"ref": "E1", "claim": "Measured", "status": "VERIFIED"}],
            "requested_recommendation": "A", "high_impact": True, "actionable_request": True,
        })
        if advice.get("recommendation", {}).get("semantic_status") != "RECOMMENDATION_NOT_DECISION":
            failures.append("runtime-recommendation-not-decision")
        if advice.get("authority", {}).get("direct_repository_write_allowed") is not False:
            failures.append("runtime-repository-write-denial")
        kinds = {item.get("kind") for item in advice.get("delegations", [])}
        if kinds != {"ACTION", "VERIFICATION"}:
            failures.append("runtime-delegation-boundary")
        unverified = build_projection({"mode": "RECOMMEND", "problem": "No evidence", "requested_recommendation": "A"})
        if unverified.get("recommendation", {}).get("evidence_status") != "UNVERIFIED":
            failures.append("runtime-missing-evidence-not-unverified")
        conflicted = build_projection({
            "mode": "RISK_ASSESSMENT", "problem": "Conflict",
            "evidence": [{"ref": "E2", "claim": "Conflict", "status": "CONFLICTED"}],
        })
        if conflicted.get("recommendation", {}).get("evidence_status") != "CONFLICTED":
            failures.append("runtime-conflict-hidden")
    except Exception as exc:
        failures.append(f"runtime-self-check:{type(exc).__name__}:{exc}")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 Ideation-Advisory gate: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("FA3 Ideation-Advisory gate: PASS")
    print("profile=FA3-IDEATION-ADVISORY-001 capabilities=143 new_authorities=0 runtime=PENDING_CURRENT_HOST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
