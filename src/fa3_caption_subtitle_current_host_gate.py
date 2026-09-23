#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from fa3_caption_studio_server import Handler
from fa3_caption_uaf import build_native_provider
from fa3_uaf import ActionDispatcher, ActionRegistry, ActionRequest, ExecutionContext, ProviderRegistry

def _post(url: str, path: str, payload: dict) -> dict:
    data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(url+path,data=data,headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))

def gate(root: Path) -> dict:
    root=root.resolve(); cases=[]; findings=[]
    def check(case_id: str, ok: bool, detail: str):
        cases.append({"id":case_id,"result":"PASS" if ok else "FAIL","detail":detail})
        if not ok: findings.append({"code":case_id,"message":detail})
    check("CAPSUB-CH-001", (os.cpu_count() or 0)>0, "generic CPU discovery available")
    check("CAPSUB-CH-002", os.access(root/"bin/fa3-caption-studio",os.X_OK) and os.access(root/"bin/fa3-narration-studio",os.X_OK), "standalone launchers executable")
    Handler.mode="subtitle"
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base=f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(base+"/",timeout=5) as r:
            page=r.read().decode("utf-8")
        check("CAPSUB-CH-003","FA3 Subtitle Studio" in page,"loopback focused GUI served")
        sample="1\n00:00:01,000 --> 00:00:02,500\nCurrent host subtitle.\n"
        parsed=_post(base,"/api/parse",{"format":"srt","language":"en","content":sample})
        check("CAPSUB-CH-004",parsed.get("validation",{}).get("status")=="PASS","loopback parse endpoint")
        qc=_post(base,"/api/qc",{"document":parsed["document"]})
        check("CAPSUB-CH-005",qc.get("schema")=="fa3.caption-quality-evidence.v1","loopback QC endpoint")
        plan=_post(base,"/api/narration-plan",{"document":parsed["document"],"mode":"NARRATION","voice_identity_ref":"FA3-VOICE-DEFAULT"})
        check("CAPSUB-CH-006",plan.get("voice_authority")=="FA3-VOICE-001" and plan.get("provider_selection_owned_by_application") is False,"narration delegates to Voice Fabric")
    except Exception as exc:
        check("CAPSUB-CH-HTTP",False,f"loopback application E2E failed: {exc}")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)

    try:
        registry=ActionRegistry.from_directory(root/"canonical/actions")
        providers=ProviderRegistry(); providers.register(build_native_provider())
        evidence=[]
        dispatcher=ActionDispatcher(registry,providers,authorize=lambda req,contract: True,evidence_sink=evidence.append)
        result=dispatcher.execute(ActionRequest(
            action_id="caption.qc",
            arguments={"document":parsed["document"]},
            principal={"id":"current-host:test"},
            context=ExecutionContext("caption-current-host",application="FA3-SUBTITLE-STUDIO-001"),
        ))
        check("CAPSUB-CH-007",result.status=="PASS" and result.provider_id=="FA3-PROVIDER-CAPTION-NATIVE-001","UAF native provider execution")
        check("CAPSUB-CH-008",bool(evidence),"UAF execution evidence emitted")
    except Exception as exc:
        check("CAPSUB-CH-UAF",False,f"UAF native-provider E2E failed: {exc}")

    result="PASS" if not findings else "FAIL"
    report={
        "schema":"fa3.caption-subtitle-current-host-evidence.v1",
        "gate_id":"FA3-CAPTION-SUBTITLE-CURRENT-HOST-GATESET-001",
        "result":result,
        "evidence_level":"CURRENT_HOST_APPLICATION_E2E_PASS" if result=="PASS" else "CURRENT_HOST_APPLICATION_E2E_FAIL",
        "caption_runtime_executed":True,
        "uaf_native_provider_executed":True if result=="PASS" else False,
        "voice_provider_audio_executed":False,
        "voice_provider_production_admission_separate":True,
        "hardsub_ocr_provider_executed":False,
        "hardsub_ocr_provider_admission_separate":True,
        "hardware_vendor_requirement":None,
        "accelerator_required":False,
        "global_promotion_claim":False,
        "cases":cases,
        "findings":findings,
    }
    out=root/"reports/caption-subtitle-current-host.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=ap.parse_args()
    report=gate(Path(args.root)); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
