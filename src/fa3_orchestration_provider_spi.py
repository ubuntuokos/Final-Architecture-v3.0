#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fa3_ai_comms import validate_message_envelope
from fa3_orchestration_workforce import EXISTING_RUNTIME_AUTHORITY_STATES,WorkforceContractError,current_host_admission_valid,load_registry
from fa3_uaf import ActionRegistry
SPI_REL=Path("canonical/contracts/FA3-ORCHESTRATION-PROVIDER-SPI-001.json")
UAF_ACTION_BY_MODE={"design":"orchestration.delegate","runtime":"orchestration.execute"}
FORBIDDEN_DIRECT_METADATA={"direct_model_provider","direct_provider_endpoint","runtime_provider_override"}
class ProviderAdapterError(WorkforceContractError): pass
class ProviderRuntimeNotPromoted(ProviderAdapterError): pass
class ProviderParticipantExpansionDenied(ProviderAdapterError): pass
def _load(path):return json.loads(path.read_text(encoding="utf-8"))
def load_spi_contract(root):
    c=_load(Path(root)/SPI_REL)
    if c.get("schema")!="fa3.provider-spi-contract.v1" or c.get("id")!="FA3-ORCHESTRATION-PROVIDER-SPI-001":raise ProviderAdapterError("unexpected provider SPI")
    return c
def _specialist(reg,sid):
    for s in reg.get("specialists",[]):
        if s.get("id")==sid:return s
    raise ProviderAdapterError("unknown specialist")
def _participants(task):
    auth=list(task.get("authorized_ai_participants",[])); req=task.get("metadata",{}).get("provider_requested_ai_participants",[])
    if not isinstance(req,list) or not all(isinstance(v,str) and v for v in req):raise ProviderParticipantExpansionDenied("invalid provider participant request")
    extra=sorted(set(req)-set(auth))
    if extra:raise ProviderParticipantExpansionDenied("provider attempted participant expansion: "+",".join(extra))
    return auth
def validate_provider_message(payload:dict[str,Any],*,sender:str,recipient:str)->dict[str,Any]:return validate_message_envelope(payload,sender=sender,recipient=recipient)
def compile_provider_envelope(root,task,route_decision,*,runtime_execution=False,admission_receipt=None):
    if route_decision.get("schema")!="fa3.orchestration-route-decision.v1" or route_decision.get("status")!="ROUTED":raise ProviderAdapterError("only ROUTED decisions may compile")
    if route_decision.get("task_id")!=task.get("task_id") or route_decision.get("uaf_execution_required") is not True:raise ProviderAdapterError("route/UAF boundary invalid")
    for k in FORBIDDEN_DIRECT_METADATA:
        if task.get("metadata",{}).get(k) not in (None,"",False):raise ProviderAdapterError(f"{k} forbidden; use Model Router/UAF")
    root=Path(root);reg=load_registry(root);spi=load_spi_contract(root);s=_specialist(reg,route_decision["specialist_id"]);pid=s.get("provider_id");kind=spi.get("adapter_kinds",{}).get(pid)
    if not kind:raise ProviderAdapterError("adapter kind missing")
    scope=set(route_decision.get("authority_scope",[]))
    if not scope.issubset(set(s.get("authority_scope",[]))):raise ProviderAdapterError("authority expansion")
    auth_participants=_participants(task)
    if runtime_execution and s.get("runtime_promotion_status") not in EXISTING_RUNTIME_AUTHORITY_STATES and not current_host_admission_valid(str(pid),admission_receipt):raise ProviderRuntimeNotPromoted("scope-bound current-host production admission receipt required")
    mode="runtime" if runtime_execution else "design";action_id=UAF_ACTION_BY_MODE[mode];ActionRegistry.from_directory(root/"canonical/actions").get(action_id)
    caps=list(task.get("required_capabilities",[]))
    return {"schema":"fa3.orchestration-provider-projection.v2","canonical":False,"executable_authority":False,"direct_runtime_invocation_allowed":False,"task_id":task["task_id"],"specialist_id":s["id"],"provider":s["provider"],"provider_id":pid,"adapter_kind":kind,"mode":mode,"provider_promotion_status_informational":s.get("runtime_promotion_status"),"runtime_admission_receipt_required":runtime_execution and s.get("runtime_promotion_status") not in EXISTING_RUNTIME_AUTHORITY_STATES,"uaf_action":{"fabric":"FA3-UNIFIED-ACTION-FABRIC-001","action_id":action_id,"direct_provider_bypass":False},"delegated_capabilities":caps,"delegated_authority_scope":sorted(scope),"required_authorities":list(task.get("required_authorities",[])),"horizontal_authorities":[e["authority"] for e in reg.get("horizontal_authorities",[]) if e.get("authority")],"authorized_ai_participants":auth_participants,"provider_payload":{"domain":task["domain"],"objective":task.get("objective") or task.get("description") or task["task_id"],"capabilities":caps,"metadata":{k:v for k,v in task.get("metadata",{}).items() if k not in FORBIDDEN_DIRECT_METADATA and k!="provider_requested_ai_participants"}},"constraints":{"provider_native_schema_is_canonical":False,"may_expand_authority":False,"may_expand_ai_participant_set":False,"may_route_models":False,"model_routing_authority":"FA3-AUTH-MODEL-ROUTER-001","ai_communication_policy":"FA3-AI-COMMS-001","private_model_language_allowed":False,"hardware_discovery_authority":False,"resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","must_return_evidence_to_fa3":True,"must_reenter_horizontal_gates_for_consequential_actions":True}}
def compile_plan_envelopes(root,request,plan,*,runtime_execution=False):
    if plan.get("schema")!="fa3.cross-domain-work-plan.v2":raise ProviderAdapterError("plan schema mismatch")
    tasks={t["task_id"]:t for t in request.get("tasks",[])};receipts=request.get("runtime_admission_receipts",{});env=[]
    for d in plan.get("decisions",[]):
        if d.get("status")!="ROUTED":raise ProviderAdapterError("unresolved plan")
        t=tasks.get(d.get("task_id"))
        if t is None:raise ProviderAdapterError("unknown task")
        env.append(compile_provider_envelope(root,t,d,runtime_execution=runtime_execution,admission_receipt=receipts.get(d.get("provider_id"))))
    return {"schema":"fa3.provider-adapter-plan.v2","canonical":False,"executable_authority":False,"source_plan_schema":plan["schema"],"execution_fabric":"FA3-UNIFIED-ACTION-FABRIC-001","mode":"runtime" if runtime_execution else "design","envelopes":env}
