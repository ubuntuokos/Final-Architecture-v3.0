#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

PROVIDER_ID="FA3-PROVIDER-CAVEMAN-001"
CONTRACT_ID="FA3-CONTEXT-TRANSFORM-CONTRACTS-001"
DECISION_ID="FA3-DEC-CAVEMAN-2026-08-30"
REFERENCE_ID="FA3-CAVEMAN-UPSTREAM-REFERENCE-2026-08-31"
GATE_ID="FA3-CAVEMAN-GATESET-001"
EVIDENCE_ID="FA3-EVIDENCE-CAVEMAN-CI-2026-08-31"
RECON_EVIDENCE_ID="FA3-EVIDENCE-CAVEMAN-GLOBAL-RECONCILIATION-2026-08-31"
UPSTREAM_RELEASE="v2.4.0"
UPSTREAM_COMMIT="df2ccd85c94ec3c8289cb62ac020d241ccfb0c60"
UPSTREAM_TAG_OBJECT="ae10845a5e4c958db8a5b52018c9ebc7ce534874"
CAPABILITY_ID="CAP-010"
CAPABILITY_COUNT=143
P0_INVARIANTS=["CAVEMAN_RECOVERY_BEFORE_LOSSY_TRANSFORM","CAVEMAN_CANONICAL_ORIGINAL_IMMUTABLE","CAVEMAN_FAILURE_UNSUPPORTED_EXACT_PASS_THROUGH","CAVEMAN_MEASURABLE_BENEFIT_GATE_REQUIRED","CAVEMAN_SEMANTIC_FIDELITY_AND_TASK_SUCCESS_GATE_REQUIRED","CAVEMAN_MEASUREMENT_PROVENANCE_CLASS_REQUIRED","CAVEMAN_RECORD_BASELINE_BEFORE_OPTIMIZE","CAVEMAN_UNKNOWN_UNSUPPORTED_NO_TRANSFORM","CAVEMAN_SOURCE_HASH_RECOVERY_LINEAGE_REQUIRED","CAVEMAN_RECOVERY_STORE_SENSITIVE_AND_HARDENED","CAVEMAN_BOUNDED_INPUT_RECOVERY_AND_RETENTION","CAVEMAN_CACHE_STABILITY_VOLATILITY_EXPLICIT","CAVEMAN_SEMANTIC_DEGRADATION_ROLLBACK_REQUIRED","CAVEMAN_TELEMETRY_OFF_UNLESS_EXPLICITLY_AUTHORIZED","CAVEMAN_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY"]

def _load(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def _write(p:Path,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _f(code,msg,**kw): return {"code":code,"severity":"P0","message":msg,**kw}
def _is_caveman(v:Any)->bool:
    if isinstance(v,str):
        u=v.upper()
        return PROVIDER_ID in v or "JULIUSBRUSSEE/CAVEMAN" in u or u.startswith("FA3-AUTH-CAVEMAN")
    if isinstance(v,dict): return any(_is_caveman(x) for x in v.values())
    if isinstance(v,(list,tuple,set)): return any(_is_caveman(x) for x in v)
    return False

def recovery_before_lossy_valid(*,lossy,recovery_persisted,recovery_handle,source_hash):
    return (not lossy) or bool(recovery_persisted and recovery_handle and source_hash)
def canonical_original_preserved_valid(*,source_mutated): return source_mutated is False
def failure_passthrough_valid(*,transform_status,input_payload,output_payload):
    return transform_status not in {"ERROR","UNSUPPORTED","POLICY_DENIED","NO_BENEFIT","FIDELITY_FAIL"} or output_payload==input_payload
def measurable_benefit_valid(*,token_before,token_after,min_savings_ratio=0.01):
    return token_before>0 and token_after>=0 and (token_before-token_after)/token_before>=min_savings_ratio
def quality_gate_valid(*,lossy,semantic_fidelity_pass,task_success_pass):
    return (not lossy) or bool(semantic_fidelity_pass and task_success_pass)
def measurement_provenance_valid(*,evidence_class,claimed_verified,provider_receipt_present):
    if evidence_class not in {"INFERRED","BENCHMARK_COUNTERFACTUAL","VERIFIED"}: return False
    if claimed_verified and evidence_class!="VERIFIED": return False
    if evidence_class=="VERIFIED" and not provider_receipt_present: return False
    return True
def record_before_optimize_valid(*,mode,baseline_recorded): return mode=="RECORD" or bool(baseline_recorded)
def unsupported_no_transform_valid(*,supported,output_equals_input): return supported or bool(output_equals_input)
def lineage_valid(*,source_artifact_id,source_sha256,projection_artifact_id,recovery_source_sha256,lossy):
    if not all((source_artifact_id,source_sha256,projection_artifact_id)): return False
    return (not lossy) or recovery_source_sha256==source_sha256
def recovery_storage_valid(*,classification,file_mode,canonical_path_validated,symlink_rejected,retention_bounded,secret_policy_declared):
    try: mode=int(file_mode)
    except Exception: return False
    return bool(classification=="SENSITIVE" and (mode & 0o077)==0 and canonical_path_validated and symlink_rejected and retention_bounded and secret_policy_declared)
def bounded_resources_valid(*,input_bytes,max_input_bytes,recovery_bytes,max_recovery_bytes,retention_days,max_retention_days):
    vals=(input_bytes,max_input_bytes,recovery_bytes,max_recovery_bytes,retention_days,max_retention_days)
    return not any(int(x)<0 for x in vals) and input_bytes<=max_input_bytes and recovery_bytes<=max_recovery_bytes and retention_days<=max_retention_days
def cache_classification_valid(segment_class): return segment_class in {"STABLE","VOLATILE"}
def semantic_rollback_valid(*,fidelity_pass,rollback_available,rolled_back): return bool(fidelity_pass) or bool(rollback_available and rolled_back)
def telemetry_default_valid(*,explicitly_authorized,enabled): return (not enabled) or bool(explicitly_authorized)

def provider_shape_valid(p):
    cls=set(p.get("classification",[]))
    return bool(p.get("id")==PROVIDER_ID and p.get("parent_profile")=="FA3-KNOWLEDGE-001" and {"OPTIONAL_PROVIDER","REFERENCE_PROVIDER","ARCHITECTURAL_PATTERN_SOURCE"}<=cls and p.get("contract_id")==CONTRACT_ID and p.get("gate_id")==GATE_ID and p.get("canonical_root") is False and p.get("architectural_authority") is False and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==CAPABILITY_COUNT and p.get("activation_mode")=="OPTIONAL_DISABLED_BY_DEFAULT" and p.get("runtime_activation_status")=="NOT_PROMOTED_REFERENCE_ONLY" and p.get("runtime_activation_requires_current_host_conformance") is True and p.get("current_host_runtime_evidence")=="NOT_CLAIMED" and p.get("global_runtime_promotion_required_when_disabled") is False and p.get("canonical_original_mutation_forbidden") is True and p.get("telemetry_default")=="OFF_UNLESS_EXPLICITLY_AUTHORIZED")

AUTH_KEYS=("identity_authority","authentication_authority","authorization_authority","secrets_authority","mcp_authority","capability_gateway_authority","model_routing_authority","workflow_authority","orchestration_authority","evidence_authority","network_egress_authority","host_resource_authority","developer_execution_authority","artifact_trust_authority","registry_authority","memory_authority","resource_authority","knowledge_authority","cache_policy_authority","authority_owner","authority_provider")
def _scan(v:Any,file_path:str,path="$"):
    out=[]
    if isinstance(v,dict):
        scoped=any(_is_caveman(v.get(k)) for k in ("id","provider_id","provider","subject","name","implementation") if k in v)
        if scoped and v.get("architectural_authority") is True: out.append(_f("CAVEMAN-AUTH-001","Caveman architectural_authority enabled",file=file_path,path=path+".architectural_authority"))
        if scoped and v.get("canonical_root") is True: out.append(_f("CAVEMAN-AUTH-002","Caveman promoted to canonical root",file=file_path,path=path+".canonical_root"))
        for k,x in v.items():
            nk=k.lower().replace("-","_")
            if (nk in AUTH_KEYS or nk.endswith("_authority")) and _is_caveman(x): out.append(_f("CAVEMAN-AUTH-003","Caveman assigned to authority-bearing field",file=file_path,path=path+"."+k))
            out.extend(_scan(x,file_path,path+"."+k))
    elif isinstance(v,list):
        for i,x in enumerate(v): out.extend(_scan(x,file_path,f"{path}[{i}]"))
    return out

def scan_canonical_authority_assignments(root:Path):
    findings=[]; scanned=0; c=root/"canonical"
    if not c.exists(): return {"result":"FAIL","scanned_json_files":0,"findings":[_f("CAVEMAN-AUTH-000","canonical directory missing")]}
    for p in sorted(c.rglob("*.json")):
        scanned+=1
        try: findings.extend(_scan(_load(p),str(p.relative_to(root))))
        except Exception as e: findings.append(_f("CAVEMAN-AUTH-004","Canonical JSON parse failure",file=str(p.relative_to(root)),error=str(e)))
    return {"result":"PASS" if not findings else "FAIL","scanned_json_files":scanned,"findings":findings}

def reference_check(root:Path):
    paths={"provider":root/"canonical/providers/FA3-PROVIDER-CAVEMAN-001.json","contract":root/"canonical/contracts/FA3-CONTEXT-TRANSFORM-CONTRACTS-001.json","decision":root/"canonical/decisions/FA3-DEC-CAVEMAN-2026-08-30.json","reference":root/"canonical/references/FA3-CAVEMAN-UPSTREAM-REFERENCE-2026-08-31.json","enforcement":root/"canonical/caveman-enforcement.json","evidence":root/"evidence/reference/caveman-ci-2026-08-31.json","reconciliation_evidence":root/"evidence/reference/caveman-global-reconciliation-ci-2026-08-31.json","policy":root/"canonical/enforcement-policy.json","registry":root/"evidence/evidence-registry.json"}
    f=[]
    for n,p in paths.items():
        if not p.exists(): f.append(_f("CAVEMAN-REF-001",f"Missing Caveman artifact: {n}",file=str(p.relative_to(root))))
    if f:return {"result":"FAIL","findings":f}
    p,c,d,r,e,ev,gr,pol,registry=(_load(paths[k]) for k in ("provider","contract","decision","reference","enforcement","evidence","reconciliation_evidence","policy","registry"))
    if not provider_shape_valid(p): f.append(_f("CAVEMAN-REF-002","Caveman provider invariant drift"))
    if not (c.get("id")==CONTRACT_ID and c.get("parent_profile")=="FA3-KNOWLEDGE-001" and c.get("provider_neutral") is True and c.get("canonical_original_mutation_forbidden") is True and c.get("new_capability") is False and c.get("new_architectural_authority") is False and c.get("capability_count")==CAPABILITY_COUNT): f.append(_f("CAVEMAN-REF-003","Context transformation contract invariant drift"))
    if not (d.get("id")==DECISION_ID and d.get("status")=="CANONICAL_CLOSED" and d.get("contract_id")==CONTRACT_ID and d.get("gate_id")==GATE_ID and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("capability_count_after")==CAPABILITY_COUNT): f.append(_f("CAVEMAN-REF-004","Caveman decision invariant drift"))
    disp=r.get("fa3_disposition",{})
    if not (r.get("id")==REFERENCE_ID and r.get("latest_release")==UPSTREAM_RELEASE and r.get("latest_release_commit")==UPSTREAM_COMMIT and r.get("latest_release_tag_object")==UPSTREAM_TAG_OBJECT and r.get("latest_release_tag_signature_verified") is True and disp.get("promotion_evidence") is False and disp.get("floating_main_allowed_as_promotion_evidence") is False and disp.get("runtime_activation_requires_separate_current_host_conformance") is True): f.append(_f("CAVEMAN-REF-005","Caveman immutable upstream reference drift"))
    if not (e.get("gate_id")==GATE_ID and e.get("contract_id")==CONTRACT_ID and e.get("fail_closed") is True and e.get("mandatory_rule_count")==len(P0_INVARIANTS) and e.get("p0_invariants")==P0_INVARIANTS and e.get("current_host_runtime_claim") is False): f.append(_f("CAVEMAN-REF-006","Caveman enforcement drift"))
    if not (ev.get("id")==EVIDENCE_ID and ev.get("status")=="PASS" and ev.get("regression_cases",{}).get("passed")==15 and ev.get("regression_cases",{}).get("total")==15 and ev.get("current_host_runtime_evidence")=="NOT_CLAIMED" and ev.get("current_host_production_claim") is False): f.append(_f("CAVEMAN-REF-007","Caveman PASS evidence drift"))
    if not (gr.get("id")==RECON_EVIDENCE_ID and gr.get("provider_id")==PROVIDER_ID and gr.get("capability_id")==CAPABILITY_ID and gr.get("status")=="PASS" and gr.get("conclusion")=="GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILIATION_PASS"): f.append(_f("CAVEMAN-REF-008","Caveman global reconciliation evidence drift"))
    if GATE_ID not in pol.get("mandatory_reference_gates",[]): f.append(_f("CAVEMAN-REF-009","Caveman gate missing from global policy"))
    if pol.get("caveman_provider_id")!=PROVIDER_ID or pol.get("caveman_context_transform_contract_id")!=CONTRACT_ID or pol.get("caveman_mandatory_p0_rules")!=P0_INVARIANTS: f.append(_f("CAVEMAN-REF-010","Global Caveman policy binding drift"))
    cap=next((x for x in registry.get("records",[]) if x.get("subject_id")==CAPABILITY_ID),{})
    req={"evidence/reference/caveman-ci-2026-08-31.json","evidence/reference/caveman-global-reconciliation-ci-2026-08-31.json"}; cps=cap.get("caveman_provider_projection_status",{})
    if not (DECISION_ID in cap.get("source_decision_ids",[]) and req<=set(cap.get("evidence_artifacts",[])) and cap.get("runtime_conformance")=="EVIDENCE-PENDING" and cap.get("status")=="PENDING_CURRENT_HOST" and cap.get("promotion_state")=="NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE" and cps.get("provider_id")==PROVIDER_ID and cps.get("reference_gate_status")=="PASS" and cps.get("runtime_activation_status")=="NOT_PROMOTED_REFERENCE_ONLY" and cps.get("current_host_runtime_evidence")=="NOT_CLAIMED"): f.append(_f("CAVEMAN-REF-011","CAP-010 Caveman evidence reconciliation drift"))
    return {"result":"PASS" if not f else "FAIL","findings":f}

def _case(i,name,pos,neg): return {"rule_id":f"FA3-CAVEMAN-P0-{i:03d}","name":name,"status":"PASS" if pos and neg else "FAIL","positive_case":bool(pos),"negative_case":bool(neg)}
def run_regressions():
    c=[]
    c.append(_case(1,"recovery before lossy transform",recovery_before_lossy_valid(lossy=True,recovery_persisted=True,recovery_handle="r",source_hash="h"),not recovery_before_lossy_valid(lossy=True,recovery_persisted=False,recovery_handle=None,source_hash="h")))
    c.append(_case(2,"canonical original immutable",canonical_original_preserved_valid(source_mutated=False),not canonical_original_preserved_valid(source_mutated=True)))
    c.append(_case(3,"failure exact pass-through",failure_passthrough_valid(transform_status="ERROR",input_payload=b"abc",output_payload=b"abc"),not failure_passthrough_valid(transform_status="ERROR",input_payload=b"abc",output_payload=b"ab")))
    c.append(_case(4,"measurable benefit gate",measurable_benefit_valid(token_before=1000,token_after=800),not measurable_benefit_valid(token_before=1000,token_after=999)))
    c.append(_case(5,"semantic fidelity and task success",quality_gate_valid(lossy=True,semantic_fidelity_pass=True,task_success_pass=True),not quality_gate_valid(lossy=True,semantic_fidelity_pass=True,task_success_pass=False)))
    c.append(_case(6,"measurement provenance class",measurement_provenance_valid(evidence_class="VERIFIED",claimed_verified=True,provider_receipt_present=True),not measurement_provenance_valid(evidence_class="INFERRED",claimed_verified=True,provider_receipt_present=False)))
    c.append(_case(7,"record baseline before optimize",record_before_optimize_valid(mode="ACTIVE",baseline_recorded=True),not record_before_optimize_valid(mode="ACTIVE",baseline_recorded=False)))
    c.append(_case(8,"unsupported no transform",unsupported_no_transform_valid(supported=False,output_equals_input=True),not unsupported_no_transform_valid(supported=False,output_equals_input=False)))
    c.append(_case(9,"source hash recovery lineage",lineage_valid(source_artifact_id="a",source_sha256="h",projection_artifact_id="p",recovery_source_sha256="h",lossy=True),not lineage_valid(source_artifact_id="a",source_sha256="h",projection_artifact_id="p",recovery_source_sha256="x",lossy=True)))
    c.append(_case(10,"sensitive hardened recovery storage",recovery_storage_valid(classification="SENSITIVE",file_mode=0o600,canonical_path_validated=True,symlink_rejected=True,retention_bounded=True,secret_policy_declared=True),not recovery_storage_valid(classification="SENSITIVE",file_mode=0o644,canonical_path_validated=True,symlink_rejected=True,retention_bounded=True,secret_policy_declared=True)))
    c.append(_case(11,"bounded input recovery retention",bounded_resources_valid(input_bytes=64,max_input_bytes=128,recovery_bytes=64,max_recovery_bytes=128,retention_days=7,max_retention_days=30),not bounded_resources_valid(input_bytes=129,max_input_bytes=128,recovery_bytes=64,max_recovery_bytes=128,retention_days=7,max_retention_days=30)))
    c.append(_case(12,"cache stability volatility explicit",cache_classification_valid("STABLE"),not cache_classification_valid("UNKNOWN")))
    c.append(_case(13,"semantic degradation rollback",semantic_rollback_valid(fidelity_pass=False,rollback_available=True,rolled_back=True),not semantic_rollback_valid(fidelity_pass=False,rollback_available=True,rolled_back=False)))
    c.append(_case(14,"telemetry explicit authorization",telemetry_default_valid(explicitly_authorized=False,enabled=False),not telemetry_default_valid(explicitly_authorized=False,enabled=True)))
    gp={"id":PROVIDER_ID,"parent_profile":"FA3-KNOWLEDGE-001","classification":["OPTIONAL_PROVIDER","REFERENCE_PROVIDER","ARCHITECTURAL_PATTERN_SOURCE"],"contract_id":CONTRACT_ID,"gate_id":GATE_ID,"canonical_root":False,"architectural_authority":False,"new_capability":False,"new_architectural_authority":False,"capability_count":143,"activation_mode":"OPTIONAL_DISABLED_BY_DEFAULT","runtime_activation_status":"NOT_PROMOTED_REFERENCE_ONLY","runtime_activation_requires_current_host_conformance":True,"current_host_runtime_evidence":"NOT_CLAIMED","global_runtime_promotion_required_when_disabled":False,"canonical_original_mutation_forbidden":True,"telemetry_default":"OFF_UNLESS_EXPLICITLY_AUTHORIZED"}; bp=dict(gp); bp["architectural_authority"]=True
    c.append(_case(15,"provider non-authority invariant",provider_shape_valid(gp),not provider_shape_valid(bp)))
    passed=sum(x["status"]=="PASS" for x in c)
    return {"schema":"fa3.caveman-regression-report.v1","result":"PASS" if passed==len(c) else "FAIL","passed":passed,"total":len(c),"cases":c}

def gate(root:Path):
    ref=reference_check(root); scan=scan_canonical_authority_assignments(root); reg=run_regressions()
    ok=ref["result"]==scan["result"]==reg["result"]=="PASS"
    out={"schema":"fa3.caveman-gate-report.v1","gate_id":GATE_ID,"provider_id":PROVIDER_ID,"contract_id":CONTRACT_ID,"capability_id":CAPABILITY_ID,"capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL","mode":"RECOVERABLE_CONTEXT_TRANSFORMATION_AND_AUTHORITY_BOUNDARY_REGRESSION","reference":ref,"authority_scan":scan,"regressions":reg,"runtime_provider_required":False,"runtime_activation_status":"NOT_PROMOTED_REFERENCE_ONLY","current_host_runtime_evidence":"NOT_CLAIMED","promotion_effect":"CANONICAL_RULES_AND_REFERENCE_EVIDENCE_ONLY_NO_PROVIDER_RUNTIME_PROMOTION"}
    _write(root/"reports/caveman-gate-report.json",out); return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args()
    r=gate(Path(a.root).resolve()); print(json.dumps(r,indent=2)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
