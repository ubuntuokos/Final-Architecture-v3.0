#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

PROVIDER_ID="FA3-PROVIDER-AUTOGPT-001"
DECISION_ID="FA3-DEC-AUTOGPT-2026-08-30"
REFERENCE_ID="FA3-AUTOGPT-UPSTREAM-REFERENCE-2026-08-30"
RUNTIME_ADMISSION_ID="FA3-AUTOGPT-RUNTIME-ADMISSION-001"
RUNTIME_CONFORMANCE_ID="FA3-AUTOGPT-RUNTIME-CONFORMANCE-001"
CONTRACT_ID="FA3-AUTOGPT-CONTRACTS-001"
GATE_ID="FA3-AUTOGPT-GATESET-001"
CAPABILITY_ID="CAP-028"
CAPABILITY_COUNT=143
OBSERVED_MASTER_HEAD="32a43d005c0c42079ceba68d9a49c28e0eeaa6c7"
REFERENCE_RELEASE="autogpt-platform-beta-v0.7.3"
REFERENCE_RELEASE_COMMIT="f49bcca95ed327396d8ebdd0bdf7810de482ac1a"
STORE_VALUE_BLOCK_ID="1ff065e9-88e8-4358-9d82-8dc91f622ba9"
RECEIPT_PATH="evidence/receipts/autogpt-current-host.json"
EVIDENCE_LEVEL="CURRENT_HOST_PRODUCTION_E2E_PASS"
CANDIDATE_STATE="CURRENT_HOST_ADMISSION_PENDING"
PASS_STATE="CURRENT_HOST_PRODUCTION_E2E_PASS"
MANDATORY_CONSTRAINT="AutoGPT SHALL NOT become an FA3 identity, authentication, authorization, secrets, MCP/capability-gateway, model-routing, durable-workflow, evidence/provenance, network-egress, host-resource, developer-execution, artifact-trust or canonical-registry authority."
P0_INVARIANTS=["AUTOGPT_TYPED_NODE_CONTRACT_REQUIRED","AUTOGPT_EXPLICIT_DELEGATED_EXECUTION_CONTEXT_REQUIRED","AUTOGPT_GRAPH_AUTH_NOT_TRANSITIVE_NODE_AUTH","AUTOGPT_DELEGATED_CAPABILITY_NARROWING_REQUIRED","AUTOGPT_CREDENTIAL_SCOPE_MONOTONIC_NARROWING","AUTOGPT_VALIDATE_BEFORE_PERSIST_ACTIVATE","AUTOGPT_TRIGGER_SCHEDULE_NOT_AUTHORITY","AUTOGPT_MODEL_CATALOG_NOT_ROUTER_AUTHORITY","AUTOGPT_CREDENTIAL_STORE_NOT_SECRETS_AUTHORITY","AUTOGPT_EXECUTOR_NOT_HOST_OR_DEVELOPER_AUTHORITY","AUTOGPT_MARKETPLACE_LIBRARY_NOT_PRODUCTION_ADMISSION","AUTOGPT_EXECUTION_EVIDENCE_ATTRIBUTABLE","AUTOGPT_INTEGRATION_BOUNDARIES_PRESERVED","AUTOGPT_IMMUTABLE_RUNTIME_REFERENCE_REQUIRED","AUTOGPT_LICENSE_BOUNDARY_ADMISSION_REQUIRED","AUTOGPT_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST","AUTOGPT_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY"]
EXTERNAL={
 "authorization_policy":"FA3-AUTH-SECURITY-GOV-001",
 "tool_mediation":"FA3-AUTH-MCP-GATEWAY-001",
 "model_routing":"FA3-AUTH-MODEL-ROUTER-001",
 "host_resource":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
 "artifact_trust":"FA3-REG-ARTIFACT-MODEL-001",
 "evidence":"FA3-AUTH-OBS-EVIDENCE-001",
 "registry":"FA3-REGISTRY-001",
}
FULL_SHA=re.compile(r"^[0-9a-f]{40}$")


def _load(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def _write(p:Path,o):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def _f(code,msg,**kw): return {"code":code,"severity":"P0","message":msg,**kw}
def _sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as fh:
  for block in iter(lambda:fh.read(1024*1024),b""): h.update(block)
 return h.hexdigest()

def _autogpt(v:Any)->bool:
 if isinstance(v,str):
  u=v.upper(); return PROVIDER_ID in v or "SIGNIFICANT-GRAVITAS/AUTOGPT" in u or u=="AUTOGPT" or u.startswith("FA3-AUTH-AUTOGPT")
 if isinstance(v,dict): return any(_autogpt(x) for x in v.values())
 if isinstance(v,(list,tuple,set)): return any(_autogpt(x) for x in v)
 return False

def typed_node_contract_valid(input_schema,output_schema): return bool(input_schema and output_schema)
def execution_context_valid(c): return all(c.get(k) for k in ("caller_identity","delegation_id","workflow_run_id","node_id","capability_scope","policy_decision_id"))
def graph_node_authorization_valid(*,graph_authorized,node_authorized,capability_admitted): return bool(graph_authorized and node_authorized and capability_admitted)
def delegated_capabilities_valid(parent,child): return set(child).issubset(set(parent))
def credential_scope_narrowing_valid(workflow,node,capability,provider):
 w,n,c,p=map(set,(workflow,node,capability,provider)); return p<=c<=n<=w
def validation_before_activation_valid(*,schema_valid,credentials_valid,policy_valid,persisted,activated): return (not (persisted or activated)) or bool(schema_valid and credentials_valid and policy_valid)
def trigger_execution_valid(*,trigger_or_schedule_fired,authorization_admitted,capability_admitted): return (not trigger_or_schedule_fired) or bool(authorization_admitted and capability_admitted)
def model_catalog_projection_valid(authority_owner): return authority_owner=="FA3-AUTH-MODEL-ROUTER-001"
def credential_store_boundary_valid(secrets_authority): return bool(secrets_authority and not _autogpt(secrets_authority))
def executor_boundary_valid(*,host_resource_authority,developer_execution_authority): return host_resource_authority=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and bool(developer_execution_authority) and not _autogpt(developer_execution_authority)
def marketplace_admission_valid(*,adopted,artifact_trust_pass,policy_admitted): return (not adopted) or bool(artifact_trust_pass and policy_admitted)
def execution_evidence_valid(e): return all(e.get(k) for k in ("caller_identity","delegation_id","workflow_run_id","graph_version","node_id","capability_id","provider_id","policy_decision_id","input_digest","output_digest","result_status"))
def integration_boundaries_valid(*,tool_mediation,network_egress,secrets_authority): return tool_mediation=="FA3-AUTH-MCP-GATEWAY-001" and bool(network_egress and secrets_authority) and not _autogpt(network_egress) and not _autogpt(secrets_authority)
def immutable_reference_valid(*,ref,commit_sha): return bool(FULL_SHA.fullmatch(commit_sha or "")) and ref.lower() not in {"master","main","dev","latest","head"}
def license_admission_valid(*,component,explicit_license_admission): return bool(explicit_license_admission) if component=="autogpt_platform" else component in {"classic","forge","benchmark"}
def disabled_provider_cost_valid(*,resident_processes,active_pollers,active_network_sessions,active_resource_leases): return all(int(x)==0 for x in (resident_processes,active_pollers,active_network_sessions,active_resource_leases))

def provider_shape_valid(p):
 b=p.get("authority_boundaries",{})
 return bool(
  p.get("id")==PROVIDER_ID and p.get("capability_count")==CAPABILITY_COUNT
  and p.get("canonical_root") is False and p.get("architectural_authority") is False
  and p.get("new_capability") is False and p.get("global_runtime_promotion_required_when_disabled") is False
  and p.get("runtime_activation_requires_current_host_conformance") is True
  and p.get("runtime_activation_status") in {CANDIDATE_STATE,PASS_STATE}
  and p.get("contract_id")==CONTRACT_ID and p.get("runtime_conformance_id")==RUNTIME_CONFORMANCE_ID
  and CAPABILITY_ID in p.get("projects_existing_capabilities",[])
  and p.get("normative_constraint")==MANDATORY_CONSTRAINT
  and all(b.get(k)==v for k,v in EXTERNAL.items())
 )

AUTH_KEYS=("identity_authority","authentication_authority","authorization_authority","secrets_authority","mcp_authority","capability_gateway_authority","model_routing_authority","workflow_authority","orchestration_authority","evidence_authority","network_egress_authority","host_resource_authority","developer_execution_authority","artifact_trust_authority","registry_authority","authority_owner","authority_provider")

def _scan(v:Any,file_path:str,path="$"):
 out=[]
 if isinstance(v,dict):
  scoped=any(_autogpt(v.get(k)) for k in ("id","provider_id","provider","subject","name","implementation") if k in v)
  if scoped and v.get("architectural_authority") is True: out.append(_f("AUTOGPT-AUTH-001","AutoGPT architectural_authority enabled",file=file_path,path=path+".architectural_authority"))
  if scoped and v.get("canonical_root") is True: out.append(_f("AUTOGPT-AUTH-002","AutoGPT promoted to canonical root",file=file_path,path=path+".canonical_root"))
  ab=v.get("authority_boundaries")
  if scoped and isinstance(ab,dict):
   for k,x in ab.items():
    if _autogpt(x): out.append(_f("AUTOGPT-AUTH-003","AutoGPT assigned as authority boundary owner",file=file_path,path=path+".authority_boundaries."+k))
  for k,x in v.items():
   nk=k.lower().replace("-","_")
   if (nk in AUTH_KEYS or nk.endswith("_authority")) and _autogpt(x): out.append(_f("AUTOGPT-AUTH-004","AutoGPT assigned to authority-bearing field",file=file_path,path=path+"."+k))
   out.extend(_scan(x,file_path,path+"."+k))
 elif isinstance(v,list):
  for i,x in enumerate(v): out.extend(_scan(x,file_path,f"{path}[{i}]"))
 return out

def scan_canonical_authority_assignments(root:Path):
 findings=[];scanned=0;c=root/"canonical"
 if not c.exists(): return {"result":"FAIL","scanned_json_files":0,"findings":[_f("AUTOGPT-AUTH-000","canonical directory missing")]}
 for p in sorted(c.rglob("*.json")):
  scanned+=1
  try: findings.extend(_scan(_load(p),str(p.relative_to(root))))
  except Exception as e: findings.append(_f("AUTOGPT-AUTH-005","Canonical JSON parse failure",file=str(p.relative_to(root)),error=str(e)))
 return {"result":"PASS" if not findings else "FAIL","scanned_json_files":scanned,"findings":findings}

def deployment_check(root:Path):
 paths={
  "dockerfile":root/"deployment/autogpt/Dockerfile.fa3",
  "runbook":root/"deployment/autogpt/README.md",
  "adapter":root/"src/fa3_autogpt_provider.py",
  "collector":root/"evidence/collect-autogpt-current-host.py",
  "bootstrap":root/"bin/fa3-autogpt-bootstrap.sh",
  "wrapper":root/"bin/fa3-autogpt-current-host.sh",
  "workflow":root/".github/workflows/fa3-autogpt-current-host.yml",
 }
 f=[_f("AUTOGPT-DEPLOY-001",f"Missing AutoGPT runtime artifact: {k}",file=str(p.relative_to(root))) for k,p in paths.items() if not p.is_file()]
 if f:return {"result":"FAIL","findings":f}
 docker=paths["dockerfile"].read_text(encoding="utf-8")
 bootstrap=paths["bootstrap"].read_text(encoding="utf-8")
 workflow=paths["workflow"].read_text(encoding="utf-8")
 required_docker=["ARG BASE_IMAGE","FROM ${BASE_IMAGE}","poetry==2.2.1","poetry.lock","AGENT_API_PORT=8006"]
 required_boot=["podman network create --internal","127.0.0.1:58006:8006","--cap-drop=all","--security-opt=no-new-privileges","--pull-never",REFERENCE_RELEASE_COMMIT,"CUDA_VISIBLE_DEVICES="]
 missing=[x for x in required_docker if x not in docker]+[x for x in required_boot if x not in bootstrap]
 if missing:f.append(_f("AUTOGPT-DEPLOY-002","Constrained runtime security/build invariant missing",missing=missing))
 if "pull_request:" in workflow or "runs-on: [self-hosted, linux, x64, fa3-current-host]" not in workflow or "push:" not in workflow or "branches: [main]" not in workflow:
  f.append(_f("AUTOGPT-DEPLOY-003","Current-host workflow must run only from trusted main/workflow_dispatch on the FA3 self-hosted runner"))
 return {"result":"PASS" if not f else "FAIL","findings":f}

def reference_check(root:Path):
 paths={
  "provider":root/"canonical/providers/FA3-PROVIDER-AUTOGPT-001.json",
  "decision":root/"canonical/decisions/FA3-DEC-AUTOGPT-2026-08-30.json",
  "reference":root/"canonical/references/FA3-AUTOGPT-UPSTREAM-REFERENCE-2026-08-30.json",
  "contract":root/"canonical/contracts/FA3-AUTOGPT-CONTRACTS-001.json",
  "runtime":root/"canonical/FA3-AUTOGPT-RUNTIME-CONFORMANCE-001.json",
  "enforcement":root/"canonical/autogpt-enforcement.json",
  "admission":root/"canonical/autogpt-runtime-admission.json",
  "policy":root/"canonical/enforcement-policy.json",
  "registry":root/"evidence/evidence-registry.json",
 }
 f=[]
 for n,p in paths.items():
  if not p.exists(): f.append(_f("AUTOGPT-REF-001",f"Missing AutoGPT artifact: {n}",file=str(p.relative_to(root))))
 if f:return {"result":"FAIL","findings":f}
 p,d,r,c,rt,e,a,pol,reg=(_load(paths[k]) for k in ("provider","decision","reference","contract","runtime","enforcement","admission","policy","registry"))
 if not provider_shape_valid(p): f.append(_f("AUTOGPT-REF-002","AutoGPT provider invariant drift"))
 if not (d.get("id")==DECISION_ID and d.get("status")=="CANONICAL_CLOSED" and d.get("gate_id")==GATE_ID and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("capability_count_after")==CAPABILITY_COUNT and d.get("mandatory_constraint")==MANDATORY_CONSTRAINT): f.append(_f("AUTOGPT-REF-003","AutoGPT decision invariant drift"))
 if not (r.get("id")==REFERENCE_ID and r.get("observed_default_branch_head")==OBSERVED_MASTER_HEAD and r.get("latest_release")==REFERENCE_RELEASE and r.get("latest_release_commit")==REFERENCE_RELEASE_COMMIT and r.get("promotion_evidence") is False and r.get("floating_master_allowed_as_promotion_evidence") is False): f.append(_f("AUTOGPT-REF-004","AutoGPT upstream reference drift"))
 if not (c.get("id")==CONTRACT_ID and c.get("provider_id")==PROVIDER_ID and c.get("canonical_capability_count")==CAPABILITY_COUNT and c.get("allowed_block_ids",{}).get("store_value")==STORE_VALUE_BLOCK_ID): f.append(_f("AUTOGPT-REF-010","AutoGPT runtime contract drift"))
 if not (rt.get("id")==RUNTIME_CONFORMANCE_ID and rt.get("provider_id")==PROVIDER_ID and rt.get("upstream",{}).get("source_commit")==REFERENCE_RELEASE_COMMIT and rt.get("execution_profile",{}).get("allowed_block_ids")==[STORE_VALUE_BLOCK_ID]): f.append(_f("AUTOGPT-REF-011","AutoGPT runtime conformance profile drift"))
 if not (e.get("gate_id")==GATE_ID and e.get("fail_closed") is True and e.get("mandatory_rule_count")==17 and e.get("p0_invariants")==P0_INVARIANTS and e.get("contract_id")==CONTRACT_ID and e.get("runtime_conformance_id")==RUNTIME_CONFORMANCE_ID): f.append(_f("AUTOGPT-REF-005","AutoGPT enforcement drift"))
 if not (a.get("id")==RUNTIME_ADMISSION_ID and a.get("status") in {"CURRENT_HOST_CANDIDATE_ADMITTED","ADMITTED_CURRENT_HOST_PRODUCTION_E2E_PASS"} and a.get("fail_closed") is True and a.get("current_host_evidence_required") is True and a.get("license_admission_required") is True and a.get("technical_license_boundary_admission",{}).get("legal_conclusion")=="NOT_ASSERTED"): f.append(_f("AUTOGPT-REF-006","AutoGPT runtime admission drift"))
 if GATE_ID not in pol.get("mandatory_reference_gates",[]): f.append(_f("AUTOGPT-REF-007","AutoGPT gate missing from global policy"))
 if pol.get("autogpt_provider_id")!=PROVIDER_ID or pol.get("autogpt_contract_id")!=CONTRACT_ID or pol.get("autogpt_runtime_conformance_id")!=RUNTIME_CONFORMANCE_ID or pol.get("autogpt_current_host_evidence_required") is not True: f.append(_f("AUTOGPT-REF-008","Global policy AutoGPT runtime binding drift"))
 if pol.get("autogpt_mandatory_p0_rules")!=P0_INVARIANTS: f.append(_f("AUTOGPT-REF-009","Global policy AutoGPT P0 invariant drift"))
 cap028=next((x for x in reg.get("records",[]) if x.get("subject_id")==CAPABILITY_ID),{})
 if "FA3-DEC-AUTOGPT-2026-08-30" not in cap028.get("source_decision_ids",[]): f.append(_f("AUTOGPT-REF-012","CAP-028 decision projection missing"))
 state=p.get("runtime_activation_status")
 coherent_candidate=state==CANDIDATE_STATE and a.get("status")=="CURRENT_HOST_CANDIDATE_ADMITTED" and cap028.get("status")=="PENDING_CURRENT_HOST"
 coherent_pass=state==PASS_STATE and a.get("status")=="ADMITTED_CURRENT_HOST_PRODUCTION_E2E_PASS" and cap028.get("status")=="PASS"
 if not (coherent_candidate or coherent_pass): f.append(_f("AUTOGPT-REF-013","AutoGPT runtime/admission/Evidence Registry state transition is incoherent",provider_state=state,admission=a.get("status"),cap028=cap028.get("status")))
 return {"result":"PASS" if not f else "FAIL","findings":f}

def _case(i,name,pos,neg): return {"rule_id":f"FA3-AUTOGPT-P0-{i:03d}","name":name,"status":"PASS" if pos and neg else "FAIL","positive_case":pos,"negative_case":neg}
def run_regressions():
 c=[]
 c.append(_case(1,"typed executable node contract",typed_node_contract_valid({"x":"str"},{"y":"str"}),not typed_node_contract_valid({},{"y":"str"})))
 good={"caller_identity":"u","delegation_id":"d","workflow_run_id":"w","node_id":"n","capability_scope":["read"],"policy_decision_id":"p"};bad=dict(good);bad.pop("delegation_id")
 c.append(_case(2,"delegated execution context required",execution_context_valid(good),not execution_context_valid(bad)))
 c.append(_case(3,"graph authorization not transitive",graph_node_authorization_valid(graph_authorized=True,node_authorized=True,capability_admitted=True),not graph_node_authorization_valid(graph_authorized=True,node_authorized=False,capability_admitted=True)))
 c.append(_case(4,"delegated capability narrowing",delegated_capabilities_valid(["r","w"],["r"]),not delegated_capabilities_valid(["r"],["r","w"])))
 c.append(_case(5,"credential scope narrowing",credential_scope_narrowing_valid(["a","b"],["a","b"],["a"],["a"]),not credential_scope_narrowing_valid(["a"],["a"],["a"],["a","b"])))
 c.append(_case(6,"validate before activation",validation_before_activation_valid(schema_valid=True,credentials_valid=True,policy_valid=True,persisted=True,activated=True),not validation_before_activation_valid(schema_valid=True,credentials_valid=False,policy_valid=True,persisted=True,activated=False)))
 c.append(_case(7,"trigger is not authorization",trigger_execution_valid(trigger_or_schedule_fired=True,authorization_admitted=True,capability_admitted=True),not trigger_execution_valid(trigger_or_schedule_fired=True,authorization_admitted=False,capability_admitted=True)))
 c.append(_case(8,"model catalog not router authority",model_catalog_projection_valid("FA3-AUTH-MODEL-ROUTER-001"),not model_catalog_projection_valid(PROVIDER_ID)))
 c.append(_case(9,"credential store not secrets authority",credential_store_boundary_valid("FA3-AUTH-SECRETS-001"),not credential_store_boundary_valid(PROVIDER_ID)))
 c.append(_case(10,"executor not host/developer authority",executor_boundary_valid(host_resource_authority="FA3-AUTH-HOST-RESOURCE-BROKER-001",developer_execution_authority="FA3-AUTH-DEVELOPER-EXECUTION-001"),not executor_boundary_valid(host_resource_authority=PROVIDER_ID,developer_execution_authority=PROVIDER_ID)))
 c.append(_case(11,"marketplace not production admission",marketplace_admission_valid(adopted=True,artifact_trust_pass=True,policy_admitted=True),not marketplace_admission_valid(adopted=True,artifact_trust_pass=False,policy_admitted=True)))
 ev={"caller_identity":"u","delegation_id":"d","workflow_run_id":"w","graph_version":"1","node_id":"n","capability_id":"CAP-001","provider_id":"p","policy_decision_id":"pd","input_digest":"sha256:i","output_digest":"sha256:o","result_status":"PASS"};bev=dict(ev);bev.pop("policy_decision_id")
 c.append(_case(12,"attributable execution evidence",execution_evidence_valid(ev),not execution_evidence_valid(bev)))
 c.append(_case(13,"integration boundaries preserved",integration_boundaries_valid(tool_mediation="FA3-AUTH-MCP-GATEWAY-001",network_egress="FA3-AUTH-NETWORK-EGRESS-001",secrets_authority="FA3-AUTH-SECRETS-001"),not integration_boundaries_valid(tool_mediation=PROVIDER_ID,network_egress=PROVIDER_ID,secrets_authority=PROVIDER_ID)))
 c.append(_case(14,"immutable runtime reference",immutable_reference_valid(ref=REFERENCE_RELEASE,commit_sha=REFERENCE_RELEASE_COMMIT),not immutable_reference_valid(ref="master",commit_sha=None)))
 c.append(_case(15,"license admission",license_admission_valid(component="autogpt_platform",explicit_license_admission=True),not license_admission_valid(component="autogpt_platform",explicit_license_admission=False)))
 c.append(_case(16,"disabled provider zero near-zero cost",disabled_provider_cost_valid(resident_processes=0,active_pollers=0,active_network_sessions=0,active_resource_leases=0),not disabled_provider_cost_valid(resident_processes=1,active_pollers=0,active_network_sessions=0,active_resource_leases=0)))
 gp={"id":PROVIDER_ID,"capability_count":143,"canonical_root":False,"architectural_authority":False,"new_capability":False,"global_runtime_promotion_required_when_disabled":False,"runtime_activation_requires_current_host_conformance":True,"runtime_activation_status":CANDIDATE_STATE,"contract_id":CONTRACT_ID,"runtime_conformance_id":RUNTIME_CONFORMANCE_ID,"projects_existing_capabilities":[CAPABILITY_ID],"authority_boundaries":EXTERNAL,"normative_constraint":MANDATORY_CONSTRAINT};bp=dict(gp);bp["architectural_authority"]=True
 c.append(_case(17,"provider non-authority invariant",provider_shape_valid(gp),not provider_shape_valid(bp)))
 passed=sum(x["status"]=="PASS" for x in c)
 return {"schema":"fa3.autogpt-regression-report.v1","result":"PASS" if passed==len(c) else "FAIL","passed":passed,"total":len(c),"cases":c}

def current_host_gate(root:Path):
 root=Path(root).resolve();path=root/RECEIPT_PATH;f=[];receipt={}
 if not path.is_file(): f.append(_f("AUTOGPT-HOST-001","AutoGPT current-host receipt is missing"))
 else:
  try: receipt=_load(path)
  except Exception as e:f.append(_f("AUTOGPT-HOST-002","AutoGPT current-host receipt is unreadable",error=str(e)))
 if receipt:
  if not (receipt.get("schema")=="fa3.autogpt-current-host-receipt.v1" and receipt.get("provider_id")==PROVIDER_ID and receipt.get("capability_id")==CAPABILITY_ID and receipt.get("status")=="PASS" and receipt.get("evidence_level")==EVIDENCE_LEVEL and receipt.get("synthetic") is False and receipt.get("collector_mode")=="REAL_CURRENT_HOST_ROOTLESS_AUTOGPT_SERVICE"):
   f.append(_f("AUTOGPT-HOST-003","Receipt identity or production evidence level mismatch"))
  up=receipt.get("upstream",{})
  if up.get("source_commit")!=REFERENCE_RELEASE_COMMIT or up.get("release")!=REFERENCE_RELEASE or not re.fullmatch(r"[0-9a-f]{64}",str(up.get("poetry_lock_sha256",""))):
   f.append(_f("AUTOGPT-HOST-004","Immutable upstream/lock identity evidence missing"))
  ids=receipt.get("runtime_identity",{})
  if not ids.get("repo_digests") or not ids.get("image_ids",{}).get("autogpt_server"):
   f.append(_f("AUTOGPT-HOST-005","Content-addressed dependency/runtime identity evidence missing"))
  isolation=receipt.get("isolation",{})
  required=("rootless_podman","internal_network","loopback_only_publish","not_privileged","no_new_privileges","effective_capabilities_zero","no_gpu_device_visible","external_network_egress_denied","source_commit_label","provider_label","runtime_profile_label")
  if not all(isolation.get(k) is True for k in required): f.append(_f("AUTOGPT-HOST-006","Runtime isolation evidence incomplete",failed=[k for k in required if isolation.get(k) is not True]))
  auth=receipt.get("authorization",{})
  if not (auth.get("autogpt_api_key_permissions")==["IDENTITY","READ_BLOCK","EXECUTE_BLOCK"] and auth.get("execute_graph_permission_absent") is True and auth.get("unauthenticated_request_denied") is True and auth.get("scope_escalation_denied") is True and auth.get("api_key_redacted") is True and auth.get("actual_central_gateway_network_hop_claimed") is False):
   f.append(_f("AUTOGPT-HOST-007","Authentication/scope boundary evidence mismatch"))
  ex=receipt.get("execution",{})
  if not (ex.get("block_id")==STORE_VALUE_BLOCK_ID and ex.get("real_autogpt_external_api") is True and ex.get("deterministic_result")=="PASS" and ex.get("provider_http_status")==200 and str(ex.get("input_digest","")).startswith("sha256:") and str(ex.get("output_digest","")).startswith("sha256:") and ex.get("caller_identity") and ex.get("delegation_id") and ex.get("authorization_decision_id") and ex.get("mcp_admission_id") and ex.get("host_resource_admission_id")):
   f.append(_f("AUTOGPT-HOST-008","Real attributed block execution evidence mismatch"))
  cleanup=receipt.get("cleanup",{})
  if not (cleanup.get("verified") is True and cleanup.get("status")=="PASS" and cleanup.get("resident_containers")==[] and cleanup.get("internal_network_exists") is False and cleanup.get("loopback_port_closed") is True):
   f.append(_f("AUTOGPT-HOST-009","Cleanup/zero-resident-runtime evidence mismatch"))
  if receipt.get("current_host_production_e2e")!="PASS" or receipt.get("global_promotion_claim") is not False or receipt.get("capability_count_after")!=CAPABILITY_COUNT:
   f.append(_f("AUTOGPT-HOST-010","Provider-specific promotion/capability semantics mismatch"))
 report={"schema":"fa3.autogpt-current-host-gate-report.v1","provider_id":PROVIDER_ID,"capability_id":CAPABILITY_ID,"result":"PASS" if not f else "FAIL","evidence_level":receipt.get("evidence_level"),"blocking_findings":len(f),"findings":f,"receipt_sha256":_sha256(path) if path.is_file() else None,"promotion_effect":"PROVIDER_SPECIFIC_CURRENT_HOST_EVIDENCE_ONLY_GLOBAL_PROMOTION_REMAINS_FAIL_CLOSED"}
 _write(root/"reports/autogpt-current-host-gate-report.json",report);return report

def gate(root:Path):
 ref=reference_check(root);deploy=deployment_check(root);scan=scan_canonical_authority_assignments(root);reg=run_regressions()
 ok=ref["result"]==deploy["result"]==scan["result"]==reg["result"]=="PASS"
 provider=_load(Path(root)/"canonical/providers/FA3-PROVIDER-AUTOGPT-001.json") if (Path(root)/"canonical/providers/FA3-PROVIDER-AUTOGPT-001.json").is_file() else {}
 out={"schema":"fa3.autogpt-gate-report.v1","gate_id":GATE_ID,"provider_id":PROVIDER_ID,"capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL","mode":"CANONICAL_BOUNDARY_RUNTIME_ADMISSION_AND_EXECUTABLE_REGRESSIONS","reference":ref,"deployment":deploy,"authority_scan":scan,"regressions":reg,"runtime_provider_required":False,"runtime_activation_status":provider.get("runtime_activation_status"),"promotion_effect":"MANDATORY_CANONICAL_INVARIANTS_OPTIONAL_RUNTIME_REQUIRES_REAL_CURRENT_HOST_EVIDENCE"}
 _write(Path(root)/"reports/autogpt-gate-report.json",out);return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));ap.add_argument("--current-host",action="store_true");a=ap.parse_args()
 r=current_host_gate(Path(a.root).resolve()) if a.current_host else gate(Path(a.root).resolve())
 print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
