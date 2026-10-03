#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from copy import deepcopy
from typing import Any
ALLOWED_PRIMITIVES={"PERSISTENT_ACTOR","OBJECT_HANDOFF","FOREGROUND_TRANSITION","MATCHED_DIRECTION","SELECTION_EXPANSION","MATERIALIZE_RESULT","EXPLODED_ASSEMBLY","REGISTERED_DECOMPOSITION","CONTINUOUS_CANVAS","CAMERA_CONTINUITY","CAUSE_EFFECT_BEAT","TYPE_CHOREOGRAPHY"}
ALLOWED_VERIFICATION={"FIXED","PARTIAL","STILL_PRESENT","REGRESSION","NOT_VERIFIABLE"}
ALLOWED_COMPONENT_TYPES={"TRANSITION","MOTION_GRAPHIC","TITLE","UI_ANIMATION","CAMERA_MOVE","THREE_D_OR_DCC_MOTION","VFX_COMPONENT","AUDIO_TRANSITION"}
REQUIRED_PLAN_FIELDS=("motion_plan_id","revision","project_id","project_revision","timeline_revision","timebase","beats","actors","transitions","camera_constraints","motion_constraints","continuity_constraints","audio_cues","quality_profile","render_intent","source_artifact_refs","provenance")
class MotionVideoQualityError(ValueError): pass
def _bytes(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha256_json(v:Any)->str:return hashlib.sha256(_bytes(v)).hexdigest()
def _payload(p):v=deepcopy(p);v.pop("digest",None);return v
def normalize_motion_plan(plan):
 if not isinstance(plan,dict) or plan.get("schema")!="fa3.motion-plan.v1":raise MotionVideoQualityError("invalid motion plan schema")
 missing=[f for f in REQUIRED_PLAN_FIELDS if f not in plan]
 if missing:raise MotionVideoQualityError("missing motion plan fields: "+",".join(missing))
 for f in ("motion_plan_id","revision","project_id","project_revision","timeline_revision"):
  if not isinstance(plan.get(f),str) or not plan[f]:raise MotionVideoQualityError("invalid motion plan identity/revision field: "+f)
 for f in ("beats","actors","transitions","camera_constraints","motion_constraints","continuity_constraints","audio_cues","source_artifact_refs"):
  if not isinstance(plan.get(f),list):raise MotionVideoQualityError("motion plan field must be a list: "+f)
 for t in plan["transitions"]:
  if not isinstance(t,dict) or t.get("primitive") not in ALLOWED_PRIMITIVES:raise MotionVideoQualityError("unknown or missing motion primitive")
 n=deepcopy(plan);expected=sha256_json(_payload(n));existing=n.get("digest")
 if existing not in (None,"",expected):raise MotionVideoQualityError("motion plan digest mismatch")
 n["digest"]=expected;return n
def build_edit_proposal(plan,current_project_revision,current_timeline_revision):
 n=normalize_motion_plan(plan)
 if n["project_revision"]!=current_project_revision:raise MotionVideoQualityError("stale project revision")
 if n["timeline_revision"]!=current_timeline_revision:raise MotionVideoQualityError("stale timeline revision")
 return {"schema":"fa3.motion-edit-proposal.v1","motion_plan_id":n["motion_plan_id"],"motion_plan_digest":n["digest"],"expected_project_revision":current_project_revision,"expected_timeline_revision":current_timeline_revision,"dry_run_required":True,"direct_native_project_mutation":False,"timeline_command_surface":"EXISTING_FA3_VIDEO_EDITOR_COMMAND_BUS_OR_OTIO","engine_selection_authority":False,"rollback_reference_required":True}
def deterministic_render_key(req):
 fields=("input_artifact_digest","motion_plan_digest","timeline_revision","frame_or_range","engine_selection_intent","render_profile");missing=[f for f in fields if f not in req]
 if missing:raise MotionVideoQualityError("missing render request fields: "+",".join(missing))
 intent=req["engine_selection_intent"]
 if not isinstance(intent,dict) or intent.get("execution_requested") is not False:raise MotionVideoQualityError("engine selection must remain non-executing intent")
 return sha256_json({f:req[f] for f in fields})
def validate_quality_profile(p):
 fields=("profile_id","motion","temporal","audio","av_sync","layout","color","continuity","perceptual","determinism","delivery")
 if not isinstance(p,dict):raise MotionVideoQualityError("quality profile must be an object")
 missing=[f for f in fields if f not in p]
 if missing:raise MotionVideoQualityError("missing quality profile fields: "+",".join(missing))
 if p.get("universal_thresholds") is not None:raise MotionVideoQualityError("universal fixed quality thresholds are forbidden")
 return deepcopy(p)
def validate_review_binding(producer_identity,reviewer_identity,verifier_identity=None):
 if not producer_identity or not reviewer_identity:raise MotionVideoQualityError("producer and reviewer identities are required")
 if producer_identity==reviewer_identity:raise MotionVideoQualityError("self-review is forbidden")
 if verifier_identity is not None and (not verifier_identity or verifier_identity in {producer_identity,reviewer_identity}):raise MotionVideoQualityError("verifier must be independent from producer and reviewer")
def validate_verification_status(status):
 if status not in ALLOWED_VERIFICATION:raise MotionVideoQualityError("invalid verification status")
 return status
def accept_component_proof(proof):
 if not isinstance(proof,dict) or proof.get("schema")!="fa3.motion-component-proof.v1":raise MotionVideoQualityError("invalid component proof schema")
 if proof.get("component_type") not in ALLOWED_COMPONENT_TYPES:raise MotionVideoQualityError("invalid component type")
 for f in ("source_revision","parameters_digest","proof_frames","motion_proof_artifact","measurement_receipt","review_receipt","output_digest","status"):
  if f not in proof:raise MotionVideoQualityError("missing component proof field: "+f)
 return proof["status"]=="ACCEPTED_FOR_COMPOSITION"
