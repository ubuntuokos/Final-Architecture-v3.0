#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fa3_buzz_global_reconcile as common  # noqa: E402

PROJECTION_ID = "FA3-WORK-MANAGEMENT-PROJECTION-001"
CONTRACT_ID = "FA3-WORK-ITEM-PROJECTION-CONTRACTS-001"
GATESET_ID = "FA3-WORK-MANAGEMENT-GATESET-001"
KANEO_ID = "FA3-PROVIDER-KANEO-001"
KANBOARD_ID = "FA3-PROVIDER-KANBOARD-001"
CAPABILITY_COUNT = 143
POLICY = "canonical/enforcement-policy.json"
ENFORCEMENT = "canonical/work-management-enforcement.json"
RELEASE = common.RELEASE
FA3_ENFORCE = "src/fa3_enforce.py"
PERMANENT_WORKFLOW = ".github/workflows/fa3-permanent-enforcement.yml"
MAIN_QML = "apps/fa3-control-center/qml/Main.qml"
CMAKE = "apps/fa3-control-center/CMakeLists.txt"
RECONCILIATION_STATUS = "GLOBAL_RELEASE_INVENTORY_RECONCILED_MANDATORY_GUI_AND_GATE_ENFORCED"


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write(rel: str, obj: dict[str, Any]) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"{label} anchor missing")
    return text.replace(old, new, 1)


def patch_policy() -> None:
    policy = load(POLICY)
    if policy.get("canonical_capability_count") != CAPABILITY_COUNT:
        raise RuntimeError("FA3 capability count must remain exactly 143")
    gates = policy.setdefault("mandatory_reference_gates", [])
    if GATESET_ID not in gates:
        gates.append(GATESET_ID)
    if len(gates) != len(set(gates)):
        raise RuntimeError("mandatory_reference_gates must remain unique")
    enforcement = load(ENFORCEMENT)
    policy["work_management_projection_id"] = PROJECTION_ID
    policy["work_management_contract_id"] = CONTRACT_ID
    policy["work_management_provider_ids"] = [KANEO_ID, KANBOARD_ID]
    policy["work_management_gui_menu"] = {"label": "Work Management", "page_index": 24, "mandatory": True}
    policy["work_management_accelerator_guard_gui"] = {"profile_id": "FA3-ACCEL-GUARD-001", "page_index": 25, "mandatory_reachability": True}
    policy["work_management_mandatory_p0_rules"] = list(enforcement.get("p0_invariants", []))
    write(POLICY, policy)


def patch_providers() -> None:
    specs = {
        "canonical/providers/FA3-PROVIDER-KANEO-001.json": "PRIMARY_INTERACTIVE_PROVIDER",
        "canonical/providers/FA3-PROVIDER-KANBOARD-001.json": "SECONDARY_OPTIONAL_PROVIDER_AND_AUTOMATION_PATTERN_SOURCE",
    }
    for rel, role in specs.items():
        obj = load(rel)
        if obj.get("capability_count") != CAPABILITY_COUNT or obj.get("architectural_authority") is not False:
            raise RuntimeError(f"provider invariant drift before Work Management binding: {rel}")
        obj["work_management_projection"] = {
            "projection_id": PROJECTION_ID,
            "contract_id": CONTRACT_ID,
            "shared_top_level_surface": "Work Management",
            "gui_role": role,
            "separate_top_level_menu": False,
            "provider_origin_is_metadata": True,
        }
        obj["resource_admission"] = {
            "contract_id": "FA3-RESOURCE-ADMISSION-CONTRACTS-001",
            "authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "default_resource_class": "CPU_LIGHTWEIGHT",
            "accelerator_required_by_default": False,
            "provider_self_admission_forbidden": True,
            "accelerator_conflict_profile": "FA3-ACCEL-GUARD-001",
        }
        write(rel, obj)


def patch_cmake() -> None:
    path = ROOT / CMAKE
    text = path.read_text(encoding="utf-8")
    prop_anchor = "set_source_files_properties(qml/AcceleratorGuardPage.qml PROPERTIES QT_RESOURCE_ALIAS AcceleratorGuardPage.qml)\n"
    prop_new = prop_anchor + "set_source_files_properties(qml/WorkManagementPage.qml PROPERTIES QT_RESOURCE_ALIAS WorkManagementPage.qml)\n"
    if "QT_RESOURCE_ALIAS WorkManagementPage.qml" not in text:
        text = replace_once(text, prop_anchor, prop_new, "CMake WorkManagement property")
    qml_anchor = "        qml/AcceleratorGuardPage.qml\n"
    qml_new = qml_anchor + "        qml/WorkManagementPage.qml\n"
    if "        qml/WorkManagementPage.qml\n" not in text:
        text = replace_once(text, qml_anchor, qml_new, "CMake WorkManagement QML")
    path.write_text(text, encoding="utf-8")


def patch_main_qml() -> None:
    path = ROOT / MAIN_QML
    text = path.read_text(encoding="utf-8")

    search_anchor = '        {title: "Projects & Workspaces", detail: "Projektek, assetek és knowledge-contextus", category: "FUNCTION", pageIndex: 2},\n'
    search_add = (
        search_anchor
        + '        {title: "Work Management", detail: "Kaneo + Kanboard provider-neutral projects, boards, tasks és automation", category: "FUNCTION", pageIndex: 24},\n'
        + '        {title: "Tasks & Boards", detail: "Provider-neutral work-item projection és reconciliation", category: "FUNCTION", pageIndex: 24},\n'
        + '        {title: "Accelerator Guard", detail: "GPU/NPU contention és explicit user arbitration", category: "FUNCTION", pageIndex: 25},\n'
    )
    if 'title: "Work Management"' not in text:
        text = replace_once(text, search_anchor, search_add, "Main.qml search index")

    nav_anchor = '                        NavButton { iconText: "▣"; label: "Projects"; pageIndex: 2 }\n'
    nav_add = (
        nav_anchor
        + '                        NavButton { iconText: "✓"; label: "Work Management"; pageIndex: 24 }\n'
        + '                        NavButton { iconText: "⚡"; label: "Accelerator Guard"; pageIndex: 25 }\n'
    )
    if 'label: "Work Management"; pageIndex: 24' not in text:
        text = replace_once(text, nav_anchor, nav_add, "Main.qml navigation")

    if "                WorkManagementPage {\n" not in text:
        stack_anchor = (
            "                LanguageControlPage {\n"
            "                    preferences: fa3Preferences\n"
            "                    panel: window.panel\n"
            "                    panelRaised: window.panelRaised\n"
            "                    border: window.border\n"
            "                    textPrimary: window.textPrimary\n"
            "                    textMuted: window.textMuted\n"
            "                    accent: window.accent\n"
            "                    green: window.green\n"
            "                    orange: window.orange\n"
            "                }\n"
            "            }\n"
        )
        stack_new = (
            "                LanguageControlPage {\n"
            "                    preferences: fa3Preferences\n"
            "                    panel: window.panel\n"
            "                    panelRaised: window.panelRaised\n"
            "                    border: window.border\n"
            "                    textPrimary: window.textPrimary\n"
            "                    textMuted: window.textMuted\n"
            "                    accent: window.accent\n"
            "                    green: window.green\n"
            "                    orange: window.orange\n"
            "                }\n\n"
            "                WorkManagementPage {\n"
            "                    panel: window.panel\n"
            "                    panelRaised: window.panelRaised\n"
            "                    border: window.border\n"
            "                    textPrimary: window.textPrimary\n"
            "                    textMuted: window.textMuted\n"
            "                    accent: window.accent\n"
            "                    green: window.green\n"
            "                    orange: window.orange\n"
            "                    magenta: window.magenta\n"
            "                }\n\n"
            "                AcceleratorGuardPage {\n"
            "                    panel: window.panel\n"
            "                    panelRaised: window.panelRaised\n"
            "                    border: window.border\n"
            "                    textPrimary: window.textPrimary\n"
            "                    textMuted: window.textMuted\n"
            "                    accent: window.accent\n"
            "                    green: window.green\n"
            "                    orange: window.orange\n"
            "                    magenta: window.magenta\n"
            "                }\n"
            "            }\n"
        )
        text = replace_once(text, stack_anchor, stack_new, "Main.qml StackLayout tail")

    path.write_text(text, encoding="utf-8")


def patch_fa3_enforce() -> None:
    path = ROOT / FA3_ENFORCE
    text = path.read_text(encoding="utf-8")
    import_line = "from fa3_work_management_gate import gate as work_management_gate\n"
    if import_line not in text:
        anchor = "from fa3_kanboard_gate import gate as kanboard_gate\n"
        text = replace_once(text, anchor, anchor + import_line, "fa3_enforce import")

    policy_check = (
        "    if \"FA3-WORK-MANAGEMENT-GATESET-001\" not in pol.get(\"mandatory_reference_gates\",[]):\n"
        "        fs.append(finding(\"FA3-STATIC-106\",\"Work Management mandatory GUI/provider-neutral gate is not bound into global enforcement policy\"))\n"
    )
    if policy_check not in text:
        anchor = "    if len(rows)!=CAPS or ids!=expected:\n"
        text = replace_once(text, anchor, policy_check + "\n" + anchor, "fa3_enforce static policy")

    gate_check = (
        "    work_management_ref=work_management_gate(root)\n"
        "    if work_management_ref[\"result\"]!=\"PASS\":\n"
        "        fs.append(finding(\"FA3-STATIC-107\",\"Work Management provider-neutral GUI gate failed\",work_management_gate=work_management_ref))\n"
    )
    if gate_check not in text:
        anchor = "    result=\"PASS\" if not fs else \"FAIL\"\n"
        text = replace_once(text, anchor, gate_check + "\n" + anchor, "fa3_enforce static gate")

    if '"work-management"' not in text:
        anchor = '"kaneo","kanboard","buzz"'
        text = replace_once(text, anchor, '"kaneo","kanboard","work-management","buzz"', "fa3_enforce command choice")

    handler = (
        "        if a.command==\"work-management\":\n"
        "            x=work_management_gate(root); print(json.dumps(x,indent=2)); return OK if x[\"result\"]==\"PASS\" else BLOCKED\n"
    )
    if handler not in text:
        anchor = "        if a.command==\"buzz\":\n"
        text = replace_once(text, anchor, handler + anchor, "fa3_enforce handler")
    path.write_text(text, encoding="utf-8")


def patch_permanent_workflow() -> None:
    path = ROOT / PERMANENT_WORKFLOW
    text = path.read_text(encoding="utf-8")
    gate_path = "src/fa3_work_management_gate.py"
    if gate_path not in text:
        anchor = "src/fa3_kaneo_gate.py src/fa3_kanboard_gate.py"
        text = replace_once(text, anchor, anchor + " " + gate_path, "permanent workflow syntax")

    step = (
        "      - name: Work Management provider-neutral GUI/resource gate\n"
        "        run: ./bin/fa3-enforce work-management\n"
    )
    if step not in text:
        anchor = "      - name: Buzz authority-separation regression gate\n"
        text = replace_once(text, anchor, step + anchor, "permanent workflow step")

    report = "            reports/work-management-gate-report.json\n"
    if report not in text:
        anchor = "            reports/kanboard-gate-report.json\n"
        text = replace_once(text, anchor, anchor + report, "permanent workflow report")
    path.write_text(text, encoding="utf-8")


def patch_release_semantics() -> None:
    release = load(RELEASE)
    policy = load(POLICY)
    release["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    release["work_management_reconciliation"] = {
        "projection_id": PROJECTION_ID,
        "contract_id": CONTRACT_ID,
        "gateset_id": GATESET_ID,
        "provider_ids": [KANEO_ID, KANBOARD_ID],
        "optional_external_adapter_type": "GITHUB_ISSUES",
        "gui_menu": "Work Management",
        "gui_page_index": 24,
        "accelerator_guard_gui_page_index": 25,
        "resource_admission_contract": "FA3-RESOURCE-ADMISSION-CONTRACTS-001",
        "resource_admission_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "default_resource_class": "CPU_LIGHTWEIGHT",
        "accelerator_required_by_default": False,
        "gui_hardware_probe_authority": False,
        "reconciliation_status": RECONCILIATION_STATUS,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
    }
    note = (
        "FA3-WORK-MANAGEMENT-PROJECTION-001 globally reconciles Kaneo and Kanboard behind one mandatory "
        "provider-neutral Work Management Control Center menu. Provider identity remains projection metadata; "
        "resource admission is workload-driven and HRB-authoritative, CPU-lightweight by default, and the existing "
        "Accelerator Guard decision surface is made GUI-reachable. Capability count remains 143 and no authority is added."
    )
    notes = release.setdefault("review_notes", [])
    if note not in notes:
        notes.append(note)
    write(RELEASE, release)


def prepare_only() -> None:
    patch_policy()
    patch_providers()
    patch_cmake()
    patch_main_qml()
    patch_fa3_enforce()
    patch_permanent_workflow()


def projection_only(snapshot_head: str) -> None:
    snapshot = common.git("rev-parse", "--verify", f"{snapshot_head}^{{commit}}")
    current = common.git("rev-parse", "HEAD")
    if snapshot != current:
        raise RuntimeError("projection snapshot must equal clean checked-out HEAD before regeneration")
    dirty = common.dirty_release_surface_paths()
    if dirty:
        raise RuntimeError(f"projection-only requires clean committed release surface: {dirty}")
    patch_release_semantics()
    common.regenerate_release(snapshot)
    release = load(RELEASE)
    verification = release.setdefault("manifest_verification", {})
    verification["work_management_reconciliation_generator"] = "tools/fa3_work_management_global_reconcile.py"
    verification["work_management_deterministic_regeneration_pass"] = True
    verification["work_management_snapshot_head"] = snapshot
    write(RELEASE, release)
    dirty_after = common.dirty_release_surface_paths()
    if dirty_after != [RELEASE]:
        raise RuntimeError("projection-only may modify exactly unified release projection; observed: " + ", ".join(dirty_after))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FA3 Work Management deterministic global reconciliation")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--projection-only", action="store_true")
    parser.add_argument("--snapshot-head")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare_only:
        prepare_only()
        print(json.dumps({"result":"PASS","mode":"PREPARE_ONLY","projection_id":PROJECTION_ID,"gateset_id":GATESET_ID}, indent=2))
        return 0
    snapshot_head = args.snapshot_head or common.git("rev-parse", "HEAD")
    projection_only(snapshot_head)
    print(json.dumps({"result":"PASS","mode":"PROJECTION_ONLY","projection_id":PROJECTION_ID,"snapshot_head":snapshot_head,"reconciliation_status":RECONCILIATION_STATUS}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
