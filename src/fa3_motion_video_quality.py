#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from typing import Any
SCHEMA="fa3.motion-plan.v1"
ALLOWED_PRIMITIVES={"PERSISTENT_ACTOR","OBJECT_HANDOFF","FOREGROUND_TRANSITION","MATCHED_DIRECTION","SELECTION_EXPANSION","MATERIALIZE_RESULT","EXPLODED_ASSEMBLY","REGISTERED_DECOMPOSITION","CONTINUOUS_CANVAS","CAMERA_CONTINUITY","CAUSE_EFFECT_BEAT","TYPE_CHOREOGRAPHY"}
VERIFY_STATES={"FIXED","PARTIAL","STILL_PRESENT","REGRESSION","NOT_VERIFIABLE"}
class MotionVideoQualityError(ValueError):pass
def canonical_digest(value:Any)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def validate_motion_plan(plan:dict[str,Any])->dict[str,Any]:
 required=("motion_plan_id","revision","project_id","project_revision","timeline_revision","timebase","beats","actors","transitions","camera_constraints","motion_constraints","continuity_constraints","audio_cues","quality_profile","render_intent","source_artifact_refs","provenance","digest")
 if plan.get("schema")!=SCHEMA:raise MotionVideoQualityError("motion plan schema mismatch")
 missing=[k for k in required if k not in plan]
 if missing:raise MotionVideoQualityError("missing fields: "+",".join(missing))
 primitives={str(x.get("primitive")) for x in plan.get("transitions",[]) if isinstance(x,dict) and x.get("primitive")}
 if not primitives.issubset(ALLOWED_PRIMITIVES):raise MotionVideoQualityError("unsupported motion primitive")
 if plan["digest"]!=canonical_digest({k:v for k,v in plan.items() if k!="digest"}):raise MotionVideoQualityError("motion plan digest mismatch")
 if plan.get("render_intent",{}).get("engine_id"):raise MotionVideoQualityError("motion plan may not select a physical engine")
 return plan
def assert_revision_binding(plan:dict[str,Any],project_revision:str,timeline_revision:str)->None:
 if str(plan.get("project_revision"))!=str(project_revision):raise MotionVideoQualityError("stale project revision")
 if str(plan.get("timeline_revision"))!=str(timeline_revision):raise MotionVideoQualityError("stale timeline revision")
def validate_independent_review(producer_identity:str,reviewer_identity:str)->None:
 if not producer_identity or not reviewer_identity:raise MotionVideoQualityError("review identities required")
 if producer_identity==reviewer_identity:raise MotionVideoQualityError("self review forbidden")
def validate_verification_state(state:str)->str:
 if state not in VERIFY_STATES:raise MotionVideoQualityError("invalid verification state")
 return state
