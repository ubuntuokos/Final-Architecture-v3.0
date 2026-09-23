#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

PROJECTION_ID = "FA3-WORK-MANAGEMENT-PROJECTION-001"
CONTRACT_ID = "FA3-WORK-ITEM-PROJECTION-CONTRACTS-001"
GATE_ID = "FA3-WORK-MANAGEMENT-GATESET-001"
KANEO_ID = "FA3-PROVIDER-KANEO-001"
KANBOARD_ID = "FA3-PROVIDER-KANBOARD-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)
P0_INVARIANTS = [
    "WORK_MANAGEMENT_SINGLE_MANDATORY_GUI_SURFACE",
    "KANEO_AND_KANBOARD_SHARE_PROVIDER_NEUTRAL_SURFACE",
    "PROVIDER_IDENTITY_CANNOT_REPLACE_CANONICAL_WORK_ITEM_IDENTITY",
    "STATE_TRANSITION_REQUIRES_SCOPED_AUTHORIZATION",
    "EVENT_DOES_NOT_AUTHORIZE_ACTION",
    "INTEGRATION_CREDENTIAL_CANNOT_BYPASS_SCOPED_AUTHORIZATION",
    "GUI_IS_NOT_ARCHITECTURAL_OR_RESOURCE_AUTHORITY",
    "GUI_HARDWARE_OBSERVATION_IS_NON_AUTHORITATIVE",
    "WORK_MANAGEMENT_RESOURCE_CLASSES_ARE_WORKLOAD_DRIVEN",
    "CPU_ONLY_WORK_MANAGEMENT_REQUIRES_NO_ACCELERATOR_LEASE",
    "ACCELERATOR_REQUEST_REQUIRES_HRB_ADMISSION_AND_FRESH_LEASE",
    "NO_SILENT_ACCELERATOR_TO_CPU_FALLBACK",
    "DISABLED_WORK_MANAGEMENT_PROVIDERS_ZERO_NEAR_ZERO_RUNTIME_COST",
    "PROVIDER_FAILURE_REQUIRES_EXPLICIT_RECONCILIATION",
    "GITHUB_ISSUES_IS_OPTIONAL_ADAPTER_NOT_AUTHORITY",
    "ACCELERATOR_GUARD_GUI_MUST_BE_REACHABLE",
    "WORK_MANAGEMENT_CAPABILITY_AND_AUTHORITY_COUNT_INVARIANT",
]


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def work_item_projection_valid(*, canonical_id: str, provider_id: str, external_id: str,
                               provider_revision: str, reconciliation_state: str,
                               provider_owns_canonical_identity: bool) -> bool:
    return bool(
        canonical_id and provider_id and external_id and provider_revision
        and reconciliation_state in {"SYNCED", "PENDING", "CONFLICT", "STALE", "DISCONNECTED"}
        and not provider_owns_canonical_identity
    )


def transition_valid(*, actor: str, scope: str, capability: str,
                     authorization_authority: str, decision: str,
                     event_implies_authorization: bool = False) -> bool:
    return bool(
        actor and scope and capability == "work_item.transition"
        and authorization_authority == "FA3-AUTH-SECURITY-GOV-001"
        and decision == "ALLOW" and not event_implies_authorization
    )


def resource_request_valid(*, resource_class: str, accelerator_required: bool,
                           hrb_authorized: bool, accelerator_lease_present: bool,
                           silent_fallback: bool) -> bool:
    if not hrb_authorized or silent_fallback:
        return False
    if accelerator_required:
        return resource_class in {"GPU", "NPU", "ACCELERATOR"} and accelerator_lease_present
    return resource_class in {"CPU_LIGHTWEIGHT", "CPU", "MEMORY", "IO", "NETWORK"} and not accelerator_lease_present


def disabled_provider_zero_cost(state: dict[str, Any]) -> bool:
    return all((
        state.get("resident_process_count") == 0,
        state.get("background_worker_count") == 0,
        state.get("network_session_count") == 0,
        state.get("accelerator_reservation_count") == 0,
        state.get("active_polling") is False,
    ))


def run_regressions() -> dict[str, Any]:
    cases = []

    def add(name: str, positive: bool, negative: bool) -> None:
        cases.append({"name": name, "status": "PASS" if positive and negative else "FAIL",
                      "positive_case": positive, "negative_case": negative})

    add(
        "provider-neutral work-item identity",
        work_item_projection_valid(canonical_id="FA3-WORK-1", provider_id=KANEO_ID,
            external_id="task:10", provider_revision="rev:2", reconciliation_state="SYNCED",
            provider_owns_canonical_identity=False),
        not work_item_projection_valid(canonical_id="", provider_id=KANBOARD_ID,
            external_id="42", provider_revision="rev:3", reconciliation_state="SYNCED",
            provider_owns_canonical_identity=True),
    )
    add(
        "scoped transition authorization",
        transition_valid(actor="user:1", scope="project:1", capability="work_item.transition",
            authorization_authority="FA3-AUTH-SECURITY-GOV-001", decision="ALLOW"),
        not transition_valid(actor="event", scope="project:1", capability="work_item.transition",
            authorization_authority="FA3-AUTH-SECURITY-GOV-001", decision="ALLOW",
            event_implies_authorization=True),
    )
    add(
        "CPU-only workload has no accelerator dependency",
        resource_request_valid(resource_class="CPU_LIGHTWEIGHT", accelerator_required=False,
            hrb_authorized=True, accelerator_lease_present=False, silent_fallback=False),
        not resource_request_valid(resource_class="CPU_LIGHTWEIGHT", accelerator_required=False,
            hrb_authorized=True, accelerator_lease_present=True, silent_fallback=False),
    )
    add(
        "accelerator workload requires explicit HRB lease",
        resource_request_valid(resource_class="GPU", accelerator_required=True,
            hrb_authorized=True, accelerator_lease_present=True, silent_fallback=False),
        not resource_request_valid(resource_class="GPU", accelerator_required=True,
            hrb_authorized=True, accelerator_lease_present=False, silent_fallback=False),
    )
    zero = {"resident_process_count": 0, "background_worker_count": 0,
            "network_session_count": 0, "accelerator_reservation_count": 0,
            "active_polling": False}
    add("disabled provider zero-cost", disabled_provider_zero_cost(zero),
        not disabled_provider_zero_cost({**zero, "background_worker_count": 1}))
    passed = sum(case["status"] == "PASS" for case in cases)
    return {"result": "PASS" if passed == len(cases) else "FAIL", "passed": passed,
            "total": len(cases), "cases": cases}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    fs: list[dict[str, Any]] = []
    paths = {
        "projection": root / "canonical/FA3-WORK-MANAGEMENT-PROJECTION-001.json",
        "contracts": root / "canonical/contracts/FA3-WORK-ITEM-PROJECTION-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-WORK-MANAGEMENT-GUI-2026-09-17.json",
        "enforcement": root / "canonical/work-management-enforcement.json",
        "kaneo": root / "canonical/providers/FA3-PROVIDER-KANEO-001.json",
        "kanboard": root / "canonical/providers/FA3-PROVIDER-KANBOARD-001.json",
        "resource": root / "canonical/FA3-RESOURCE-ADMISSION-CONTRACTS-001.json",
        "hardware": root / "canonical/decisions/FA3-DEC-HARDWARE-AUDIT-2026-09-20.json",
        "accelerator_guard": root / "canonical/profiles/FA3-ACCEL-GUARD-001.json",
        "policy": root / "canonical/enforcement-policy.json",
        "main_qml": root / "apps/fa3-control-center/qml/Main.qml",
        "work_qml": root / "apps/fa3-control-center/qml/WorkManagementPage.qml",
        "cmake": root / "apps/fa3-control-center/CMakeLists.txt",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        fs.append(finding("WM-001", "Required Work Management materialization file missing", missing=missing))
        report = {"schema":"fa3.work-management-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":fs}
        return report

    p = loadj(paths["projection"]); c = loadj(paths["contracts"]); e = loadj(paths["enforcement"])
    kaneo = loadj(paths["kaneo"]); kanboard = loadj(paths["kanboard"])
    resource = loadj(paths["resource"]); hardware = loadj(paths["hardware"])
    accel = loadj(paths["accelerator_guard"]); policy = loadj(paths["policy"])
    main_qml = paths["main_qml"].read_text(encoding="utf-8")
    work_qml = paths["work_qml"].read_text(encoding="utf-8")
    cmake = paths["cmake"].read_text(encoding="utf-8")

    if p.get("id") != PROJECTION_ID or p.get("new_capability") is not False or p.get("new_architectural_authority") is not False or p.get("capability_count") != CAPABILITY_COUNT:
        fs.append(finding("WM-002", "Projection capability/authority invariant drift"))
    gui = p.get("gui_surface", {})
    if gui.get("menu_label") != "Work Management" or gui.get("page_index") != 24 or gui.get("mandatory") is not True or gui.get("provider_neutral") is not True:
        fs.append(finding("WM-003", "Mandatory provider-neutral Work Management GUI contract drift"))
    if c.get("id") != CONTRACT_ID or c.get("capability_delta") != 0 or c.get("authority_delta") != 0:
        fs.append(finding("WM-004", "Work-item contract identity or delta drift"))
    if c.get("work_item_contract", {}).get("canonical_identity_may_equal_provider_object_id") is not False:
        fs.append(finding("WM-005", "Provider object identity may replace canonical work-item identity"))
    if c.get("mutation_contract", {}).get("authorization_authority") != "FA3-AUTH-SECURITY-GOV-001" or c.get("event_action_contract", {}).get("event_occurrence_implies_action_authorization") is not False:
        fs.append(finding("WM-006", "Authorization/event-action boundary drift"))

    for provider, expected_role in ((kaneo, "PRIMARY_INTERACTIVE_PROVIDER"), (kanboard, "SECONDARY_OPTIONAL_PROVIDER_AND_AUTOMATION_PATTERN_SOURCE")):
        wm = provider.get("work_management_projection", {})
        if wm.get("projection_id") != PROJECTION_ID or wm.get("gui_role") != expected_role or wm.get("shared_top_level_surface") != "Work Management" or wm.get("separate_top_level_menu") is not False:
            fs.append(finding("WM-007", "Provider is not bound to the shared Work Management surface", provider_id=provider.get("id")))
        ra = provider.get("resource_admission", {})
        if ra.get("contract_id") != "FA3-RESOURCE-ADMISSION-CONTRACTS-001" or ra.get("default_resource_class") != "CPU_LIGHTWEIGHT" or ra.get("accelerator_required_by_default") is not False or ra.get("provider_self_admission_forbidden") is not True:
            fs.append(finding("WM-008", "Provider resource semantics are not workload-driven CPU-lightweight by default", provider_id=provider.get("id")))

    sem = resource.get("admission_semantics", {})
    if sem.get("workload_driven_resource_classes") is not True or sem.get("cpu_only_workload_must_not_require_accelerator_discovery_or_accelerator_lease") is not True or resource.get("authoritative_admission_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        fs.append(finding("WM-009", "Canonical resource-admission semantics incompatible with Work Management"))
    if (
        hardware.get("authority", {}).get("discovery") != "NON_AUTHORITY_CAPABILITY"
        or hardware.get("authority", {}).get("resource_admission_placement_reservation_lease") != "FA3-AUTH-HOST-RESOURCE-BROKER-001"
    ):
        fs.append(finding("WM-010", "Hardware discovery/resource-admission authority boundary drift"))
    if accel.get("id") != "FA3-ACCEL-GUARD-001" or accel.get("new_architectural_authority") is not False:
        fs.append(finding("WM-011", "Accelerator Guard boundary drift"))

    if e.get("gate_id") != GATE_ID or e.get("p0_invariants") != P0_INVARIANTS or e.get("mandatory_rule_count") != len(P0_INVARIANTS):
        fs.append(finding("WM-012", "Work Management enforcement invariant set drift"))
    if GATE_ID not in policy.get("mandatory_reference_gates", []) or policy.get("work_management_mandatory_p0_rules") != P0_INVARIANTS:
        fs.append(finding("WM-013", "Work Management gate is not globally bound"))

    required_main = [
        'label: "Work Management"; routeId: "home.work-management"',
        'title: "Work Management"',
        'WorkManagementPage {',
        'label: "Accelerator Guard"; routeId: "system.accelerator-guard"',
        'title: "Accelerator Guard"',
        'AcceleratorGuardPage {',
        '"home.work-management": 24',
        '"system.accelerator-guard": 25',
    ]
    absent = [item for item in required_main if item not in main_qml]
    if absent or 'label: "Kaneo"' in main_qml or 'label: "Kanboard"' in main_qml:
        fs.append(finding("WM-014", "Mandatory shared GUI navigation or accelerator-guard reachability drift", missing=absent))
    if "qml/WorkManagementPage.qml" not in cmake or "qml/AcceleratorGuardPage.qml" not in cmake:
        fs.append(finding("WM-015", "Required QML pages are not registered in CMake"))
    for text in ("Kaneo", "Kanboard", "GitHub Issues", "CPU-lightweight", "HRB", "provider-neutral"):
        if text not in work_qml:
            fs.append(finding("WM-016", "Work Management page omits mandatory operator context", token=text))

    regressions = run_regressions()
    if regressions["result"] != "PASS":
        fs.append(finding("WM-017", "Executable Work Management regressions failed", regressions=regressions))

    report = {
        "schema": "fa3.work-management-gate-report.v1",
        "gate_id": GATE_ID,
        "projection_id": PROJECTION_ID,
        "result": "PASS" if not fs else "FAIL",
        "blocking_findings": len(fs),
        "findings": fs,
        "regressions": regressions,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "gui": {
            "work_management_route_id": "home.work-management",
            "work_management_page_index": 24,
            "accelerator_guard_route_id": "system.accelerator-guard",
            "accelerator_guard_page_index": 25,
        },
    }
    out = root / "reports/work-management-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = gate(root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
