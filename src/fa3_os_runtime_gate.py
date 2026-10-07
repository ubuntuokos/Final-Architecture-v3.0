#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_os_runtime import run_reference_conformance
from fa3_release_baseline import active_capability_count

GATE_ID = "FA3-OS-RUNTIME-GATESET-001"
PROFILE_ID = "FA3-OS-RUNTIME-001"
PARENT_PROFILE_ID = "FA3-OS-001"
CONFORMANCE_ID = "FA3-OS-RUNTIME-CONFORMANCE-001"
JOURNAL_AUTHORITY = "FA3-JOURNAL-001"
GUI_PAGE_INDEX = 26
GUI_ROUTE_ID = "integrations.fa3-os"
WORK_MANAGEMENT_ROUTE_ID = "home.work-management"
ACCELERATOR_GUARD_ROUTE_ID = "system.accelerator-guard"

PROFILE_PATH = Path("canonical/profiles/FA3-OS-RUNTIME-001.json")
ROOT_PROFILE_PATH = Path("canonical/profiles/FA3-OS-001.json")
CONFORMANCE_PATH = Path("canonical/FA3-OS-RUNTIME-CONFORMANCE-001.json")
RUNTIME_PATH = Path("src/fa3_os_runtime.py")
CLI_PATH = Path("bin/fa3-os")
GUI_PAGE_PATH = Path("apps/fa3-control-center/qml/Fa3OsPage.qml")
GUI_MAIN_PATH = Path("apps/fa3-control-center/qml/Main.qml")
GUI_CMAKE_PATH = Path("apps/fa3-control-center/CMakeLists.txt")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _require(ok: bool, findings: list[dict[str, Any]], code: str, message: str, **details: Any) -> None:
    if not ok:
        findings.append(_finding(code, message, **details))


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    required = [PROFILE_PATH, ROOT_PROFILE_PATH, CONFORMANCE_PATH, RUNTIME_PATH, CLI_PATH, GUI_PAGE_PATH, GUI_MAIN_PATH, GUI_CMAKE_PATH]
    for rel in required:
        _require((root / rel).is_file(), findings, "FA3-OS-RUNTIME-REF-001", "Required runtime materialization artifact missing", path=str(rel))
    if findings:
        return {"gate_id": GATE_ID, "profile_id": PROFILE_ID, "result": "FAIL", "findings": findings}
    try:
        profile = _load(root / PROFILE_PATH)
        parent = _load(root / ROOT_PROFILE_PATH)
        conformance = _load(root / CONFORMANCE_PATH)
        capability_count = active_capability_count(root)
    except Exception as exc:
        return {"gate_id": GATE_ID, "profile_id": PROFILE_ID, "result": "FAIL", "findings": [_finding("FA3-OS-RUNTIME-REF-002", "Runtime canonical artifacts could not be loaded", error=str(exc))]}

    _require(profile.get("schema") == "fa3.profile-record.v1", findings, "FA3-OS-RUNTIME-PROFILE-001", "Runtime profile schema drift")
    _require(profile.get("id") == PROFILE_ID, findings, "FA3-OS-RUNTIME-PROFILE-002", "Runtime profile identity drift")
    _require(profile.get("parent_profile") == PARENT_PROFILE_ID and profile.get("relationship") == "SUBPROFILE-OF", findings, "FA3-OS-RUNTIME-PROFILE-003", "Runtime parent relationship drift")
    _require(profile.get("canonical_root") is False, findings, "FA3-OS-RUNTIME-AUTH-001", "Runtime became a canonical root")
    _require(profile.get("new_architectural_authority") is False, findings, "FA3-OS-RUNTIME-AUTH-002", "Runtime introduced architectural authority")
    _require(profile.get("new_capability") is False, findings, "FA3-OS-RUNTIME-CAP-001", "Runtime introduced a new capability")
    _require(profile.get("capability_count") == capability_count, findings, "FA3-OS-RUNTIME-CAP-002", "Capability count drift")
    _require(profile.get("ledger_authority") == JOURNAL_AUTHORITY, findings, "FA3-OS-RUNTIME-AUTH-003", "Runtime ledger authority drift")
    _require(profile.get("runtime_gate") == GATE_ID, findings, "FA3-OS-RUNTIME-GATE-001", "Runtime gate binding drift")
    _require(profile.get("current_host_conformance") == CONFORMANCE_ID, findings, "FA3-OS-RUNTIME-HOST-001", "Current-host conformance binding drift")
    _require(PROFILE_ID in set(parent.get("subprofiles", [])), findings, "FA3-OS-RUNTIME-PARENT-001", "FA3 OS root does not project the runtime subprofile")
    gui_surface = profile.get("gui_surface", {})
    _require(gui_surface.get("page_index") == GUI_PAGE_INDEX, findings, "FA3-OS-RUNTIME-GUI-000", "Runtime profile GUI page index drift", expected=GUI_PAGE_INDEX)
    _require(gui_surface.get("semantic_route_id") == GUI_ROUTE_ID, findings, "FA3-OS-RUNTIME-GUI-000A", "Runtime profile semantic GUI route drift", expected=GUI_ROUTE_ID)

    projection = profile.get("projection_policy", {})
    _require(projection.get("authoritative_history") is False and projection.get("rebuildable") is True, findings, "FA3-OS-RUNTIME-PROJ-001", "Derived projection authority boundary drift")
    boundaries = profile.get("authority_boundaries", {})
    _require(boundaries.get("execution_authority") is False, findings, "FA3-OS-RUNTIME-AUTH-004", "Runtime gained execution authority")
    _require(boundaries.get("orchestration_authority") is False and boundaries.get("resource_authority") is False, findings, "FA3-OS-RUNTIME-AUTH-005", "Runtime crossed orchestration/resource authority boundary")

    _require(conformance.get("schema") == "fa3.runtime-conformance-record.v1", findings, "FA3-OS-RUNTIME-CONF-001", "Runtime conformance schema drift")
    _require(conformance.get("id") == CONFORMANCE_ID and conformance.get("profile_id") == PROFILE_ID, findings, "FA3-OS-RUNTIME-CONF-002", "Runtime conformance identity drift")
    conformance_status = conformance.get("status")
    _require(conformance_status in {"PENDING_CURRENT_HOST", "CURRENT_HOST_ADMITTED"}, findings, "FA3-OS-RUNTIME-CONF-003", "Unknown current-host conformance status")
    if conformance_status == "PENDING_CURRENT_HOST":
        _require(
            conformance.get("production_admitted") is False
            and conformance.get("promotion_claimed") is False
            and conformance.get("evidence_present") is False,
            findings,
            "FA3-OS-RUNTIME-CONF-004",
            "Pending current-host state must remain fail-closed",
        )
    elif conformance_status == "CURRENT_HOST_ADMITTED":
        evidence_ref = str(conformance.get("current_host_evidence_ref", "")).strip()
        _require(
            conformance.get("production_admitted") is True
            and conformance.get("promotion_claimed") is False
            and conformance.get("evidence_present") is True,
            findings,
            "FA3-OS-RUNTIME-CONF-005",
            "Admitted current-host state is missing verified component evidence semantics",
        )
        _require(bool(evidence_ref) and (root / evidence_ref).is_file(), findings, "FA3-OS-RUNTIME-CONF-006", "Durable current-host evidence reference is missing")
        _require(
            conformance.get("agent_exposure_admitted") is False
            and conformance.get("agent_exposure_status") == "ADAPTER_GATED",
            findings,
            "FA3-OS-RUNTIME-CONF-007",
            "Current-host runtime admission improperly promoted agent exposure",
        )
        if evidence_ref and (root / evidence_ref).is_file():
            try:
                evidence_ref_record = _load(root / evidence_ref)
                _require(evidence_ref_record.get("result") == "PASS", findings, "FA3-OS-RUNTIME-CONF-008", "Durable current-host evidence does not claim PASS")
                _require(evidence_ref_record.get("production_admitted") is True, findings, "FA3-OS-RUNTIME-CONF-009", "Durable evidence does not bind production admission")
                _require(evidence_ref_record.get("global_promotion_claim") is False, findings, "FA3-OS-RUNTIME-CONF-010", "Component evidence improperly claims global promotion")
                _require(evidence_ref_record.get("agent_exposure_admitted") is False, findings, "FA3-OS-RUNTIME-CONF-011", "Component evidence improperly admits agent exposure")
            except Exception as exc:
                findings.append(_finding("FA3-OS-RUNTIME-CONF-012", "Durable current-host evidence could not be validated", error=str(exc)))

    main_qml = (root / GUI_MAIN_PATH).read_text(encoding="utf-8")
    cmake = (root / GUI_CMAKE_PATH).read_text(encoding="utf-8")
    page = (root / GUI_PAGE_PATH).read_text(encoding="utf-8")
    _require(f'label: "FA3 OS"; routeId: "{GUI_ROUTE_ID}"' in main_qml, findings, "FA3-OS-RUNTIME-GUI-001", "FA3 OS first-class navigation item missing")
    _require('title: "FA3 OS"' in main_qml and f'routeId: "{GUI_ROUTE_ID}"' in main_qml, findings, "FA3-OS-RUNTIME-GUI-002", "FA3 OS global search route missing")
    _require(f'"{GUI_ROUTE_ID}": {GUI_PAGE_INDEX}' in main_qml, findings, "FA3-OS-RUNTIME-GUI-002A", "FA3 OS semantic route is not bound to the expected internal slot")
    _require("Fa3OsPage {" in main_qml, findings, "FA3-OS-RUNTIME-GUI-003", "FA3 OS page is not mounted in the Control Center")
    _require("qml/Fa3OsPage.qml" in cmake, findings, "FA3-OS-RUNTIME-GUI-004", "FA3 OS page is not packaged by CMake")
    if conformance_status == "CURRENT_HOST_ADMITTED":
        _require("CURRENT HOST E2E ADMITTED" in page, findings, "FA3-OS-RUNTIME-GUI-005", "GUI does not expose admitted current-host state")
        _require("AGENT EXPOSURE ADAPTER-GATED" in page, findings, "FA3-OS-RUNTIME-GUI-008A", "GUI does not preserve the agent-exposure boundary")
    else:
        _require("CURRENT HOST E2E PENDING" in page, findings, "FA3-OS-RUNTIME-GUI-005", "GUI does not expose the current-host evidence boundary")
    _require("fa3Journal.filteredEvents" in page, findings, "FA3-OS-RUNTIME-GUI-006", "GUI timeline is not bound to the canonical Journal projection")
    _require(f'label: "Work Management"; routeId: "{WORK_MANAGEMENT_ROUTE_ID}"' in main_qml and f'"{WORK_MANAGEMENT_ROUTE_ID}": 24' in main_qml, findings, "FA3-OS-RUNTIME-GUI-007", "Work Management semantic route was displaced by FA3 OS")
    _require(f'label: "Accelerator Guard"; routeId: "{ACCELERATOR_GUARD_ROUTE_ID}"' in main_qml and f'"{ACCELERATOR_GUARD_ROUTE_ID}": 25' in main_qml, findings, "FA3-OS-RUNTIME-GUI-008", "Accelerator Guard semantic route was displaced by FA3 OS")

    runtime_result = run_reference_conformance()
    if runtime_result.get("result") != "PASS":
        findings.append(_finding("FA3-OS-RUNTIME-EXEC-001", "Executable reference runtime conformance failed", runtime=runtime_result))
    return {
        "gate_id": GATE_ID, "profile_id": PROFILE_ID, "parent_profile_id": PARENT_PROFILE_ID,
        "ledger_authority": JOURNAL_AUTHORITY, "result": "PASS" if not findings else "FAIL",
        "capability_count": capability_count, "current_host_status": conformance.get("status"),
        "gui_page_index": GUI_PAGE_INDEX, "reference_runtime": runtime_result, "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 OS executable reference runtime regression gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = gate(Path(args.repo_root))
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
