#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def git_head()->str:
    try:return subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
    except Exception:return "UNKNOWN"

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--selection",required=True)
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--ir",required=True)
    ap.add_argument("--hrb")
    ap.add_argument("--artifact-output",default="evidence/runtime/motion-video-current-host/output.bin")
    args=ap.parse_args()
    cmd=[
      "python3",str(ROOT/"src/fa3_motion_video_provider_adapter.py"),
      "--selection",args.selection,"--manifest",args.manifest,"--ir",args.ir,
      "--output",str(ROOT/"evidence/receipts/motion-video-current-host.json"),
      "--artifact-output",args.artifact_output
    ]
    if args.hrb: cmd += ["--hrb",args.hrb]
    p=subprocess.run(cmd,cwd=ROOT)
    if p.returncode!=0:return p.returncode
    path=ROOT/"evidence/receipts/motion-video-current-host.json"
    obj=json.loads(path.read_text(encoding="utf-8"))
    obj["repository_head"]=git_head()
    obj["evidence_scope"]="REAL_PROVIDER_CURRENT_HOST"
    obj["synthetic_or_mock_provider"]=False
    obj["global_promotion_claim"]=False
    path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
