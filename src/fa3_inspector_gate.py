#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from fa3_inspector import classify_inspection, self_check

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "profile": ROOT / "canonical/profiles/FA3-INSPECTOR-001.json",
    "contracts": ROOT / "canonical/contracts/FA3-INSPECTION-CONTRACTS-001.json",
    "provider": ROOT / "canonical/providers/FA3-PROVIDER-INSPECTOR-LOCAL-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-INSPECTOR-2026-09-12.json",
    "policy": ROOT / "canonical/FA3-INSPECTION-POLICY-001.json",
    "evidence": ROOT / "canonical/FA3-INSPECTION-EVIDENCE-001.json",
    "enforcement": ROOT / "canonical/inspector-enforcement.json",
    "conformance": ROOT / "canonical/FA3-INSPECTION-CONFORMANCE-MATRIX-001.json",
    "runtime": ROOT / "canonical/FA3-INSPECTOR-RUNTIME-CONFORMANCE-001.json",
    "gate": ROOT / "canonical/FA3-GATE-INDEPENDENT-VERIFICATION-001.json",
}
MANDATORY_RULES = {
    "INSPECTOR_P0_MUST_PROVIDER_INDEPENDENT", "INSPECTOR_NOT_ARCHITECTURAL_AUTHORITY",
    "INSPECTOR_NO_GENERAL_EXECUTION_AUTHORITY", "INSPECTOR_EXECUTOR_NOT_SOLE_ACCEPTING_VERIFIER",
    "INSPECTOR_P0_MUST_PRODUCTION_SELF_ATTESTATION_ONLY_BLOCKED", "INSPECTOR_LIFECYCLE_STATES_DISTINCT",
    "INSPECTOR_EVIDENCE_PROVENANCE_REQUIRED", "INSPECTOR_EVIDENCE_FRESHNESS_REQUIRED_FOR_PRODUCTION_PASS",
    "INSPECTOR_REPRODUCIBILITY_REQUIRED_FOR_RUNTIME_AND_PRODUCTION_PASS", "INSPECTOR_SILENT_REPAIR_DURING_CERTIFICATION_FORBIDDEN",
    "INSPECTOR_REMEDIATION_REQUIRES_REINSPECTION", "INSPECTOR_NON_PASS_OR_DRIFT_FAILS_CLOSED_FOR_PROMOTION",
}

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def validate() -> list[str]:
    failures: list[str] = []
    for name, path in REQUIRED.items():
        if not path.exists(): failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures: return failures
    p, c, provider, d, policy, evidence, enf, conf, runtime, gate = [load(REQUIRED[k]) for k in ["profile","contracts","provider","decision","policy","evidence","enforcement","conformance","runtime","gate"]]
    checks = [
        (p.get("id") == "FA3-INSPECTOR-001", "profile-id"),
        (p.get("priority") == "P0" and p.get("requirement") == "MUST", "profile-p0-must"),
        (p.get("new_capability") is False and p.get("capability_count") == 143, "profile-capability-invariant"),
        (p.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (c.get("provider_neutral") is True, "contracts-provider-neutral"),
        (c.get("separation_of_duties", {}).get("executor_may_be_sole_accepting_verifier") is False, "separation-of-duties"),
        (provider.get("architectural_authority") is False and provider.get("current_host_promotion_claimed") is False, "provider-boundary"),
        (d.get("canonical_invariant", {}).get("id") == "FA3-INVARIANT-INDEPENDENT-VERIFICATION-001", "canonical-invariant"),
        (d.get("conformance_matrix_id") == "FA3-INSPECTION-CONFORMANCE-MATRIX-001", "decision-conformance-link"),
        (policy.get("fail_closed") is True and len(policy.get("lifecycle_distinctions", [])) == 5, "policy-fail-closed-lifecycle"),
        (evidence.get("provenance", {}).get("self_attestation_may_be_sole_p0_must_production_evidence") is False, "evidence-no-self-attestation-only"),
        (enf.get("fail_closed") is True and set(enf.get("rules", [])) == MANDATORY_RULES, "enforcement-rules"),
        (conf.get("decision_ref") == "FA3-DEC-INSPECTOR-2026-09-12", "conformance-decision-link"),
        (runtime.get("status") == "PENDING_CURRENT_HOST" and runtime.get("production_admitted") is False and runtime.get("evidence_present") is False, "runtime-not-falsely-promoted"),
        (gate.get("fail_closed") is True and gate.get("rule_count") == 12 and gate.get("capability_count_after") == 143, "gate-invariants"),
    ]
    failures.extend(name for ok, name in checks if not ok)
    try:
        self_check()
        same_actor = classify_inspection({"subject_id":"x","level":"L3_PRODUCTION","executor_id":"a","inspector_id":"a","evidence_present":True,"evidence_fresh":True,"canonical_compliant":True,"implementation_verified":True,"reproducible":True,"runtime_verified":True})
        if same_actor.get("status") != "BLOCKED": failures.append("runtime-separation-of-duties")
    except Exception as exc:
        failures.append(f"runtime-self-check:{type(exc).__name__}:{exc}")
    return failures

def main() -> int:
    failures = validate()
    if failures:
        print("FA3 Inspector gate: FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("FA3 Inspector gate: PASS")
    print("profile=FA3-INSPECTOR-001 capabilities=143 new_authorities=0 runtime=PENDING_CURRENT_HOST")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
