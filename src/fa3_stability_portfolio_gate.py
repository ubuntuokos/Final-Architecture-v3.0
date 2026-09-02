#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
GATE_ID="FA3-STABILITY-PORTFOLIO-GATESET-001"; PROFILE_ID="FA3-STABILITY-PORTFOLIO-001"; CONTRACT_ID="FA3-STABILITY-PORTFOLIO-CONTRACTS-001"; CAPABILITY_COUNT=143
P0_RULES=["STABILITY_PORTFOLIO_IS_MANDATORY_SUPPORT_PROFILE_NOT_NEW_CAPABILITY","STABILITY_PROVIDERS_NOT_ARCHITECTURAL_AUTHORITIES","STABILITY_CAPABILITY_COUNT_REMAINS_143","STABILITY_MODELSPEC_COMPATIBILITY_BRIDGE_REQUIRED","STABILITY_MODELSPEC_NOT_CANONICAL_MODEL_SCHEMA_AUTHORITY","STABILITY_CODE_MODEL_OUTPUT_LICENSE_DIMENSIONS_SEPARATE","STABILITY_AUP_AND_LICENSE_SNAPSHOT_VERSIONED_AND_PROVENANCED","STABILITY_CODE_LICENSE_NEVER_IMPLIES_WEIGHT_OR_OUTPUT_ADMISSION","STABILITY_IMMUTABLE_REPO_MODEL_RUNTIME_PINS_REQUIRED","STABILITY_HRB_REQUIRED_FOR_ACCELERATOR_PLACEMENT","STABILITY_LIVE_TOPOLOGY_DISCOVERY_OVERRIDES_STATIC_CPU_GPU_NUMBERING","STABILITY_T7910_REFERENCE_CPU_IS_E5_2696_V4_NOT_E5_2697_V4","STABILITY_NO_SILENT_DEVICE_PROVIDER_OR_CLOUD_FALLBACK","STABILITY_CURRENT_HOST_12GB_GPU_ROUTE_MUST_BE_EXPLICITLY_ADMITTED","STABLE_AUDIO_3_REQUIRED_SUPPORTED_AUDIO_PROVIDER","STABLE_AUDIO_DAW_INTEGRATION_PROFILE_REQUIRED_PROVIDER_PLUGIN_OPTIONAL","SD35_REQUIRED_SUPPORTED_IMAGE_PROVIDER","SD35_NVIDIA_NIM_IS_DEPLOYMENT_PROVIDER_NOT_ROUTING_AUTHORITY","SD35_NIM_NOT_CURRENT_HOST_LOCAL_DEFAULT_ON_RTX3080_CLASS_HARDWARE","SPAR3D_PRIMARY_STABILITY_SINGLE_IMAGE_3D_RECONSTRUCTION_PROVIDER","SF3D_REQUIRED_LOWER_VRAM_FALLBACK_PROVIDER","ARBOR_REQUIRED_CONSTRAINED_TEXT_TO_3D_PROVIDER","RELI3D_REQUIRED_MULTIVIEW_RELIGHTABLE_RECONSTRUCTION_PROVIDER","STABLE_VIRTUAL_CAMERA_REQUIRED_SUPPORTED_LICENSE_GATED_NVS_PROVIDER","SGM_SV3D_SV4D_REQUIRED_SUPPORTED_RESEARCH_LICENSE_GATED_MULTIVIEW_PROVIDER","STABLE_LAYERS_REQUIRED_SUPPORTED_REMOTE_DISTRIBUTED_FIRST_DECOMPOSITION_PROVIDER","STABILITY_PROVIDER_RUNTIME_ISOLATED_PIP_VENV_OR_CONTAINER_NO_CONDA_BASELINE","STABILITY_CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E_EVIDENCE"]
PROVIDER_PATHS=["canonical/providers/FA3-PROVIDER-STABILITY-MODELSPEC-001.json","canonical/providers/FA3-PROVIDER-STABILITY-SD35-001.json","canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json","canonical/providers/FA3-PROVIDER-SPAR3D-001.json","canonical/providers/FA3-PROVIDER-SF3D-001.json","canonical/providers/FA3-PROVIDER-ARBOR-001.json","canonical/providers/FA3-PROVIDER-RELI3D-001.json","canonical/providers/FA3-PROVIDER-STABLE-VIRTUAL-CAMERA-001.json","canonical/providers/FA3-PROVIDER-STABLE-LAYERS-001.json","canonical/providers/FA3-PROVIDER-SD35-NVIDIA-NIM-001.json","canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json"]
def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def provider_non_authority(d:dict[str,Any])->bool: return d.get("canonical_root") is False and d.get("architectural_authority") is False and d.get("new_capability") is False and d.get("new_architectural_authority") is False and d.get("capability_count")==143
def hardware_policy_valid(c:dict[str,Any])->bool:
    h=c.get("hardware_reference",{})
    return h.get("cpu")=="2x Intel Xeon E5-2696 v4 @ 2.20GHz" and h.get("physical_cores")==44 and h.get("logical_cpus")==88 and h.get("static_cpu_or_numa_numbering_forbidden") is True and "E5-2697" not in json.dumps(h)
def license_policy_valid(c:dict[str,Any])->bool:
    l=c.get("license_admission",{}); req={"CodeLicense","ModelLicense","OutputUsageRights","CommercialThreshold","AttributionRequirement","AUPUseRestriction","RedistributionPolicy"}
    return req<=set(l.get("dimensions",[])) and l.get("code_license_implies_model_license") is False and l.get("code_license_implies_output_rights") is False and l.get("commercial_threshold_is_versioned_policy_not_static_architecture_constant") is True
def gate(root:Path)->dict[str,Any]:
    root=Path(root).resolve(); f=[]
    paths={"profile":root/"canonical/profiles/FA3-STABILITY-PORTFOLIO-001.json","contract":root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json","decision":root/"canonical/decisions/FA3-DEC-STABILITY-PORTFOLIO-2026-09-02.json","enforcement":root/"canonical/stability-portfolio-enforcement.json","gate":root/"canonical/FA3-GATE-STABILITY-PORTFOLIO-001.json","evidence":root/"evidence/reference/stability-portfolio-ci-2026-09-02.json","policy":root/"canonical/enforcement-policy.json"}
    for n,p in paths.items():
        if not p.is_file(): f.append(finding("STAB-REF-001","required record missing",record=n,path=str(p)))
    if f: return {"gate_id":GATE_ID,"result":"FAIL","findings":f}
    r={k:loadj(v) for k,v in paths.items()}
    if r["profile"].get("id")!=PROFILE_ID or r["profile"].get("requirement")!="MUST" or r["profile"].get("capability_count")!=143: f.append(finding("STAB-REF-002","portfolio profile invariant mismatch"))
    if r["contract"].get("id")!=CONTRACT_ID or r["contract"].get("mandatory_p0_rules")!=P0_RULES: f.append(finding("STAB-REF-003","contract or P0 rule set mismatch"))
    if not hardware_policy_valid(r["contract"]): f.append(finding("STAB-HW-001","FA3 T7910 hardware baseline/current-host discovery policy mismatch"))
    if not license_policy_valid(r["contract"]): f.append(finding("STAB-LIC-001","license/AUP dimensions are not separated and versioned"))
    providers=[]
    for rel in PROVIDER_PATHS:
        p=root/rel
        if not p.is_file(): f.append(finding("STAB-PROV-001","provider record missing",path=rel)); continue
        d=loadj(p); providers.append(d)
        if not provider_non_authority(d): f.append(finding("STAB-PROV-002","provider authority/capability invariant violated",provider=d.get("id")))
    ids={x.get("id") for x in providers}
    for reqid in r["profile"].get("providers",[]):
        if reqid not in ids: f.append(finding("STAB-PROV-003","profile provider not materialized",provider=reqid))
    nim=next((x for x in providers if x.get("id")=="FA3-PROVIDER-SD35-NVIDIA-NIM-001"),{})
    if nim.get("current_host_local_default") is not False: f.append(finding("STAB-HW-002","NIM was incorrectly admitted as current-host local default"))
    layers=next((x for x in providers if x.get("id")=="FA3-PROVIDER-STABLE-LAYERS-001"),{})
    if layers.get("current_host_route")!="REMOTE_DISTRIBUTED_FIRST": f.append(finding("STAB-HW-003","Stable Layers must remain remote/distributed-first on current host"))
    pol=r["policy"]
    if GATE_ID not in pol.get("mandatory_reference_gates",[]) or pol.get("stability_portfolio_mandatory_p0_rules")!=P0_RULES: f.append(finding("STAB-GLOBAL-001","global enforcement policy not bound to portfolio gate"))
    ev=r["evidence"]
    if ev.get("status")!="PASS" or ev.get("current_host_runtime_evidence") is not False or ev.get("mandatory_rules_passed")!=len(P0_RULES): f.append(finding("STAB-EVID-001","reference evidence invalid or overclaims runtime promotion"))
    result="PASS" if not f else "FAIL"; report={"schema":"fa3.stability-portfolio-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"contract_id":CONTRACT_ID,"result":result,"blocking_findings":len(f),"findings":f,"mandatory_rules":len(P0_RULES),"providers_checked":len(providers),"capability_count":143,"new_capabilities":0,"new_architectural_authorities":0,"current_host_provider_e2e":False}
    out=root/"reports/stability-portfolio-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return report
