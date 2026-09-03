#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

GATE_ID="FA3-VIDEO-PROVIDER-LIFECYCLE-GATESET-001"
EXECUTABLE_GATE_ID="FA3-GATE-VIDEO-PROVIDER-LIFECYCLE-001"
PROFILE_ID="FA3-VIDEO-001"
CONTRACT_ID="FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001"
DECISION_ID="FA3-DEC-PKU-YUAN-VIDEO-PROVIDER-LIFECYCLE-2026-09-03"
REFERENCE_ID="FA3-PKU-YUAN-VIDEO-UPSTREAM-REFERENCE-2026-09-03"
EVIDENCE_ID="FA3-EVIDENCE-PKU-YUAN-VIDEO-LIFECYCLE-CI-2026-09-03"
OPEN_SORA_ID="FA3-PROVIDER-OPEN-SORA-PLAN-001"
HELIOS_ID="FA3-PROVIDER-HELIOS-001"
OPEN_SORA_PIN="f7fa604f4e3a523d6b973e4c89a5620ed1aff65a"
HELIOS_PIN="babed9811266e4b5b111c9c1e0977a07899066ab"
CAPABILITY_COUNT=143
CAPABILITIES=["CAP-016","CAP-123","CAP-126"]
P0_RULES=[
"VIDEO_PKU_PROVIDERS_NOT_AUTHORITY",
"VIDEO_PKU_CAPABILITY_AUTHORITY_COUNT_INVARIANT",
"VIDEO_PKU_IMMUTABLE_UPSTREAM_PINS",
"VIDEO_PROVIDER_LIFECYCLE_EXPLICIT_PREDECESSOR_SUCCESSOR",
"VIDEO_LIFECYCLE_TRANSITION_NOT_AUTO_PROMOTION",
"VIDEO_PROVIDER_NEUTRAL_IR_PRESERVED",
"VIDEO_REQUESTED_BACKEND_EQUALS_OBSERVED",
"VIDEO_BACKEND_FALLBACK_EXPLICIT_FAIL_CLOSED",
"VIDEO_LOCAL_ACCELERATOR_REQUIRES_HRB_LEASE_UUID_BDF",
"VIDEO_BACKEND_RUNTIME_VERSION_TUPLE_PINNED",
"VIDEO_MODEL_VAE_TEXT_ENCODER_COMPATIBILITY_EXPLICIT",
"VIDEO_DERIVED_CACHE_NOT_AUTHORITY",
"VIDEO_CACHE_KEY_BINDS_SOURCE_MODEL_VAE_ENCODER_RUNTIME",
"VIDEO_CACHE_INVALIDATED_ON_SEMANTIC_OR_VERSION_DRIFT",
"VIDEO_CACHE_SCOPE_AND_TENANT_BOUND",
"VIDEO_CACHE_PROVENANCE_REQUIRED",
"VIDEO_CACHE_MISS_OR_STALE_RECOMPUTE_NO_SILENT_REUSE",
"OPEN_SORA_V15_ASCEND_ONLY_REFERENCE_AT_PIN",
"OPEN_SORA_GPU_COMING_SOON_NOT_PRODUCTION_EVIDENCE",
"OPEN_SORA_LICENSE_METADATA_DRIFT_FAIL_CLOSED",
"HELIOS_CODE_LICENSE_APACHE_MODEL_LICENSE_SEPARATE",
"HELIOS_LOW_VRAM_MODE_REQUIRES_HOST_RAM_CGROUP_PREFLIGHT",
"HELIOS_CONTEXT_PARALLELISM_NOT_PLACEMENT_AUTHORITY",
"HELIOS_OFFLOAD_NOT_HRB_BYPASS",
"HELIOS_LONG_VIDEO_FRAME_FPS_DURATION_LINEAGE",
"HELIOS_BASE_MID_DISTILLED_VARIANTS_DISTINCT_ARTIFACTS",
"HELIOS_INTEGRATION_TARGETS_NOT_ROUTING_AUTHORITY",
"CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E_QC_PROVENANCE_ROLLBACK",
"DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
"PKU_PROVIDER_LIFECYCLE_MIGRATION_PRESERVES_ARTIFACT_PROVENANCE"
]
PATHS={
"open_sora":"canonical/providers/FA3-PROVIDER-OPEN-SORA-PLAN-001.json",
"helios":"canonical/providers/FA3-PROVIDER-HELIOS-001.json",
"contract":"canonical/contracts/FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001.json",
"decision":"canonical/decisions/FA3-DEC-PKU-YUAN-VIDEO-PROVIDER-LIFECYCLE-2026-09-03.json",
"reference":"canonical/references/FA3-PKU-YUAN-VIDEO-UPSTREAM-REFERENCE-2026-09-03.json",
"gate_record":"canonical/FA3-GATE-VIDEO-PROVIDER-LIFECYCLE-001.json",
"enforcement":"canonical/video-provider-lifecycle-enforcement.json",
"admission":"canonical/video-provider-lifecycle-runtime-admission.json",
"evidence":"evidence/reference/pku-yuan-video-lifecycle-ci-2026-09-03.json",
"policy":"canonical/enforcement-policy.json",
"profile":"canonical/profiles/FA3-VIDEO-001.json",
"video_enforcement":"canonical/video-enforcement.json"
}

def _load(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def _write(p:Path,v:dict[str,Any])->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _f(code,msg,**extra): return {"code":code,"severity":"P0","message":msg,**extra}

def provider_not_authority(canonical_root=False,architectural_authority=False,owns_authority=False):
    return not canonical_root and not architectural_authority and not owns_authority
def count_invariant(count=143,new_caps=0,new_auth=0): return count==143 and new_caps==0 and new_auth==0
def immutable_pins_valid(open_pin,helios_pin):
    return open_pin==OPEN_SORA_PIN and helios_pin==HELIOS_PIN and all(x not in {"main","master","latest","floating",""} for x in (open_pin,helios_pin))
def lifecycle_valid(predecessor,successor,distinct): return predecessor==OPEN_SORA_ID and successor==HELIOS_ID and distinct
def lifecycle_no_auto_promotion(auto_migrate,auto_promote): return not auto_migrate and not auto_promote
def provider_neutral_ir_valid(provider_native_ir_is_canonical,canonical_contract): return not provider_native_ir_is_canonical and canonical_contract=="FA3-VIDEO-CONTRACTS-001"
def backend_match_valid(requested,observed): return bool(requested) and requested==observed
def fallback_valid(explicit,authorized,silent): return explicit and authorized and not silent
def accelerator_valid(hrb,uuid,bdf,ordinal_only): return hrb and bool(uuid) and bool(bdf) and not ordinal_only
def runtime_tuple_valid(runtime,adapter,model): return bool(runtime) and bool(adapter) and bool(model) and all(x not in {"latest","main","floating"} for x in (runtime,adapter,model))
def component_compat_valid(model,vae,text_encoder,compat_evidence): return all((model,vae,text_encoder,compat_evidence))
def cache_not_authority(derived_only,canonical_state): return derived_only and not canonical_state
def cache_key_valid(model,vae,encoder,runtime,semantic): return all((model,vae,encoder,runtime,semantic))
def cache_invalidation_valid(version_changed,semantic_changed,invalidated): return invalidated==(version_changed or semantic_changed)
def cache_scope_valid(scope,tenant,broad_global): return bool(scope) and bool(tenant) and not broad_global
def cache_provenance_valid(source_hashes,receipt): return bool(source_hashes) and bool(receipt)
def cache_recompute_valid(stale,reused,recomputed): return (not stale and (reused or recomputed)) or (stale and not reused and recomputed)
def open_sora_backend_valid(version,backend,gpu_production): return version=="v1.5.0" and backend=="ASCEND_910_SERIES" and not gpu_production
def open_sora_gpu_claim_valid(readme_state,production_evidence): return readme_state=="COMING_SOON" and not production_evidence
def open_sora_license_valid(root_license,metadata_license,blocked): return root_license=="MIT" and metadata_license=="Apache" and blocked
def helios_license_valid(code_license,model_license_separate): return code_license=="Apache-2.0" and model_license_separate
def low_vram_preflight_valid(vram_claim,host_ram_checked,cgroup_checked,hrb): return bool(vram_claim) and host_ram_checked and cgroup_checked and hrb
def context_parallel_valid(enabled,placement_authority): return (not enabled) or not placement_authority
def offload_valid(enabled,hrb_bypassed): return (not enabled) or not hrb_bypassed
def long_video_lineage_valid(frames,fps,duration,model_variant): return frames>0 and fps>0 and duration>0 and bool(model_variant) and abs(duration-(frames/fps))<1.0
def variant_identity_valid(variants,digests): return len(variants)==len(set(variants))==len(digests) and all(digests.get(x) for x in variants)
def integration_target_valid(is_adapter,routing_authority): return is_adapter and not routing_authority
def promotion_valid(license_pass,resource_pass,e2e,qc,provenance,rollback,claimed): return claimed==(license_pass and resource_pass and e2e and qc and provenance and rollback)
def disabled_valid(enabled,resident,workers,leases): return enabled or (resident==0 and workers==0 and leases==0)
def migration_provenance_valid(old_provider,new_provider,artifact_lineage,execution_lineage): return old_provider==OPEN_SORA_ID and new_provider==HELIOS_ID and artifact_lineage and execution_lineage

def run_regressions():
    c=[]
    def add(rule,name,p,n): c.append({"rule_id":rule,"name":name,"status":"PASS" if p and n else "FAIL","positive_case":bool(p),"negative_case":bool(n)})
    add(P0_RULES[0],"providers are never architectural authorities",provider_not_authority(),not provider_not_authority(False,True,True))
    add(P0_RULES[1],"capability and authority count invariant",count_invariant(),not count_invariant(144,1,1))
    add(P0_RULES[2],"immutable upstream pins",immutable_pins_valid(OPEN_SORA_PIN,HELIOS_PIN),not immutable_pins_valid("main",HELIOS_PIN))
    add(P0_RULES[3],"explicit predecessor successor lifecycle",lifecycle_valid(OPEN_SORA_ID,HELIOS_ID,True),not lifecycle_valid(OPEN_SORA_ID,HELIOS_ID,False))
    add(P0_RULES[4],"lifecycle transition never auto promotes",lifecycle_no_auto_promotion(False,False),not lifecycle_no_auto_promotion(True,True))
    add(P0_RULES[5],"canonical video IR remains provider neutral",provider_neutral_ir_valid(False,"FA3-VIDEO-CONTRACTS-001"),not provider_neutral_ir_valid(True,"provider-ir"))
    add(P0_RULES[6],"requested backend equals observed backend",backend_match_valid("cuda","cuda"),not backend_match_valid("cuda","cpu"))
    add(P0_RULES[7],"backend fallback explicit and authorized",fallback_valid(True,True,False),not fallback_valid(False,False,True))
    add(P0_RULES[8],"local accelerator requires HRB UUID BDF",accelerator_valid(True,"GPU-u","0000:05:00.0",False),not accelerator_valid(False,None,None,True))
    add(P0_RULES[9],"runtime adapter model tuple pinned",runtime_tuple_valid("torch-2.10.0","diffusers-0.38.0","sha256:model"),not runtime_tuple_valid("latest","main","floating"))
    add(P0_RULES[10],"model VAE text encoder compatibility explicit",component_compat_valid("m","v","t","receipt"),not component_compat_valid("m",None,"t",None))
    add(P0_RULES[11],"cache is derived not canonical state",cache_not_authority(True,False),not cache_not_authority(False,True))
    add(P0_RULES[12],"cache key binds all semantic component identities",cache_key_valid("m","v","t","r","s"),not cache_key_valid("m","v",None,"r","s"))
    add(P0_RULES[13],"cache invalidates on version or semantic drift",cache_invalidation_valid(True,False,True),not cache_invalidation_valid(True,False,False))
    add(P0_RULES[14],"cache scope and tenant explicit",cache_scope_valid("job:a","tenant:a",False),not cache_scope_valid(None,None,True))
    add(P0_RULES[15],"cache provenance required",cache_provenance_valid(["sha256:a"],"receipt"),not cache_provenance_valid([],None))
    add(P0_RULES[16],"stale cache recomputed never silently reused",cache_recompute_valid(True,False,True),not cache_recompute_valid(True,True,False))
    add(P0_RULES[17],"Open-Sora v1.5 Ascend-only reference at pin",open_sora_backend_valid("v1.5.0","ASCEND_910_SERIES",False),not open_sora_backend_valid("v1.5.0","CUDA",True))
    add(P0_RULES[18],"Open-Sora future GPU statement is not evidence",open_sora_gpu_claim_valid("COMING_SOON",False),not open_sora_gpu_claim_valid("COMING_SOON",True))
    add(P0_RULES[19],"Open-Sora license metadata drift blocks admission",open_sora_license_valid("MIT","Apache",True),not open_sora_license_valid("MIT","Apache",False))
    add(P0_RULES[20],"Helios code and model license dimensions separate",helios_license_valid("Apache-2.0",True),not helios_license_valid("Apache-2.0",False))
    add(P0_RULES[21],"Helios low-VRAM mode preflights host RAM and cgroup",low_vram_preflight_valid("~6GB",True,True,True),not low_vram_preflight_valid("~6GB",False,False,False))
    add(P0_RULES[22],"context parallelism is not placement authority",context_parallel_valid(True,False),not context_parallel_valid(True,True))
    add(P0_RULES[23],"offload does not bypass HRB",offload_valid(True,False),not offload_valid(True,True))
    add(P0_RULES[24],"long video frame FPS duration lineage",long_video_lineage_valid(240,24,10.0,"HELIOS_DISTILLED"),not long_video_lineage_valid(240,0,0,None))
    add(P0_RULES[25],"base mid distilled are distinct artifacts",variant_identity_valid(["BASE","MID","DISTILLED"],{"BASE":"a","MID":"b","DISTILLED":"c"}),not variant_identity_valid(["BASE","MID","DISTILLED"],{"BASE":"a","MID":"a"}))
    add(P0_RULES[26],"integration targets remain adapters not routing authority",integration_target_valid(True,False),not integration_target_valid(True,True))
    add(P0_RULES[27],"current-host promotion requires complete evidence",promotion_valid(True,True,True,True,True,True,True),not promotion_valid(False,False,False,False,False,False,True))
    add(P0_RULES[28],"disabled provider has zero near-zero runtime cost",disabled_valid(False,0,0,0),not disabled_valid(False,1,1,1))
    add(P0_RULES[29],"migration preserves artifact and execution provenance",migration_provenance_valid(OPEN_SORA_ID,HELIOS_ID,True,True),not migration_provenance_valid(OPEN_SORA_ID,HELIOS_ID,False,False))
    passed=sum(x["status"]=="PASS" for x in c)
    return {"schema":"fa3.video-provider-lifecycle-regression-report.v1","result":"PASS" if passed==len(c) else "FAIL","passed":passed,"total":len(c),"cases":c}

def scan_authority(root:Path):
    fs=[];scanned=0
    provider_ids={OPEN_SORA_ID,HELIOS_ID}
    for p in sorted((root/"canonical").rglob("*.json")):
        scanned+=1
        try:o=_load(p)
        except Exception as exc:
            fs.append(_f("VPLC-AUTH-000","JSON parse failure",file=str(p.relative_to(root)),error=str(exc)));continue
        def walk(v,path="$"):
            if isinstance(v,dict):
                for k,x in v.items():
                    kp=f"{path}.{k}"
                    if "authority" in k.lower().replace("-","_") and x in provider_ids:
                        fs.append(_f("VPLC-AUTH-001","provider assigned to authority field",file=str(p.relative_to(root)),path=kp,provider=x))
                    walk(x,kp)
            elif isinstance(v,list):
                for i,x in enumerate(v): walk(x,f"{path}[{i}]")
        walk(o)
    return {"result":"PASS" if not fs else "FAIL","scanned_json_files":scanned,"findings":fs}

def reference_check(root:Path):
    fs=[];d={}
    for name,rel in PATHS.items():
        p=root/rel
        if not p.is_file():
            fs.append(_f("VPLC-REF-001","required file missing",path=rel));continue
        try:d[name]=_load(p)
        except Exception as exc: fs.append(_f("VPLC-REF-002","invalid JSON",path=rel,error=str(exc)))
    if fs:return {"result":"FAIL","findings":fs}
    osp,hel,c,dec,ref,gate_rec,enf,adm,ev,pol,profile,venf=[d[x] for x in ("open_sora","helios","contract","decision","reference","gate_record","enforcement","admission","evidence","policy","profile","video_enforcement")]
    if not(osp.get("id")==OPEN_SORA_ID and osp.get("canonical_root") is False and osp.get("architectural_authority") is False and osp.get("capability_projection")==CAPABILITIES and osp.get("capability_count")==143 and osp.get("upstream",{}).get("immutable_commit")==OPEN_SORA_PIN):
        fs.append(_f("VPLC-REF-003","Open-Sora provider drift"))
    if not(hel.get("id")==HELIOS_ID and hel.get("canonical_root") is False and hel.get("architectural_authority") is False and hel.get("capability_projection")==CAPABILITIES and hel.get("capability_count")==143 and hel.get("upstream",{}).get("immutable_commit")==HELIOS_PIN):
        fs.append(_f("VPLC-REF-004","Helios provider drift"))
    if not(c.get("id")==CONTRACT_ID and c.get("status")=="CANONICAL" and c.get("provider_neutral") is True and c.get("rules",{}).get("cache_is_derived_not_canonical") is True):
        fs.append(_f("VPLC-REF-005","contract drift"))
    if not(dec.get("id")==DECISION_ID and dec.get("mandatory_p0_rules")==P0_RULES and dec.get("new_capabilities")==0 and dec.get("new_architectural_authorities")==0 and dec.get("capability_count_after")==143):
        fs.append(_f("VPLC-REF-006","decision drift"))
    if not(ref.get("id")==REFERENCE_ID and ref.get("open_sora_plan",{}).get("immutable_observed_commit")==OPEN_SORA_PIN and ref.get("helios",{}).get("immutable_observed_commit")==HELIOS_PIN and ref.get("promotion_evidence") is False):
        fs.append(_f("VPLC-REF-007","upstream reference drift"))
    if not(gate_rec.get("id")==EXECUTABLE_GATE_ID and gate_rec.get("gateset_id")==GATE_ID and gate_rec.get("mandatory_rule_count")==30 and gate_rec.get("fail_closed") is True):
        fs.append(_f("VPLC-REF-008","gate record drift"))
    if not(enf.get("gate_id")==GATE_ID and enf.get("p0_invariants")==P0_RULES and enf.get("mandatory_rule_count")==30 and enf.get("fail_closed") is True):
        fs.append(_f("VPLC-REF-009","enforcement drift"))
    if not(adm.get("production_provider_admission") is False and adm.get("current_host_runtime_evidence")=="NOT_CLAIMED" and adm.get("global_promotion_claim") is False):
        fs.append(_f("VPLC-REF-010","runtime incorrectly promoted"))
    if not(ev.get("id")==EVIDENCE_ID and ev.get("status")=="PASS" and ev.get("regression_cases_total")==30 and ev.get("regression_cases_passed")==30 and ev.get("current_host_provider_runtime_evidence") is False):
        fs.append(_f("VPLC-REF-011","reference evidence drift"))
    if GATE_ID not in pol.get("mandatory_reference_gates",[]) or pol.get("video_provider_lifecycle_contract_id")!=CONTRACT_ID or pol.get("video_provider_lifecycle_provider_ids")!=[OPEN_SORA_ID,HELIOS_ID] or pol.get("video_provider_lifecycle_mandatory_p0_rules")!=P0_RULES:
        fs.append(_f("VPLC-REF-012","global enforcement policy binding drift"))
    if not all(x in profile.get("providers",[]) for x in (OPEN_SORA_ID,HELIOS_ID)) or CONTRACT_ID not in profile.get("contracts",[]):
        fs.append(_f("VPLC-REF-013","video profile binding missing"))
    if not all(x in venf.get("provider_ids",[]) for x in (OPEN_SORA_ID,HELIOS_ID)) or venf.get("provider_lifecycle_gate")!=GATE_ID:
        fs.append(_f("VPLC-REF-014","video enforcement binding missing"))
    return {"result":"PASS" if not fs else "FAIL","findings":fs}

def gate(root:Path):
    ref=reference_check(root);auth=scan_authority(root);reg=run_regressions()
    ok=ref["result"]==auth["result"]==reg["result"]=="PASS"
    r={"schema":"fa3.video-provider-lifecycle-gate-report.v1","gate_id":GATE_ID,"executable_gate_id":EXECUTABLE_GATE_ID,"profile_id":PROFILE_ID,"contract_id":CONTRACT_ID,"provider_ids":[OPEN_SORA_ID,HELIOS_ID],"capability_count":143,"result":"PASS" if ok else "FAIL","reference":ref,"authority_scan":auth,"regressions":reg,"runtime_provider_required":False,"current_host_provider_runtime_evidence":False,"runtime_activation_status":"REFERENCE_AND_CANDIDATE_NOT_PROMOTED"}
    _write(root/"reports/video-provider-lifecycle-gate-report.json",r)
    return r

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));a=ap.parse_args()
    r=gate(Path(a.root).resolve());print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
