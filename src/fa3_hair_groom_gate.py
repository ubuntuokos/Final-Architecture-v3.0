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
IMPACT_RUNTIME_FALSE = (
    "runtime_change","service_change","daemon_change","port_or_socket_change",
    "package_dependency_change","provider_or_model_activation","hardware_mutation",
    "credential_path_change","physical_application_binding",
    "current_host_runtime_promotion_claim","physical_current_host_pass_claimed",
    "host_requalification_required_now",
)
ENFORCEMENT_P0 = {
    "HAIR_GROOM_SHARED_NON_AUTHORITY",
    "CAPABILITY_BASELINE_175_UNCHANGED",
    "PROFILE_CONTRACT_BINDING_PARITY",
    "SOLE_GEOMETRY_AUTHORITY_PRESERVED",
    "DCC_FINAL_ASSET_AUTHORITY_PRESERVED",
    "MODEL_ROUTER_HRB_ENGINE_SELECTION_AUTHORITIES_PRESERVED",
    "CPU_ONLY_CONTROL_PATH_VALID",
    "DISPLAY_GPU_IMPLICIT_AI_ENLISTMENT_FORBIDDEN",
    "NO_SILENT_FALLBACK",
    "NON_AI_MANUAL_PROCEDURAL_PATH_REQUIRED",
    "CANONICAL_HAIR_ASSET_REPRESENTATION_SET_FIXED",
    "NON_DESTRUCTIVE_GROOM_HISTORY_REQUIRED",
    "APPLICATION_CAPABILITY_BINDING_DERIVED_ONLY",
    "PENDING_DONORS_NOT_CONSUMED",
    "DONOR_USAGE_EDGE_COUNT_ZERO_FOR_STATIC_MATERIALIZATION",
    "STATIC_PASS_NOT_CURRENT_HOST_RUNTIME_PASS",
}
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
    intent=rows["intent"]
    enforcement=rows["enforcement"]
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

    if not (
        intent.get("schema")=="fa3.application-intent.v1"
        and intent.get("id")=="FA3-SHARED-HAIR-GROOM-APPLICATION-INTENT-2026-10-03"
        and intent.get("project_id")=="FA3-SHARED-HAIR-GROOM-001"
        and intent.get("project_type")=="SHARED_SYSTEM_COMPONENT"
        and intent.get("required_capabilities")==CAPS
        and intent.get("declared_new_capabilities")==[]
        and intent.get("proposed_authority_roles")==[]
        and intent.get("execution_classes")==["STATIC_CONTRACT_AND_MAPPING"]
        and intent.get("hardware_audit",{}).get("vendor_neutral") is True
        and intent.get("hardware_audit",{}).get("cpu_only_viable") is True
        and intent.get("hardware_audit",{}).get("global_accelerator_requirement") is False
        and intent.get("hardware_audit",{}).get("hardware_mutation") is False
        and intent.get("namespace_claims",{}).get("requires_upstream_uninstall") is False
        and intent.get("namespace_claims",{}).get("global_environment_mutation") is False
        and intent.get("namespace_claims",{}).get("claims_default_port") is False
    ):
        findings.append(finding("HAIR-006A","application intent identity/invariants failed"))

    if not (
        enforcement.get("schema")=="fa3.shared-hair-groom-enforcement.v1"
        and enforcement.get("id")=="FA3-SHARED-HAIR-GROOM-ENFORCEMENT-001"
        and enforcement.get("gate_id")=="FA3-SHARED-HAIR-GROOM-GATESET-001"
        and enforcement.get("executable_gate_id")=="FA3-GATE-SHARED-HAIR-GROOM-001"
        and enforcement.get("profile_id")=="FA3-SHARED-HAIR-GROOM-001"
        and enforcement.get("contract_id")=="FA3-SHARED-HAIR-GROOM-CONTRACTS-001"
        and enforcement.get("decision_id")=="FA3-DEC-SHARED-HAIR-GROOM-2026-10-03"
        and enforcement.get("capability_bindings")==CAPS
        and enforcement.get("capability_count")==baseline
        and enforcement.get("fail_closed") is True
        and enforcement.get("current_host_runtime_promotion_claim") is False
        and ENFORCEMENT_P0.issubset(set(enforcement.get("p0_invariants",[])))
    ):
        findings.append(finding("HAIR-006B","enforcement record identity/P0 invariants failed"))
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
    if snap.get("published_main_commit")!="8332a0fd5fadc141f7f4c00db052c5c33c1a9bbd" or snap.get("donor_registry_blob_sha")!="4ac6c46935176c0e2027d771557cdec159e4c2bf" or snap.get("donor_registry_entry_count")!=1421:
        findings.append(finding("HAIR-018","donor planning snapshot drift"))
    if "FA3-DONOR-" in json.dumps(p,sort_keys=True) or "FA3-DONOR-" in json.dumps(c,sort_keys=True):
        findings.append(finding("HAIR-019","static Hair/Groom profile/contract may not forge donor adoption"))

    impact=rows["impact"]
    if (
        impact.get("schema")!="fa3.current-host-structural-impact.v1"
        or impact.get("id")!="FA3-SHARED-HAIR-GROOM-CURRENT-HOST-IMPACT-001"
        or impact.get("subject_id")!="FA3-SHARED-HAIR-GROOM-001"
        or impact.get("status")!="NO_RUNTIME_IMPACT"
        or impact.get("capability_baseline")!=baseline
        or impact.get("capability_delta")!=0
        or impact.get("authority_delta")!=0
        or impact.get("runtime_delta")!="NONE"
        or any(impact.get(k) is not False for k in IMPACT_RUNTIME_FALSE)
        or impact.get("alignment_scope",{}).get("executable_current_host_path_added") is not False
    ):
        findings.append(finding("HAIR-020","static materialization Current Host impact/runtime flags invalid"))
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
