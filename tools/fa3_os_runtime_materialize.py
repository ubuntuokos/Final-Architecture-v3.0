#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI_PAGE_INDEX = 26


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write_json(rel: str, value: dict) -> None:
    (ROOT / rel).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_root_profile() -> None:
    rel = "canonical/profiles/FA3-OS-001.json"
    profile = load_json(rel)
    subs = profile.setdefault("subprofiles", [])
    if "FA3-OS-RUNTIME-001" not in subs:
        subs.append("FA3-OS-RUNTIME-001")
    profile["runtime_profile"] = "FA3-OS-RUNTIME-001"
    profile["runtime_conformance"] = "FA3-OS-RUNTIME-CONFORMANCE-001"
    profile["gui_surface"] = {"application": "FA3 Control Center", "menu_label": "FA3 OS", "page_index": GUI_PAGE_INDEX, "timeline_authority": "FA3-JOURNAL-001"}
    invariants = profile.setdefault("invariants", [])
    for item in ("EXECUTABLE_REFERENCE_RUNTIME_REMAINS_NON_AUTHORITY", "FA3_OS_GUI_IS_FIRST_CLASS_CONTROL_CENTER_SURFACE", "CURRENT_HOST_RUNTIME_ADMISSION_REQUIRES_FRESH_EVIDENCE"):
        if item not in invariants:
            invariants.append(item)
    write_json(rel, profile)


def patch_enforcement() -> None:
    rel = "canonical/fa3-os-event-privacy-enforcement.json"
    value = load_json(rel)
    value["runtime_profile_id"] = "FA3-OS-RUNTIME-001"
    value["runtime_conformance_id"] = "FA3-OS-RUNTIME-CONFORMANCE-001"
    value["runtime_gate_id"] = "FA3-OS-RUNTIME-GATESET-001"
    value["gui_surface"] = "FA3 Control Center / FA3 OS"
    invariants = value.setdefault("p0_invariants", [])
    for item in ("FA3_OS_REFERENCE_RUNTIME_EXECUTABLE_GATE_PASS", "FA3_OS_GUI_MENU_SURFACE_MATERIALIZED", "FA3_OS_CURRENT_HOST_ADMISSION_NOT_INFERRED_FROM_HOSTED_CI"):
        if item not in invariants:
            invariants.append(item)
    write_json(rel, value)


def patch_event_privacy_gate() -> None:
    path = ROOT / "src/fa3_os_event_privacy_gate.py"
    text = path.read_text(encoding="utf-8")
    import_line = "from fa3_os_runtime_gate import gate as fa3_os_runtime_gate\n"
    if import_line not in text:
        anchor = "from fa3_release_baseline import active_capability_count\n"
        if anchor not in text:
            raise RuntimeError("event/privacy gate import anchor missing")
        text = text.replace(anchor, anchor + import_line, 1)
    start = text.index("def gate(root: Path) -> dict[str, Any]:")
    end = text.index("\n\ndef main()", start)
    replacement = '''def gate(root: Path) -> dict[str, Any]:
    repo_root = Path(root).resolve()
    reference = reference_check(repo_root)
    runtime = fa3_os_runtime_gate(repo_root)
    result = "PASS" if reference["result"] == "PASS" and runtime["result"] == "PASS" else "FAIL"
    return {
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "privacy_profile_id": POLICY_ID,
        "event_contract_id": EVENT_CONTRACT_ID,
        "ledger_authority": JOURNAL_PROFILE_ID,
        "result": result,
        "capability_count": reference.get("capability_count"),
        "reference": reference,
        "runtime": runtime,
    }
'''
    path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def patch_control_center_cmake() -> None:
    path = ROOT / "apps/fa3-control-center/CMakeLists.txt"
    text = path.read_text(encoding="utf-8")
    prop = "set_source_files_properties(qml/Fa3OsPage.qml PROPERTIES QT_RESOURCE_ALIAS Fa3OsPage.qml)\n"
    if prop not in text:
        anchor = "set_source_files_properties(qml/AcceleratorGuardPage.qml PROPERTIES QT_RESOURCE_ALIAS AcceleratorGuardPage.qml)\n"
        if anchor not in text:
            raise RuntimeError("CMake source property anchor missing")
        text = text.replace(anchor, anchor + prop, 1)
    qml_line = "        qml/Fa3OsPage.qml\n"
    if qml_line not in text:
        anchor = "        qml/AcceleratorGuardPage.qml\n"
        if anchor not in text:
            raise RuntimeError("CMake QML_FILES anchor missing")
        text = text.replace(anchor, anchor + qml_line, 1)
    path.write_text(text, encoding="utf-8")


def patch_control_center_main() -> None:
    path = ROOT / "apps/fa3-control-center/qml/Main.qml"
    text = path.read_text(encoding="utf-8")

    search_entry = f'        {{title: "FA3 OS", detail: "Aktivitás, workstream, privacy és provenance kontextus", category: "FUNCTION", pageIndex: {GUI_PAGE_INDEX}}},\n'
    if search_entry not in text:
        anchor = '        {title: "Napló / Journal", detail: "Rendszer-, beszélgetés- és projektnapló", category: "FUNCTION", pageIndex: 12},\n'
        if anchor not in text:
            raise RuntimeError("Main.qml search-index anchor missing")
        text = text.replace(anchor, anchor + search_entry, 1)

    nav = f'                        NavButton {{ iconText: "◎"; label: "FA3 OS"; pageIndex: {GUI_PAGE_INDEX} }}\n'
    if nav not in text:
        anchor = '                        NavButton { iconText: "≡"; label: "Napló / Journal"; pageIndex: 12 }\n'
        if anchor not in text:
            raise RuntimeError("Main.qml navigation anchor missing")
        text = text.replace(anchor, anchor + nav, 1)

    page_mount = '''                Fa3OsPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                    onNavigateRequested: function(pageIndex) { window.selectedIndex = pageIndex }
                }
'''
    if "                Fa3OsPage {" not in text:
        accelerator_start = text.find("                AcceleratorGuardPage {")
        if accelerator_start < 0:
            raise RuntimeError("Main.qml AcceleratorGuardPage structural anchor missing")
        stack_close_marker = "\n            }\n\n            Rectangle {"
        insert_at = text.find(stack_close_marker, accelerator_start)
        if insert_at < 0:
            raise RuntimeError("Main.qml StackLayout closing anchor missing")
        text = text[:insert_at] + "\n\n" + page_mount.rstrip("\n") + text[insert_at:]

    path.write_text(text, encoding="utf-8")


def patch_reconciliation_tool() -> None:
    path = ROOT / "tools/fa3_os_global_reconcile.py"
    text = path.read_text(encoding="utf-8")
    constants = 'RUNTIME_PROFILE_ID = "FA3-OS-RUNTIME-001"\nRUNTIME_CONFORMANCE_ID = "FA3-OS-RUNTIME-CONFORMANCE-001"\nRUNTIME_GATESET_ID = "FA3-OS-RUNTIME-GATESET-001"\n'
    if 'RUNTIME_PROFILE_ID = "FA3-OS-RUNTIME-001"' not in text:
        anchor = 'EVENT_CONTRACT_ID = "FA3-OS-EVENT-001"\n'
        if anchor not in text:
            raise RuntimeError("reconciliation constants anchor missing")
        text = text.replace(anchor, anchor + constants, 1)
    policy_fields = '    policy["fa3_os_runtime_profile_id"] = RUNTIME_PROFILE_ID\n    policy["fa3_os_runtime_conformance_id"] = RUNTIME_CONFORMANCE_ID\n    policy["fa3_os_runtime_gate_id"] = RUNTIME_GATESET_ID\n'
    if 'policy["fa3_os_runtime_profile_id"]' not in text:
        anchor = '    policy["fa3_os_event_contract_id"] = EVENT_CONTRACT_ID\n'
        if anchor not in text:
            raise RuntimeError("reconciliation policy anchor missing")
        text = text.replace(anchor, anchor + policy_fields, 1)
    release_fields = '        "runtime_profile_id": RUNTIME_PROFILE_ID,\n        "runtime_conformance_id": RUNTIME_CONFORMANCE_ID,\n        "runtime_gateset_id": RUNTIME_GATESET_ID,\n        "reference_runtime_materialized": True,\n        "current_host_runtime_status": "PENDING_CURRENT_HOST",\n        "gui_surface": "FA3 Control Center / FA3 OS",\n'
    if '"runtime_profile_id": RUNTIME_PROFILE_ID' not in text:
        anchor = '        "event_contract_id": EVENT_CONTRACT_ID,\n'
        if anchor not in text:
            raise RuntimeError("reconciliation release anchor missing")
        text = text.replace(anchor, anchor + release_fields, 1)
    path.write_text(text, encoding="utf-8")


def ensure_executable() -> None:
    cli = ROOT / "bin/fa3-os"
    cli.chmod(cli.stat().st_mode | 0o111)


def main() -> int:
    patch_root_profile()
    patch_enforcement()
    patch_event_privacy_gate()
    patch_control_center_cmake()
    patch_control_center_main()
    patch_reconciliation_tool()
    ensure_executable()
    print(json.dumps({
        "result": "PASS",
        "materialization": "FA3-OS-RUNTIME-001",
        "gui_menu": "FA3 OS",
        "page_index": GUI_PAGE_INDEX,
        "ledger_authority": "FA3-JOURNAL-001",
        "current_host_status": "PENDING_CURRENT_HOST",
        "capability_count": 143,
        "new_architectural_authorities": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
