#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CAPS = ["CAP-015","CAP-016","CAP-032","CAP-163","CAP-164","CAP-166"]
RUNTIME_FALSE = (
    "new_service","new_daemon","new_port","new_socket","new_package_dependency",
    "provider_activation","model_selection","hardware_mutation","physical_application_binding"
)
PATHS = {
    "baseline": "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json",
    "profile": "canonical/profiles/FA3-SHARED-HAIR-GROOM-001.json",
    "contract": "canonical/contracts/FA3-SHARED-HAIR-GROOM-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-SHARED-HAIR-GROOM-2026-10-03.json",
    "intent": "canonical/intents/FA3-SHARED-HAIR-GROOM-APPLICATION-INTENT-2026-10-03.json",
    "assessment": "canonical/assessments/FA3-SHARED-HAIR-GROOM-REUSE-ASSESSMENT-2026-10-03.json",
    "impact": "canonical/FA3-SHARED-HAIR-GROOM-CURRENT-HOST-IMPACT-001.json",
    "enforcement": "canonical/FA3-SHARED-HAIR-GROOM-ENFORCEMENT-001.json",
    "apps": "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
    "catalogue": "canonical/FA3-SHARED-MODULE-PATTERN-CATALOGUE-001.json",
    "geometry": "canonical/profiles/FA3-3D-GEOM-001.json",
}

def load(root: Path, key: str) -> dict[str, Any]:
    value=json.loads((root/PATHS[key]).read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError("JSON object required: "+PATHS[key])
    return value

def finding(code: str, message: str) -> dict[str, str]:
    return {"code":code,"severity":"P0","message":message}

def gate(root: Path) -> dict[str, Any]:
    root=Path(root).resolve()
    findings=[]
    missing=[p for p in PATHS.values() if not (root/p).is_file()]
    if missing:
        return {"schema":"fa3.shared-hair-groom-gate-report.v1","gate_id":"FA3-SHARED-HAIR-GROOM-GATESET-001","result":"FAIL","findings":[finding("HAIR-000","missing:"+",".join(missing))],"current_host_runtime_promotion_claim":False}
    try:
        rows={k:load(root,k) for k in PATHS}
    except Exception as exc:
        return {"schema":"fa3.shared-hair-groom-gate-report.v1","gate_id":"FA3-SHARED-HAIR-GROOM-GATESET-001","result":"FAIL","findings":[finding("HAIR-001",str(exc))],"current_host_runtime_promotion_claim":False}

    baseline=rows["baseline"].get("current_release_capability_count")
    p,c=rows["profile"],rows["contract"]
    if baseline!=175 or p.get("capability_count")!=baseline or c.get("capability_count")!=baseline:
        findings.append(finding("HAIR-002","capability baseline/count drift"))
    if p.get("capability_bindings")!=CAPS or c.get("capability_bindings")!=CAPS:
        findings.append(finding("HAIR-003","profile/contract capability binding parity drift"))
    if p.get("new_capability") is not False or c.get("new_capability") is not False:
        findings.append(finding("HAIR-004","new capability forbidden"))
    if p.get("new_architectural_authority") is not False or c.get("new_architectural_authority") is not False:
        findings.append(finding("HAIR-005","new architectural authority forbidden"))
    if p.get("provider_neutral") is not True or c.get("provider_neutral") is not True or p.get("shared_component") is not True:
        findings.append(finding("HAIR-006","shared/provider-neutral invariant failed"))
    auth=p.get("authority_bindings",{})
    if auth.get("geometry_semantics")!="FA3-3D-GEOM-001" or rows["geometry"].get("authority_role")!="SOLE_CANONICAL_GEOMETRY_SEMANTIC_AUTHORITY":
        findings.append(finding("HAIR-007","sole geometry authority not preserved"))
    if auth.get("dcc_scene_and_final_asset")!="FA3-DCC-RT3D-001":
        findings.append(finding("HAIR-008","DCC final asset authority not preserved"))
    runtime=p.get("runtime_materialization",{})
    if any(runtime.get(k) is not False for k in RUNTIME_FALSE):
        findings.append(finding("HAIR-009","static profile activates runtime surface"))
    if p.get("ai_policy",{}).get("non_ai_manual_and_procedural_path_required") is not True or p.get("ai_policy",{}).get("silent_fallback") is not False:
        findings.append(finding("HAIR-010","non-AI path or no-silent-fallback invariant failed"))

    asset=c.get("hair_asset",{})
    if asset.get("representation_modes")!=["STRANDS","GUIDES","CURVES","CARDS","HYBRID"]:
        findings.append(finding("HAIR-011","canonical hair representation set drift"))
    if c.get("grooming",{}).get("non_destructive_history_required") is not True:
        findings.append(finding("HAIR-012","non-destructive groom history required"))
    if c.get("hardware_policy",{}).get("cpu_only_control_path_valid") is not True or c.get("hardware_policy",{}).get("display_gpu_implicit_selection") is not False:
        findings.append(finding("HAIR-013","hardware policy invariant failed"))

    app=next((x for x in rows["apps"].get("shared_capabilities",[]) if x.get("id")=="FA3-SHARED-HAIR-GROOM-001"),None)
    if not app or app.get("status")!="MATERIALIZED_STATIC" or app.get("fa3_bindings",{}).get("capability_ids"):
        findings.append(finding("HAIR-014","application shared-capability binding missing or manually bound"))
    elif (app.get("current_host_impact") or {}).get("classification")!="NO_RUNTIME_IMPACT":
        findings.append(finding("HAIR-015","application projection runtime impact drift"))

    mat=next((x for x in rows["catalogue"].get("materialized_shared_components",[]) if x.get("id")=="FA3-SHARED-HAIR-GROOM-001"),None)
    if not mat or mat.get("binding_semantics")!="DERIVED_FROM_CANONICAL_PROFILE_CONTRACT_ONLY" or mat.get("current_host_impact")!="NO_RUNTIME_IMPACT":
        findings.append(finding("HAIR-016","shared catalogue materialization missing or invalid"))

    assess=rows["assessment"]
    snap=assess.get("donor_planning_snapshot",{})
    if assess.get("pending_or_unmerged_donors_consumed") is not False or assess.get("donor_usage_edges_created")!=0:
        findings.append(finding("HAIR-017","pending donor consumption or forged usage edge"))
    if snap.get("published_main_commit")!="0a5641204c6f8caaf65e2e4bfc4af928b5579d54" or snap.get("donor_registry_blob_sha")!="ee3a274e842471a3362c343f1ffa2eee935f85f0" or snap.get("donor_registry_entry_count")!=1405:
        findings.append(finding("HAIR-018","donor planning snapshot drift"))
    if "FA3-DONOR-" in json.dumps(p,sort_keys=True) or "FA3-DONOR-" in json.dumps(c,sort_keys=True):
        findings.append(finding("HAIR-019","static Hair/Groom profile/contract may not forge donor adoption"))

    impact=rows["impact"]
    if impact.get("status")!="NO_RUNTIME_IMPACT" or impact.get("host_requalification_required_now") is not False or impact.get("current_host_runtime_promotion_claim") is not False:
        findings.append(finding("HAIR-020","static materialization must not claim Current Host runtime promotion"))
    if rows["decision"].get("status")!="OWNER_APPROVED_MATERIALIZATION":
        findings.append(finding("HAIR-021","owner-approved materialization decision missing"))

    return {
        "schema":"fa3.shared-hair-groom-gate-report.v1",
        "gate_id":"FA3-SHARED-HAIR-GROOM-GATESET-001",
        "capability_baseline":baseline,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "current_host_runtime_promotion_claim":False,
    }
