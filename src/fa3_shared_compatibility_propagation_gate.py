#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from fa3_application_donor_index import build_index  # noqa: E402

POLICY_REL = Path("canonical/FA3-SHARED-COMPATIBILITY-PROPAGATION-001.json")
LINKS_REL = Path("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
ASSESSMENT_SCHEMA = "fa3.application-compatibility-assessment.v1"

REQUIRED_LINK_POLICY = (
    "multi_application_feature_shared_layer_required",
    "shared_capability_local_duplication_forbidden_without_justification",
    "retrospective_shared_impact_required",
    "affected_application_manual_update_required",
    "structural_change_current_host_alignment_required",
    "capability_loss_during_shared_migration_forbidden",
    "all_applications_in_scope_even_without_declared_dependency",
    "declared_and_implicit_dependencies_must_be_reconciled",
    "shared_capability_consumer_reverse_traceability_required",
    "shared_capability_binding_must_be_canonical_derived",
    "shared_capability_manual_capability_ids_forbidden",
    "shared_capability_current_host_impact_required",
    "gates_evidence_and_release_projection_reconciliation_required",
)

REQUIRED_RULES = {
    "EVERY_NEW_APPLICATION_MUST_ASSESS_COMPATIBILITY_WITH_ALL_APPLICABLE_EXISTING_SHARED_CAPABILITIES_BEFORE_ADMISSION",
    "EVERY_MATERIALLY_MODIFIED_APPLICATION_MUST_REASSESS_APPLICABLE_SHARED_CAPABILITY_COMPATIBILITY",
    "EVERY_SHARED_CAPABILITY_CHANGE_MUST_DERIVE_ALL_AFFECTED_CONSUMERS_FROM_CANONICAL_BINDINGS_AND_CONSUMER_MAPS",
    "SHARED_CAPABILITY_GROWTH_MUST_PROPAGATE_TO_ALL_AFFECTED_CURRENT_APPLICATIONS",
    "SHARED_CAPABILITY_GROWTH_MUST_DEFINE_FORWARD_COMPATIBILITY_REQUIREMENTS_FOR_FUTURE_APPLICATIONS",
    "PLANNED_IN_PROGRESS_MATERIALIZED_AND_FUTURE_APPLICATIONS_ARE_IN_SCOPE",
    "NO_NEW_CROSS_LAYER_FABRIC_MAY_BE_CREATED_WHEN_AN_EXISTING_CANONICAL_OWNER_CAN_BE_EXTENDED",
    "UNKNOWN_SHARED_COMPONENT_OR_UNRESOLVED_CONSUMER_SCOPE_FAILS_CLOSED",
}

DISPOSITIONS = {
    "NO_CHANGE",
    "GUI_PROJECTION",
    "CONTRACT_ADAPTER",
    "SHARED_CAPABILITY_BINDING",
    "LOCAL_TO_SHARED_MIGRATION",
    "RUNTIME_REQUALIFICATION",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def finding(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def expected_components_for_application(index: dict[str, Any], application_id: str) -> set[str]:
    shared_map = index.get("shared_capability_consumer_map", {})
    edges = {
        edge.get("id"): edge
        for edge in shared_map.get("edges", [])
        if isinstance(edge, dict) and isinstance(edge.get("id"), str)
    }
    edge_ids = (
        shared_map.get("views", {})
        .get("by_consumer", {})
        .get("APPLICATION:" + application_id, [])
    )
    return {
        edges[edge_id]["shared_capability_id"]
        for edge_id in edge_ids
        if edge_id in edges and isinstance(edges[edge_id].get("shared_capability_id"), str)
    }


def validate_assessment(
    assessment: dict[str, Any],
    index: dict[str, Any],
    *,
    require_pass: bool,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if assessment.get("schema") != ASSESSMENT_SCHEMA:
        findings.append(finding("COMPAT-ASM-001", "assessment schema mismatch"))
        return findings

    app_id = assessment.get("application_id")
    if not isinstance(app_id, str) or not app_id:
        findings.append(finding("COMPAT-ASM-002", "application_id missing"))
        return findings

    state = assessment.get("application_state")
    if state not in {"PLANNED", "IN_PROGRESS", "MATERIALIZED", "FUTURE"}:
        findings.append(finding("COMPAT-ASM-003", "application_state invalid"))

    declared = assessment.get("applicable_shared_components")
    if not isinstance(declared, list) or any(not isinstance(v, str) or not v for v in declared):
        findings.append(finding("COMPAT-ASM-004", "applicable_shared_components invalid"))
        declared = []
    if len(declared) != len(set(declared)):
        findings.append(finding("COMPAT-ASM-005", "applicable_shared_components contains duplicates"))

    known_shared = {
        edge.get("shared_capability_id")
        for edge in index.get("shared_capability_consumer_map", {}).get("edges", [])
        if isinstance(edge, dict) and isinstance(edge.get("shared_capability_id"), str)
    }
    unknown = sorted(set(declared) - known_shared)
    if unknown:
        findings.append(finding("COMPAT-ASM-006", "unknown shared components: " + ", ".join(unknown)))

    registered_apps = {
        row.get("application_id")
        for row in index.get("applications", [])
        if isinstance(row, dict)
    }
    if app_id in registered_apps:
        expected = expected_components_for_application(index, app_id)
        missing = sorted(expected - set(declared))
        if missing:
            findings.append(
                finding(
                    "COMPAT-ASM-007",
                    "registered application assessment omits derived shared consumers: "
                    + ", ".join(missing),
                )
            )

    results = assessment.get("compatibility_results")
    if not isinstance(results, list):
        findings.append(finding("COMPAT-ASM-008", "compatibility_results must be a list"))
        results = []

    seen: set[str] = set()
    for row in results:
        if not isinstance(row, dict):
            findings.append(finding("COMPAT-ASM-009", "compatibility result must be an object"))
            continue
        sid = row.get("shared_component_id")
        disposition = row.get("disposition")
        if not isinstance(sid, str) or not sid:
            findings.append(finding("COMPAT-ASM-010", "compatibility result missing shared_component_id"))
            continue
        if sid in seen:
            findings.append(finding("COMPAT-ASM-011", "duplicate compatibility result: " + sid))
        seen.add(sid)
        if disposition not in DISPOSITIONS:
            findings.append(finding("COMPAT-ASM-012", "invalid disposition for " + sid))

    uncovered = sorted(set(declared) - seen)
    extra = sorted(seen - set(declared))
    if uncovered:
        findings.append(
            finding("COMPAT-ASM-013", "shared components without disposition: " + ", ".join(uncovered))
        )
    if extra:
        findings.append(
            finding("COMPAT-ASM-014", "dispositions outside applicable scope: " + ", ".join(extra))
        )

    if assessment.get("capability_regression") is not False:
        findings.append(finding("COMPAT-ASM-015", "capability_regression must be false"))
    if assessment.get("new_architectural_authority") is not False:
        findings.append(finding("COMPAT-ASM-016", "new_architectural_authority must be false"))

    if require_pass and assessment.get("overall_result") != "PASS":
        findings.append(finding("COMPAT-ASM-017", "enforced assessment must be PASS"))
    elif assessment.get("overall_result") not in {"PASS", "PENDING_ADAPTATION", "BLOCKED"}:
        findings.append(finding("COMPAT-ASM-018", "overall_result invalid"))

    if assessment.get("current_host_impact") not in {
        "NO_RUNTIME_IMPACT",
        "STRUCTURAL_REASSESSMENT_REQUIRED",
        "RUNTIME_REQUALIFICATION_REQUIRED",
    }:
        findings.append(finding("COMPAT-ASM-019", "current_host_impact invalid"))

    return findings


def gate(root: Path, assessment_path: Path | None = None, enforce: bool = False) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, str]] = []

    policy = load_json(root / POLICY_REL)
    links = load_json(root / LINKS_REL)
    index = build_index(root)

    if policy.get("id") != "FA3-SHARED-COMPATIBILITY-PROPAGATION-001":
        findings.append(finding("COMPAT-001", "policy identity drift"))
    if policy.get("authority") is not False:
        findings.append(finding("COMPAT-002", "policy must remain non-authoritative"))
    if policy.get("capability_baseline") != 175:
        findings.append(finding("COMPAT-003", "capability baseline drift"))
    if policy.get("new_capabilities") != 0 or policy.get("new_architectural_authorities") != 0:
        findings.append(finding("COMPAT-004", "capability or authority delta forbidden"))

    scopes = set(policy.get("application_scope", []))
    if scopes != {"PLANNED", "IN_PROGRESS", "MATERIALIZED", "FUTURE"}:
        findings.append(finding("COMPAT-005", "application scope must cover current and future applications"))

    dispositions = set(policy.get("required_impact_dispositions", []))
    if dispositions != DISPOSITIONS:
        findings.append(finding("COMPAT-006", "compatibility disposition set drift"))

    rules = set(policy.get("mandatory_rules", []))
    missing_rules = sorted(REQUIRED_RULES - rules)
    if missing_rules:
        findings.append(finding("COMPAT-007", "mandatory rules missing: " + ", ".join(missing_rules)))

    link_policy = links.get("policy", {})
    for key in REQUIRED_LINK_POLICY:
        if link_policy.get(key) is not True:
            findings.append(finding("COMPAT-008", "existing application/shared policy missing: " + key))

    validation = index.get("validation", {})
    if validation.get("result") != "PASS":
        findings.append(finding("COMPAT-009", "derived application/consumer index is not PASS"))

    shared_map = index.get("shared_capability_consumer_map", {})
    if (
        shared_map.get("schema") != "fa3.shared-capability-consumer-map.v1"
        or shared_map.get("derived") is not True
        or shared_map.get("authority") is not False
    ):
        findings.append(finding("COMPAT-010", "shared capability consumer map boundary drift"))

    for edge in shared_map.get("edges", []):
        if not isinstance(edge, dict):
            findings.append(finding("COMPAT-011", "invalid shared capability edge"))
            continue
        if edge.get("fa3_bindings", {}).get("resolution") == "UNRESOLVED_CAPABILITY_BINDING":
            findings.append(
                finding(
                    "COMPAT-012",
                    "unresolved shared capability binding: " + str(edge.get("shared_capability_id")),
                )
            )

    activation = policy.get("enforcement_activation", {})
    current_mode = activation.get("current_mode")
    if current_mode not in {"STAGED_DURING_ACTIVE_PR_RECONCILIATION", "P0_FAIL_CLOSED"}:
        findings.append(finding("COMPAT-013", "unsupported enforcement activation mode"))
    if current_mode == "STAGED_DURING_ACTIVE_PR_RECONCILIATION":
        if activation.get("global_mandatory_binding_deferred") is not True:
            findings.append(finding("COMPAT-014", "staged mode must defer global mandatory binding"))
    else:
        if activation.get("global_mandatory_binding_deferred") is not False:
            findings.append(finding("COMPAT-015", "P0 mode cannot defer global mandatory binding"))

    assessment_result = None
    if assessment_path is not None:
        assessment = load_json(assessment_path)
        assessment_findings = validate_assessment(
            assessment,
            index,
            require_pass=enforce or current_mode == "P0_FAIL_CLOSED",
        )
        findings.extend(assessment_findings)
        assessment_result = {
            "path": str(assessment_path),
            "application_id": assessment.get("application_id"),
            "overall_result": assessment.get("overall_result"),
            "finding_count": len(assessment_findings),
        }

    return {
        "schema": "fa3.shared-compatibility-propagation-gate-report.v1",
        "id": "FA3-SHARED-COMPATIBILITY-PROPAGATION-GATE-001",
        "result": "PASS" if not findings else "FAIL",
        "fail_closed": True,
        "enforcement_mode": current_mode,
        "capability_baseline": 175,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "derived_application_count": index.get("counts", {}).get("total_apps"),
        "shared_capability_count": index.get("counts", {}).get("shared_capabilities"),
        "assessment": assessment_result,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CFA3 shared compatibility propagation gate")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--assessment", type=Path)
    parser.add_argument("--enforce", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    assessment_path = None
    if args.assessment:
        assessment_path = args.assessment
        if not assessment_path.is_absolute():
            assessment_path = args.root / assessment_path

    report = gate(args.root, assessment_path=assessment_path, enforce=args.enforce)
    if args.output:
        output = args.output if args.output.is_absolute() else args.root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
