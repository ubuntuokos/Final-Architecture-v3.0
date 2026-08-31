#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, platform, socket, sys, wave
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_cosyvoice_provider import PROVIDER_ID, PROFILE_ID, execute_synthesis, sha256_file

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def write(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(description="FA3 CosyVoice real current-host production E2E collector")
    ap.add_argument("--request",required=True)
    ap.add_argument("--cosyvoice-repo",required=True)
    ap.add_argument("--model-dir",required=True)
    ap.add_argument("--device",default="cpu")
    ap.add_argument("--hrb-lease")
    ap.add_argument("--output",default=str(ROOT/"evidence/receipts/cosyvoice-current-host.json"))
    args=ap.parse_args()

    if os.environ.get("GITHUB_ACTIONS","").lower()=="true" and os.environ.get("FA3_CURRENT_HOST_RUNNER")!="1":
        raise SystemExit("CURRENT_HOST evidence is forbidden on non-designated GitHub runners")

    req_path=Path(args.request).expanduser().resolve()
    req=json.loads(req_path.read_text(encoding="utf-8"))
    runtime_dir=ROOT/"evidence/runtime/cosyvoice-current-host"
    audio=runtime_dir/"cosyvoice-output.wav"
    result=execute_synthesis(
        ROOT,req,
        Path(args.cosyvoice_repo).expanduser().resolve(),
        Path(args.model_dir).expanduser().resolve(),
        audio,args.device,args.hrb_lease
    )
    result_path=runtime_dir/"provider-result.json"
    write(result_path,result)

    with wave.open(str(audio),"rb") as w:
        sample_rate=w.getframerate(); channels=w.getnchannels(); frames=w.getnframes()
    if sample_rate!=24000 or channels!=1 or frames<=0:
        raise SystemExit("current-host output WAV failed canonical audio contract")

    receipt={
        "schema":"fa3.cosyvoice-current-host-evidence.v1",
        "status":"CURRENT_HOST_COSYVOICE_E2E_PASS",
        "provider_id":PROVIDER_ID,
        "profile_id":PROFILE_ID,
        "collected_at":now(),
        "current_host":True,
        "production_e2e":True,
        "host":{"hostname":socket.gethostname(),"platform":platform.platform(),"python":platform.python_version()},
        "request_path":str(req_path),
        "request_sha256":sha256_file(req_path),
        "voice_identity_ref":req["voice_identity_ref"],
        "consent_provenance_ref":req["consent_proof"]["provenance_ref"],
        "language":req["language"],
        "language_promotion_status":result["language_promotion_status"],
        "device":args.device,
        "output_audio_path":str(audio.resolve()),
        "output_audio_sha256":sha256_file(audio),
        "sample_rate_hz":sample_rate,
        "channels":channels,
        "frame_count":frames,
        "provider_result_path":str(result_path.resolve()),
        "provider_result_sha256":sha256_file(result_path),
        "execution_evidence":result["execution_evidence"]
    }
    write(Path(args.output).expanduser().resolve(),receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
