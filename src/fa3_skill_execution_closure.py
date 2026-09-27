#!/usr/bin/env python3
from __future__ import annotations
import copy, json, re
from pathlib import Path
from typing import Any
from fa3_release_baseline import load_active_release_baseline

SHA256=re.compile(r"^[0-9a-f]{64}$")
PROFILE="canonical/profiles/FA3-SKILL-FABRIC-001.json"
CONTRACT="canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json"
WORKLOAD="canonical/profiles/FA3-AGENT-WORKLOAD-RUNTIME-001.json"
SANDBOX="canonical/profiles/FA3-AGENT-SANDBOX-001.json"
HRB="canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
SECRET="canonical/profiles/FA3-SECRET-BROKER-001.json"
HARDWARE="canonical/decisions/FA3-DEC-HARDWARE-SAFETY-2026-09-26.json"
COEXISTENCE="canonical/FA3-COEXISTENCE-POLICY-001.json"
DECISION="canonical/decisions/FA3-DEC-SKILL-EXECUTION-CLOSURE-2026-09-26.json"
INTENT="canonical/intents/FA3-SKILL-EXECUTION-CLOSURE-APPLICATION-INTENT-001.json"
ASSESSMENT="canonical/assessments/FA3-SKILL-EXECUTION-CLOSURE-REUSE-ASSESSMENT-001.json"

ALLOWED_CLASSES={"CONTEXT_ONLY","READ_ONLY_TOOL","MUTATING_TOOL","MODEL_OPERATION","USER_JOB","RESOURCE_JOB","BROWSER_ACTION","PRIVILEGED_HOST_ACTION","DURABLE_AGENT_LOOP","UNTRUSTED_CODE"}
CODE_CLASSES={"USER_JOB","RESOURCE_JOB","PRIVILEGED_HOST_ACTION","UNTRUSTED_CODE"}
RESOURCE_CLASSES={"MODEL_OPERATION","USER_JOB","RESOURCE_JOB","PRIVILEGED_HOST_ACTION","DURABLE_AGENT_LOOP","UNTRUSTED_CODE"}
EXPECTED_AUTHORITIES={"tool_mediation":"FA3-AUTH-MCP-GATEWAY-001","model_routing":"FA3-AUTH-MODEL-ROUTER-001","host_resources":"FA3-AUTH-HOST-RESOURCE-BROKER-001","secrets":"FA3-AUTH-SECRETS-001","evidence":"FA3-AUTH-OBS-EVIDENCE-001"}

def _load(root:Path, rel:str)->dict[str,Any]:
    obj=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError(rel)
    return obj

def good_execution_binding()->dict[str,Any]:
    return {"schema":"fa3.skill-execution-binding.v1","skill_id":"fa3.example.skill","skill_version":"1.0.0","content_sha256":"a"*64,"task_scope":"task.example","execution_class":"RESOURCE_JOB","admission_receipt_ref":"skill-admit:test:1","selection_receipt_ref":"skill-select:test:1","activation_preview_ref":"skill-preview:test:1","requested_capabilities":["test.read"],"authority_bindings":copy.deepcopy(EXPECTED_AUTHORITIES),"runtime":{"agent_workload_profile":"FA3-AGENT-WORKLOAD-RUNTIME-001","sandbox_profile":"FA3-AGENT-SANDBOX-001","unsandboxed_execution":False},"admission":{"hrb_admission_ref":"hrb-admit:test:1","model_route_ref":None,"mcp_authorization_ref":None,"secret_refs":[]},"safety":{"hardware_safety_decision":"FA3-DEC-HARDWARE-SAFETY-2026-09-26","hardware_safety_result":"PASS","coexistence_policy":"FA3-COEXISTENCE-POLICY-001","coexistence_result":"PASS"},"privilege":{"requested":False,"arbitrary_root_shell":False,"exact_helper":None,"authorization_receipt":None,"human_gate_ref":None},"bypass":{"direct_model_provider":False,"direct_tool":False,"direct_secret_value":False,"direct_resource_assignment":False},"postconditions":["acceptance_checked"],"current_host_runtime_claim":False}

def execution_binding_allowed(b:dict[str,Any])->bool:
    try:
        if b.get("schema")!="fa3.skill-execution-binding.v1" or not SHA256.fullmatch(str(b.get("content_sha256",""))): return False
        if not all(b.get(k) for k in ("skill_id","skill_version","task_scope","admission_receipt_ref","selection_receipt_ref","activation_preview_ref")): return False
        cls=b.get("execution_class")
        if cls not in ALLOWED_CLASSES: return False
        auth=b.get("authority_bindings",{})
        if any(auth.get(k)!=v for k,v in EXPECTED_AUTHORITIES.items()): return False
        if any(b.get("bypass",{}).get(k) is not False for k in ("direct_model_provider","direct_tool","direct_secret_value","direct_resource_assignment")): return False
        safe=b.get("safety",{})
        if safe.get("hardware_safety_decision")!="FA3-DEC-HARDWARE-SAFETY-2026-09-26" or safe.get("hardware_safety_result")!="PASS": return False
        if safe.get("coexistence_policy")!="FA3-COEXISTENCE-POLICY-001" or safe.get("coexistence_result")!="PASS": return False
        run=b.get("runtime",{})
        if cls in CODE_CLASSES and (run.get("agent_workload_profile")!="FA3-AGENT-WORKLOAD-RUNTIME-001" or run.get("sandbox_profile")!="FA3-AGENT-SANDBOX-001" or run.get("unsandboxed_execution") is not False): return False
        adm=b.get("admission",{})
        if cls in RESOURCE_CLASSES and not adm.get("hrb_admission_ref"): return False
        if cls=="MODEL_OPERATION" and not adm.get("model_route_ref"): return False
        if cls in {"READ_ONLY_TOOL","MUTATING_TOOL","BROWSER_ACTION"} and not adm.get("mcp_authorization_ref"): return False
        if cls=="MUTATING_TOOL" and not adm.get("mutation_authorization_receipt"): return False
        priv=b.get("privilege",{})
        if priv.get("arbitrary_root_shell") is not False: return False
        if cls=="PRIVILEGED_HOST_ACTION" and (priv.get("requested") is not True or not priv.get("exact_helper") or not priv.get("authorization_receipt")): return False
        if not isinstance(b.get("postconditions"),list) or not b["postconditions"] or b.get("current_host_runtime_claim") is not False: return False
        return True
    except (TypeError,AttributeError):
        return False

def good_execution_receipt()->dict[str,Any]:
    return {"schema":"fa3.skill-execution-receipt.v1","execution_id":"exec:test:1","task_id":"task:test:1","binding_ref":"skill-exec-binding:test:1","binding_digest_sha256":"b"*64,"result":"PASS","authority_receipts":{"mcp":None,"model_router":None,"hrb":"hrb-admit:test:1","secret_broker":[]},"postconditions":{"checked":True,"result":"PASS","refs":["post:test:1"]},"cleanup":{"worker_gone":True,"transient_unit_gone":True,"hrb_lease_released":True,"secrets_revoked":True,"network_lease_released":True,"device_released":True,"workspace_clean":True},"rollback":{"required":False,"result":"NOT_REQUIRED","ref":None},"current_host":{"claim":False,"status":"STATIC_ONLY","physical_evidence_ref":None},"secret_values_collected":False}

def execution_receipt_allowed(binding:dict[str,Any], r:dict[str,Any])->bool:
    try:
        if not execution_binding_allowed(binding) or r.get("schema")!="fa3.skill-execution-receipt.v1": return False
        if not all(r.get(k) for k in ("execution_id","task_id","binding_ref")) or not SHA256.fullmatch(str(r.get("binding_digest_sha256",""))): return False
        if r.get("secret_values_collected") is not False: return False
        current=r.get("current_host",{})
        if current.get("claim") is True and not current.get("physical_evidence_ref"): return False
        if current.get("status") in {"PASS","CURRENT_HOST_PASS","CURRENT_HOST_ADMITTED"} and not current.get("physical_evidence_ref"): return False
        cleanup=r.get("cleanup",{}); required=("worker_gone","transient_unit_gone","hrb_lease_released","secrets_revoked","network_lease_released","device_released","workspace_clean")
        if r.get("result")=="PASS":
            post=r.get("postconditions",{})
            if post.get("checked") is not True or post.get("result")!="PASS" or not post.get("refs") or any(cleanup.get(k) is not True for k in required): return False
            rb=r.get("rollback",{})
            if rb.get("required") is True and (rb.get("result")!="PASS" or not rb.get("ref")): return False
            if rb.get("required") is False and rb.get("result")!="NOT_REQUIRED": return False
        if binding.get("execution_class") in RESOURCE_CLASSES and not r.get("authority_receipts",{}).get("hrb"): return False
        return r.get("result") in {"PASS","FAIL"}
    except (TypeError,AttributeError):
        return False

def _mut(obj,fn): out=copy.deepcopy(obj);fn(out);return out

def regressions()->dict[str,Any]:
    b=good_execution_binding();r=good_execution_receipt()
    checks=[execution_binding_allowed(b),execution_receipt_allowed(b,r),
      not execution_binding_allowed(_mut(b,lambda x:x["authority_bindings"].update(tool_mediation="DIRECT"))),
      not execution_binding_allowed(_mut(b,lambda x:x["authority_bindings"].update(model_routing="DIRECT"))),
      not execution_binding_allowed(_mut(b,lambda x:x["authority_bindings"].update(host_resources="DIRECT"))),
      not execution_binding_allowed(_mut(b,lambda x:x["authority_bindings"].update(secrets="DIRECT"))),
      not execution_binding_allowed(_mut(b,lambda x:x["bypass"].update(direct_model_provider=True))),
      not execution_binding_allowed(_mut(b,lambda x:x["bypass"].update(direct_tool=True))),
      not execution_binding_allowed(_mut(b,lambda x:x["bypass"].update(direct_secret_value=True))),
      not execution_binding_allowed(_mut(b,lambda x:x["bypass"].update(direct_resource_assignment=True))),
      not execution_binding_allowed(_mut(b,lambda x:x["runtime"].update(unsandboxed_execution=True))),
      not execution_binding_allowed(_mut(b,lambda x:x["admission"].update(hrb_admission_ref=None))),
      not execution_binding_allowed(_mut(b,lambda x:x["safety"].update(hardware_safety_result="SKIPPED"))),
      not execution_binding_allowed(_mut(b,lambda x:x["safety"].update(coexistence_result="PENDING"))),
      not execution_binding_allowed(_mut(b,lambda x:x["privilege"].update(arbitrary_root_shell=True))),
      not execution_binding_allowed(_mut(b,lambda x:x.update(postconditions=[]))),
      not execution_binding_allowed(_mut(b,lambda x:x.update(current_host_runtime_claim=True))),
      not execution_receipt_allowed(b,_mut(r,lambda x:x.update(secret_values_collected=True))),
      not execution_receipt_allowed(b,_mut(r,lambda x:x["postconditions"].update(checked=False))),
      not execution_receipt_allowed(b,_mut(r,lambda x:x["cleanup"].update(worker_gone=False))),
      not execution_receipt_allowed(b,_mut(r,lambda x:x["cleanup"].update(hrb_lease_released=False))),
      not execution_receipt_allowed(b,_mut(r,lambda x:x["cleanup"].update(workspace_clean=False))),
      not execution_receipt_allowed(b,_mut(r,lambda x:x["current_host"].update(claim=True,status="CURRENT_HOST_PASS",physical_evidence_ref=None)))]
    cases=[{"case_id":f"SKX-{i:03d}","status":"PASS" if ok else "FAIL"} for i,ok in enumerate(checks,1)]
    return {"result":"PASS" if all(checks) else "FAIL","total":len(cases),"passed":sum(c["status"]=="PASS" for c in cases),"cases":cases}

def canonical_check(root:Path)->list[str]:
    cap=load_active_release_baseline(root).capability_count
    p=_load(root,PROFILE);c=_load(root,CONTRACT);w=_load(root,WORKLOAD);s=_load(root,SANDBOX);h=_load(root,HRB);sec=_load(root,SECRET);hw=_load(root,HARDWARE);co=_load(root,COEXISTENCE);d=_load(root,DECISION);i=_load(root,INTENT);a=_load(root,ASSESSMENT);f=[]
    cl=p.get("skill_execution_closure",{})
    if not (p.get("capability_count")==cap and p.get("new_capability") is False and p.get("new_architectural_authority") is False): f.append("profile governance drift")
    if not (cl.get("decision_id")==d.get("id") and cl.get("execution_authority") is False and cl.get("current_host_runtime_claim") is False): f.append("skill execution closure binding drift")
    if not {"SkillExecutionBinding","SkillExecutionReceipt"}.issubset(set(c.get("contracts",[]))): f.append("execution contracts missing")
    if c.get("skill_execution_binding_governance",{}).get("existing_authorities_only") is not True: f.append("existing-authority-only rule missing")
    if w.get("id")!="FA3-AGENT-WORKLOAD-RUNTIME-001" or w.get("authority_boundaries",{}).get("host_resources")!="FA3-AUTH-HOST-RESOURCE-BROKER-001": f.append("workload authority drift")
    if s.get("id")!="FA3-AGENT-SANDBOX-001" or s.get("network_policy",{}).get("default")!="DENY": f.append("sandbox boundary drift")
    if h.get("existing_authority_id")!="FA3-AUTH-HOST-RESOURCE-BROKER-001": f.append("HRB authority drift")
    if sec.get("id")!="FA3-SECRET-BROKER-001" or sec.get("architectural_authority") is not False: f.append("secret broker boundary drift")
    if hw.get("id")!="FA3-DEC-HARDWARE-SAFETY-2026-09-26" or hw.get("enforcement",{}).get("fail_closed") is not True: f.append("hardware safety drift")
    if co.get("id")!="FA3-COEXISTENCE-POLICY-001" or co.get("capability_id")!="CAP-175" or co.get("current_host",{}).get("static_pass_promotes_runtime") is not False: f.append("CAP-175 coexistence drift")
    if not (d.get("capability_delta")==0 and d.get("authority_delta")==0 and d.get("provider_delta")==0 and d.get("new_daemon_count")==0 and d.get("current_host_runtime_claim") is False): f.append("decision delta drift")
    if not (i.get("proposed_authority_roles")==[] and i.get("declared_new_capabilities")==[] and i.get("current_host_runtime_promotion_claim") is False): f.append("ApplicationIntent drift")
    if not (a.get("result")=="PASS" and a.get("capability_delta")==0 and a.get("authority_delta")==0 and a.get("provider_delta")==0 and a.get("current_host_runtime_promotion_claim") is False): f.append("ReuseAssessment drift")
    return f

def evaluate(root:Path)->dict[str,Any]:
    root=root.resolve();findings=canonical_check(root);reg=regressions()
    return {"schema":"fa3.skill-execution-closure-report.v1","result":"PASS" if not findings and reg["result"]=="PASS" else "FAIL","findings":findings,"regressions":reg,"capability_count":load_active_release_baseline(root).capability_count,"capability_delta":0,"authority_delta":0,"provider_delta":0,"current_host_runtime_claim":False}
