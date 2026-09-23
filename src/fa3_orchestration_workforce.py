#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
REGISTRY_REL=Path("canonical/FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001.json")
ADMISSION_SCHEMA="fa3.orchestration-provider-current-host-admission.v1"
EXISTING_RUNTIME_AUTHORITY_STATES={"EXISTING_CANONICAL_AUTHORITY"}
class WorkforceContractError(ValueError): pass
class DecisionAdvisoryError(WorkforceContractError): pass
@dataclass(frozen=True)
class Rejection:
    specialist_id:str
    reasons:tuple[str,...]
    def as_dict(self)->dict[str,Any]: return {"specialist_id":self.specialist_id,"reasons":list(self.reasons)}
def _load_json(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def load_registry(root:Path|str)->dict[str,Any]:
    r=_load_json(Path(root)/REGISTRY_REL)
    if r.get("schema")!="fa3.orchestration-workforce-registry.v1" or r.get("id")!="FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001": raise WorkforceContractError("unexpected workforce registry")
    if not isinstance(r.get("specialists"),list) or not r["specialists"]: raise WorkforceContractError("workforce registry must contain specialists")
    return r
def current_host_admission_valid(provider_id:str,receipt:Any)->bool:
    if not isinstance(receipt,dict): return False
    e2e=receipt.get("production_e2e"); ident=receipt.get("runtime_identity")
    return receipt.get("schema")==ADMISSION_SCHEMA and receipt.get("provider_id")==provider_id and isinstance(receipt.get("scope_id"),str) and bool(receipt.get("scope_id")) and receipt.get("status")=="ADMITTED" and receipt.get("evidence_level")=="CURRENT_HOST_PRODUCTION_E2E_PASS" and isinstance(ident,dict) and bool(ident) and isinstance(e2e,dict) and e2e.get("result")=="PASS" and isinstance(e2e.get("evidence_refs"),list) and bool(e2e.get("evidence_refs")) and receipt.get("global_promotion_claim") is False
def _require_task_shape(t:dict[str,Any])->None:
    for k in ("task_id","domain","required_capabilities"):
        if k not in t: raise WorkforceContractError(f"work request missing required field: {k}")
    if not isinstance(t["task_id"],str) or not t["task_id"].strip() or not isinstance(t["domain"],str) or not t["domain"].strip(): raise WorkforceContractError("task_id/domain must be non-empty strings")
    if not isinstance(t["required_capabilities"],list) or not all(isinstance(v,str) and v for v in t["required_capabilities"]): raise WorkforceContractError("required_capabilities must be non-empty strings")
    for k in ("required_authorities","forbidden_specialists","authorized_ai_participants"):
        v=t.get(k,[])
        if not isinstance(v,list) or not all(isinstance(x,str) and x for x in v) or len(v)!=len(set(v)): raise WorkforceContractError(f"{k} must be a unique string list")
    if not isinstance(t.get("resource_requirements",{}),dict) or not isinstance(t.get("metadata",{}),dict): raise WorkforceContractError("resource_requirements/metadata must be objects")
def _caps(s): return set(s.get("strong_capabilities",[]))|set(s.get("supported_capabilities",[]))
def _runtime_ok(s,receipts):
    if s.get("runtime_promotion_status") in EXISTING_RUNTIME_AUTHORITY_STATES: return True
    pid=s.get("provider_id"); return isinstance(pid,str) and bool(pid) and current_host_admission_valid(pid,receipts.get(pid))
def _reasons(s,t,runtime,receipts):
    out=[]; required=set(t["required_capabilities"]); auth=set(t.get("required_authorities",[]))
    if s.get("id") in set(t.get("forbidden_specialists",[])): out.append("SPECIALIST_EXPLICITLY_FORBIDDEN")
    if not s.get("enabled_for_design",False): out.append("SPECIALIST_DISABLED")
    if t["domain"] not in set(s.get("domains",[])): out.append("DOMAIN_MISMATCH")
    anti=sorted(required&set(s.get("anti_capabilities",[])))
    if anti: out.append("ANTI_CAPABILITY:"+",".join(anti))
    missing=sorted(required-_caps(s))
    if missing: out.append("MISSING_CAPABILITY:"+",".join(missing))
    ma=sorted(auth-set(s.get("authority_scope",[])))
    if ma: out.append("MISSING_AUTHORITY_SCOPE:"+",".join(ma))
    if runtime and not _runtime_ok(s,receipts): out.append("CURRENT_HOST_ADMISSION_RECEIPT_REQUIRED")
    return out
def _score(s,t):
    req=set(t["required_capabilities"]); strong=set(s.get("strong_capabilities",[])); supported=set(s.get("supported_capabilities",[]))
    return int(s.get("rank_bias",0))+30*len(req&strong)+12*len(req&supported)+{"P0":12,"P1":6,"P2":0}.get(s.get("priority"),0),s.get("id","")
def _advisory(ranked,a):
    deterministic=ranked[0]; ids=[s["id"] for s in ranked]
    trace={"fabric":"FA3-DECISION-FABRIC-001","role":"OPTIONAL_ADVISORY_AFTER_DETERMINISTIC_ELIGIBILITY","candidate_ids":ids,"candidate_set_expanded":False,"deterministic_specialist_id":deterministic["id"],"advisory_applied":False,"rollout":"NONE"}
    if a is None:return deterministic,trace
    if not isinstance(a,dict) or a.get("authority") is not False or a.get("candidate_set_expanded") is not False: raise DecisionAdvisoryError("invalid Decision Fabric authority/candidate boundary")
    supplied=a.get("candidate_ids")
    if not isinstance(supplied,list) or set(supplied)!=set(ids) or len(supplied)!=len(ids): raise DecisionAdvisoryError("Decision Fabric candidate set must exactly match deterministic eligibility")
    selected=a.get("selected_specialist_id")
    if selected not in ids: raise DecisionAdvisoryError("Decision Fabric selected outside eligible set")
    rollout=a.get("rollout","ADVISORY")
    if rollout not in {"SHADOW","ADVISORY","ACTIVE"}: raise DecisionAdvisoryError("unsupported Decision Fabric rollout")
    trace.update({"rollout":rollout,"advisory_specialist_id":selected,"advisory_status":a.get("status","DECIDED")})
    if rollout=="ACTIVE" and a.get("status","DECIDED")=="DECIDED":
        trace["advisory_applied"]=True; return next(s for s in ranked if s["id"]==selected),trace
    return deterministic,trace
def route_task(root,task,*,runtime_execution=None,admission_receipts=None,decision_advisory=None):
    _require_task_shape(task); reg=load_registry(root); runtime=bool(task.get("runtime_execution",False)) if runtime_execution is None else runtime_execution; receipts=admission_receipts or {}
    accepted=[]; rejected=[]
    for s in reg["specialists"]:
        rs=_reasons(s,task,runtime,receipts)
        (rejected.append(Rejection(s["id"],tuple(rs))) if rs else accepted.append(s))
    common={"schema":"fa3.orchestration-route-decision.v1","task_id":task["task_id"],"runtime_execution":runtime,"horizontal_gates":reg.get("horizontal_authorities",[]),"horizontal_fabrics":reg.get("horizontal_fabrics",[]),"resource_boundary":{"hardware_discovery":"FA3-HARDWARE-DISCOVERY-CONTRACTS-001","resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","accelerator_conflict":"FA3-ACCEL-GUARD-001","requirements":task.get("resource_requirements",{})},"authorized_ai_participants":list(task.get("authorized_ai_participants",[]))}
    if not accepted:return {**common,"status":"HUMAN_ESCALATION","reason":"NO_ELIGIBLE_SPECIALIST_AFTER_HARD_FILTERS","rejected":[r.as_dict() for r in rejected]}
    ranked=sorted(accepted,key=lambda s:(-_score(s,task)[0],_score(s,task)[1])); top=_score(ranked[0],task)[0]; ties=[s for s in ranked if _score(s,task)[0]==top]
    if len(ties)>1 and task.get("require_unambiguous",False): return {**common,"status":"HUMAN_ESCALATION","reason":"AMBIGUOUS_TOP_SPECIALIST","top_candidates":[{"specialist_id":s["id"],"provider":s["provider"],"score":top} for s in ties],"rejected":[r.as_dict() for r in rejected]}
    winner,trace=_advisory(ranked,decision_advisory)
    return {**common,"status":"ROUTED","specialist_id":winner["id"],"specialist_name":winner["name"],"provider":winner["provider"],"provider_id":winner["provider_id"],"score":_score(winner,task)[0],"authority_scope":winner.get("authority_scope",[]),"decision_fabric":trace,"uaf_execution_required":True,"fallback_candidates":[{"specialist_id":s["id"],"provider":s["provider"],"score":_score(s,task)[0]} for s in ranked if s["id"]!=winner["id"]],"rejected":[r.as_dict() for r in rejected]}
def compile_cross_domain_plan(root,request,*,runtime_execution=None):
    tasks=request.get("tasks"); receipts=request.get("runtime_admission_receipts",{}); advisories=request.get("decision_advisories",{})
    if not isinstance(tasks,list) or not tasks: raise WorkforceContractError("cross-domain request requires tasks")
    if not isinstance(receipts,dict) or not isinstance(advisories,dict): raise WorkforceContractError("receipt/advisory maps must be objects")
    seen=set(); decisions=[]
    for t in tasks:
        _require_task_shape(t)
        if t["task_id"] in seen: raise WorkforceContractError("duplicate task_id")
        seen.add(t["task_id"]); decisions.append(route_task(root,t,runtime_execution=runtime_execution,admission_receipts=receipts,decision_advisory=advisories.get(t["task_id"])))
    return {"schema":"fa3.cross-domain-work-plan.v2","goal":request.get("goal",""),"status":"READY" if all(d["status"]=="ROUTED" for d in decisions) else "HUMAN_REQUIRED","director":"FA3-ORCHESTRATION-DIRECTOR-001","provider_neutral":True,"execution_fabric":"FA3-UNIFIED-ACTION-FABRIC-001","decision_fabric":"FA3-DECISION-FABRIC-001_OPTIONAL_ADVISORY","ai_communication_policy":"FA3-AI-COMMS-001","hardware_discovery":"FA3-HARDWARE-DISCOVERY-CONTRACTS-001","resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","decisions":decisions}
def _main():
    p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));p.add_argument("--request",required=True);p.add_argument("--runtime",action="store_true");a=p.parse_args()
    plan=compile_cross_domain_plan(Path(a.root).resolve(),_load_json(Path(a.request)),runtime_execution=a.runtime);print(json.dumps(plan,ensure_ascii=False,indent=2));return 0 if plan["status"]=="READY" else 2
if __name__=="__main__": raise SystemExit(_main())
