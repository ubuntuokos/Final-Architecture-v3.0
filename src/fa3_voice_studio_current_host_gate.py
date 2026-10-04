#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,tempfile,threading,urllib.request
from pathlib import Path
from fa3_voice_studio_server import Handler,ThreadingHTTPServer
from fa3_voice_workspace import VoiceWorkspace
def run(root:Path)->dict:
    checks=[]
    def chk(i,ok,d): checks.append({"id":i,"result":"PASS" if ok else "FAIL","detail":d})
    with tempfile.TemporaryDirectory() as td:
      ws=VoiceWorkspace(root,Path(td)); Handler.workspace=ws; Handler.token="current-host-test-token"
      server=ThreadingHTTPServer(("127.0.0.1",0),Handler); th=threading.Thread(target=server.serve_forever,daemon=True);th.start();base="http://127.0.0.1:"+str(server.server_address[1])
      try:
        with urllib.request.urlopen(base+"/healthz",timeout=5) as r: h=json.load(r)
        chk("VOICEAPP-CH-001",h.get("status")=="ok","loopback health")
        req=urllib.request.Request(base+"/api/fit-to-clip",data=json.dumps({"target_ms":1000,"actual_ms":1100}).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer current-host-test-token"},method="POST")
        with urllib.request.urlopen(req,timeout=5) as r: fit=json.load(r)
        chk("VOICEAPP-CH-002",fit.get("decision")=="BOUNDED_RATE_ADJUSTMENT" and fit.get("text_rewrite") is False,"fit-to-clip")
        req=urllib.request.Request(base+"/api/quick-dub",data=json.dumps({"source_media_ref":"CURRENT_HOST_TEST","source_language":"en","target_language":"hu-HU"}).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer current-host-test-token"},method="POST")
        with urllib.request.urlopen(req,timeout=5) as r: dub=json.load(r)
        chk("VOICEAPP-CH-003",dub.get("provider_selection_owned_by_application") is False and "FA3-VOICE-001" in dub.get("stages",[]),"quick dub delegation")
      finally:
        server.shutdown();server.server_close();ws.close()
    passed=sum(x["result"]=="PASS" for x in checks)
    return {"schema":"fa3.voice-studio-current-host-report.v1","result":"PASS" if passed==len(checks) else "FAIL","passed":passed,"total":len(checks),"cases":checks,"provider_audio_execution":"SEPARATE_PROVIDER_SPECIFIC_CURRENT_HOST_EVIDENCE","production_promotion_claim":False}
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));a=ap.parse_args();r=run(Path(a.root));print(json.dumps(r,indent=2));raise SystemExit(0 if r["result"]=="PASS" else 2)
