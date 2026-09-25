#!/usr/bin/env python3
from __future__ import annotations
import copy
from pathlib import PurePosixPath
from typing import Any

GRAPH_SCHEMA="fa3.agent-workflow-graph.v1"
MODEL_CAP_SCHEMA="fa3.model-capability-descriptor.v1"
LEDGER_SCHEMA="fa3.agent-execution-ledger.v1"
CONFIRMATION_SCHEMA="fa3.tool-confirmation.v1"
ROUTER_AUTHORITY="FA3-AUTH-MODEL-ROUTER-001"
CONFIRMATION_AUTHORITY="FA3-AUTH-SECURITY-GOV-001_OR_AUTH-HUMAN"
NODE_KINDS={"AGENT","FUNCTION","SEQUENTIAL","PARALLEL","LOOP","DECISION"}
MODEL_CAP_SOURCES={"PROVIDER_DECLARED","ADMITTED_PROBE","PROVIDER_DECLARED_AND_PROBED"}
MCP_RESULT_FIELDS={"content","isError","structuredContent","_meta"}
BUDGET_DIMENSIONS={"model_calls","tool_calls","retries","transfer_hops"}

class RuntimeSemanticsError(ValueError): pass

def _nonempty(v:Any)->bool: return isinstance(v,str) and bool(v.strip())
def _strict_bool(v:Any)->bool: return type(v) is bool

def validate_graph(graph:dict[str,Any])->dict[str,Any]:
    if graph.get("schema")!=GRAPH_SCHEMA: raise RuntimeSemanticsError("graph schema mismatch")
    if not _nonempty(graph.get("graph_id")) or not _nonempty(graph.get("entry_node")): raise RuntimeSemanticsError("graph identity incomplete")
    if graph.get("yaml_is_canonical") is True: raise RuntimeSemanticsError("YAML may be import syntax, not canonical IR")
    nodes,edges=graph.get("nodes"),graph.get("edges")
    if not isinstance(nodes,list) or not nodes or not isinstance(edges,list): raise RuntimeSemanticsError("graph nodes/edges invalid")
    ids=set()
    for node in nodes:
        if not isinstance(node,dict) or not _nonempty(node.get("node_id")) or node.get("kind") not in NODE_KINDS: raise RuntimeSemanticsError("invalid graph node")
        if node["node_id"] in ids: raise RuntimeSemanticsError("duplicate graph node")
        ids.add(node["node_id"])
        retry=node.get("retry",{}) if node.get("retry",{}) is not None else {}
        if not isinstance(retry,dict): raise RuntimeSemanticsError("retry policy must be object")
        max_attempts=retry.get("max_attempts",1)
        if not isinstance(max_attempts,int) or isinstance(max_attempts,bool) or max_attempts<1: raise RuntimeSemanticsError("invalid retry max_attempts")
        resume=node.get("resume_policy","RERUN_FAILED")
        if resume not in {"RERUN_FAILED","REUSE_COMPLETED_DIGEST_BOUND"}: raise RuntimeSemanticsError("invalid resume policy")
        if node.get("side_effecting") is True and (max_attempts>1 or resume=="RERUN_FAILED") and not (_nonempty(node.get("idempotency_key_strategy")) or _nonempty(node.get("compensation_action_ref"))):
            raise RuntimeSemanticsError("side-effecting retry/resume requires idempotency or compensation")
    if graph["entry_node"] not in ids: raise RuntimeSemanticsError("entry node not found")
    for edge in edges:
        if not isinstance(edge,dict) or edge.get("from") not in ids or edge.get("to") not in ids: raise RuntimeSemanticsError("edge references unknown node")
    return copy.deepcopy(graph)

def validate_model_capability_descriptor(d:dict[str,Any])->dict[str,Any]:
    if d.get("schema")!=MODEL_CAP_SCHEMA: raise RuntimeSemanticsError("model capability schema mismatch")
    if not _nonempty(d.get("logical_model_id")): raise RuntimeSemanticsError("logical model identity required")
    if d.get("router_authority")!=ROUTER_AUTHORITY: raise RuntimeSemanticsError("Model Router authority required")
    if d.get("source") not in MODEL_CAP_SOURCES: raise RuntimeSemanticsError("untrusted model capability source")
    if d.get("model_id_heuristic") is not False: raise RuntimeSemanticsError("model-id capability inference forbidden")
    caps=d.get("capabilities"); required=("tools","structured_output","media_input","media_output","streaming")
    if not isinstance(caps,dict) or any(k not in caps or not _strict_bool(caps[k]) for k in required) or any(not _strict_bool(v) for v in caps.values()):
        raise RuntimeSemanticsError("explicit boolean model capabilities required")
    return copy.deepcopy(d)

def capabilities_satisfy(d:dict[str,Any],required:set[str])->bool:
    caps=validate_model_capability_descriptor(d)["capabilities"]
    return all(caps.get(k) is True for k in required)

def make_execution_ledger(fanout_limits:dict[str,Any],*,max_transfer_hops:int)->dict[str,Any]:
    limits={"model_calls":fanout_limits.get("max_model_requests"),"tool_calls":fanout_limits.get("max_tool_calls"),"retries":fanout_limits.get("max_retries"),"transfer_hops":max_transfer_hops}
    if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in limits.values()): raise RuntimeSemanticsError("execution budget limits invalid")
    return {"schema":LEDGER_SCHEMA,"limits":limits,"used":{k:0 for k in limits},"termination_reason":None}

def validate_execution_ledger(ledger:dict[str,Any])->dict[str,Any]:
    if ledger.get("schema")!=LEDGER_SCHEMA: raise RuntimeSemanticsError("execution ledger schema mismatch")
    limits,used=ledger.get("limits"),ledger.get("used")
    if not isinstance(limits,dict) or not isinstance(used,dict) or set(limits)!=BUDGET_DIMENSIONS or set(used)!=BUDGET_DIMENSIONS: raise RuntimeSemanticsError("ledger dimensions drift")
    for key in BUDGET_DIMENSIONS:
        a,b=limits[key],used[key]
        if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in (a,b)): raise RuntimeSemanticsError("ledger counters invalid")
        if b>a: raise RuntimeSemanticsError(f"execution budget exceeded: {key}")
    return copy.deepcopy(ledger)

def consume_budget(ledger:dict[str,Any],dimension:str,amount:int=1)->dict[str,Any]:
    checked=validate_execution_ledger(ledger)
    if dimension not in BUDGET_DIMENSIONS or not isinstance(amount,int) or isinstance(amount,bool) or amount<1: raise RuntimeSemanticsError("invalid budget consumption")
    checked["used"][dimension]+=amount
    if checked["used"][dimension]>checked["limits"][dimension]: raise RuntimeSemanticsError(f"BUDGET_EXHAUSTED:{dimension}")
    return checked

def plan_resume(node:dict[str,Any],prior_state:str,*,receipt_spec_digest:str|None=None,current_spec_digest:str|None=None)->str:
    if prior_state=="FAILED":
        if node.get("side_effecting") is True and not (_nonempty(node.get("idempotency_key_strategy")) or _nonempty(node.get("compensation_action_ref"))): raise RuntimeSemanticsError("unsafe side-effecting failed-node rerun")
        return "RERUN_FAILED_NODE"
    if prior_state=="COMPLETED":
        if not _nonempty(receipt_spec_digest) or not _nonempty(current_spec_digest) or receipt_spec_digest!=current_spec_digest: raise RuntimeSemanticsError("completed node receipt/spec digest mismatch")
        return "REUSE_COMPLETED_NODE"
    raise RuntimeSemanticsError("resume state unsupported")

def validate_tool_confirmation(r:dict[str,Any])->dict[str,Any]:
    if r.get("schema")!=CONFIRMATION_SCHEMA: raise RuntimeSemanticsError("tool confirmation schema mismatch")
    if not _nonempty(r.get("tool_id")) or not _nonempty(r.get("tool_args_digest")): raise RuntimeSemanticsError("tool confirmation identity required")
    if not _strict_bool(r.get("required")) or not _strict_bool(r.get("approved")): raise RuntimeSemanticsError("confirmation fields must be exact booleans")
    if r.get("authority")!=CONFIRMATION_AUTHORITY: raise RuntimeSemanticsError("confirmation authority drift")
    if r["required"] is True and (r["approved"] is not True or not _nonempty(r.get("approval_receipt_ref"))): raise RuntimeSemanticsError("required confirmation lacks approval receipt")
    return copy.deepcopy(r)

def fence_relayed_output(content:str,source_agent:str)->dict[str,Any]:
    if not _nonempty(content) or not _nonempty(source_agent): raise RuntimeSemanticsError("relay content/source required")
    return {"schema":"fa3.relayed-agent-output.v1","source_agent":source_agent,"trust":"UNTRUSTED_RELAYED_DATA","instruction_authority":False,"content":content}

def validate_transfer(req:dict[str,Any],authorized_targets:set[str],ledger:dict[str,Any])->tuple[dict[str,Any],dict[str,Any]]:
    if any(not _nonempty(req.get(k)) for k in ("source_agent","target_agent","reason")): raise RuntimeSemanticsError("transfer source/target/reason required")
    if req["source_agent"]==req["target_agent"]: raise RuntimeSemanticsError("self transfer forbidden")
    if req["target_agent"] not in authorized_targets: raise RuntimeSemanticsError("transfer target not pre-authorized")
    return copy.deepcopy(req),consume_budget(ledger,"transfer_hops")

def normalize_mcp_result(result:dict[str,Any])->dict[str,Any]:
    if not isinstance(result,dict): raise RuntimeSemanticsError("MCP result must be object")
    unknown=set(result)-MCP_RESULT_FIELDS
    if unknown: raise RuntimeSemanticsError(f"MCP vendor extensions must be under _meta: {sorted(unknown)}")
    if "_meta" in result and not isinstance(result["_meta"],dict): raise RuntimeSemanticsError("MCP _meta must be object")
    if "isError" in result and not _strict_bool(result["isError"]): raise RuntimeSemanticsError("MCP isError must be boolean")
    return copy.deepcopy(result)

def validate_session_append(session:dict[str,Any],event:dict[str,Any],seen_event_ids:set[str])->dict[str,Any]:
    if session.get("state")!="ACTIVE" or not _nonempty(session.get("session_id")) or not _nonempty(session.get("thread_id")): raise RuntimeSemanticsError("known active session/thread required")
    if any(not _nonempty(event.get(k)) for k in ("event_id","session_id","thread_id")): raise RuntimeSemanticsError("session event identity required")
    if event["session_id"]!=session["session_id"] or event["thread_id"]!=session["thread_id"]: raise RuntimeSemanticsError("cross-session/thread append forbidden")
    if event["event_id"] in seen_event_ids: raise RuntimeSemanticsError("duplicate session event")
    return copy.deepcopy(event)

def validate_artifact_write(relative_path:str,size_bytes:int,max_bytes:int,*,previous_version:int|None=None,requested_version:int|None=None)->dict[str,Any]:
    if not _nonempty(relative_path): raise RuntimeSemanticsError("artifact relative path required")
    p=PurePosixPath(relative_path)
    if p.is_absolute() or ".." in p.parts or str(p) in {"",".","/"}: raise RuntimeSemanticsError("artifact path escapes declared relative scope")
    if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in (size_bytes,max_bytes)) or size_bytes>max_bytes: raise RuntimeSemanticsError("artifact size policy invalid/exceeded")
    if requested_version is not None:
        if not isinstance(requested_version,int) or isinstance(requested_version,bool) or requested_version<1: raise RuntimeSemanticsError("artifact version invalid")
        if previous_version is not None and requested_version!=previous_version+1: raise RuntimeSemanticsError("artifact version must advance atomically by one")
    return {"relative_path":str(p),"size_bytes":size_bytes,"max_bytes":max_bytes,"version":requested_version}
