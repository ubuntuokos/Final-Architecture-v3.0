#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_engine_selector import (
    SELECTABLE_HEALTH,
    compatibility_report,
    fallback_candidates,
    materialize_catalog,
    selection_intent,
)

CAPABILITY_COUNT=module_active_capability_count(__file__)
PROFILE_ID="FA3-ENGINE-SELECTION-FABRIC-001"
CONTRACT_ID="FA3-ENGINE-SELECTION-CONTRACTS-001"
REGISTRY_ID="FA3-ENGINE-REGISTRY-001"
DECISION_ID="FA3-DEC-ENGINE-SELECTION-FABRIC-2026-10-03"
GATE_ID="FA3-ENGINE-SELECTION-GATESET-001"
DONOR_REL="canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _git(root: Path, *args: str, check: bool=True) -> subprocess.CompletedProcess[str]:
    proc=subprocess.run(
        ["git","-C",str(root),*args],text=True,capture_output=True,check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc

def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii")+data).hexdigest()

def donor_registry_fingerprint_bytes(data: bytes) -> dict[str, Any]:
    obj=json.loads(data.decode("utf-8"))
    entries=obj.get("entries")
    if not isinstance(entries,list):
        raise RuntimeError("donor registry entries missing")
    return {
        "donor_registry_id":obj.get("id"),
        "donor_registry_blob_sha":_blob_sha(data),
        "donor_registry_entry_count":len(entries),
        "donor_registry_sha256":hashlib.sha256(data).hexdigest(),
    }

def donor_registry_fingerprint(path: Path) -> dict[str, Any]:
    return donor_registry_fingerprint_bytes(path.read_bytes())

def donor_snapshot_findings(root: Path, snapshot: dict[str, Any]) -> list[str]:
    findings=[]
    try:
        commit=str(snapshot.get("published_main_commit","")).strip()
        if not commit:
            findings.append("donor planning snapshot published main commit missing")
            return findings
        ancestor=_git(root,"merge-base","--is-ancestor",commit,"HEAD",check=False)
        if ancestor.returncode != 0:
            findings.append("donor planning snapshot commit is not an ancestor of HEAD")
        show=subprocess.run(
            ["git","-C",str(root),"show",f"{commit}:{DONOR_REL}"],
            capture_output=True,check=False)
        if show.returncode != 0:
            findings.append("donor planning snapshot published-main registry unavailable")
            return findings
        published=donor_registry_fingerprint_bytes(show.stdout)
        for key in ("donor_registry_id","donor_registry_blob_sha","donor_registry_entry_count","donor_registry_sha256"):
            if snapshot.get(key)!=published.get(key):
                findings.append(f"donor planning snapshot published-main mismatch:{key}")
        snap_blob=_git(root,"rev-parse",f"{commit}:{DONOR_REL}").stdout.strip()
        if snap_blob != snapshot.get("donor_registry_blob_sha"):
            findings.append("donor planning snapshot commit/blob mismatch")
    except Exception as exc:
        findings.append(f"donor planning snapshot verification failed:{exc}")
    return findings

def gate(root: Path) -> dict[str, Any]:
    findings=[]
    paths={
        "profile":root/"canonical/profiles/FA3-ENGINE-SELECTION-FABRIC-001.json",
        "contract":root/"canonical/contracts/FA3-ENGINE-SELECTION-CONTRACTS-001.json",
        "registry":root/"canonical/FA3-ENGINE-REGISTRY-001.json",
        "decision":root/"canonical/decisions/FA3-DEC-ENGINE-SELECTION-FABRIC-2026-10-03.json",
        "assessment":root/"canonical/assessments/FA3-ENGINE-SELECTION-REUSE-ASSESSMENT-2026-10-03.json",
        "decision_assessment":root/"canonical/assessments/FA3-ENGINE-SELECTION-DECISION-ASSESSMENT-2026-10-03.json",
        "enforcement":root/"canonical/engine-selection-enforcement.json",
        "selector":root/"src/fa3_engine_selector.py",
        "qml":root/"apps/shared/engine-selector/qml/EngineSelectorPanel.qml",
        "control_service":root/"apps/fa3-control-center/src/EngineSelectorService.cpp",
        "control_page":root/"apps/fa3-control-center/qml/EngineManagerPage.qml",
        "control_main":root/"apps/fa3-control-center/qml/Main.qml",
        "control_main_cpp":root/"apps/fa3-control-center/src/main.cpp",
        "control_cmake":root/"apps/fa3-control-center/CMakeLists.txt",
        "gui_registry":root/"canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
        "donor_registry":root/DONOR_REL,
    }
    for name,path in paths.items():
        if not path.is_file():
            findings.append(f"missing:{name}:{path.relative_to(root)}")
    if findings:
        return {"schema":"fa3.engine-selection-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}

    profile=_load(paths["profile"]); contract=_load(paths["contract"]); registry=_load(paths["registry"])
    decision=_load(paths["decision"]); assessment=_load(paths["assessment"])
    decision_assessment=_load(paths["decision_assessment"]); enforcement=_load(paths["enforcement"])

    if (
        profile.get("id")!=PROFILE_ID
        or profile.get("new_capability") is not False
        or profile.get("new_architectural_authority") is not False
        or profile.get("capability_count")!=CAPABILITY_COUNT
    ):
        findings.append("profile authority/capability invariant")
    if (
        contract.get("id")!=CONTRACT_ID
        or contract.get("architectural_authority") is not False
        or contract.get("capability_count")!=CAPABILITY_COUNT
    ):
        findings.append("contract authority/capability invariant")
    if (
        registry.get("id")!=REGISTRY_ID
        or registry.get("authority") is not False
        or registry.get("selection_is_execution_authority") is not False
        or registry.get("capability_count")!=CAPABILITY_COUNT
    ):
        findings.append("registry authority/capability invariant")
    if registry.get("default_engine") is not None or registry.get("default_fallback_mode")!="OFF":
        findings.append("default engine/fallback mandate forbidden")
    if registry.get("provider_projection_missing_required_record")!="FAIL_CLOSED":
        findings.append("required provider projection fail-closed invariant")
    if decision.get("id")!=DECISION_ID or decision.get("capability_count_after")!=CAPABILITY_COUNT or decision.get("new_capabilities")!=0 or decision.get("new_architectural_authorities")!=0:
        findings.append("decision baseline invariant")
    if enforcement.get("gate_id")!=GATE_ID or enforcement.get("fail_closed") is not True or enforcement.get("capability_count")!=CAPABILITY_COUNT:
        findings.append("enforcement invariant")
    if assessment.get("result")!="PASS" or assessment.get("pending_or_unmerged_donors_consumed") is not False or assessment.get("capability_count_after")!=CAPABILITY_COUNT:
        findings.append("reuse assessment invariant")
    if (decision_assessment.get("schema")!="fa3.decision-fabric-assessment.v1" or decision_assessment.get("assessment")!="NOT_APPLICABLE" or PROFILE_ID not in decision_assessment.get("covered_ids",[])):
        findings.append("Decision Fabric applicability assessment invariant")
    if decision_assessment.get("project_radar_checked") is not True:
        findings.append("Decision Fabric Project Radar review invariant")
    sb=decision_assessment.get("security_boundary",{})
    if any(sb.get(k) is not False for k in ("may_grant_permission","may_expand_candidate_set","may_create_agent","may_admit_model","may_admit_provider")):
        findings.append("Decision Fabric security boundary invariant")

    findings.extend(donor_snapshot_findings(root,assessment.get("donor_planning_snapshot",{})))

    gui=profile.get("gui",{})
    if gui.get("compact_and_advanced_modes") is not False or gui.get("privacy_cost_license_hardware_filters") is not False:
        findings.append("unmaterialized GUI controls must not be claimed")

    records={x.get("engine_id"):x for x in registry.get("engine_records",[])}
    mlt=records.get("FA3-ENGINE-MLT-001",{})
    native=records.get("FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001",{})
    human=records.get("FA3-ENGINE-FA3-DIGITAL-HUMAN-NATIVE-001",{})
    if mlt.get("permanent_parallel_option") is not True or mlt.get("replacement_target") is not False:
        findings.append("MLT preservation invariant")
    if native.get("permanent_parallel_option") is not True or native.get("replaces_engine_ids")!=[]:
        findings.append("FA3 native media must remain parallel")
    if "CAP-043" not in human.get("capability_projection",[]) or human.get("permanent_parallel_option") is not True:
        findings.append("digital human existing capability/parallel invariant")

    service_text=paths["control_service"].read_text(encoding="utf-8")
    page_text=paths["control_page"].read_text(encoding="utf-8")
    main_text=paths["control_main"].read_text(encoding="utf-8")
    main_cpp_text=paths["control_main_cpp"].read_text(encoding="utf-8")
    cmake_text=paths["control_cmake"].read_text(encoding="utf-8")
    qml_text=paths["qml"].read_text(encoding="utf-8")
    selector_text=paths["selector"].read_text(encoding="utf-8")
    gui_registry=_load(paths["gui_registry"])
    gui_surface=next((x for x in gui_registry.get("surfaces",[]) if x.get("route_id")=="models.engines"), {})
    for token in ["filterEngines", "prepareSelection", "prepareComparison", "compatibilityReport", "FA3-AUTH-MODEL-ROUTER-001", "FA3-AUTH-HOST-RESOURCE-BROKER-001"]:
        if token not in service_text:
            findings.append(f"Control Center service missing:{token}")
    if "EngineSelectorPanel" not in page_text or "fa3EngineSelector" not in main_text or '"models.engines"' not in main_text:
        findings.append("Control Center Engine Manager QML wiring invariant")
    if 'setContextProperty("fa3EngineSelector"' not in main_cpp_text or "EngineSelectorService" not in main_cpp_text:
        findings.append("Control Center EngineSelectorService context wiring invariant")
    if "EngineSelectorService.cpp" not in cmake_text or "EngineManagerPage.qml" not in cmake_text or "EngineSelectorPanel.qml" not in cmake_text:
        findings.append("Control Center Engine Manager build wiring invariant")
    if gui_surface.get("profile_id")!=PROFILE_ID or gui_surface.get("authority") is not False or gui_surface.get("direct_provider_execution") is not False:
        findings.append("GUI surface registry engine manager boundary invariant")
    for token in ["scopeTarget", "requiredCaps", "compatibilityReport", "compareIds.indexOf"]:
        if token not in qml_text:
            findings.append(f"Engine Selector QML review hardening missing:{token}")
    for token in ["--approved-fallback-engine","--scope-target","compare"]:
        if token not in selector_text:
            findings.append(f"selector CLI review hardening missing:{token}")

    try:
        catalog=materialize_catalog(root)
        ids={x["engine_id"] for x in catalog}
        if "FA3-ENGINE-MLT-001" not in ids or "FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001" not in ids:
            findings.append("catalog missing mandatory parallel engines")

        provider_ids=[x.get("provider_record") for x in catalog if x.get("provider_record")]
        if len(provider_ids)!=len(set(provider_ids)):
            findings.append("provider projection duplicate binding invariant")

        for capability_id in profile.get("capabilities",[]):
            if not any(capability_id in x.get("capability_projection",[]) for x in catalog):
                findings.append(f"profile capability has no engine binding:{capability_id}")

        by_provider={x.get("provider_record"):x for x in catalog if x.get("provider_record")}
        open_sora=by_provider.get("FA3-PROVIDER-OPEN-SORA-PLAN-001")
        if open_sora and open_sora.get("health_state") in SELECTABLE_HEALTH:
            findings.append("non-admitted Open-Sora provider became selectable")
        minimax=by_provider.get("FA3-PROVIDER-MINIMAX-H3-001")
        if minimax and not {"LOCAL","REMOTE","HYBRID"}.issubset(set(minimax.get("execution_modes",[]))):
            findings.append("MiniMax hybrid execution modes lost")
        opendlss=by_provider.get("FA3-PROVIDER-OPENDLSS-NR-001")
        if opendlss and "CAP-136" not in opendlss.get("capability_projection",[]):
            findings.append("OpenDLSS capability_bindings normalization lost")

        intent=selection_intent(
            catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",scope_target_id="project:test",
            required_capabilities=["CAP-121"],fallback_mode="OFF")
        if intent.get("execution_requested") is not False or intent.get("silent_fallback") is not False:
            findings.append("selection intent crossed execution/fallback boundary")
        if intent.get("scope_target_id")!="project:test":
            findings.append("selection scope target invariant")
        if fallback_candidates(catalog,intent)!=[]:
            findings.append("fallback OFF returned candidates")
        comp=compatibility_report(catalog,engine_id="FA3-ENGINE-MLT-001",required_capabilities=["CAP-121","CAP-043"])
        if comp.get("grade")!="PARTIAL" or comp.get("missing_capabilities")!=["CAP-043"]:
            findings.append("compatibility report invariant")
    except Exception as exc:
        findings.append(f"selector validation failed:{exc}")

    return {
        "schema":"fa3.engine-selection-gate-report.v1",
        "gate_id":GATE_ID,
        "profile_id":PROFILE_ID,
        "registry_id":REGISTRY_ID,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "current_host_runtime_promotion_claim":False
    }

if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    report=gate(root)
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report["result"]=="PASS" else 2)
