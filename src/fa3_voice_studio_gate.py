#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
def gate(root:Path)->dict:
    req={"app":root/"canonical/FA3-VOICE-STUDIO-APPLICATION-001.json","runtime":root/"canonical/FA3-VOICE-STUDIO-RUNTIME-CONFORMANCE-001.json","workspace":root/"src/fa3_voice_workspace.py","server":root/"src/fa3_voice_studio_server.py","piper":root/"src/fa3_piper_provider.py","client_h":root/"apps/fa3-control-center/src/VoiceWorkspaceService.h","client_cpp":root/"apps/fa3-control-center/src/VoiceWorkspaceService.cpp","voice_qml":root/"apps/fa3-control-center/qml/VoiceStudioPage.qml","quick_qml":root/"apps/fa3-control-center/qml/QuickVoicePluginPage.qml","launcher":root/"bin/fa3-voice-studio"}
    findings=[]; missing=[str(p.relative_to(root)) for p in req.values() if not p.is_file()]
    if missing: findings.append({"code":"VOICEAPP-001","message":"missing files","missing":missing})
    if not missing:
      app=json.loads(req["app"].read_text()); rt=json.loads(req["runtime"].read_text())
      def chk(ok,code,msg):
        if not ok: findings.append({"code":code,"message":msg})
      chk(app.get("capability_count")==175 and app.get("new_capabilities")==0,"VOICEAPP-002","capability baseline drift")
      chk(app.get("new_architectural_authorities")==0,"VOICEAPP-003","new authority forbidden")
      chk(app.get("authority_boundaries",{}).get("voice")=="FA3-VOICE-001","VOICEAPP-004","voice authority drift")
      chk(app.get("authority_boundaries",{}).get("provider_routing")=="FA3-AUTH-MODEL-ROUTER-001","VOICEAPP-005","router authority drift")
      chk(app.get("runtime",{}).get("bind")=="127.0.0.1:18796" and app.get("runtime",{}).get("network_fetch") is False,"VOICEAPP-006","loopback/network boundary drift")
      chk(rt.get("production_admitted") is False and rt.get("current_host_receipt_present") is False,"VOICEAPP-007","unearned runtime PASS")
      w=req["workspace"].read_text(); s=req["server"].read_text(); p=req["piper"].read_text(); cpp=req["client_cpp"].read_text(); v=req["voice_qml"].read_text(); q=req["quick_qml"].read_text()
      chk("sqlite3" in w and "fit_to_clip" in w and "quick_dub_plan" in w and "timeline_handoff" in w and "effects_plan" in w and "transcribe" in w and "transform_preflight" in w,"VOICEAPP-008","workspace workflow missing")
      chk("127.0.0.1" in s and "Authorization" in s and "voice-studio.token" in s,"VOICEAPP-009","authenticated loopback server missing")
      chk('req.get("device","cpu")!="cpu"' in p and "FA3_PIPER_MODEL_ROOT" in p,"VOICEAPP-010","Piper CPU/model boundary missing")
      chk("QNetworkAccessManager" in cpp and "Authorization" in cpp and "/api/generate" in cpp and "/api/transcribe" in cpp and "/api/effects/plan" in cpp,"VOICEAPP-011","GUI live client missing")
      chk("License & Rights evidence ref" in v and "License & Rights evidence ref" in q and "FA3-VOICE-WORKSPACE-USER-AUTHORIZED" not in cpp,"VOICEAPP-017","fabricated or missing rights evidence boundary")
      chk("Model Router selection receipt required" in w and "FA3-AUTH-MODEL-ROUTER-001" in w and "silent fallback receipt forbidden" in w,"VOICEAPP-018","Model Router selection receipt boundary missing")
      chk("fa3VoiceWorkspace.generate" in v and "fa3VoiceWorkspace.transcribe" in v and "fa3VoiceWorkspace.planEffects" in v and "fa3VoiceWorkspace.generate" in q and "fa3VoiceWorkspace.quickDub" in q,"VOICEAPP-012","QML action binding missing")
      chk(app.get("runtime",{}).get("workflow_authority")=="TEMPORAL" and app.get("runtime",{}).get("local_sqlite_role")=="NON_AUTHORITATIVE_JOB_LEDGER_AND_PROFILE_CACHE","VOICEAPP-014","Temporal workflow authority drift")
      chk(app.get("mcp_projection",{}).get("gateway")=="FA3-AUTH-MCP-GATEWAY-001" and app.get("mcp_projection",{}).get("direct_mcp_server") is False,"VOICEAPP-015","MCP gateway boundary drift")
      chk({"voice.speak","voice.transcribe","voice.transform.preflight","voice.effects.plan","voice.profile.put","voice.fit-to-clip","voice.quick-dub.plan"}.issubset(set(app.get("uaf_actions",[]))),"VOICEAPP-016","UAF voice action inventory incomplete")
      chk("Allow candidate CPU provider" in v and "checked: false" in v and "Allow candidate CPU provider" in q and "checked: false" in q,"VOICEAPP-013","explicit candidate acknowledgement UI missing")
    return {"schema":"fa3.voice-studio-application-gate.v1","result":"PASS" if not findings else "FAIL","findings":findings}
if __name__=="__main__":
 import argparse; ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));a=ap.parse_args();r=gate(Path(a.root));print(json.dumps(r,indent=2));raise SystemExit(0 if r["result"]=="PASS" else 2)
