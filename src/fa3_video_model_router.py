#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
AUTHORITY="FA3-AUTH-MODEL-ROUTER-001"
COST_ORDER={"FREE_LOCAL":0,"FREE_REMOTE":1,"BILLABLE_REMOTE":2}
class VideoRouteDenied(RuntimeError): pass
def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def provider_record(pid:str)->dict[str,Any]:
    p=ROOT/"canonical/providers"/f"{pid}.json"
    if not p.is_file(): raise VideoRouteDenied("canonical provider record missing")
    r=loadj(p)
    if r.get("architectural_authority") is not False or r.get("status") in {"RETIRED_REFERENCE_ONLY","REJECTED","SUPERSEDED"} or r.get("activation_mode") in {"DISABLED_FORBIDDEN","FORBIDDEN"}:
        raise VideoRouteDenied("provider ineligible")
    return r
def admission_ok(m:dict[str,Any],mp:Path)->bool:
    ref=Path(str(m.get("admission_receipt",""))).expanduser()
    if not ref.is_absolute(): ref=(ROOT/ref).resolve()
    exp=str(m.get("admission_receipt_sha256","")).lower()
    if not ref.is_file() or len(exp)!=64 or sha(ref)!=exp: return False
    try:r=loadj(ref)
    except Exception:return False
    return r.get("provider_id")==m.get("provider_id") and (r.get("status") in {"PASS","ADMITTED"} or r.get("result") in {"PASS","ADMITTED"}) and r.get("synthetic_or_mock_provider") is not True
def subset(req:Any,have:Any)->bool:
    return set(req or []).issubset(set(have or []))
def select(request:dict[str,Any],manifest_paths:list[Path])->dict[str,Any]:
    if request.get("schema")!="fa3.motion-video-route-request.v2": raise VideoRouteDenied("route request schema mismatch")
    for forbidden in ("provider_id","provider","model_id","model","api_base","executable"):
        if request.get(forbidden) not in (None,"",False): raise VideoRouteDenied(f"physical routing field forbidden: {forbidden}")
    allow_billable=request.get("allow_billable") is True
    allowed_costs=set(request.get("allowed_cost_classes") or ["FREE_LOCAL","FREE_REMOTE"]+(["BILLABLE_REMOTE"] if allow_billable else []))
    if "BILLABLE_REMOTE" in allowed_costs and not allow_billable: raise VideoRouteDenied("billable route requires explicit permission")
    req=request.get("requirements",{})
    if not isinstance(req,dict): raise VideoRouteDenied("requirements object required")
    eligible=[]
    for mp in manifest_paths:
        m=loadj(mp)
        if m.get("schema")!="fa3.motion-video-execution-manifest.v2" or m.get("status")!="ADMITTED" or m.get("execution_enabled") is not True or not admission_ok(m,mp): continue
        pid=str(m.get("provider_id","")); provider_record(pid)
        if m.get("cost_class") not in allowed_costs or m.get("silent_fallback_allowed") is not False: continue
        snap=m.get("capability_snapshot",{})
        if snap.get("schema")!="fa3.video-capability-snapshot.v2": continue
        checks=[
          subset(req.get("conditioning"),snap.get("conditioning")),
          subset(req.get("generation_modes"),snap.get("generation_modes")),
          subset(req.get("output_modes"),snap.get("output_modes")),
          subset(req.get("temporal_modes"),snap.get("temporal_modes")),
          subset(req.get("execution_topologies"),snap.get("execution_topologies")),
        ]
        if not all(checks): continue
        topology=m.get("execution_topology_class")
        if req.get("execution_topologies") and topology not in set(req["execution_topologies"]): continue
        if not isinstance(m.get("service_provider"),str) or not isinstance(m.get("model_family"),str): continue
        eligible.append((COST_ORDER.get(m.get("cost_class"),99),pid,str(mp),mp,m))
    if not eligible: raise VideoRouteDenied("no admitted motion/video provider satisfies capability requirements")
    eligible.sort(key=lambda x:(x[0],x[1],x[2]))
    _,pid,_,mp,m=eligible[0]
    return {
      "schema":"fa3.motion-video-route-selection-receipt.v2","authority":AUTHORITY,"status":"ROUTED",
      "request_id":request.get("request_id"),"provider_id":pid,"service_provider":m.get("service_provider"),
      "model_family":m.get("model_family"),"model_id":m.get("model_id"),"model_version":m.get("model_version"),
      "capability_snapshot":m.get("capability_snapshot"),"provider_manifest_path":str(mp.resolve()),
      "provider_manifest_sha256":sha(mp),"cost_class":m.get("cost_class"),
      "execution_topology_class":m.get("execution_topology_class"),"candidate_count":len(eligible),
      "selection_policy":"ADMITTED_MULTIDIMENSIONAL_CAPABILITY_COST_TOPOLOGY_DETERMINISTIC",
      "physical_provider_pin_in_application":False,"silent_fallback_allowed":False
    }
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--request",required=True); ap.add_argument("--manifest-list",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    req=loadj(Path(a.request)); lst=loadj(Path(a.manifest_list))
    if lst.get("schema")!="fa3.motion-video-candidate-manifests.v2" or not isinstance(lst.get("manifests"),list): raise SystemExit("candidate manifest list schema mismatch")
    try:r=select(req,[Path(x).expanduser().resolve() for x in lst["manifests"] if isinstance(x,str) and x])
    except Exception as exc: print(json.dumps({"authority":AUTHORITY,"status":"BLOCKED","error":str(exc)},indent=2)); return 2
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8"); print(json.dumps(r,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
