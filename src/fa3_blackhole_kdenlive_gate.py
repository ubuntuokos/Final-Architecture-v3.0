#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_blackhole_kdenlive import run_executable_conformance

PROFILE_ID = "FA3-BLACKHOLE-KDENLIVE-001"
STT_PROFILE_ID = "FA3-STT-001"
STT_MEDIA_PROFILE_ID = "FA3-STT-MEDIA-001"
GATE_ID = "FA3-BLACKHOLE-KDENLIVE-GATESET-001"
CAPABILITY_COUNT = 143

RULES = [
    "BLACKHOLE_MEDIA_STT_PROVIDER_NEUTRAL",
    "DEMUCS_OPTIONAL_PREPROCESSOR_ONLY",
    "STT_MUST_WORK_WITHOUT_DEMUCS",
    "NO_SILENT_PREPROCESSING_FALLBACK",
    "TIMELINE_RANGE_AND_OFFSET_EXPLICIT",
    "TRANSCRIPTION_RESULT_TIMING_VALIDATED",
    "KDENLIVE_PROJECT_XML_DIRECT_MUTATION_FORBIDDEN",
    "SRT_VTT_SIDECAR_IMPORT_PROJECTION_REQUIRED",
    "STT_PROVIDER_COMMAND_TYPED_AND_SHELL_FALSE",
    "MEDIA_AND_DERIVED_AUDIO_HASH_LINEAGE_REQUIRED",
    "NO_CONDA_OR_MINIFORGE_RUNTIME",
    "SEPARATE_BLACKHOLE_GUI_NOT_REQUIRED",
]

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code":code,"severity":"P0","message":message,**details}

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "stt": root/"canonical/profiles/FA3-STT-001.json",
        "stt_media": root/"canonical/profiles/FA3-STT-MEDIA-001.json",
        "integration": root/"canonical/profiles/FA3-BLACKHOLE-KDENLIVE-001.json",
        "stt_contracts": root/"canonical/contracts/FA3-STT-CONTRACTS-001.json",
        "media_contracts": root/"canonical/contracts/FA3-STT-MEDIA-CONTRACTS-001.json",
        "integration_contracts": root/"canonical/contracts/FA3-BLACKHOLE-KDENLIVE-CONTRACTS-001.json",
        "decision": root/"canonical/decisions/FA3-DEC-BLACKHOLE-KDENLIVE-DEMUCS-2026-08-30.json",
        "enforcement": root/"canonical/blackhole-kdenlive-enforcement.json",
        "adapter": root/"src/fa3_blackhole_kdenlive.py",
    }
    for i,(name,path) in enumerate(paths.items(),1):
        if not path.is_file():
            findings.append(finding(f"BLACKHOLE-REF-{i:03d}",f"Missing Blackhole/Kdenlive artifact: {path.relative_to(root)}",artifact=name))
    if findings:
        return {"result":"FAIL","findings":findings}

    stt=_load(paths["stt"])
    media=_load(paths["stt_media"])
    integ=_load(paths["integration"])
    contracts=_load(paths["media_contracts"])
    decision=_load(paths["decision"])
    enforcement=_load(paths["enforcement"])

    if stt.get("id")!=STT_PROFILE_ID or stt.get("status")!="CANONICAL":
        findings.append(finding("BLACKHOLE-REF-020","FA3-STT-001 identity/status drift"))
    if any(stt.get(k) is not False for k in ("canonical_root","new_capability","new_architectural_authority")):
        findings.append(finding("BLACKHOLE-REF-021","FA3-STT-001 became forbidden root/capability/authority"))

    if media.get("id")!=STT_MEDIA_PROFILE_ID or media.get("subprofile_of")!=STT_PROFILE_ID:
        findings.append(finding("BLACKHOLE-REF-022","FA3-STT-MEDIA-001 parent relationship drift"))
    if "FA3-AUDIO-SEPARATION-001" not in media.get("optional_preprocessors",[]):
        findings.append(finding("BLACKHOLE-REF-023","Audio separation is not registered as optional preprocessing"))
    invariants=set(media.get("invariants",[]))
    if not any("STT must remain executable" in x for x in invariants):
        findings.append(finding("BLACKHOLE-REF-024","STT-without-Demucs invariant missing"))

    if integ.get("id")!=PROFILE_ID or integ.get("profile_type")!="INTEGRATION_PROJECTION":
        findings.append(finding("BLACKHOLE-REF-025","Blackhole/Kdenlive integration identity/type drift"))
    if integ.get("demucs_role")!="OPTIONAL_PREPROCESSOR_ONLY":
        findings.append(finding("BLACKHOLE-REF-026","Demucs was promoted beyond optional preprocessing"))
    if integ.get("direct_kdenlive_project_xml_mutation") is not False:
        findings.append(finding("BLACKHOLE-REF-027","Direct Kdenlive project XML mutation was enabled"))
    if integ.get("conda_or_miniforge_allowed") is not False:
        findings.append(finding("BLACKHOLE-REF-028","Conda/Miniforge runtime was enabled"))
    if integ.get("separate_blackhole_gui_required") is not False:
        findings.append(finding("BLACKHOLE-REF-029","Separate Blackhole GUI became required"))
    if any(integ.get(k) is not False for k in ("canonical_root","new_capability","new_architectural_authority")):
        findings.append(finding("BLACKHOLE-REF-030","Integration created forbidden root/capability/authority"))

    optional=contracts.get("optional_preprocessing",{})
    if optional.get("demucs_provider")!="FA3-PROVIDER-DEMUCS-001" or optional.get("silent_fallback_forbidden") is not True or optional.get("stt_without_preprocessor_required") is not True:
        findings.append(finding("BLACKHOLE-REF-031","Media STT optional-preprocessing contract drift"))

    if decision.get("status")!="CANONICAL_CLOSED" or decision.get("decision")!="IMPLEMENT":
        findings.append(finding("BLACKHOLE-REF-032","Blackhole/Kdenlive decision is not closed IMPLEMENT"))
    if decision.get("new_capabilities")!=0 or decision.get("new_architectural_authorities")!=0 or decision.get("capability_count_after")!=CAPABILITY_COUNT:
        findings.append(finding("BLACKHOLE-REF-033","Integration changed capability/authority invariant"))
    if decision.get("mandatory_rules")!=RULES:
        findings.append(finding("BLACKHOLE-REF-034","Blackhole/Kdenlive mandatory rule set drift"))

    if enforcement.get("gate_id")!=GATE_ID or enforcement.get("profile_id")!=PROFILE_ID:
        findings.append(finding("BLACKHOLE-REF-035","Blackhole/Kdenlive gate/profile identity mismatch"))
    if enforcement.get("capability_count")!=CAPABILITY_COUNT or enforcement.get("rule_count")!=len(RULES):
        findings.append(finding("BLACKHOLE-REF-036","Blackhole/Kdenlive count invariant drift"))
    if enforcement.get("rules")!=RULES or enforcement.get("fail_closed") is not True:
        findings.append(finding("BLACKHOLE-REF-037","Blackhole/Kdenlive fail-closed rule set drift"))
    if enforcement.get("runtime_required_for_global_promotion") is not False:
        findings.append(finding("BLACKHOLE-REF-038","Optional integration became global runtime promotion dependency"))

    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path) -> dict[str, Any]:
    reference=reference_check(root)
    conformance=run_executable_conformance(root)
    ok=reference["result"]=="PASS" and conformance["result"]=="PASS"
    report={
        "schema":"fa3.blackhole-kdenlive-gate-report.v1",
        "gate_id":GATE_ID,
        "profile_id":PROFILE_ID,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if ok else "FAIL",
        "reference":reference,
        "conformance":conformance,
        "runtime_required_for_global_promotion":False,
        "promotion_effect":"MANDATORY_INTEGRATION_CONTRACTS_RUNTIME_OPTIONAL",
    }
    _write(root/"reports/blackhole-kdenlive-gate-report.json",report)
    return report

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 Blackhole/Kdenlive integration gate")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    report=gate(Path(args.root).resolve())
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
