#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
GATE_ID="FA3-TENCENTDB-AGENT-MEMORY-GATESET-001"; EXECUTABLE_GATE_ID="FA3-GATE-TENCENTDB-AGENT-MEMORY-001"; PROVIDER_ID="FA3-PROVIDER-TENCENTDB-AGENT-MEMORY-001"; CONTRACT_ID="FA3-AGENT-MEMORY-ASSET-GOVERNANCE-CONTRACTS-001"; DECISION_ID="FA3-DEC-TENCENTDB-AGENT-MEMORY-2026-09-03"; REFERENCE_ID="FA3-TENCENTDB-AGENT-MEMORY-UPSTREAM-REFERENCE-2026-09-03"; EVIDENCE_ID="FA3-EVIDENCE-TENCENTDB-AGENT-MEMORY-CI-2026-09-03"; PINNED_COMMIT="3efcd317b84146d6a08518ac0f7ee7c8a8d200ec"; RUNTIME_STATUS="NOT_ADMITTED_PENDING_SECURITY_LICENSE_CURRENT_HOST"; CAPABILITY_COUNT=143
CAPABILITY_IDS=["CAP-010","CAP-021","CAP-023","CAP-094","CAP-102","CAP-110","CAP-139"]
P0_RULES=["TDAI_PROVIDER_NOT_AUTHORITY","TDAI_CAPABILITY_AUTHORITY_COUNT_INVARIANT","TDAI_UPSTREAM_IMMUTABLE_PIN_REQUIRED","TDAI_LAYERED_L0_L3_LINEAGE_REQUIRED","TDAI_SOURCE_DERIVED_MEMORY_SEPARATION_REQUIRED","TDAI_MEMORY_ASSET_OWNER_VISIBILITY_VERSION_EXPLICIT","TDAI_CROSS_AGENT_RECALL_REQUIRES_EXPLICIT_BINDING","TDAI_FANOUT_RESULTS_PRESERVE_SOURCE_AGENT_PROVENANCE","TDAI_PERMISSION_FILTER_BEFORE_RELEVANCE_AND_RERANK","TDAI_MISSING_SCOPE_CANNOT_SILENTLY_BROADEN_RECALL","TDAI_RETRIEVAL_ITEM_CONTEXT_TIME_BUDGETS_REQUIRED","TDAI_DURABLE_WRITE_REQUIRES_TYPED_CONSENT_AUTHORITY_ESCALATION","TDAI_CONSOLIDATION_IDEMPOTENT_REPLAY_SAFE","TDAI_DERIVED_MEMORY_VERSION_SUPERSEDES_LINEAGE","TDAI_DELETE_REVOKE_TOMBSTONE_PROPAGATION_REQUIRED","TDAI_SKILL_ASSET_VERSION_REVIEW_AND_CAPABILITY_NARROWING","TDAI_ON_DEMAND_KNOWLEDGE_NO_GLOBAL_CORPUS_AUTO_INJECTION","TDAI_FRAMEWORK_PORTABILITY_PRESERVES_IDENTITY_PROVENANCE","TDAI_MEMORY_EVENTS_EXPORT_VIA_CANONICAL_EVIDENCE","TDAI_PROXY_CANNOT_BYPASS_CENTRAL_POLICY_MEMORY_GATEWAY","TDAI_PROVIDER_ACL_NOT_CANONICAL_AUTHORIZATION","TDAI_ADMIN_ENDPOINTS_FAIL_CLOSED_AUTH_REQUIRED","TDAI_EMPTY_ADMIN_CREDENTIAL_FAIL_OPEN_FORBIDDEN","TDAI_GIT_FETCH_SSRF_DNS_REBINDING_PRIVATE_RANGE_DENIED","TDAI_GIT_SOURCE_ARGUMENT_INJECTION_DENIED","TDAI_LICENSE_COMPONENT_CLARITY_REQUIRED_FOR_PRODUCTION","TDAI_HRB_LIVE_NUMA_RESOURCE_ADMISSION_NO_STATIC_HARDWARE_DEFAULTS","TDAI_ACCELERATOR_MODEL_ROUTING_VIA_EXISTING_ROUTER_AND_HRB_UUID_BDF_ONLY","TDAI_CURRENT_HOST_PROMOTION_REQUIRES_SECURITY_LICENSE_E2E","TDAI_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST"]
PATHS={"provider":"canonical/providers/FA3-PROVIDER-TENCENTDB-AGENT-MEMORY-001.json","contract":"canonical/contracts/FA3-AGENT-MEMORY-ASSET-GOVERNANCE-CONTRACTS-001.json","decision":"canonical/decisions/FA3-DEC-TENCENTDB-AGENT-MEMORY-2026-09-03.json","reference":"canonical/references/FA3-TENCENTDB-AGENT-MEMORY-UPSTREAM-REFERENCE-2026-09-03.json","gate_record":"canonical/FA3-GATE-TENCENTDB-AGENT-MEMORY-001.json","enforcement":"canonical/tencentdb-agent-memory-enforcement.json","admission":"canonical/tencentdb-agent-memory-runtime-admission.json","evidence":"evidence/reference/tencentdb-agent-memory-ci-2026-09-03.json","policy":"canonical/enforcement-policy.json","knowledge":"canonical/profiles/FA3-KNOWLEDGE-001.json"}
def _load(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def _write(p:Path,v:dict[str,Any])->None: p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _f(code,msg,**extra): return {"code":code,"severity":"P0","message":msg,**extra}
def provider_not_authority(canonical_root=False,architectural_authority=False,provider_owns_boundary=False): return not canonical_root and not architectural_authority and not provider_owns_boundary
def count_invariant(capability_count=143,new_capabilities=0,new_authorities=0): return capability_count==143 and new_capabilities==0 and new_authorities==0
def immutable_pin_valid(commit): return commit==PINNED_COMMIT and commit not in {"main","master","latest","floating",""}
def layered_lineage_valid(levels,source_linked): return levels==["L0_CONVERSATION","L1_ATOM","L2_SCENARIO","L3_CORE_PERSONA"] and source_linked
def source_derived_valid(raw_preserved,separate_types): return raw_preserved and separate_types
def asset_governance_valid(owner,visibility,version,status): return owner and visibility and version and status
def binding_valid(explicit_binding,same_team,authorized): return explicit_binding and same_team and authorized
def fanout_provenance_valid(rows): return bool(rows) and all(r.get("source_agent_id") and r.get("source_role") in {"self","imported_from"} for r in rows)
def permission_order_valid(stages): return all(x in stages for x in ("permission","retrieve","rerank")) and stages.index("permission")<stages.index("retrieve")<=stages.index("rerank")
def scope_valid(scope,explicit_broad_receipt): return bool(scope) or explicit_broad_receipt
def retrieval_budget_valid(items,max_items,chars,max_chars,elapsed,timeout): return 0<=items<=max_items and 0<=chars<=max_chars and 0<=elapsed<=timeout
def durable_write_valid(typed,consent,authorized): return typed and consent and authorized
def consolidation_valid(idempotency_key,source_hash,replay_same): return bool(idempotency_key) and bool(source_hash) and replay_same
def version_lineage_valid(version,supersedes): return version>=1 and (version==1 or bool(supersedes))
def tombstone_valid(revoked,retrievable,binding_active,propagated): return (not revoked) or (not retrievable and not binding_active and propagated)
def skill_valid(versioned,reviewed,capability_expansion): return versioned and reviewed and not capability_expansion
def knowledge_injection_valid(global_auto,on_demand): return not global_auto and on_demand
def portability_valid(canonical_id,provenance,provider_local_is_canonical): return canonical_id and provenance and not provider_local_is_canonical
def evidence_valid(provider_log_authority,canonical_export): return not provider_log_authority and canonical_export
def proxy_boundary_valid(canonical_policy,direct_bypass): return canonical_policy and not direct_bypass
def provider_acl_valid(provider_allows,canonical_authorized,read_allowed): return read_allowed==(provider_allows and canonical_authorized)
def admin_auth_valid(admin_route,authenticated): return (not admin_route) or authenticated
def empty_admin_key_valid(admin_route,key_configured,request_allowed): return not (admin_route and not key_configured and request_allowed)
def ssrf_valid(dns_resolved,resolved_private,redirects_revalidated,bypass_enabled): return dns_resolved and not resolved_private and redirects_revalidated and not bypass_enabled
def git_arg_valid(url): return url.startswith("https://") and not any(c.isspace() for c in url) and " --" not in url
def license_valid(root_mit,docker_proprietary,written_component_resolution): return root_mit and (not docker_proprietary or written_component_resolution)
def hrb_valid(live_discovery,hrb_receipt,static_cpu_ids,reference_as_constant): return live_discovery and hrb_receipt and not static_cpu_ids and not reference_as_constant
def accelerator_valid(model_router,hrb_lease,uuid,bdf,ordinal_only): return model_router and hrb_lease and bool(uuid) and bool(bdf) and not ordinal_only
def promotion_valid(security_pass,license_pass,real_e2e,claims): return claims==(security_pass and license_pass and real_e2e)
def disabled_valid(enabled,resident,background,leases): return enabled or (resident==0 and background==0 and leases==0)
def run_regressions():
 c=[]
 def add(rule,name,p,n): c.append({"rule_id":rule,"name":name,"status":"PASS" if p and n else "FAIL","positive_case":bool(p),"negative_case":bool(n)})
 add(P0_RULES[0],"provider is never authority",provider_not_authority(),not provider_not_authority(architectural_authority=True,provider_owns_boundary=True))
 add(P0_RULES[1],"143 capability and zero authority delta",count_invariant(),not count_invariant(144,1,1))
 add(P0_RULES[2],"immutable upstream pin",immutable_pin_valid(PINNED_COMMIT),not immutable_pin_valid("main"))
 add(P0_RULES[3],"L0-L3 lineage",layered_lineage_valid(["L0_CONVERSATION","L1_ATOM","L2_SCENARIO","L3_CORE_PERSONA"],True),not layered_lineage_valid(["L0_CONVERSATION","L3_CORE_PERSONA"],False))
 add(P0_RULES[4],"source/derived separation",source_derived_valid(True,True),not source_derived_valid(False,False))
 add(P0_RULES[5],"asset governance explicit",asset_governance_valid(True,True,True,True),not asset_governance_valid(True,False,True,True))
 add(P0_RULES[6],"explicit cross-agent binding",binding_valid(True,True,True),not binding_valid(False,True,True))
 add(P0_RULES[7],"fanout provenance",fanout_provenance_valid([{"source_agent_id":"a1","source_role":"self"},{"source_agent_id":"a2","source_role":"imported_from"}]),not fanout_provenance_valid([{"source_agent_id":"","source_role":"imported_from"}]))
 add(P0_RULES[8],"permission before retrieval",permission_order_valid(["permission","retrieve","rerank"]),not permission_order_valid(["retrieve","permission","rerank"]))
 add(P0_RULES[9],"missing scope cannot broaden",scope_valid("agent:a1",False),not scope_valid(None,False))
 add(P0_RULES[10],"bounded retrieval",retrieval_budget_valid(4,5,8000,10000,50,100),not retrieval_budget_valid(7,5,12000,10000,150,100))
 add(P0_RULES[11],"typed consented authorized write",durable_write_valid(True,True,True),not durable_write_valid(True,False,True))
 add(P0_RULES[12],"idempotent consolidation",consolidation_valid("i","h",True),not consolidation_valid(None,"h",False))
 add(P0_RULES[13],"derived version lineage",version_lineage_valid(2,"v1"),not version_lineage_valid(2,None))
 add(P0_RULES[14],"tombstone propagation",tombstone_valid(True,False,False,True),not tombstone_valid(True,True,True,False))
 add(P0_RULES[15],"skill narrowing",skill_valid(True,True,False),not skill_valid(True,False,True))
 add(P0_RULES[16],"knowledge on demand",knowledge_injection_valid(False,True),not knowledge_injection_valid(True,True))
 add(P0_RULES[17],"portable identity/provenance",portability_valid(True,True,False),not portability_valid(False,False,True))
 add(P0_RULES[18],"canonical evidence export",evidence_valid(False,True),not evidence_valid(True,False))
 add(P0_RULES[19],"proxy boundary",proxy_boundary_valid(True,False),not proxy_boundary_valid(False,True))
 add(P0_RULES[20],"provider ACL not authority",provider_acl_valid(True,True,True),not provider_acl_valid(True,False,True))
 add(P0_RULES[21],"admin auth required",admin_auth_valid(True,True),not admin_auth_valid(True,False))
 add(P0_RULES[22],"empty admin key fail-open denied",empty_admin_key_valid(True,False,False),not empty_admin_key_valid(True,False,True))
 add(P0_RULES[23],"SSRF DNS/rebinding denied",ssrf_valid(True,False,True,False),not ssrf_valid(False,False,False,True))
 add(P0_RULES[24],"Git argument injection denied",git_arg_valid("https://github.com/a/b.git"),not git_arg_valid("https://github.com/a/b.git --upload-pack=x"))
 add(P0_RULES[25],"component licence clarity",license_valid(True,True,True),not license_valid(True,True,False))
 add(P0_RULES[26],"HRB live topology",hrb_valid(True,True,False,False),not hrb_valid(False,False,True,True))
 add(P0_RULES[27],"accelerator UUID+BDF",accelerator_valid(True,True,"GPU-u","0000:05:00.0",False),not accelerator_valid(False,False,None,None,True))
 add(P0_RULES[28],"promotion requires security/licence/E2E",promotion_valid(True,True,True,True),not promotion_valid(False,False,False,True))
 add(P0_RULES[29],"disabled zero residency",disabled_valid(False,0,0,0),not disabled_valid(False,1,1,0))
 p=sum(x["status"]=="PASS" for x in c); return {"schema":"fa3.tencentdb-agent-memory-regression-report.v1","result":"PASS" if p==len(c) else "FAIL","passed":p,"total":len(c),"cases":c}
def scan_authority(root):
 fs=[]; scanned=0
 for p in sorted((root/"canonical").rglob("*.json")):
  scanned+=1
  try:o=_load(p)
  except Exception as exc: fs.append(_f("TDAI-AUTH-000","JSON parse failure",file=str(p.relative_to(root)),error=str(exc))); continue
  def walk(v,path="$"):
   if isinstance(v,dict):
    for k,x in v.items():
     kp=f"{path}.{k}"
     if "authority" in k.lower().replace("-","_") and x==PROVIDER_ID: fs.append(_f("TDAI-AUTH-001","provider assigned to authority field",file=str(p.relative_to(root)),path=kp))
     walk(x,kp)
   elif isinstance(v,list):
    for i,x in enumerate(v): walk(x,f"{path}[{i}]")
  walk(o)
 return {"result":"PASS" if not fs else "FAIL","scanned_json_files":scanned,"findings":fs}
def reference_check(root):
 fs=[];d={}
 for n,rel in PATHS.items():
  p=root/rel
  if not p.is_file(): fs.append(_f("TDAI-REF-001","required file missing",path=rel)); continue
  try:d[n]=_load(p)
  except Exception as exc:fs.append(_f("TDAI-REF-002","invalid JSON",path=rel,error=str(exc)))
 if fs:return {"result":"FAIL","findings":fs}
 p,c,dec,ref,enf,adm,ev,pol,know=[d[x] for x in ("provider","contract","decision","reference","enforcement","admission","evidence","policy","knowledge")]
 if not(p.get("id")==PROVIDER_ID and p.get("canonical_root") is False and p.get("architectural_authority") is False and p.get("capability_projection")==CAPABILITY_IDS and p.get("capability_count")==143 and p.get("runtime_activation_status")==RUNTIME_STATUS):fs.append(_f("TDAI-REF-003","provider drift"))
 if not(c.get("id")==CONTRACT_ID and c.get("status")=="CANONICAL" and c.get("provider_neutral") is True):fs.append(_f("TDAI-REF-004","contract drift"))
 if not(dec.get("id")==DECISION_ID and dec.get("mandatory_p0_rules")==P0_RULES and dec.get("new_capabilities")==0 and dec.get("new_architectural_authorities")==0):fs.append(_f("TDAI-REF-005","decision drift"))
 if not(ref.get("id")==REFERENCE_ID and ref.get("immutable_observed_commit")==PINNED_COMMIT and ref.get("promotion_evidence") is False and ref.get("security_observations",{}).get("issue_672",{}).get("confirmed_at_pin") is True and ref.get("acl_issue_890",{}).get("blocker") is False and ref.get("license_observations",{}).get("issue_1073",{}).get("blocker") is True):fs.append(_f("TDAI-REF-006","upstream risk/reference drift"))
 if not(enf.get("gate_id")==GATE_ID and enf.get("p0_invariants")==P0_RULES and enf.get("mandatory_rule_count")==30 and enf.get("fail_closed") is True):fs.append(_f("TDAI-REF-007","enforcement drift"))
 if not(adm.get("status")==RUNTIME_STATUS and adm.get("production_provider_admission") is False and adm.get("current_host_runtime_evidence")=="NOT_CLAIMED"):fs.append(_f("TDAI-REF-008","runtime incorrectly promoted"))
 if not(ev.get("id")==EVIDENCE_ID and ev.get("status")=="PASS" and ev.get("regression_cases_total")==30 and ev.get("security_runtime_admission_pass") is False and ev.get("license_runtime_admission_pass") is False and ev.get("current_host_provider_runtime_evidence") is False):fs.append(_f("TDAI-REF-009","evidence drift"))
 if GATE_ID not in pol.get("mandatory_reference_gates",[]) or pol.get("tencentdb_agent_memory_provider_id")!=PROVIDER_ID or pol.get("tencentdb_agent_memory_contract_id")!=CONTRACT_ID or pol.get("tencentdb_agent_memory_mandatory_p0_rules")!=P0_RULES:fs.append(_f("TDAI-REF-010","policy binding drift"))
 if CONTRACT_ID not in know.get("contracts",[]):fs.append(_f("TDAI-REF-011","Knowledge contract binding missing"))
 return {"result":"PASS" if not fs else "FAIL","findings":fs}
def gate(root):
 ref=reference_check(root);auth=scan_authority(root);reg=run_regressions();ok=ref["result"]==auth["result"]==reg["result"]=="PASS"
 r={"schema":"fa3.tencentdb-agent-memory-gate-report.v1","gate_id":GATE_ID,"executable_gate_id":EXECUTABLE_GATE_ID,"provider_id":PROVIDER_ID,"contract_id":CONTRACT_ID,"capability_count":143,"result":"PASS" if ok else "FAIL","reference":ref,"authority_scan":auth,"regressions":reg,"runtime_provider_required":False,"current_host_provider_runtime_evidence":False,"runtime_activation_status":RUNTIME_STATUS}
 _write(root/"reports/tencentdb-agent-memory-gate-report.json",r);return r
def main():
 a=argparse.ArgumentParser();a.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));x=a.parse_args();r=gate(Path(x.root).resolve());print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
