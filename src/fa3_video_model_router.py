#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from typing import Any

AUTHORITY="FA3-AUTH-MODEL-ROUTER-001"
ROOT=Path(__file__).resolve().parents[1]
COST_ORDER={"FREE_LOCAL":0,"FREE_REMOTE":1,"BILLABLE_REMOTE":2}
OPERATION_MAP={
 "TEXT_TO_VIDEO":{"TEXT_TO_VIDEO","TEXT_IMAGE_TO_VIDEO"},
 "IMAGE_TO_VIDEO":{"IMAGE_TO_VIDEO","TEXT_IMAGE_TO_VIDEO"},
 "TEXT_IMAGE_TO_VIDEO":{"TEXT_IMAGE_TO_VIDEO"},
 "SPEECH_TO_VIDEO":{"SPEECH_TO_VIDEO"},
 "CHARACTER_ANIMATION":{"CHARACTER_ANIMATION"},
 "CHARACTER_REPLACEMENT":{"CHARACTER_REPLACEMENT"},
}

class VideoRouteDenied(RuntimeError):pass

def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()

def provider_record(provider_id:str)->dict[str,Any]:
 p=ROOT/"canonical/providers"/f"{provider_id}.json"
 if not p.is_file():raise VideoRouteDenied(f"canonical provider record missing: {provider_id}")
 r=loadj(p)
 if r.get("architectural_authority") is not False:raise VideoRouteDenied("provider cannot be architectural authority")
 if r.get("profile")!="FA3-VIDEO-001":raise VideoRouteDenied("provider is outside FA3-VIDEO-001")
 return r

def admission_ok(manifest:dict[str,Any],manifest_path:Path)->bool:
 ref=str(manifest.get("admission_receipt","")).strip();expected=str(manifest.get("admission_receipt_sha256","")).strip().lower()
 if not ref or len(expected)!=64:return False
 p=Path(ref).expanduser()
 if not p.is_absolute():p=(ROOT/p).resolve()
 if not p.is_file() or sha(p)!=expected:return False
 try:r=loadj(p)
 except Exception:return False
 return r.get("provider_id")==manifest.get("provider_id") and (r.get("status") in {"PASS","ADMITTED"} or r.get("result") in {"PASS","ADMITTED"}) and r.get("synthetic_or_mock_provider") is not True

def select(request:dict[str,Any], manifest_paths:list[Path])->dict[str,Any]:
 if request.get("schema")!="fa3.motion-video-route-request.v1":raise VideoRouteDenied("route request schema mismatch")
 for forbidden in ("provider_id","provider","model_id","model","api_base","executable"):
  if request.get(forbidden) not in (None,"",False):raise VideoRouteDenied(f"application physical routing field forbidden: {forbidden}")
 op=str(request.get("operation","")).strip().upper()
 if op not in OPERATION_MAP:raise VideoRouteDenied("unsupported video route operation")
 allow_billable=request.get("allow_billable") is True
 allowed_costs=set(request.get("allowed_cost_classes") or ["FREE_LOCAL","FREE_REMOTE"] + (["BILLABLE_REMOTE"] if allow_billable else []))
 if "BILLABLE_REMOTE" in allowed_costs and not allow_billable:raise VideoRouteDenied("billable cost class requires explicit route permission")
 topologies=set(request.get("allowed_execution_topologies") or ["LOCAL","REMOTE"])
 eligible=[]
 for mp in manifest_paths:
  m=loadj(mp)
  if m.get("schema")!="fa3.motion-video-execution-manifest.v1" or m.get("status")!="ADMITTED":continue
  pid=str(m.get("provider_id",""))
  if not pid or not admission_ok(m,mp):continue
  record=provider_record(pid)
  supported=set(record.get("supported_projection_classes",[]))
  if not (supported & OPERATION_MAP[op]):continue
  if m.get("cost_class") not in allowed_costs:continue
  if m.get("execution_topology") not in topologies:continue
  if m.get("silent_fallback_allowed") is not False:continue
  eligible.append((COST_ORDER.get(str(m.get("cost_class")),99),pid,mp,m))
 if not eligible:raise VideoRouteDenied("no admitted motion/video provider can satisfy route")
 eligible.sort(key=lambda x:(x[0],x[1],str(x[2])))
 _,pid,mp,m=eligible[0]
 return {
  "schema":"fa3.motion-video-route-selection-receipt.v1","authority":AUTHORITY,"status":"ROUTED",
  "request_id":request.get("request_id"),"operation":op,"provider_id":pid,
  "provider_manifest_path":str(mp.resolve()),"provider_manifest_sha256":sha(mp),
  "cost_class":m.get("cost_class"),"execution_topology":m.get("execution_topology"),
  "selection_policy":"ADMITTED_CAPABILITY_COST_TOPOLOGY_DETERMINISTIC",
  "candidate_count":len(eligible),"physical_provider_pin_in_application":False,
  "silent_fallback_allowed":False
 }

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument("--request",required=True);ap.add_argument("--manifest-list",required=True);ap.add_argument("--output",required=True)
 a=ap.parse_args();req=loadj(Path(a.request));lst=loadj(Path(a.manifest_list))
 if lst.get("schema")!="fa3.motion-video-candidate-manifests.v1" or not isinstance(lst.get("manifests"),list):raise SystemExit("candidate manifest list schema mismatch")
 paths=[Path(x).expanduser().resolve() for x in lst["manifests"] if isinstance(x,str) and x]
 try:r=select(req,paths)
 except Exception as exc:
  print(json.dumps({"authority":AUTHORITY,"status":"BLOCKED","error":str(exc)},indent=2));return 2
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
