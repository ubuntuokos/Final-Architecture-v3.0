#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fa3_stable_audio_3_gate import gate as stable_audio_3_gate

GATE_ID="FA3-STABILITY-PORTFOLIO-GATESET-001"; PROFILE_ID="FA3-STABILITY-PORTFOLIO-001"; CONTRACT_ID="FA3-STABILITY-PORTFOLIO-CONTRACTS-001"; CAPABILITY_COUNT=143
P0_RULES=["STABILITY_PORTFOLIO_IS_MANDATORY_SUPPORT_PROFILE_NOT_NEW_CAPABILITY","STABILITY_PROVIDERS_NOT_ARCHITECTURAL_AUTHORITIES","STABILITY_CAPABILITY_COUNT_REMAINS_143","STABILITY_MODELSPEC_COMPATIBILITY_BRIDGE_REQUIRED","STABILITY_MODELSPEC_NOT_CANONICAL_MODEL_SCHEMA_AUTHORITY","STABILITY_CODE_MODEL_OUTPUT_LICENSE_DIMENSIONS_SEPARATE","STABILITY_AUP_AND_LICENSE_SNAPSHOT_VERSIONED_AND_PROVENANCED","STABILITY_CODE_LICENSE_NEVER_IMPLIES_WEIGHT_OR_OUTPUT_ADMISSION","STABILITY_IMMUTABLE_REPO_MODEL_RUNTIME_PINS_REQUIRED","STABILITY_HRB_REQUIRED_FOR_ACCELERATOR_PLACEMENT","STABILITY_LIVE_TOPOLOGY_DISCOVERY_OVERRIDES_STATIC_CPU_GPU_NUMBERING","STABILITY_T7910_REFERENCE_CPU_IS_E5_2696_V4_NOT_E5_2697_V4","STABILITY_NO_SILENT_DEVICE_PROVIDER_OR_CLOUD_FALLBACK","STABILITY_CURRENT_HOST_12GB_GPU_ROUTE_MUST_BE_EXPLICITLY_ADMITTED","STABLE_AUDIO_3_REQUIRED_SUPPORTED_AUDIO_PROVIDER","STABLE_AUDIO_DAW_INTEGRATION_PROFILE_REQUIRED_PROVIDER_PLUGIN_OPTIONAL","SD35_REQUIRED_SUPPORTED_IMAGE_PROVIDER","SD35_NVIDIA_NIM_IS_DEPLOYMENT_PROVIDER_NOT_ROUTING_AUTHORITY","SD35_NIM_NOT_CURRENT_HOST_LOCAL_DEFAULT_ON_RTX3080_CLASS_HARDWARE","SPAR3D_PRIMARY_STABILITY_SINGLE_IMAGE_3D_RECONSTRUCTION_PROVIDER","SF3D_REQUIRED_LOWER_VRAM_FALLBACK_PROVIDER","ARBOR_REQUIRED_CONSTRAINED_TEXT_TO_3D_PROVIDER","RELI3D_REQUIRED_MULTIVIEW_RELIGHTABLE_RECONSTRUCTION_PROVIDER","STABLE_VIRTUAL_CAMERA_REQUIRED_SUPPORTED_LICENSE_GATED_NVS_PROVIDER","SGM_SV3D_SV4D_REQUIRED_SUPPORTED_RESEARCH_LICENSE_GATED_MULTIVIEW_PROVIDER","STABLE_LAYERS_REQUIRED_SUPPORTED_REMOTE_DISTRIBUTED_FIRST_DECOMPOSITION_PROVIDER","STABILITY_PROVIDER_RUNTIME_ISOLATED_PIP_VENV_OR_CONTAINER_NO_CONDA_BASELINE","STABILITY_CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E_EVIDENCE"]
PROVIDER_PATHS=["canonical/providers/FA3-PROVIDER-STABILITY-MODELSPEC-001.json","canonical/providers/FA3-PROVIDER-STABILITY-SD35-001.json","canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json","canonical/providers/FA3-PROVIDER-SPAR3D-001.json","canonical/providers/FA3-PROVIDER-SF3D-001.json","canonical/providers/FA3-PROVIDER-ARBOR-001.json","canonical/providers/FA3-PROVIDER-RELI3D-001.json","canonical/providers/FA3-PROVIDER-STABLE-VIRTUAL-CAMERA-001.json","canonical/providers/FA3-PROVIDER-STABLE-LAYERS-001.json","canonical/providers/FA3-PROVIDER-SD35-NVIDIA-NIM-001.json","canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json"]

def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def provider_non_authority(d:dict[str,Any])->bool: return d.get("canonical_root") is False and d.get("architectural_authority") is False and d.get("new_capability") is False and d.get("new_architectural_authority") is False and d.get("capability_count")==143

def hardware_policy_valid(c:dict[str,Any])->bool:
    h=c.get("hardware_admission",{})
    aliases=h.get("legacy_rule_identifier_semantics",{})
    required_aliases={
      "STABILITY_T7910_REFERENCE_CPU_IS_E5_2696_V4_NOT_E5_2697_V4":"DEPRECATED_IDENTIFIER_COMPATIBILITY_ONLY_CURRENT_HOST_FACTS_ARE_EVIDENCE_NOT_REQUIREMENTS",
      "STABILITY_CURRENT_HOST_12GB_GPU_ROUTE_MUST_BE_EXPLICITLY_ADMITTED":"DEPRECATED_IDENTIFIER_COMPATIBILITY_ONLY_LOCAL_ROUTE_USES_LIVE_RESOURCE_ENVELOPE_AND_HRB_ADMISSION",
      "SD35_NIM_NOT_CURRENT_HOST_LOCAL_DEFAULT_ON_RTX3080_CLASS_HARDWARE":"DEPRECATED_IDENTIFIER_COMPATIBILITY_ONLY_NIM_LOCALITY_IS_CAPABILITY_AND_VENDOR_SUPPORT_DRIVEN",
    }
    return (
      "hardware_reference" not in c
      and h.get("canonical_profile")=="FA3-HARDWARE-BASELINE-001"
      and h.get("discovery_contract")=="FA3-HARDWARE-DISCOVERY-CONTRACTS-001"
      and h.get("resource_authority")=="FA3-AUTH-HOST-RESOURCE-BROKER-001"
      and h.get("hardware_snapshot_required_before_local_admission") is True
      and h.get("minimum_host_qualification_delegated_to_hardware_baseline") is True
      and h.get("current_host_tuple_is_evidence_only") is True
      and h.get("concrete_cpu_vendor_model_socket_count_as_stability_requirement") is False
      and h.get("concrete_gpu_sku_vram_sm_device_count_as_stability_requirement") is False
      and h.get("static_cpu_id_numa_node_pci_bdf_cuda_ordinal_as_portable_placement") is False
      and h.get("numa_is_optional_discovered_topology") is True
      and h.get("incomplete_or_stale_discovery_fails_closed") is True
      and h.get("provider_resource_envelope_is_workload_metadata_not_hardware_identity") is True
      and h.get("provider_resource_envelope_compared_against_live_snapshot") is True
      and h.get("local_accelerator_execution_requires_hrb_lease") is True
      and h.get("no_silent_device_provider_or_cloud_fallback") is True
      and h.get("cpu_only_provider_route_does_not_relax_global_hardware_baseline") is True
      and h.get("newer_supported_hardware_must_not_be_rejected_by_legacy_model_or_sku_pin") is True
      and aliases==required_aliases
    )

def license_policy_valid(c:dict[str,Any])->bool:
    l=c.get("license_admission",{}); req={"CodeLicense","ModelLicense","OutputUsageRights","DeploymentEntitlement","CommercialThreshold","IndemnificationTerms","AttributionRequirement","AUPUseRestriction","RedistributionPolicy"}
    aup=l.get("aup_reference",{})
    return req<=set(l.get("dimensions",[])) and l.get("code_license_implies_model_license") is False and l.get("code_license_implies_output_rights") is False and l.get("weight_availability_implies_deployment_entitlement") is False and l.get("commercial_threshold_is_versioned_policy_not_static_architecture_constant") is True and l.get("indemnification_is_metadata_not_execution_authority") is True and aup.get("effective")=="2026-09-30" and aup.get("snapshot_required_before_execution") is True

def portable_provider_routes_valid(providers:list[dict[str,Any]])->bool:
    byid={x.get("id"):x for x in providers}
    nim=byid.get("FA3-PROVIDER-SD35-NVIDIA-NIM-001",{})
    layers=byid.get("FA3-PROVIDER-STABLE-LAYERS-001",{})
    spar=byid.get("FA3-PROVIDER-SPAR3D-001",{})
    sf=byid.get("FA3-PROVIDER-SF3D-001",{})
    return (
      nim.get("local_default_without_discovery") is False
      and nim.get("hardware_admission",{}).get("canonical_profile")=="FA3-HARDWARE-BASELINE-001"
      and nim.get("hardware_admission",{}).get("concrete_gpu_sku_or_vram_as_fa3_baseline") is False
      and layers.get("routing_policy",{}).get("concrete_current_host_gpu_assumption") is False
      and layers.get("routing_policy",{}).get("silent_local_to_remote_fallback") is False
      and spar.get("local_admission",{}).get("fixed_gpu_sku_or_device_index") is False
      and sf.get("local_admission",{}).get("fixed_gpu_sku_or_device_index") is False
      and spar.get("local_admission",{}).get("hardware_snapshot_required") is True
      and sf.get("local_admission",{}).get("hardware_snapshot_required") is True
    )

def gate(root:Path)->dict[str,Any]:
    root=Path(root).resolve(); f=[]
    paths={"profile":root/"canonical/profiles/FA3-STABILITY-PORTFOLIO-001.json","contract":root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json","decision":root/"canonical/decisions/FA3-DEC-STABILITY-PORTFOLIO-2026-09-02.json","enforcement":root/"canonical/stability-portfolio-enforcement.json","gate":root/"canonical/FA3-GATE-STABILITY-PORTFOLIO-001.json","evidence":root/"evidence/reference/stability-portfolio-ci-2026-09-02.json","policy":root/"canonical/enforcement-policy.json","hardware_profile":root/"canonical/profiles/FA3-HARDWARE-BASELINE-001.json","hardware_contract":root/"canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json"}
    for n,p in paths.items():
        if not p.is_file(): f.append(finding("STAB-REF-001","required record missing",record=n,path=str(p)))
    if f: return {"gate_id":GATE_ID,"result":"FAIL","findings":f}
    r={k:loadj(v) for k,v in paths.items()}
    if r["profile"].get("id")!=PROFILE_ID or r["profile"].get("requirement")!="MUST" or r["profile"].get("capability_count")!=143: f.append(finding("STAB-REF-002","portfolio profile invariant mismatch"))
    if r["contract"].get("id")!=CONTRACT_ID or r["contract"].get("mandatory_p0_rules")!=P0_RULES: f.append(finding("STAB-REF-003","contract or P0 rule set mismatch"))
    if r["hardware_profile"].get("id")!="FA3-HARDWARE-BASELINE-001" or r["hardware_profile"].get("capability_count")!=143: f.append(finding("STAB-HW-000","canonical hardware portability baseline missing or invalid"))
    if r["hardware_contract"].get("id")!="FA3-HARDWARE-DISCOVERY-CONTRACTS-001": f.append(finding("STAB-HW-000B","hardware discovery contract binding invalid"))
    if not hardware_policy_valid(r["contract"]): f.append(finding("STAB-HW-001","Stability portfolio hardware admission is not provider-neutral and dynamically discovered"))
    if not license_policy_valid(r["contract"]): f.append(finding("STAB-LIC-001","license/AUP/deployment dimensions are not separated and versioned"))
    providers=[]
    for rel in PROVIDER_PATHS:
        p=root/rel
        if not p.is_file(): f.append(finding("STAB-PROV-001","provider record missing",path=rel)); continue
        d=loadj(p); providers.append(d)
        if not provider_non_authority(d): f.append(finding("STAB-PROV-002","provider authority/capability invariant violated",provider=d.get("id")))
    ids={x.get("id") for x in providers}
    for reqid in r["profile"].get("providers",[]):
        if reqid not in ids: f.append(finding("STAB-PROV-003","profile provider not materialized",provider=reqid))
    if not portable_provider_routes_valid(providers): f.append(finding("STAB-HW-002","one or more Stability provider routes retain host-SKU assumptions or bypass live admission"))
    pol=r["policy"]
    if GATE_ID not in pol.get("mandatory_reference_gates",[]) or pol.get("stability_portfolio_mandatory_p0_rules")!=P0_RULES: f.append(finding("STAB-GLOBAL-001","global enforcement policy not bound to portfolio gate"))
    enf=r["enforcement"]
    if enf.get("child_gates") != ["FA3-STABLE-AUDIO-3-GATESET-001"] or enf.get("child_gate_fail_closed") is not True: f.append(finding("STAB-CHILD-001","Stable Audio 3 child gate is not fail-closed under Stability portfolio"))
    child=stable_audio_3_gate(root)
    if child.get("result")!="PASS": f.append(finding("STAB-CHILD-002","Stable Audio 3 child gate failed",child_gate=child))
    ev=r["evidence"]
    if ev.get("status")!="PASS" or ev.get("current_host_runtime_evidence") is not False or ev.get("mandatory_rules_passed")!=len(P0_RULES): f.append(finding("STAB-EVID-001","reference evidence invalid or overclaims runtime promotion"))
    result="PASS" if not f else "FAIL"; report={"schema":"fa3.stability-portfolio-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"contract_id":CONTRACT_ID,"result":result,"blocking_findings":len(f),"findings":f,"mandatory_rules":len(P0_RULES),"providers_checked":len(providers),"child_gates_checked":1,"stable_audio_3_child_gate_result":child.get("result"),"hardware_portability_profile":"FA3-HARDWARE-BASELINE-001","capability_count":143,"new_capabilities":0,"new_architectural_authorities":0,"current_host_provider_e2e":False}
    out=root/"reports/stability-portfolio-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return report
