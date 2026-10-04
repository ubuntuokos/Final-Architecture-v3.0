#!/usr/bin/env python3
import json
from pathlib import Path

from fa3_release_baseline import active_capability_count

POLICY = Path("canonical/FA3-CFA3-CANONICAL-NAMING-COMPATIBILITY-POLICY-001.json")
DECISION = Path("canonical/decisions/FA3-DEC-CFA3-CANONICAL-NAMING-2026-10-04.json")
EXPECTED_ALIASES = {"CFA3", "FA3", "FA3/CFA3", "CFA3/FA3"}
EXPECTED_DECISION = "CFA3_IS_FINAL_CANONICAL_NAME_AND_FA3_CFA3_FA3_CFA3_CFA3_FA3_ARE_RETROACTIVELY_EQUIVALENT_SYSTEM_REFERENCES"
REQUIRED_OWNER_DIRECTIVES = {
    "CFA3_IS_THE_FINAL_CANONICAL_PRODUCT_NAME",
    "FA3_IS_THE_HISTORICAL_ORIGIN_ALIAS",
    "FA3_CFA3_CFA3_FA3_AND_CFA3_REFER_TO_THE_SAME_SYSTEM",
    "EQUIVALENCE_APPLIES_RETROACTIVELY_AND_FORWARD",
    "HISTORICAL_AND_MACHINE_IDENTIFIERS_MUST_NOT_BE_DESTRUCTIVELY_RENAMED_BY_THIS_RULE",
}

def _load(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))

def evaluate(root: Path) -> dict:
    root = root.resolve()
    active_count = active_capability_count(root)
    policy = _load(root, POLICY)
    decision = _load(root, DECISION)
    observed_aliases = policy.get("semantic_aliases", [])
    observed_baseline = policy.get("capability_baseline")
    directives = set(decision.get("owner_directive", []))
    checks = {
        "canonical-name-cfa3": policy.get("canonical_product_name") == "CFA3",
        "historical-origin-fa3": policy.get("historical_origin_name") == "FA3",
        "alias-equivalence-complete": set(observed_aliases) == EXPECTED_ALIASES,
        "retroactive-and-forward": policy.get("semantic_equivalence", {}).get("scope") == "RETROACTIVE_AND_FORWARD",
        "one-system": policy.get("semantic_equivalence", {}).get("all_aliases_refer_to_same_system") is True
            and policy.get("semantic_equivalence", {}).get("fa3_is_separate_product") is False,
        "history-preserved": policy.get("non_destructive_history", {}).get("rewrite_required") is False
            and policy.get("migration_safety", {}).get("bulk_search_replace_forbidden") is True,
        "machine-identifiers-not-auto-renamed": policy.get("machine_identifier_compatibility", {}).get("semantic_alias_rule_authorizes_literal_rename") is False
            and policy.get("machine_identifier_compatibility", {}).get("rename_requires") == "SEPARATE_EXPLICITLY_APPROVED_COMPATIBILITY_MIGRATION",
        "baseline-preserved": observed_baseline == active_count
            and policy.get("capability_delta") == 0
            and policy.get("authority_delta") == 0
            and policy.get("donor_delta") == 0,
        "decision-identity-bound": decision.get("id") == "FA3-DEC-CFA3-CANONICAL-NAMING-2026-10-04"
            and decision.get("policy_id") == policy.get("id")
            and decision.get("decision") == EXPECTED_DECISION,
        "decision-equivalence-bound": REQUIRED_OWNER_DIRECTIVES <= directives,
        "decision-nondestructive-bound": decision.get("destructive_history_rewrite") is False
            and decision.get("automatic_machine_identifier_rename") is False
            and decision.get("existing_authorities_only") is True,
        "decision-baseline-bound": decision.get("capability_count_after") == active_count
            and decision.get("new_capabilities") == 0
            and decision.get("new_architectural_authorities") == 0
            and decision.get("donor_delta") == 0,
        "no-runtime-promotion": policy.get("current_host_runtime_promotion_claim") is False
            and decision.get("current_host_runtime_promotion_claim") is False,
    }
    passed = all(checks.values())
    return {
        "schema": "fa3.cfa3-naming-compatibility-gate-report.v1",
        "policy_id": policy.get("id"),
        "canonical_product_name": policy.get("canonical_product_name"),
        "semantic_aliases": observed_aliases,
        "expected_semantic_aliases": sorted(EXPECTED_ALIASES),
        "capability_count": observed_baseline,
        "expected_active_capability_count": active_count,
        "decision_id": decision.get("id"),
        "result": "PASS" if passed else "FAIL",
        "checks": [{"name": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()],
    }

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = evaluate(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
