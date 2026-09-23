#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from dataclasses import dataclass,field
from typing import Any,Callable,Iterable

TRUST_CLASS="UNTRUSTED_EXTERNAL_CONTENT"
MODEL_ROUTER_AUTHORITY="FA3-AUTH-MODEL-ROUTER-001"
ELEMENT_OPERATIONS={"CLICK","TYPE_TEXT","SELECT","SCROLL_INTO_VIEW","PRESS_KEY"}
MUTATING_OPERATIONS={"CLICK","TYPE_TEXT","SELECT","PRESS_KEY"}

class BrowserActionDenied(RuntimeError):
    def __init__(self,code:str,message:str):
        super().__init__(message); self.code=code

def _digest(value:Any)->str:
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def _text(value:Any,name:str)->str:
    if not isinstance(value,str) or not value.strip():
        raise BrowserActionDenied("BROWSER-OBSERVATION-INVALID",f"{name} required")
    return value.strip()

def normalize_observation(raw:dict[str,Any])->dict[str,Any]:
    if not isinstance(raw,dict): raise BrowserActionDenied("BROWSER-OBSERVATION-INVALID","object required")
    revision=raw.get("revision")
    if not isinstance(revision,int) or revision<0:
        raise BrowserActionDenied("BROWSER-OBSERVATION-INVALID","non-negative revision required")
    elements=raw.get("elements")
    if not isinstance(elements,list): raise BrowserActionDenied("BROWSER-OBSERVATION-INVALID","elements list required")
    rows=[]; seen=set()
    for item in elements:
        if not isinstance(item,dict): raise BrowserActionDenied("BROWSER-OBSERVATION-INVALID","element object required")
        eid=_text(item.get("element_id"),"element_id")
        if eid in seen: raise BrowserActionDenied("BROWSER-OBSERVATION-INVALID","duplicate element_id")
        seen.add(eid)
        actions=item.get("supported_actions",[])
        if not isinstance(actions,list) or any(x not in ELEMENT_OPERATIONS for x in actions):
            raise BrowserActionDenied("BROWSER-OBSERVATION-INVALID","invalid supported_actions")
        rows.append({
            "element_id":eid,"role":str(item.get("role","")),"label":str(item.get("label","")),
            "value":item.get("value"),"visible":item.get("visible") is True,
            "enabled":item.get("enabled") is not False,"occluded":item.get("occluded") is True,
            "supported_actions":sorted(set(actions)),
            "metadata":item.get("metadata",{}) if isinstance(item.get("metadata",{}),dict) else {}
        })
    return {
        "schema":"fa3.browser-observation.v1",
        "observation_id":_text(raw.get("observation_id"),"observation_id"),
        "revision":revision,
        "document_id":_text(raw.get("document_id"),"document_id"),
        "page_fingerprint":_text(raw.get("page_fingerprint"),"page_fingerprint"),
        "url":str(raw.get("url","")),
        "trust_class":TRUST_CLASS,
        "elements":sorted(rows,key=lambda x:x["element_id"]),
        "provenance":raw.get("provenance",{}) if isinstance(raw.get("provenance",{}),dict) else {}
    }

def build_action_space(raw:dict[str,Any])->dict[str,Any]:
    obs=normalize_observation(raw); candidates=[]; idx=0
    for elem in obs["elements"]:
        for op in elem["supported_actions"]:
            candidates.append({
                "id":str(idx),"action_id":f"{op}:{elem['element_id']}","operation":op,
                "target_id":elem["element_id"],
                "description":f"{op} role={elem['role']} label={elem['label']}".strip(),
                "metadata":{"role":elem["role"],"label":elem["label"],"trust_class":TRUST_CLASS}
            }); idx+=1
    for op in ("WAIT","DONE","BLOCKED"):
        candidates.append({"id":str(idx),"action_id":op,"operation":op,"target_id":None,
                           "description":op,"metadata":{"trust_class":"FA3_RUNTIME_CONTROL"}}); idx+=1
    body={"schema":"fa3.browser-action-space.v1","observation_id":obs["observation_id"],
          "revision":obs["revision"],"document_id":obs["document_id"],
          "page_fingerprint":obs["page_fingerprint"],"candidates":candidates,
          "candidate_set_source":"FA3_BROWSER_RUNTIME_ONLY","candidate_set_expansion":"DENY"}
    body["action_space_hash"]=_digest(body); return body

def decision_request(space:dict[str,Any],*,purpose:str,state:Any=None,rollout:str="SHADOW")->dict[str,Any]:
    return {"contract":"SELECT_ONE","purpose":purpose,
      "candidates":[{"id":r["id"],"description":r["description"],
                     "metadata":{**r["metadata"],"operation":r["operation"],"target_id":r["target_id"],"action_id":r["action_id"]}}
                    for r in space["candidates"]],
      "constraints":{"candidate_set_expansion":"DENY","executable_code_generation":"DENY"},
      "policy_context":{"consumer":"FA3-WEB-AI-001","observation_id":space["observation_id"],
                        "revision":space["revision"],"action_space_hash":space["action_space_hash"],
                        "page_content_trust":TRUST_CLASS},
      "evidence_refs":[],"state":state,"failure_policy":"FAIL_CLOSED","rollout":rollout,
      "final_policy_owner":"FA3-WEB-AI-001"}

def bind_selected_action(space:dict[str,Any],selected_candidate_id:str)->dict[str,Any]:
    row=next((x for x in space["candidates"] if x["id"]==str(selected_candidate_id)),None)
    if row is None: raise BrowserActionDenied("BROWSER-CANDIDATE-ESCAPE","candidate outside bounded action space")
    return {"schema":"fa3.browser-decision-binding.v1","observation_id":space["observation_id"],
            "revision":space["revision"],"document_id":space["document_id"],
            "page_fingerprint":space["page_fingerprint"],"action_space_hash":space["action_space_hash"],
            "selected_candidate":row}

def decide_action(fabric:Any,space:dict[str,Any],*,purpose:str,
                  provider_id:str="FA3-PROVIDER-DECISION-RULES-001",
                  state:Any=None,rollout:str="SHADOW")->tuple[dict[str,Any],dict[str,Any]]:
    trace=fabric.decide(decision_request(space,purpose=purpose,state=state,rollout=rollout),provider_id)
    if trace.get("status")!="DECIDED":
        raise BrowserActionDenied("BROWSER-DECISION-NOT-AVAILABLE",str(trace.get("status")))
    selected=(trace.get("result") or {}).get("selected")
    if not isinstance(selected,str): raise BrowserActionDenied("BROWSER-DECISION-INVALID","selected id missing")
    return bind_selected_action(space,selected),trace

def revalidate(binding:dict[str,Any],raw:dict[str,Any])->dict[str,Any]:
    obs=normalize_observation(raw); fresh=build_action_space(obs)
    for key in ("observation_id","revision","document_id","page_fingerprint","action_space_hash"):
        if fresh.get(key)!=binding.get(key):
            raise BrowserActionDenied("STALE_OBSERVATION",f"binding mismatch: {key}")
    wanted=binding.get("selected_candidate",{})
    current=next((x for x in fresh["candidates"] if x["id"]==wanted.get("id") and x["action_id"]==wanted.get("action_id")),None)
    if current is None: raise BrowserActionDenied("STALE_OBSERVATION","selected action disappeared")
    guards=["OBSERVATION_CURRENT","DOCUMENT_MATCH","ACTION_SPACE_MATCH","OPERATION_SUPPORTED"]
    if current["target_id"] is not None:
        target=next((x for x in obs["elements"] if x["element_id"]==current["target_id"]),None)
        if target is None: raise BrowserActionDenied("TARGET_MISSING","target missing")
        if not target["visible"]: raise BrowserActionDenied("TARGET_NOT_VISIBLE","target not visible")
        guards.append("VISIBLE")
        if current["operation"] in {"CLICK","TYPE_TEXT","SELECT","PRESS_KEY"}:
            if not target["enabled"]: raise BrowserActionDenied("TARGET_DISABLED","target disabled")
            guards.append("ENABLED")
        if current["operation"]=="CLICK":
            if target["occluded"]: raise BrowserActionDenied("TARGET_OCCLUDED","target occluded")
            guards.append("NOT_OCCLUDED")
    return {"schema":"fa3.browser-execution-guard-result.v1","result":"PASS","guards":guards,
            "candidate":current,"observation_id":obs["observation_id"],"revision":obs["revision"]}

@dataclass
class MutationLedger:
    attempted:set[str]=field(default_factory=set)
    def begin(self,binding:dict[str,Any])->str:
        c=binding["selected_candidate"]
        token=_digest({"observation_id":binding["observation_id"],"revision":binding["revision"],"action_id":c["action_id"]})
        if c["operation"] in MUTATING_OPERATIONS and token in self.attempted:
            raise BrowserActionDenied("BLIND_MUTATION_RETRY_DENIED","mutation cannot be blindly retried")
        if c["operation"] in MUTATING_OPERATIONS: self.attempted.add(token)
        return token

def execute_action(binding:dict[str,Any],current:dict[str,Any],
                   executor:Callable[[dict[str,Any],dict[str,Any]],dict[str,Any]],
                   *,ledger:MutationLedger|None=None)->dict[str,Any]:
    guard=revalidate(binding,current); candidate=guard["candidate"]; op=candidate["operation"]
    if op=="DONE":
        return {"schema":"fa3.browser-execution-receipt.v1","status":"COMPLETION_CLAIM",
                "verified_success":False,"candidate":candidate,"guard_result":guard,"global_promotion_claim":False}
    if op=="BLOCKED":
        return {"schema":"fa3.browser-execution-receipt.v1","status":"BLOCKED_CLAIM",
                "verified_success":False,"candidate":candidate,"guard_result":guard,"global_promotion_claim":False}
    ledger=ledger or MutationLedger(); token=ledger.begin(binding)
    output=executor(candidate,normalize_observation(current))
    if not isinstance(output,dict): raise BrowserActionDenied("BROWSER-EXECUTION-INVALID","executor object required")
    return {"schema":"fa3.browser-execution-receipt.v1","status":"EXECUTED","verified_success":False,
            "candidate":candidate,"guard_result":guard,"attempt_token":token,"provider_output":output,
            "global_promotion_claim":False}

def type_text_generation_request(binding:dict[str,Any],*,purpose:str,field_context:dict[str,Any]|None=None)->dict[str,Any]:
    c=binding.get("selected_candidate",{})
    if c.get("operation")!="TYPE_TEXT":
        raise BrowserActionDenied("BROWSER-TEXT-REQUEST-INVALID","TYPE_TEXT required")
    return {"schema":"fa3.browser-text-generation-request.v1","authority":MODEL_ROUTER_AUTHORITY,
            "logical_route":"fa3-text-primary","purpose":purpose,"target_id":c.get("target_id"),
            "field_context":field_context or {},
            "rules":{"provider_selection":"MODEL_ROUTER_ONLY","physical_model_selection":"MODEL_ROUTER_ONLY",
                     "page_content_trust":TRUST_CLASS}}

def verify_outcome(expected_postconditions:Iterable[dict[str,Any]],raw_post:dict[str,Any])->dict[str,Any]:
    obs=normalize_observation(raw_post); conditions=list(expected_postconditions)
    if not conditions:
        return {"schema":"fa3.browser-outcome-verification.v1","result":"INDETERMINATE",
                "checks":[],"global_promotion_claim":False}
    by_id={x["element_id"]:x for x in obs["elements"]}; checks=[]
    for c in conditions:
        kind=c.get("type"); passed=None
        if kind=="url_equals": passed=obs["url"]==c.get("value")
        elif kind=="url_contains": passed=isinstance(c.get("value"),str) and c["value"] in obs["url"]
        elif kind=="element_present": passed=c.get("element_id") in by_id
        elif kind=="element_absent": passed=c.get("element_id") not in by_id
        elif kind=="element_value_equals":
            e=by_id.get(c.get("element_id")); passed=e is not None and e.get("value")==c.get("value")
        checks.append({"condition":c,"passed":passed})
    result="VERIFIED_FAILURE" if any(x["passed"] is False for x in checks) else (
           "VERIFIED_SUCCESS" if all(x["passed"] is True for x in checks) else "INDETERMINATE")
    return {"schema":"fa3.browser-outcome-verification.v1","result":result,"checks":checks,
            "observation_id":obs["observation_id"],"revision":obs["revision"],"global_promotion_claim":False}
