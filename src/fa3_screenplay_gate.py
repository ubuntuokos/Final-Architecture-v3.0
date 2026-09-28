"""Fail-closed static consistency gate, not a current-host pass receipt."""
from __future__ import annotations
import json
from pathlib import Path
from fa3_screenplay import FORMATS, PROFILES, derive_breakdown, export_screenplay, import_screenplay, project_handoff

CONTRACT = "canonical/contracts/FA3-STORY-SCREENPLAY-IMPLEMENTATION-CONTRACTS-001.json"
SCHEMA = "canonical/contracts/FA3-SCREENPLAY-DOCUMENT-001.schema.json"
DONOR = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


def gate(root: Path) -> dict:
    findings: list[str] = []
    def check(cond: bool, code: str) -> None:
        if not cond:
            findings.append(code)
    try:
        contract = json.loads((root / CONTRACT).read_text(encoding="utf-8"))
        schema = json.loads((root / SCHEMA).read_text(encoding="utf-8"))
        donor = json.loads((root / DONOR).read_text(encoding="utf-8"))
        check(contract["id"] == "FA3-STORY-SCREENPLAY-IMPLEMENTATION-CONTRACTS-001", "CONTRACT_ID")
        check(contract["new_capability"] is False and contract["new_architectural_authority"] is False,
              "NEW_AUTHORITY_FORBIDDEN")
        check(set(contract["document"]["production_profiles"]) == PROFILES, "PROFILE_CONTRACT_DRIFT")
        check(set(contract["interchange"]["experimental_bidirectional_subsets"]) == set(FORMATS),
              "CODEC_CONTRACT_DRIFT")
        check(contract["interchange"]["office_family_codec_admission"] == "NOT_ADMITTED", "FALSE_OFFICE_ADMISSION")
        check(contract["handoff"]["publish_authority"] is False and contract["handoff"]["schedule_authority"] is False,
              "HANDOFF_AUTHORITY")
        check(contract["ai"]["direct_provider_execution"] is False, "AI_AUTHORITY")
        check(contract["current_host"]["status"] == "PENDING_REAL_CURRENT_HOST_EXECUTION", "FABRICATED_HOST_EVIDENCE")
        check(contract["hardware_audit"]["cpu_only_viable"] is True and
              contract["hardware_audit"]["global_accelerator_requirement"] is False and
              contract["hardware_audit"]["wayland_preferred_x11_supported"] is True, "HARDWARE_DRIFT")
        check(schema["properties"]["schema"]["const"] == "fa3.screenplay-document.v1", "JSON_SCHEMA_DRIFT")
        check(donor["id"] == "FA3-DONOR-REFERENCE-REGISTRY-001" and
              donor["backfill"]["entry_count"] == len(donor["entries"]), "DONOR_REGISTRY_DRIFT")
        needed = ("github:wildwinter/screenplay-tools", "github:wassermanproductions/scriptbreak",
                  "github:proteus-technologies-private-limited/opendraft")
        check(set(needed).issubset({e["source"]["normalized_key"] for e in donor["entries"]}),
              "MISSING_DONOR_REUSE_DISCOVERY")
        links = json.loads((root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json").read_text(encoding="utf-8"))
        check(any(e["application_id"] == "fa3.story-screenplay" for e in links["applications"]),
              "APPLICATION_NOT_DECLARED")
        simple = "INT. LAB - DAY\n\nPROP: lámpa; CLOSE ON it.\n\n@RITA\nSzia!\n"
        doc, _ = import_screenplay(simple, "fountain")
        fdx, receipt = export_screenplay(doc, "fdx")
        back, _ = import_screenplay(fdx, "fdx")
        check(doc["scenes"] == back["scenes"] and not receipt["losses"], "CODEC_REFERENCE_FAILURE")
        bd = derive_breakdown(doc)
        check(project_handoff(doc, bd)["status"] == "BLOCKED", "UNREVIEWED_PROPOSAL_BYPASS")
        gui_main = (root / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        gui_build = (root / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        check('"create.story-screenplay"' in gui_main and "StoryScreenplayPage" in gui_build,
              "GUI_ROUTE_MISSING")
    except (OSError, KeyError, ValueError, TypeError) as exc:
        findings.append("GATE_INPUT_INVALID: " + str(exc))
    return {"schema": "fa3.screenplay-reference-gate-report.v1",
            "result": "FAIL" if findings else "PASS", "findings": findings,
            "evidence_level": "REFERENCE_ONLY_NOT_CURRENT_HOST", "current_host_status": "PENDING"}
