#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROVIDER_ID="FA3-PROVIDER-WAN22-001"
def sha(p:Path):
 h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--runtime-config",required=True);ap.add_argument("--admission-receipt",required=True);ap.add_argument("--output",required=True)
 a=ap.parse_args();cfgp=Path(a.runtime_config).resolve();admp=Path(a.admission_receipt).resolve();cfg=json.loads(cfgp.read_text());adm=json.loads(admp.read_text())
 if adm.get("provider_id")!=PROVIDER_ID or adm.get("status")!="PASS":raise SystemExit("Wan2.2 admission receipt not PASS")
 wrapper=(ROOT/"bin/fa3-wan22-provider-exec.py").resolve()
 out={
  "schema":"fa3.motion-video-execution-manifest.v1","status":"ADMITTED","provider_id":PROVIDER_ID,
  "provider_selection_authority":"FA3-AUTH-MODEL-ROUTER-001","resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
  "transport":"FA3_EXECUTOR_COMMAND","cost_class":"FREE_LOCAL","execution_topology":"LOCAL","requires_accelerator":True,
  "silent_fallback_allowed":False,"admission_receipt":str(admp),"admission_receipt_sha256":sha(admp),
  "executable":str(wrapper),"executable_sha256":sha(wrapper),
  "argv":["--runtime-config",str(cfgp),"--ir","{ir}","--output","{output}"],
  "provider_task":cfg.get("task"),"source_revision":adm.get("source_revision")
 }
 Path(a.output).write_text(json.dumps(out,indent=2)+"\n")
 print(json.dumps(out,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
