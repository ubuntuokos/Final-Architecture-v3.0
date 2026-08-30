#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_blackhole_kdenlive import (
    PreparationRequest,
    run_pipeline,
    sha256_file,
)

PROFILE_ID="FA3-BLACKHOLE-KDENLIVE-001"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def write_json(path: Path,obj: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def command_version(command: str) -> str | None:
    resolved=shutil.which(command)
    if not resolved:
        return None
    try:
        out=subprocess.run([resolved,"-version"],check=False,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
    except Exception:
        return None
    line=out.stdout.splitlines()[0] if out.stdout else ""
    return line[:300]

def main() -> int:
    ap=argparse.ArgumentParser(description="Collect FA3 Blackhole/Kdenlive current-host integration evidence")
    ap.add_argument("--request",required=True,help="Blackhole/Kdenlive preparation/pipeline request JSON")
    ap.add_argument("--receipt",default=str(ROOT/"evidence/receipts/blackhole-kdenlive-current-host.json"))
    args=ap.parse_args()

    request_path=Path(args.request).expanduser().resolve()
    request=PreparationRequest.from_dict(json.loads(request_path.read_text(encoding="utf-8")))
    input_path=Path(request.input_media).expanduser().resolve()
    if not input_path.is_file():
        raise SystemExit("input media missing")

    pipeline=run_pipeline(ROOT,request)
    full_e2e=pipeline.get("status")=="PASS" and pipeline.get("subtitle_import") is not None
    level="CURRENT_HOST_KDENLIVE_BLACKHOLE_E2E_PASS" if full_e2e else "CURRENT_HOST_MEDIA_PREP_PASS"
    receipt={
        "schema":"fa3.blackhole-kdenlive-current-host-evidence.v1",
        "status":"PASS",
        "profile_id":PROFILE_ID,
        "evidence_level":level,
        "collected_at":utc_now(),
        "host":{
            "node":platform.node(),
            "platform":platform.platform(),
            "python":sys.version.split()[0],
            "ffmpeg":command_version(request.ffmpeg_bin),
        },
        "request":{
            "path":str(request_path),
            "sha256":sha256_file(request_path),
            "preprocessing":request.preprocessing,
            "zone_start_seconds":request.zone_start_seconds,
            "zone_end_seconds":request.zone_end_seconds,
            "stt_provider_command_supplied":bool(request.stt_command),
        },
        "source_media":{
            "path":str(input_path),
            "sha256":sha256_file(input_path),
            "size_bytes":input_path.stat().st_size,
        },
        "pipeline":pipeline,
        "claims":{
            "current_host":True,
            "ci":False,
            "kdenlive_project_xml_mutated":False,
            "demucs_is_stt_authority":False,
        },
    }
    receipt_path=Path(args.receipt).expanduser().resolve()
    write_json(receipt_path,receipt)
    print(json.dumps(receipt,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
