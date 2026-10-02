#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROUTER="FA3-AUTH-MODEL-ROUTER-001"
HRB="FA3-AUTH-HOST-RESOURCE-BROKER-001"
MODES={"ONE_STEP_DISTILLED","MULTI_STEP_REFERENCE"}
QUALITY={"REFERENCE","OPTIMIZED","APPROXIMATE"}
BACKENDS={"CPU_REFERENCE","CUDA_OPTIONAL","ROCM_HIP_OPTIONAL","INTEL_XPU_OPTIONAL","REMOTE_OPTIONAL"}

class RefinementDenied(RuntimeError): pass

def _pos_int(v:Any)->bool: return isinstance(v,int) and not isinstance(v,bool) and v>0
def _resolution(obj:dict[str,Any], key:str)->tuple[int,int]:
    r=obj.get(key)
    if not isinstance(r,dict) or not _pos_int(r.get("width")) or not _pos_int(r.get("height")):
        raise RefinementDenied(f"{key} invalid")
    return r["width"],r["height"]

def build_plan(request:dict[str,Any], generator_receipt:dict[str,Any], selection:dict[str,Any], manifest:dict[str,Any])->dict[str,Any]:
    if request.get("schema")!="fa3.video-refinement-request.v1": raise RefinementDenied("request schema mismatch")
    if generator_receipt.get("schema")!="fa3.motion-video-execution-receipt.v2" or generator_receipt.get("status")!="PASS":
        raise RefinementDenied("generator receipt required")
    if selection.get("schema")!="fa3.video-refinement-selection-receipt.v1" or selection.get("authority")!=ROUTER or selection.get("status")!="ROUTED":
        raise RefinementDenied("Model Router refinement selection required")
    if manifest.get("schema")!="fa3.video-refiner-manifest.v1" or manifest.get("status")!="ADMITTED" or manifest.get("execution_enabled") is not True:
        raise RefinementDenied("explicitly admitted and enabled refiner manifest required")
    if manifest.get("provider_id")!=selection.get("provider_id") or manifest.get("refiner_id")!=selection.get("refiner_id"):
        raise RefinementDenied("refiner identity mismatch")
    if manifest.get("silent_fallback_allowed") is not False: raise RefinementDenied("silent fallback forbidden")
    mode=request.get("refinement_mode"); quality=request.get("quality_mode"); backend=manifest.get("backend_class")
    if mode not in MODES or quality not in QUALITY or backend not in BACKENDS: raise RefinementDenied("unsupported refinement mode")
    dw,dh=_resolution(request,"draft_resolution"); tw,th=_resolution(request,"target_resolution")
    if tw<dw or th<dh: raise RefinementDenied("target resolution cannot be lower than draft")
    if not request.get("draft_artifact_sha256") or len(str(request["draft_artifact_sha256"]))!=64:
        raise RefinementDenied("draft artifact hash required")
    if quality=="APPROXIMATE" and request.get("approximate_quality_disclosure_ack") is not True:
        raise RefinementDenied("approximate mode requires visible quality disclosure acknowledgement")
    local=backend!="REMOTE_OPTIONAL"
    if local and backend!="CPU_REFERENCE" and manifest.get("resource_authority")!=HRB:
        raise RefinementDenied("accelerated local refinement requires HRB authority")
    if manifest.get("model_router_authority")!=ROUTER: raise RefinementDenied("router authority mismatch")
    return {
      "schema":"fa3.video-refinement-execution-plan.v1","status":"READY",
      "generator_receipt_id":generator_receipt.get("receipt_id"),
      "generator_provider_id":generator_receipt.get("provider_id"),
      "refiner_provider_id":manifest.get("provider_id"),"refiner_id":manifest.get("refiner_id"),
      "refinement_mode":mode,"quality_mode":quality,"backend_class":backend,
      "draft_resolution":{"width":dw,"height":dh},"target_resolution":{"width":tw,"height":th},
      "draft_artifact_sha256":request["draft_artifact_sha256"],
      "model_router_authority":ROUTER,"resource_authority":HRB if local else None,
      "silent_fallback_allowed":False,"lineage_required":True,
      "current_host_runtime_promotion_claim":False
    }

def main()->int:
    import argparse
    ap=argparse.ArgumentParser()
    for n in ("request","generator-receipt","selection","manifest","output"): ap.add_argument("--"+n,required=True)
    a=ap.parse_args()
    try:
      vals=[json.loads(Path(getattr(a,n.replace("-","_"))).read_text()) for n in ("request","generator-receipt","selection","manifest")]
      plan=build_plan(*vals)
    except Exception as exc:
      print(json.dumps({"status":"BLOCKED","error":str(exc)},indent=2)); return 2
    Path(a.output).write_text(json.dumps(plan,indent=2)+"\n"); print(json.dumps(plan,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
