#!/usr/bin/env python3
"""FA3 Conversation & Meeting -> Work Fabric reference core.

Zero-authority shared core: normalizes source events, creates reviewable work
proposals, projects one graph into views, and emits typed draft intents.
"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Any, Iterable

PROFILE_ID="FA3-CONVERSATION-MEETING-WORK-FABRIC-001"
SUPPORTED_OBJECT_TYPES={"TOPIC","IDEA","REQUIREMENT","PROPOSAL","DECISION","ALTERNATIVE","QUESTION","ACTION_ITEM","TASK","ACTOR","DEADLINE","DEPENDENCY","BLOCKER","APPROVAL_GATE","MILESTONE","ARTIFACT","EVIDENCE","FOLLOW_UP"}
DRAFT_TARGETS={"TASK":"FA3-WORK-MANAGEMENT-PROJECTION-001","ACTION_ITEM":"FA3-WORK-MANAGEMENT-PROJECTION-001","DECISION":"FA3-DECISION-FABRIC-001","REQUIREMENT":"FA3-JOURNAL-001","QUESTION":"FA3-JOURNAL-001","DEADLINE":"DEADLINE_MILESTONE_SHARED_TARGET","MILESTONE":"DEADLINE_MILESTONE_SHARED_TARGET","DEPENDENCY":"WORK_COORDINATION_SHARED_TARGET","BLOCKER":"WORK_COORDINATION_SHARED_TARGET","FOLLOW_UP":"MEETING_MANAGER_SHARED_TARGET"}

class WorkPolicyError(ValueError): pass

@dataclass(frozen=True)
class SourceEvent:
    event_id:str; source_id:str; timestamp:str; speaker_id:str; speaker_role:str
    origin:str; object_type:str; text:str; confidence:float|None=None
    metadata:dict[str,Any]=field(default_factory=dict)

@dataclass(frozen=True)
class WorkProposal:
    proposal_id:str; object_type:str; text:str; source_event_id:str; source_id:str; origin:str
    state:str="PROPOSED"; human_verified:bool=False; rejection_reason:str|None=None
    metadata:dict[str,Any]=field(default_factory=dict)

def normalize_event(raw:dict[str,Any],*,ai_enabled:bool=True)->SourceEvent:
    required=("event_id","source_id","timestamp","speaker_id","speaker_role","origin","object_type","text")
    missing=[k for k in required if not raw.get(k)]
    if missing: raise WorkPolicyError("MISSING_PROVENANCE:"+",".join(missing))
    origin=str(raw["origin"]).upper(); object_type=str(raw["object_type"]).upper()
    if origin not in {"MANUAL","DETERMINISTIC","AI_PROPOSAL"}: raise WorkPolicyError("UNSUPPORTED_ORIGIN")
    if origin=="AI_PROPOSAL" and not ai_enabled: raise WorkPolicyError("AI_DISABLED")
    if object_type not in SUPPORTED_OBJECT_TYPES: raise WorkPolicyError("UNSUPPORTED_OBJECT_TYPE")
    confidence=raw.get("confidence")
    if confidence is not None and not (0.0<=float(confidence)<=1.0): raise WorkPolicyError("INVALID_CONFIDENCE")
    return SourceEvent(str(raw["event_id"]),str(raw["source_id"]),str(raw["timestamp"]),str(raw["speaker_id"]),str(raw["speaker_role"]),origin,object_type,str(raw["text"]).strip(),None if confidence is None else float(confidence),dict(raw.get("metadata") or {}))

def propose(event:SourceEvent)->WorkProposal:
    return WorkProposal(f"work:{event.event_id}",event.object_type,event.text,event.event_id,event.source_id,event.origin,metadata={"speaker_id":event.speaker_id,"speaker_role":event.speaker_role,"speaker_confidence":event.confidence,**event.metadata})

def verify_human(p:WorkProposal,*,verifier_id:str)->WorkProposal:
    if p.state!="PROPOSED" or not verifier_id: raise WorkPolicyError("INVALID_STATE_TRANSITION")
    return replace(p,state="HUMAN_VERIFIED",human_verified=True,metadata={**p.metadata,"verified_by":verifier_id})

def reject(p:WorkProposal,*,reviewer_id:str,reason:str)->WorkProposal:
    if p.state not in {"PROPOSED","HUMAN_VERIFIED"}: raise WorkPolicyError("INVALID_STATE_TRANSITION")
    if not reviewer_id or not reason: raise WorkPolicyError("REVIEWER_AND_REASON_REQUIRED")
    return replace(p,state="REJECTED",rejection_reason=reason,metadata={**p.metadata,"rejected_by":reviewer_id})

def approve_for_materialization(p:WorkProposal,*,approver_id:str,permissions:Iterable[str])->WorkProposal:
    if p.state!="HUMAN_VERIFIED" or not p.human_verified: raise WorkPolicyError("HUMAN_VERIFICATION_REQUIRED")
    if not approver_id or "MATERIALIZE_WORK" not in set(permissions): raise WorkPolicyError("APPROVER_NOT_AUTHORIZED")
    return replace(p,state="APPROVED_FOR_MATERIALIZATION",metadata={**p.metadata,"approved_by":approver_id})

def emit_draft_intent(p:WorkProposal)->dict[str,Any]:
    if p.state!="APPROVED_FOR_MATERIALIZATION": raise WorkPolicyError("MATERIALIZATION_APPROVAL_REQUIRED")
    return {"schema":"fa3.work-draft-intent.v1","authority":False,"profile_id":PROFILE_ID,"proposal_id":p.proposal_id,"object_type":p.object_type,"target":DRAFT_TARGETS.get(p.object_type,"FA3-JOURNAL-001"),"payload":{"text":p.text,"metadata":p.metadata},"source":{"source_id":p.source_id,"event_id":p.source_event_id},"state":"DRAFT_NOT_CANONICAL","target_authority_must_finalize":True}

def rollback_draft(p:WorkProposal)->WorkProposal:
    if p.state!="APPROVED_FOR_MATERIALIZATION": raise WorkPolicyError("INVALID_STATE_TRANSITION")
    return replace(p,state="HUMAN_VERIFIED",metadata={**p.metadata,"draft_retracted":True})

def project_views(proposals:Iterable[WorkProposal])->dict[str,Any]:
    active=[p for p in proposals if p.state!="REJECTED"]; by={}
    for p in active: by.setdefault(p.object_type,[]).append({"id":p.proposal_id,"text":p.text,"state":p.state,"source_event_id":p.source_event_id})
    nodes=[x for rows in by.values() for x in rows]
    return {"schema":"fa3.structured-work-projection.v1","source_of_truth":False,"shared_graph_node_count":len(active),"views":{
      "MIND_MAP":{"nodes":nodes},"DECISION_MAP":{"items":by.get("DECISION",[])+by.get("PROPOSAL",[])},
      "TASK_LIST":{"items":by.get("TASK",[])+by.get("ACTION_ITEM",[])},
      "WORK_PLAN":{"tasks":by.get("TASK",[])+by.get("ACTION_ITEM",[]),"dependencies":by.get("DEPENDENCY",[]),"blockers":by.get("BLOCKER",[])},
      "TIMELINE_MILESTONE":{"deadlines":by.get("DEADLINE",[]),"milestones":by.get("MILESTONE",[])},
      "MEETING_MINUTES":{"topics":by.get("TOPIC",[]),"decisions":by.get("DECISION",[]),"questions":by.get("QUESTION",[])},
      "OPEN_QUESTIONS":{"items":by.get("QUESTION",[])},"FOLLOW_UP_AGENDA":{"items":by.get("FOLLOW_UP",[])+by.get("QUESTION",[])}}}

def self_test()->dict[str,Any]:
    raw={"event_id":"evt-1","source_id":"meeting-1","timestamp":"2026-10-01T10:00:00+02:00","speaker_id":"p","speaker_role":"participant","origin":"DETERMINISTIC","object_type":"TASK","text":"Prepare follow-up."}
    p=verify_human(propose(normalize_event(raw)),verifier_id="reviewer")
    p=approve_for_materialization(p,approver_id="approver",permissions={"MATERIALIZE_WORK"})
    d=emit_draft_intent(p)
    return {"profile_id":PROFILE_ID,"result":"PASS" if d["state"]=="DRAFT_NOT_CANONICAL" and d["authority"] is False else "FAIL","current_host_promotion_claim":False}

if __name__=="__main__":
    import json; print(json.dumps(self_test(),indent=2))
