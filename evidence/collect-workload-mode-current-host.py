#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,subprocess
from pathlib import Path
from typing import Any
SCHEMA="fa3.workload-mode-current-host-receipt.v1"
def run(cmd:list[str],timeout:int=10)->tuple[int,str,str]:
    try:
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,check=False)
        return p.returncode,p.stdout.strip(),p.stderr.strip()
    except (OSError,subprocess.TimeoutExpired) as exc:
        return 127,"",str(exc)
def collect(root:Path)->dict[str,Any]:
    root=root.resolve();checks=[]
    rc,out,err=run(["git","-C",str(root),"rev-parse","HEAD"]);source_sha=out if rc==0 else "UNKNOWN"
    checks.append({"name":"exact_source_sha","pass":rc==0 and len(source_sha)==40,"detail":source_sha})
    ctl=os.environ.get("FA3_WORKLOAD_MODE_CTL",str(Path.home()/".local/bin/workmodectl"))
    rc,out,err=run([ctl,"status"])
    try: status=json.loads(out) if rc==0 else {}
    except json.JSONDecodeError: status={}
    checks.append({"name":"dbus_status","pass":rc==0 and bool(status),"detail":err or status.get("effective_mode","")})
    checks.append({"name":"fa3_bridge_connected","pass":status.get("fa3_state")=="CONNECTED" and status.get("authority")=="FA3_HRB","detail":status.get("authority","UNAVAILABLE")})
    checks.append({"name":"safety_state","pass":status.get("safety_state")=="PASS","detail":status.get("safety_state","UNKNOWN")})
    for unit in ("workmoded.service","fa3-workload-mode-bridge.service"):
        rc,out,err=run(["systemctl","--user","is-active",unit])
        checks.append({"name":"systemd_user_"+unit,"pass":rc==0 and out=="active","detail":out or err})
    cgroup=Path("/sys/fs/cgroup/cgroup.controllers");checks.append({"name":"cgroup_v2_available","pass":cgroup.is_file(),"detail":str(cgroup)})
    revision=Path.home()/".local/share/workload-mode/source-revision";installed=revision.read_text(encoding="utf-8").strip() if revision.is_file() else ""
    checks.append({"name":"installed_source_exact","pass":installed==source_sha,"detail":installed or "MISSING"})
    gm=status.get("gamemode_state","UNAVAILABLE");checks.append({"name":"gamemode_state_typed","pass":gm in {"UNAVAILABLE","AVAILABLE","ACTIVE"},"detail":gm})
    result="PASS" if all(x["pass"] for x in checks) else "FAIL"
    return {"schema":SCHEMA,"result":result,"source_sha":source_sha,"capability_count":175,"scope":"WORKLOAD_MODE_BROKER_FA3_BRIDGE_INSTALLATION_AND_DBUS_RUNTIME","status":status,"checks":checks,"systemd_cgroup_resource_mutation_proven":False,"vendor_gpu_telemetry_proven":False,"global_promotion_claim":False,"current_host_runtime_promotion_scope":"SCOPED_REFERENCE_RUNTIME_ONLY" if result=="PASS" else "NONE"}
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--output",required=True);ns=ap.parse_args()
    receipt=collect(Path(ns.root));out=Path(ns.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(receipt,indent=2,sort_keys=True));return 0 if receipt["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
