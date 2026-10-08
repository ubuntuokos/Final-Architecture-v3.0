#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
AUTHORITY="FA3-AUTH-MODEL-ROUTER-001"
class VoiceRouteDenied(RuntimeError): pass
def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def route_voice_request(root:Path,request:dict[str,Any],available_provider_ids:set[str])->dict[str,Any]:
    admission=loadj(root/"canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json")
    quality=loadj(root/"canonical/FA3-VOICE-QUALITY-ROUTING-001.json")
    language=str(request.get("language","")).replace("_","-")
    if language=="hu": language="hu-HU"
    if language!="hu-HU": raise VoiceRouteDenied("voice route extension currently materializes hu-HU only")
    mode=str(request.get("mode") or "plain")
    route_key="voice_clone" if mode in {"voice_clone","zero_shot","cross_lingual","instruct2"} else "plain_or_preset_tts"
    requested_quality=str(request.get("quality_class") or ("PREMIUM_CLONING" if route_key=="voice_clone" else "STANDARD"))
    if requested_quality not in quality.get("quality_classes",{}): raise VoiceRouteDenied("unknown quality class")
    route_candidates=list(admission.get("routing",{}).get("hu-HU",{}).get(route_key,[]))
    quality_map=quality.get("provider_quality_eligibility",{})
    eligible=[]
    for pid in route_candidates:
        if pid not in available_provider_ids or requested_quality not in quality_map.get(pid,[]): continue
        row=admission.get("providers",{}).get(pid,{})
        production=str(row.get("production_status",""))
        if production in {"ADMITTED","PRODUCTION_ADMITTED","CURRENT_HOST_PRODUCTION_E2E_PASS"}:
            eligible.append((0,pid,True))
        elif request.get("candidate_execution_ack") is True:
            eligible.append((1,pid,False))
    if not eligible: raise VoiceRouteDenied("no Model Router eligible voice provider")
    eligible.sort(key=lambda x:(x[0],route_candidates.index(x[1])))
    _,pid,production=eligible[0]
    if not production and request.get("candidate_execution_ack") is not True: raise VoiceRouteDenied("candidate provider requires explicit acknowledgement")
    return {
      "schema":"fa3.voice-model-router-selection.v1",
      "authority":AUTHORITY,
      "result":"PASS",
      "status":"PRODUCTION_ROUTE" if production else "CANDIDATE_ROUTE",
      "request_id":request.get("request_id"),
      "selected_provider_id":pid,
      "language":language,
      "quality_class":requested_quality,
      "provider_selection_owned_by_application":False,
      "production_provider_admitted":production,
      "candidate_execution_ack":bool(request.get("candidate_execution_ack")),
      "silent_fallback":False
    }
