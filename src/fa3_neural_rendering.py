#!/usr/bin/env python3
"""FA3 provider-neutral neural-rendering selection and execution preflight.

Jev is optional advisory input only. Deterministic policy receives an already
bounded candidate set and remains authoritative for eligibility. This module
does not discover hardware, lease devices, authorize actions, route models, or
execute providers directly.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field
from typing import Any, Callable

DECISION_SCHEMA="fa3.neural-rendering-decision-receipt.v1"
CONTEXT_SCHEMA="fa3.neural-rendering-context-envelope.v1"
MAX_CANDIDATES=32
MAX_CONTEXT_ITEMS=32
EXECUTION_CLASSES={"CPU_SOFTWARE","HOST_NATIVE_ACCELERATED","BROWSER_WEBGPU"}
FEATURE_CLASSES={"NEURAL_RENDER","SUPER_RESOLUTION","NATIVE_RESOLUTION_AA","RAY_RECONSTRUCTION","DENOISE","TEMPORAL_RECONSTRUCTION","FRAME_GENERATION","LOW_LATENCY_PRESENTATION"}
TEMPORAL_FEATURES={"NEURAL_RENDER","SUPER_RESOLUTION","NATIVE_RESOLUTION_AA","RAY_RECONSTRUCTION","DENOISE","TEMPORAL_RECONSTRUCTION","FRAME_GENERATION"}
FRAME_GENERATION_FORBIDDEN_OUTPUTS={"FINAL_MASTER","ARCHIVAL_MASTER","EXR_SEQUENCE","VFX_HANDOFF"}

class NeuralRenderingError(ValueError):
    def __init__(self,code:str,message:str):
        super().__init__(message); self.code=code

@dataclass(frozen=True)
class SelectionRequest:
    operation_id:str
    candidates:tuple[dict[str,Any],...]
    context:tuple[dict[str,Any],...]=()
    requested_provider_id:str|None=None
    requested_execution_class:str|None=None
    feature_class:str="NEURAL_RENDER"
    signals:dict[str,Any]=field(default_factory=dict)

def _digest(value:Any)->str:
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def _id(item:dict[str,Any])->str:
    value=str(item.get("id","")).strip()
    if not value: raise NeuralRenderingError("NR-CANDIDATE-INVALID","candidate id is required")
    return value

def _bounded(items:tuple[dict[str,Any],...],label:str,maximum:int)->list[dict[str,Any]]:
    if not items: raise NeuralRenderingError("NR-CANDIDATE-SET-EMPTY",f"{label} must be non-empty")
    if len(items)>maximum: raise NeuralRenderingError("NR-CANDIDATE-SET-UNBOUNDED",f"{label} exceeds {maximum}")
    result=[]; seen=set()
    for raw in items:
        if not isinstance(raw,dict): raise NeuralRenderingError("NR-CANDIDATE-INVALID",f"{label} entries must be objects")
        item=dict(raw); ident=_id(item)
        if ident in seen: raise NeuralRenderingError("NR-CANDIDATE-DUPLICATE",ident)
        seen.add(ident); result.append(item)
    return result

def _eligible(item:dict[str,Any],request:SelectionRequest)->tuple[bool,str]:
    if request.requested_provider_id and _id(item)!=request.requested_provider_id:
        return False,"not-explicitly-requested-provider"
    execution_class=str(item.get("execution_class","")).strip()
    if execution_class not in EXECUTION_CLASSES: return False,"unsupported-execution-class"
    if request.requested_execution_class and execution_class!=request.requested_execution_class:
        return False,"not-requested-execution-class"
    supported=item.get("feature_classes")
    if isinstance(supported,(list,tuple,set)) and request.feature_class not in supported:
        return False,"feature-class-unsupported"
    for field_name,reason in (
        ("policy_eligible","policy-ineligible"),("provider_admitted","provider-not-admitted"),
        ("model_artifact_admitted","model-artifact-not-admitted"),("runtime_compatible","runtime-incompatible"),
        ("hardware_compatible","hardware-incompatible"),("supply_chain_valid","supply-chain-invalid"),
    ):
        if item.get(field_name) is not True: return False,reason
    return True,"policy-eligible"

def _rank_key(item:dict[str,Any])->tuple[int,float,str]:
    preferred=1 if item.get("preferred") is True else 0
    priority=item.get("priority",0)
    if isinstance(priority,bool) or not isinstance(priority,(int,float)):
        raise NeuralRenderingError("NR-CANDIDATE-INVALID","priority must be numeric")
    return (-preferred,-float(priority),_id(item))

def _context_envelope(context:tuple[dict[str,Any],...])->dict[str,Any]:
    if not context:
        envelope={"schema":CONTEXT_SCHEMA,"selected":[],"rejected":[]}; envelope["digest"]=_digest(envelope); return envelope
    items=_bounded(context,"context",MAX_CANDIDATES); ordered=sorted(items,key=_rank_key)
    selected=[{"ref":_id(item),"reason":"bounded-context"} for item in ordered[:MAX_CONTEXT_ITEMS]]
    rejected=[{"ref":_id(item),"reason":"context-budget"} for item in ordered[MAX_CONTEXT_ITEMS:]]
    envelope={"schema":CONTEXT_SCHEMA,"selected":selected,"rejected":rejected}; envelope["digest"]=_digest(envelope); return envelope

def validate_frame_surface(surface:dict[str,Any],*,feature_class:str,output_class:str="INTERACTIVE_PREVIEW")->dict[str,Any]:
    if feature_class not in FEATURE_CLASSES:
        raise NeuralRenderingError("NR-FEATURE-CLASS-INVALID",feature_class)
    if feature_class=="FRAME_GENERATION" and output_class in FRAME_GENERATION_FORBIDDEN_OUTPUTS:
        raise NeuralRenderingError("NR-FRAME-GENERATION-FINAL-FORBIDDEN",output_class)
    required={"frame_id","width","height","color_space","timecode","source_artifact_ref","provenance_ref"}
    if feature_class in TEMPORAL_FEATURES:
        required.update({"motion_vectors_ref","depth_ref","temporal_history_ref","camera_ref","jitter"})
    if feature_class=="RAY_RECONSTRUCTION":
        required.add("normal_ref")
    missing=sorted(k for k in required if surface.get(k) in (None,""))
    if missing:
        raise NeuralRenderingError("NR-FRAME-SURFACE-INCOMPLETE",",".join(missing))
    for dim in ("width","height"):
        value=surface.get(dim)
        if isinstance(value,bool) or not isinstance(value,int) or value<=0:
            raise NeuralRenderingError("NR-FRAME-SURFACE-DIMENSION",dim)
    if feature_class=="SUPER_RESOLUTION":
        for dim in ("target_width","target_height"):
            value=surface.get(dim)
            if isinstance(value,bool) or not isinstance(value,int) or value<=0:
                raise NeuralRenderingError("NR-TARGET-DIMENSION-MISSING",dim)
    receipt={
        "schema":"fa3.neural-frame-surface-receipt.v1",
        "feature_class":feature_class,
        "output_class":output_class,
        "source_artifact_ref":surface["source_artifact_ref"],
        "provenance_ref":surface["provenance_ref"],
        "canonical_timeline_mutated":False,
        "generated_presentation_frames_canonical":False,
        "status":"VALIDATED",
    }
    receipt["digest"]=_digest(receipt)
    return receipt

def validate_output_policy(*,feature_class:str,output_class:str)->dict[str,Any]:
    if feature_class not in FEATURE_CLASSES:
        raise NeuralRenderingError("NR-FEATURE-CLASS-INVALID",feature_class)
    if feature_class=="FRAME_GENERATION" and output_class in FRAME_GENERATION_FORBIDDEN_OUTPUTS:
        raise NeuralRenderingError("NR-FRAME-GENERATION-FINAL-FORBIDDEN",output_class)
    return {
        "schema":"fa3.neural-output-policy-receipt.v1",
        "feature_class":feature_class,
        "output_class":output_class,
        "canonical_timeline_preserved":True,
        "frame_generation_preview_only":feature_class=="FRAME_GENERATION",
        "status":"ALLOWED",
    }

def select_provider(request:SelectionRequest,advisory:Callable[[tuple[str,...],dict[str,Any]],list[str]]|None=None)->dict[str,Any]:
    if not request.operation_id.strip(): raise NeuralRenderingError("NR-REQUEST-INVALID","operation_id is required")
    if request.feature_class not in FEATURE_CLASSES: raise NeuralRenderingError("NR-FEATURE-CLASS-INVALID",request.feature_class)
    candidates=_bounded(request.candidates,"candidates",MAX_CANDIDATES); eligible=[]; rejected=[]
    for candidate in candidates:
        ok,reason=_eligible(candidate,request)
        if ok: eligible.append(candidate)
        else: rejected.append({"id":_id(candidate),"reason":reason})
    eligible.sort(key=_rank_key); implementation="deterministic-policy-selection"; advisory_error=None
    if advisory is not None and eligible:
        allowed=tuple(_id(item) for item in eligible)
        try:
            proposed=advisory(allowed,dict(request.signals))
            if not isinstance(proposed,list) or len(proposed)!=len(allowed) or len(set(proposed))!=len(proposed) or set(proposed)!=set(allowed):
                raise NeuralRenderingError("NR-ADVISORY-EXPANSION","advisory result must be an exact permutation of eligible candidates")
            by_id={_id(item):item for item in eligible}; eligible=[by_id[item_id] for item_id in proposed]
            implementation="optional-jev-advisory-rerank-after-deterministic-policy"
        except NeuralRenderingError: raise
        except Exception as exc:
            advisory_error=type(exc).__name__; implementation="deterministic-selection-after-optional-advisory-error"
    selected=eligible[0] if eligible else None; outcome="CONTINUE" if selected else "STOP_BLOCKED"
    reason="policy-eligible-candidate-selected" if selected else "no-policy-eligible-candidate"
    receipt={
        "schema":DECISION_SCHEMA,"operation_id":request.operation_id,
        "input_digest":_digest({"candidates":candidates,"context":request.context,"requested_provider_id":request.requested_provider_id,"requested_execution_class":request.requested_execution_class,"feature_class":request.feature_class,"signals":request.signals}),
        "candidate_ids":[_id(i) for i in candidates],"eligible_ranked_ids":[_id(i) for i in eligible],"feature_class":request.feature_class,
        "selected_ids":[_id(selected)] if selected else [],"selected_execution_class":selected.get("execution_class") if selected else None,
        "rejected":rejected,"outcome":outcome,"reason":reason,"human_readable_reason":reason.replace("-"," "),
        "implementation":implementation,"advisory_provider_is_authority":False,"candidate_expansion":False,
        "execution_authorized_by_decision":False,"context_envelope":_context_envelope(request.context),
        "project_radar":{"status":outcome,"provenance_refs":list(request.signals.get("provenance_refs",[])),"evidence_refs":list(request.signals.get("evidence_refs",[]))}
    }
    if advisory_error: receipt["advisory_error"]=advisory_error
    receipt["receipt_digest"]=_digest(receipt); return receipt

def validate_execution_preflight(*,selected_provider_id:str,executed_provider_id:str,execution_class:str,model_artifact_ref:str,supply_chain_receipt_ref:str,evidence_context_ref:str,hrb_lease_ref:str|None=None,web_ai_capability_receipt_ref:str|None=None,model_router_receipt_ref:str|None=None,feature_class:str="NEURAL_RENDER",output_class:str="INTERACTIVE_PREVIEW",frame_surface:dict[str,Any]|None=None)->dict[str,Any]:
    if not selected_provider_id or selected_provider_id!=executed_provider_id:
        raise NeuralRenderingError("NR-PROVIDER-MISMATCH","selected and executed provider must match")
    if execution_class not in EXECUTION_CLASSES: raise NeuralRenderingError("NR-EXECUTION-CLASS-INVALID",execution_class)
    validate_output_policy(feature_class=feature_class,output_class=output_class)
    surface_receipt=validate_frame_surface(frame_surface,feature_class=feature_class,output_class=output_class) if frame_surface is not None else None
    for value,code in ((model_artifact_ref,"NR-MODEL-ADMISSION-MISSING"),(supply_chain_receipt_ref,"NR-SUPPLY-CHAIN-MISSING"),(evidence_context_ref,"NR-EVIDENCE-CONTEXT-MISSING")):
        if not str(value).strip(): raise NeuralRenderingError(code,"required opaque receipt reference missing")
    if execution_class in {"CPU_SOFTWARE","HOST_NATIVE_ACCELERATED"} and not str(hrb_lease_ref or "").strip():
        raise NeuralRenderingError("NR-HRB-LEASE-MISSING","host execution requires an HRB lease")
    if execution_class=="CPU_SOFTWARE" and not str(model_router_receipt_ref or "").strip():
        raise NeuralRenderingError("NR-MODEL-ROUTER-RECEIPT-MISSING","CPU neural execution requires an explicit Model Router receipt")
    if execution_class=="BROWSER_WEBGPU" and not str(web_ai_capability_receipt_ref or "").strip():
        raise NeuralRenderingError("NR-WEB-AI-RECEIPT-MISSING","browser execution requires a Web-AI capability receipt")
    result={"schema":"fa3.neural-rendering-execution-preflight.v2","provider_id":executed_provider_id,"execution_class":execution_class,
            "feature_class":feature_class,"output_class":output_class,
            "model_artifact_ref":model_artifact_ref,"supply_chain_receipt_ref":supply_chain_receipt_ref,
            "evidence_context_ref":evidence_context_ref,"hrb_lease_ref":hrb_lease_ref,
            "web_ai_capability_receipt_ref":web_ai_capability_receipt_ref,"model_router_receipt_ref":model_router_receipt_ref,
            "frame_surface_receipt":surface_receipt,"provider_substitution_allowed":False,
            "silent_fallback_allowed":False,"canonical_timeline_mutation_allowed":False,
            "status":"READY_FOR_GOVERNED_PROVIDER_ADAPTER"}
    result["digest"]=_digest(result); return result
