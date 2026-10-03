#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

POLICY = "canonical/FA3-APPLICATION-GUI-DESIGN-POLICY-001.json"
LIFECYCLE = "canonical/FA3-APP-LIFECYCLE-001.json"
AUDIT = "canonical/FA3-APPLICATION-GUI-RETROACTIVE-AUDIT-001.json"
RECORD_SCHEMA = "canonical/contracts/FA3-APPLICATION-GUI-DESIGN-RECORD-001.schema.json"
GATE_RECORD = "canonical/FA3-GATE-APPLICATION-GUI-DESIGN-001.json"
GUI_REGISTRY = "canonical/FA3-GUI-SURFACE-REGISTRY-001.json"
APP_CATALOG = "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json"
APP_LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
GATE_REGISTRY = "canonical/FA3-GATE-REGISTRY-001.json"
ENFORCEMENT = "canonical/enforcement-policy.json"
DOC = "docs/FA3-APPLICATION-GUI-DESIGN-POLICY-001.md"

GATE_ID = "FA3-GATE-APPLICATION-GUI-DESIGN-001"
GATESET_ID = "FA3-APPLICATION-GUI-DESIGN-GATESET-001"
POLICY_ID = "FA3-APPLICATION-GUI-DESIGN-POLICY-001"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def _applications(catalog: dict[str, Any], links: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in catalog.get("applications", []):
        rows.append({
            "application_id": "studio." + str(item.get("id")),
            "name": str(item.get("name")),
            "lifecycle": "CATALOG_" + str(item.get("admission", "UNKNOWN")),
            "gui_review": "GUI_PLACEMENT_REVIEW_REQUIRED_UNLESS_APPROVED_RECORD_EXISTS",
        })
    for item in links.get("applications", []):
        lifecycle = str(item.get("lifecycle", "UNKNOWN"))
        rows.append({
            "application_id": str(item.get("application_id")),
            "name": str(item.get("name")),
            "lifecycle": lifecycle,
            "gui_review": (
                "REFERENCE_ONLY_NO_FA3_GUI_MUTATION"
                if lifecycle == "REFERENCE_ONLY"
                else "GUI_PLACEMENT_REVIEW_REQUIRED_UNLESS_APPROVED_RECORD_EXISTS"
            ),
        })
    return rows


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []
    paths = [
        POLICY, LIFECYCLE, AUDIT, RECORD_SCHEMA, GATE_RECORD, GUI_REGISTRY,
        APP_CATALOG, APP_LINKS, GATE_REGISTRY, ENFORCEMENT, DOC,
    ]
    missing = [rel for rel in paths if not (root / rel).is_file()]
    if missing:
        return {
            "schema": "fa3.application-gui-design-gate-report.v1",
            "gate_id": GATESET_ID,
            "result": "FAIL",
            "findings": [_finding("GUI-POLICY-000", "missing required files: " + ",".join(missing))],
            "current_host_runtime_promotion_claim": False,
        }

    try:
        policy = _load(root / POLICY)
        lifecycle = _load(root / LIFECYCLE)
        audit = _load(root / AUDIT)
        record_schema = _load(root / RECORD_SCHEMA)
        gate_record = _load(root / GATE_RECORD)
        gui_registry = _load(root / GUI_REGISTRY)
        catalog = _load(root / APP_CATALOG)
        links = _load(root / APP_LINKS)
        gate_registry = _load(root / GATE_REGISTRY)
        enforcement = _load(root / ENFORCEMENT)
        doc = (root / DOC).read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "schema": "fa3.application-gui-design-gate-report.v1",
            "gate_id": GATESET_ID,
            "result": "FAIL",
            "findings": [_finding("GUI-POLICY-001", str(exc))],
            "current_host_runtime_promotion_claim": False,
        }

    capability_count = load_active_release_baseline(root).capability_count
    scope = policy.get("scope", {})
    cls = policy.get("gui_classification", {})
    placement = policy.get("placement", {})
    design = policy.get("design_system", {})
    change = policy.get("change_synchronization", {})
    shared = policy.get("shared_gui", {})
    manual = policy.get("documentation", {})
    retro = policy.get("retroactive_audit", {})

    checks = [
        (policy.get("id") == POLICY_ID and policy.get("status") == "CANONICAL" and policy.get("priority") == "P0",
         "GUI-POLICY-002", "canonical policy identity/status/priority drift"),
        (policy.get("capability_count") == capability_count == 175 and policy.get("new_capability") is False
         and policy.get("new_architectural_authority") is False,
         "GUI-POLICY-003", "capability or authority invariant drift"),
        (scope.get("retroactive") is True and scope.get("forward_enforced") is True
         and scope.get("continuous_change_sync") is True and scope.get("grandfathering_allowed") is False,
         "GUI-POLICY-004", "retroactive/forward/change-synchronized scope drift"),
        (set(cls.get("allowed", [])) == {"GUI_REQUIRED", "GUI_POSSIBLE", "HEADLESS_ONLY"}
         and cls.get("gui_required_or_possible_requires_design") is True
         and cls.get("headless_only_requires_explicit_justification") is True,
         "GUI-POLICY-005", "GUI classification contract drift"),
        (placement.get("global_fa3_placement_required") is True
         and placement.get("application_local_placement_required") is True
         and placement.get("exact_final_application_local_placement_requires_owner_approval") is True
         and placement.get("automatic_final_placement_forbidden") is True
         and placement.get("finalization_without_owner_approved_placement_forbidden") is True,
         "GUI-POLICY-006", "placement/owner approval contract drift"),
        (design.get("mode") == "FA3_DESIGN_SYSTEM_LOCKED"
         and design.get("fa3_visual_and_interaction_language_required") is True
         and design.get("application_specific_independent_design_system_forbidden") is True
         and design.get("profile_id") == "FA3-UI-COMPONENT-FABRIC-001"
         and design.get("contract_id") == "FA3-UI-COMPONENT-FABRIC-CONTRACTS-001"
         and design.get("surface_registry_id") == "FA3-GUI-SURFACE-REGISTRY-001"
         and design.get("deviation_allowed") is False
         and design.get("external_or_donor_gui_requires_fa3_native_adaptation") is True,
         "GUI-POLICY-007", "FA3 Design System lock drift"),
        (change.get("functional_delta_requires_gui_impact_assessment") is True
         and change.get("removed_function_may_not_leave_orphan_gui") is True
         and change.get("gui_revision_may_not_lag_required_functional_revision") is True
         and change.get("application_and_required_gui_change_same_change_set") is True,
         "GUI-POLICY-008", "functional/GUI synchronization drift"),
        (shared.get("shared_first") is True
         and shared.get("duplicate_shared_gui_component_forbidden_without_reviewed_justification") is True,
         "GUI-POLICY-009", "shared GUI reuse rule drift"),
        (manual.get("materialized_gui_and_application_manual_must_match") is True
         and manual.get("real_gui_names_required") is True
         and manual.get("real_menu_toolbar_placement_required") is True,
         "GUI-POLICY-010", "manual/GUI synchronization drift"),
        (retro.get("required") is True and retro.get("preserve_existing_compliant_gui") is True
         and retro.get("missing_prior_placement_approval_becomes_review_required") is True
         and retro.get("approval_may_not_be_fabricated") is True,
         "GUI-POLICY-011", "retroactive audit semantics drift"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append(_finding(code, message))

    lg = lifecycle.get("application_gui_governance", {})
    if not (
        lg.get("policy_id") == POLICY_ID
        and lg.get("retroactive") is True
        and lg.get("grandfathering_allowed") is False
        and lg.get("functional_delta_gui_impact_assessment_required") is True
        and lg.get("fa3_design_system_required") is True
        and lg.get("exact_application_local_placement_owner_approval_required") is True
    ):
        findings.append(_finding("GUI-POLICY-012", "application lifecycle GUI governance binding drift"))

    if not (
        audit.get("policy_id") == POLICY_ID
        and audit.get("applies_retroactively") is True
        and audit.get("fabricated_approval_forbidden") is True
        and audit.get("grandfathering_allowed") is False
    ):
        findings.append(_finding("GUI-POLICY-013", "retroactive audit contract drift"))

    required_record_fields = {
        "application_id", "application_lifecycle_state", "gui_classification",
        "retroactive_policy_applies", "continuous_gui_sync_required",
        "fa3_design_system_required", "fa3_gui_placement", "application_navigation_model",
        "functional_revision", "gui_revision", "function_to_gui_mapping",
        "placement_status", "design_system_compliance_status", "materialization_status",
        "verification_status", "manual_projection_status",
    }
    if not required_record_fields.issubset(set(record_schema.get("required", []))):
        findings.append(_finding("GUI-POLICY-014", "application GUI design record schema missing required fields"))

    if not (
        gate_record.get("id") == GATE_ID
        and gate_record.get("gateset_id") == GATESET_ID
        and gate_record.get("priority") == "P0"
        and gate_record.get("fail_closed") is True
        and gate_record.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(_finding("GUI-POLICY-015", "gate record drift"))

    gates = gate_registry.get("mandatory_reference_gates", [])
    mirror = enforcement.get("mandatory_reference_gates", [])
    if GATESET_ID not in gates or gates != mirror:
        findings.append(_finding("GUI-POLICY-016", "mandatory gate registry/enforcement mirror binding missing"))

    if not (
        gui_registry.get("id") == "FA3-GUI-SURFACE-REGISTRY-001"
        and gui_registry.get("profile") == "FA3-DESKTOP-001"
        and gui_registry.get("capability_count") == 175
    ):
        findings.append(_finding("GUI-POLICY-017", "canonical GUI surface registry baseline drift"))

    gui_rules = gui_registry.get("rules", {})
    if not (
        gui_rules.get("application_gui_design_policy") == POLICY_ID
        and gui_rules.get("fa3_design_system_required_for_all_fa3_application_gui") is True
        and gui_rules.get("independent_application_visual_system_forbidden") is True
        and gui_rules.get("exact_application_local_placement_owner_approval_required") is True
        and gui_rules.get("functional_delta_gui_impact_assessment_required") is True
        and gui_rules.get("removed_function_orphan_gui_forbidden") is True
        and gui_rules.get("retroactive_application_gui_review_required") is True
        and gui_rules.get("fabricated_placement_approval_forbidden") is True
    ):
        findings.append(_finding("GUI-POLICY-020", "GUI surface registry policy binding drift"))

    link_policy = links.get("policy", {})
    if not (
        link_policy.get("application_gui_design_policy_required") is True
        and link_policy.get("application_gui_design_policy_id") == POLICY_ID
        and link_policy.get("retroactive_application_gui_audit_required") is True
        and link_policy.get("gui_change_impact_assessment_required") is True
        and link_policy.get("fa3_design_system_compliance_required") is True
        and link_policy.get("independent_application_design_system_forbidden") is True
        and link_policy.get("gui_placement_owner_approval_required") is True
        and link_policy.get("fabricated_gui_placement_approval_forbidden") is True
        and link_policy.get("removed_function_orphan_gui_forbidden") is True
        and link_policy.get("application_manual_gui_sync_required") is True
    ):
        findings.append(_finding("GUI-POLICY-021", "application inventory GUI policy binding drift"))

    expected_rules = {
        "APPLICATION_GUI_POLICY_RETROACTIVE_NO_GRANDFATHERING",
        "GUI_REQUIRED_OR_POSSIBLE_REQUIRES_DESIGN",
        "HEADLESS_ONLY_REQUIRES_JUSTIFICATION",
        "FA3_GLOBAL_AND_APPLICATION_LOCAL_PLACEMENT_REQUIRED",
        "EXACT_APPLICATION_LOCAL_PLACEMENT_REQUIRES_OWNER_APPROVAL",
        "FUNCTIONAL_DELTA_REQUIRES_GUI_IMPACT_ASSESSMENT",
        "REMOVED_FUNCTION_ORPHAN_GUI_FORBIDDEN",
        "FA3_DESIGN_SYSTEM_LOCKED_NO_APPLICATION_VISUAL_FORK",
        "SHARED_GUI_REUSE_FIRST",
        "GUI_FUNCTIONAL_REVISION_SYNC_REQUIRED",
        "MATERIALIZED_GUI_AND_MANUAL_MUST_MATCH",
        "RETROACTIVE_REVIEW_MAY_NOT_FABRICATE_APPROVAL",
        "STATIC_POLICY_DOES_NOT_CLAIM_CURRENT_HOST_RUNTIME_PASS",
    }
    actual_rules = enforcement.get("application_gui_design_mandatory_p0_rules")
    if not (
        enforcement.get("application_gui_design_policy_id") == POLICY_ID
        and enforcement.get("application_gui_design_gate_id") == GATESET_ID
        and isinstance(actual_rules, list)
        and len(actual_rules) == len(set(actual_rules))
        and set(actual_rules) == expected_rules
    ):
        findings.append(_finding("GUI-POLICY-022", "global enforcement GUI policy binding drift"))

    required_doc_terms = [
        "RETROACTIVE", "CHANGE-SYNCHRONIZED", "DESIGN-SYSTEM-LOCKED",
        "GUI_PLACEMENT_REVIEW_REQUIRED", "explicit owner approval",
    ]
    if any(term not in doc for term in required_doc_terms):
        findings.append(_finding("GUI-POLICY-018", "policy documentation is incomplete"))

    apps = _applications(catalog, links)
    if not apps:
        findings.append(_finding("GUI-POLICY-019", "retroactive application inventory projection is empty"))

    return {
        "schema": "fa3.application-gui-design-gate-report.v1",
        "gate_id": GATESET_ID,
        "policy_id": POLICY_ID,
        "result": "PASS" if not findings else "FAIL",
        "capability_count": capability_count,
        "retroactive": True,
        "application_review_projection": apps,
        "application_review_count": len(apps),
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
    }


if __name__ == "__main__":
    import sys
    report = gate(Path(__file__).resolve().parents[1])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["result"] == "PASS" else 2)
