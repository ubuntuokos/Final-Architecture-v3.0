#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count
from fa3_engine_selector import materialize_catalog, selection_intent, fallback_candidates

CAPABILITY_COUNT=module_active_capability_count(__file__)
PROFILE_ID="FA3-ENGINE-SELECTION-FABRIC-001"
CONTRACT_ID="FA3-ENGINE-SELECTION-CONTRACTS-001"
REGISTRY_ID="FA3-ENGINE-REGISTRY-001"
DECISION_ID="FA3-DEC-ENGINE-SELECTION-FABRIC-2026-10-03"
GATE_ID="FA3-ENGINE-SELECTION-GATESET-001"

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

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
    }
    for name,path in paths.items():
        if not path.is_file():
            findings.append(f"missing:{name}:{path.relative_to(root)}")
    if findings:
        return {"schema":"fa3.engine-selection-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}

    profile=_load(paths["profile"]); contract=_load(paths["contract"]); registry=_load(paths["registry"])
    decision=_load(paths["decision"]); assessment=_load(paths["assessment"]); decision_assessment=_load(paths["decision_assessment"]); enforcement=_load(paths["enforcement"])

    if profile.get("id")!=PROFILE_ID or profile.get("new_capability") is not False or profile.get("new_architectural_authority") is not False:
        findings.append("profile authority/capability invariant")
    if contract.get("id")!=CONTRACT_ID or contract.get("architectural_authority") is not False:
        findings.append("contract authority invariant")
    if registry.get("id")!=REGISTRY_ID or registry.get("authority") is not False or registry.get("selection_is_execution_authority") is not False:
        findings.append("registry authority invariant")
    if registry.get("default_engine") is not None or registry.get("default_fallback_mode")!="OFF":
        findings.append("default engine/fallback mandate forbidden")
    if decision.get("id")!=DECISION_ID or decision.get("capability_count_after")!=CAPABILITY_COUNT or decision.get("new_capabilities")!=0 or decision.get("new_architectural_authorities")!=0:
        findings.append("decision baseline invariant")
    if enforcement.get("gate_id")!=GATE_ID or enforcement.get("fail_closed") is not True or enforcement.get("capability_count")!=CAPABILITY_COUNT:
        findings.append("enforcement invariant")
    if assessment.get("result")!="PASS" or assessment.get("pending_or_unmerged_donors_consumed") is not False or assessment.get("capability_count_after")!=CAPABILITY_COUNT:
        findings.append("reuse assessment invariant")
    if (decision_assessment.get("schema")!="fa3.decision-fabric-assessment.v1" or decision_assessment.get("assessment")!="NOT_APPLICABLE" or PROFILE_ID not in decision_assessment.get("covered_ids",[]):
        findings.append("Decision Fabric applicability assessment invariant")
    if decision_assessment.get("project_radar_checked") is not True:
        findings.append("Decision Fabric Project Radar review invariant")
    sb=decision_assessment.get("security_boundary",{})
    if any(sb.get(k) is not False for k in ("may_grant_permission","may_expand_candidate_set","may_create_agent","may_admit_model","may_admit_provider")):
        findings.append("Decision Fabric security boundary invariant")
    snap=assessment.get("donor_planning_snapshot",{})
    if snap.get("donor_registry_blob_sha")!="50580a9f3082161a3317383baa3e18879e98187e" or snap.get("donor_registry_entry_count")!=1357:
        findings.append("donor planning snapshot drift")

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

    try:
        catalog=materialize_catalog(root)
        ids={x["engine_id"] for x in catalog}
        if "FA3-ENGINE-MLT-001" not in ids or "FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001" not in ids:
            findings.append("catalog missing mandatory parallel engines")
        intent=selection_intent(catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",required_capabilities=["CAP-121"],fallback_mode="OFF")
        if intent.get("execution_requested") is not False or intent.get("silent_fallback") is not False:
            findings.append("selection intent crossed execution/fallback boundary")
        if fallback_candidates(catalog,intent)!=[]:
            findings.append("fallback OFF returned candidates")
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
