#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, platform, socket, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_whisper_stt_provider import RuntimeOptions, execute_transcription, sha256_file

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(description="FA3 Whisper STT current-host evidence collector")
    ap.add_argument("--request",required=True)
    ap.add_argument("--model",default="turbo")
    ap.add_argument("--device",default="cpu")
    ap.add_argument("--model-cache")
    ap.add_argument("--allow-network-model-fetch",action="store_true")
    ap.add_argument("--hrb-lease")
    ap.add_argument("--hrb-verifier-bin",default="/usr/local/bin/fa3-host-resource-broker")
    ap.add_argument("--output",default=str(ROOT/"evidence/receipts/whisper-stt-current-host.json"))
    args=ap.parse_args()

    if os.environ.get("GITHUB_ACTIONS","").lower()=="true":
        raise SystemExit("CURRENT_HOST evidence is forbidden on GitHub-hosted CI")

    request_path=Path(args.request).expanduser().resolve()
    request=json.loads(request_path.read_text(encoding="utf-8"))
    result_path=Path(args.output).expanduser().resolve().with_name("whisper-stt-provider-result.json")
    opts=RuntimeOptions(
        model=args.model,device=args.device,offline=not args.allow_network_model_fetch,
        model_cache=args.model_cache,word_timestamps=True,hrb_lease_path=args.hrb_lease,
        hrb_verify_command=(args.hrb_verifier_bin,"validate-lease","{lease}"),
    )
    result=execute_transcription(ROOT,request,opts)
    write(result_path,result)
    if not result.get("segments"):
        raise SystemExit("Provider returned PASS without speech segments")

    gpu=None
    if args.device.startswith("cuda:"):
        try:
            gpu=subprocess.run(
                ["nvidia-smi","--query-gpu=index,uuid,name,driver_version","--format=csv,noheader"],
                check=False,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,
            ).stdout.strip()
        except Exception:
            gpu=None

    receipt={
        "schema":"fa3.whisper-stt-current-host-evidence.v1",
        "status":"CURRENT_HOST_WHISPER_STT_E2E_PASS",
        "provider_id":"FA3-PROVIDER-WHISPER-001",
        "profile_id":"FA3-STT-MEDIA-001",
        "collected_at":now(),
        "current_host":True,
        "ci":False,
        "host":{
            "hostname":socket.gethostname(),
            "platform":platform.platform(),
            "python":platform.python_version(),
            "gpu_inventory":gpu,
        },
        "request_path":str(request_path),
        "request_sha256":sha256_file(request_path),
        "audio_hash":request.get("audio_hash"),
        "model":args.model,
        "device":args.device,
        "provider_result_path":str(result_path),
        "provider_result_sha256":sha256_file(result_path),
        "segment_count":len(result["segments"]),
        "detected_language":result.get("language"),
        "device_lease":result.get("execution_evidence",{}).get("device_lease"),
        "model_artifact_sha256":result.get("execution_evidence",{}).get("model_artifact_sha256"),
    }
    write(Path(args.output).expanduser().resolve(),receipt)
    print(json.dumps(receipt,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
