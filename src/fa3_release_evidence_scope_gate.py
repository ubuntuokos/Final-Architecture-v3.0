#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from fa3_release_baseline import BaselineError, load_active_release_baseline

BASELINE_ID = "FA3-RELEASE-CAPABILITY-BASELINE-001"
SCOPE_ID = "FA3-EVIDENCE-SCOPE-001"
DECISION_ID = "FA3-DEC-RELEASE-BASELINE-EVIDENCE-SCOPE-2026-09-13"
GATESET_ID = "FA3-RELEASE-EVIDENCE-SCOPE-GATESET-001"

PATHS = {
    "baseline": "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json",
    "scope": "canonical/FA3-EVIDENCE-SCOPE-001.json",
    "decision": "canonical/decisions/FA3-DEC-RELEASE-BASELINE-EVIDENCE-SCOPE-2026-09-13.json",
    "policy": "canonical/enforcement-policy.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    "registry": "evidence/evidence-registry.json",
    "governance": "canonical/FA3-GOVERNANCE-TIERING-001.json",
    "current_host_workflow": ".github/workflows/fa3-global-current-host-closure.yml",
    "enforce": "src/fa3_enforce.py",
}


def load_json(root: Path, key: str) -> dict[str, Any]:
    return json.loads((root / PATHS[key]).read_text(encoding="utf-8"))


def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == item_id:
            return item
    return {}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    missing = [path for path in PATHS.values() if not (root / path).is_file()]
    if missing:
        return {
            "schema": "fa3.release-evidence-scope-gate-report.v1",
            "gate_set_id": GATESET_ID,
            "baseline_id": BASELINE_ID,
            "scope_id": SCOPE_ID,
            "result": "FAIL",
            "blocking_findings": len(missing),
            "checks_passed": 0,
            "checks_total": 18,
            "findings": [finding("RESCOPE-000", f"missing {path}") for path in missing],
        }

    try:
        active_baseline = load_active_release_baseline(root)
    except BaselineError as exc:
        return {
            "schema": "fa3.release-evidence-scope-gate-report.v1",
            "gate_set_id": GATESET_ID,
            "baseline_id": BASELINE_ID,
            "scope_id": SCOPE_ID,
            "result": "FAIL",
            "blocking_findings": 1,
            "checks_passed": 0,
            "checks_total": 18,
            "findings": [finding("RESCOPE-003", str(exc))],
        }
    CURRENT_RELEASE = active_baseline.release
    CURRENT_RELEASE_COUNT = active_baseline.capability_count
    baseline = load_json(root, "baseline")
    scope = load_json(root, "scope")
    decision = load_json(root, "decision")
    policy = load_json(root, "policy")
    release = load_json(root, "release")
    registry = load_json(root, "registry")
    governance = load_json(root, "governance")
    workflow_text = (root / PATHS["current_host_workflow"]).read_text(encoding="utf-8")
    enforce_text = (root / PATHS["enforce"]).read_text(encoding="utf-8")

    baseline_count = baseline.get("current_release_capability_count")
    release_records = baseline.get("release_baselines", [])
    active_release = by_id([], "unused")
    for item in release_records:
        if item.get("release") == baseline.get("current_release"):
            active_release = item
            break

    observations = scope.get("observation_model", {})
    classes = scope.get("evidence_classes", {})
    negative = scope.get("negative_assurance", {})
    registry_rules = scope.get("registry_interpretation", {})
    boundaries = scope.get("authority_boundaries", {})
    rules = scope.get("scope_rules", [])
    mandatory_rule = by_id(rules, "EVID-SCOPE-MANDATORY-ACTIVE")
    enabled_rule = by_id(rules, "EVID-SCOPE-ENABLED-OR-ACTIVE")
    promotion_rule = by_id(rules, "EVID-SCOPE-PROMOTION")
    optional_rule = by_id(rules, "EVID-SCOPE-OPTIONAL-DISABLED")
    release_invariants = release.get("invariants", {})
    registry_records = registry.get("records", [])
    previous_count = baseline.get("previous_release_capability_count")
    declared_delta = baseline.get("capability_delta")
    migration_consistent = (
        isinstance(previous_count, int)
        and isinstance(declared_delta, int)
        and declared_delta == baseline_count - previous_count
        and declared_delta >= 0
    )

    expected_negative_checks = {
        "NO_UNEXPECTED_PROCESS",
        "NO_UNEXPECTED_LISTENING_PORT",
        "NO_UNEXPECTED_ACCELERATOR_OR_RESOURCE_LEASE",
        "NO_UNEXPECTED_NETWORK_EGRESS",
        "NO_UNEXPECTED_AUTHORITY_CLAIM",
        "NO_UNEXPECTED_SECRET_USE",
    }
    expected_forbidden = {
        "CANONICAL_SUPPORTED_IMPLIES_HOST_AVAILABLE",
        "HOST_AVAILABLE_IMPLIES_HOST_ENABLED",
        "HOST_ENABLED_IMPLIES_HOST_ACTIVE",
        "HOST_ACTIVE_IMPLIES_PRODUCTION_PROMOTED",
        "NEGATIVE_ASSURANCE_IMPLIES_POSITIVE_RUNTIME_PASS",
        "REFERENCE_CI_IMPLIES_CURRENT_HOST_PASS",
        "MISSING_HOST_DISPOSITION_IS_NONBLOCKING",
    }

    checks: list[tuple[str, bool, str]] = [
        (
            "RESCOPE-001",
            baseline.get("schema") == "fa3.release-capability-baseline.v1"
            and baseline.get("id") == BASELINE_ID
            and baseline.get("type") == "CANONICAL_RELEASE_BASELINE_POLICY",
            "release capability baseline identity/schema/type drift",
        ),
        (
            "RESCOPE-002",
            baseline.get("authority_delta") == 0
            and baseline.get("baseline_semantics") == "RELEASE_SCOPED"
            and migration_consistent,
            "release baseline capability delta is undeclared/inconsistent, gained authority, or stopped being release-scoped",
        ),
        (
            "RESCOPE-003",
            baseline.get("current_release") == CURRENT_RELEASE
            and baseline_count == CURRENT_RELEASE_COUNT
            and active_release.get("capability_count") == CURRENT_RELEASE_COUNT
            and active_release.get("status") == "ACTIVE_BASELINE",
            "active release baseline drift",
        ),
        (
            "RESCOPE-004",
            baseline.get("interpretation", {}).get("capability_count_is_not_timeless_global_constant") is True
            and baseline.get("interpretation", {}).get("future_release_must_declare_its_own_baseline") is True
            and baseline.get("interpretation", {}).get("implicit_carry_forward_of_count_forbidden") is True
            and baseline.get("change_control", {}).get("baseline_change_requires_release_projection_reconciliation") is True,
            "release-scoped count semantics or explicit future-release reconciliation weakened",
        ),
        (
            "RESCOPE-005",
            policy.get("architecture_release") == CURRENT_RELEASE
            and policy.get("canonical_capability_count") == baseline_count
            and policy.get("fail_closed") is True,
            "enforcement policy no longer mirrors the active release baseline fail-closed",
        ),
        (
            "RESCOPE-006",
            release.get("base_release") == CURRENT_RELEASE
            and release_invariants.get("canonical_capability_count") == baseline_count
            and release_invariants.get("new_capabilities") == declared_delta
            and release_invariants.get("new_architectural_authorities") == 0,
            "release projection baseline/capability/authority invariant drift",
        ),
        (
            "RESCOPE-007",
            registry.get("architecture_release") == CURRENT_RELEASE
            and registry.get("canonical_capability_count") == baseline_count
            and registry.get("record_count") == baseline_count
            and len(registry_records) == baseline_count,
            "Evidence Registry count/release no longer matches active release baseline",
        ),
        (
            "RESCOPE-008",
            not any(record.get("subject_id") in {BASELINE_ID, SCOPE_ID} for record in registry_records),
            "release/evidence policies were incorrectly registered as capabilities",
        ),
        (
            "RESCOPE-009",
            scope.get("schema") == "fa3.evidence-scope.policy.v1"
            and scope.get("id") == SCOPE_ID
            and scope.get("type") == "CANONICAL_EVIDENCE_SCOPE_POLICY"
            and scope.get("authority_delta") == 0
            and scope.get("capability_delta") == 0
            and scope.get("fail_closed") is True,
            "evidence scope identity or zero-delta/fail-closed invariant drift",
        ),
        (
            "RESCOPE-010",
            set(observations) >= {"CANONICAL_SUPPORTED", "HOST_AVAILABLE", "HOST_ENABLED", "HOST_ACTIVE", "PRODUCTION_PROMOTED"}
            and observations.get("CANONICAL_SUPPORTED", {}).get("positive_current_host_required") is False
            and observations.get("HOST_AVAILABLE", {}).get("positive_current_host_required") is False
            and observations.get("HOST_ENABLED", {}).get("positive_current_host_required") is True
            and observations.get("HOST_ACTIVE", {}).get("positive_current_host_required") is True
            and observations.get("PRODUCTION_PROMOTED", {}).get("positive_current_host_required") is True,
            "canonical/host/promotion observation separation drift",
        ),
        (
            "RESCOPE-011",
            classes.get("DESIGN_OR_REFERENCE", {}).get("may_prove_current_host_runtime") is False
            and classes.get("DESIGN_OR_REFERENCE", {}).get("may_prove_production_promotion") is False
            and classes.get("NEGATIVE_HOST_ASSURANCE", {}).get("may_prove_positive_runtime") is False
            and classes.get("NEGATIVE_HOST_ASSURANCE", {}).get("may_prove_production_promotion") is False
            and classes.get("POSITIVE_CURRENT_HOST", {}).get("requires_real_current_host_execution") is True
            and classes.get("PROMOTION_RECEIPT", {}).get("requires_positive_current_host_evidence") is True,
            "evidence classes permit reference or negative evidence to impersonate runtime/promotion evidence",
        ),
        (
            "RESCOPE-012",
            negative.get("allowed_only_for_optional_or_conditional_disabled_components") is True
            and negative.get("may_not_substitute_for_enabled_active_or_promoted_runtime") is True
            and negative.get("explicit_disabled_disposition_required") is True
            and negative.get("unknown_or_partial_result") == "BLOCKING_OR_PENDING"
            and expected_negative_checks.issubset(set(negative.get("required_checks", []))),
            "negative assurance scope or fail-closed checks weakened",
        ),
        (
            "RESCOPE-013",
            mandatory_rule.get("required_evidence") == "POSITIVE_CURRENT_HOST"
            and mandatory_rule.get("blocking") is True
            and enabled_rule.get("required_evidence") == "POSITIVE_CURRENT_HOST"
            and enabled_rule.get("blocking") is True
            and promotion_rule.get("required_evidence") == "POSITIVE_CURRENT_HOST_PLUS_ACCEPTANCE_AND_PROMOTION_RECEIPT"
            and promotion_rule.get("blocking") is True
            and optional_rule.get("required_evidence") == "NEGATIVE_HOST_ASSURANCE"
            and optional_rule.get("blocking_if_negative_assurance_passes") is False
            and optional_rule.get("positive_runtime_evidence_required") is False,
            "evidence-scope decision table drift",
        ),
        (
            "RESCOPE-014",
            registry_rules.get("scope_policy_may_not_downgrade_mandatory_obligation") is True
            and registry_rules.get("scope_policy_may_not_create_runtime_pass") is True
            and registry_rules.get("scope_policy_may_not_mutate_evidence_registry") is True
            and registry_rules.get("legacy_blocking_field_remains_authoritative_for_current_release_until_scoped_disposition_exists") is True,
            "scope policy acquired authority to downgrade mandatory evidence or mutate runtime PASS",
        ),
        (
            "RESCOPE-015",
            all(boundaries.get(key) is True for key in [
                "canonical_support_authority_unchanged",
                "evidence_registry_authority_unchanged",
                "acceptance_authority_unchanged",
                "promotion_authority_unchanged",
                "current_host_receipt_authority_unchanged",
                "reference_ci_cannot_promote_runtime",
                "documentation_cannot_promote_runtime",
            ]),
            "existing canonical/evidence/Acceptance/Promotion authority boundary drift",
        ),
        (
            "RESCOPE-016",
            expected_forbidden.issubset(set(scope.get("forbidden_inferences", []))),
            "required evidence-scope anti-inference invariants are missing",
        ),
        (
            "RESCOPE-017",
            policy.get("runtime_promotion_requires_current_host_evidence") is True
            and policy.get("document_only_promotion_forbidden") is True
            and "conditional providers explicitly dormant or evidence-promoted" in enforce_text
            and "runs-on: [self-hosted, linux, x64, fa3-current-host]" in workflow_text,
            "existing conditional-provider/current-host/promotion safety boundary drift",
        ),
        (
            "RESCOPE-018",
            decision.get("id") == DECISION_ID
            and decision.get("status") == "CANONICAL_CLOSED"
            and decision.get("decision", {}).get("v3_0_11_capability_count") == previous_count
            and decision.get("decision", {}).get("capability_count_semantics") == "RELEASE_SCOPED"
            and governance.get("authority_delta") == 0
            and governance.get("capability_delta") == declared_delta
            and governance.get("canonical_capability_count_before") == previous_count
            and governance.get("canonical_capability_count_after") == baseline_count,
            "criteria decision or governance-tiering compatibility drift",
        ),
    ]

    findings = [finding(code, message) for code, ok, message in checks if not ok]
    return {
        "schema": "fa3.release-evidence-scope-gate-report.v1",
        "gate_set_id": GATESET_ID,
        "baseline_id": BASELINE_ID,
        "scope_id": SCOPE_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "checks_passed": sum(1 for _, ok, _ in checks if ok),
        "checks_total": len(checks),
        "active_release": baseline.get("current_release"),
        "active_release_capability_count": baseline_count,
        "authority_delta": baseline.get("authority_delta", 0) + scope.get("authority_delta", 0),
        "capability_delta": baseline.get("capability_delta", 0) + scope.get("capability_delta", 0),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FA3 release-scoped capability baseline and host-scoped evidence policy")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/release-evidence-scope-gate-report.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = gate(root)
    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
