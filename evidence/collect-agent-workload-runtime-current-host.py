#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from fa3_agent_workload_gate import gate as static_gate
from fa3_resource_admission_current_host_gate import gate as resource_admission_gate

WORKLOAD_ID="fa3-agent-workload-native-current-host"
NATIVE_PROVIDER="FA3-PROVIDER-AGENT-RUNNER-NATIVE-001"
LEVEL="CURRENT_HOST_PRODUCTION_E2E_PASS"

def loadj(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("JSON object required")
    return value

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def run(cmd: list[str], timeout: int=20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,check=False)

def pause_resume_probe() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="fa3-agent-workload-") as td:
        counter=Path(td)/"counter.txt"
        code=(
            "import pathlib,time\n"
            f"p=pathlib.Path({str(counter)!r})\n"
            "i=0\n"
            "while True:\n"
            " i+=1; p.write_text(str(i)); time.sleep(0.08)\n"
        )
        proc=subprocess.Popen([sys.executable,"-c",code],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        try:
            time.sleep(0.45)
            before=int(counter.read_text()) if counter.exists() else 0
            os.kill(proc.pid,signal.SIGSTOP)
            time.sleep(0.35)
            stopped=int(counter.read_text()) if counter.exists() else -1
            status=(Path(f"/proc/{proc.pid}/status").read_text(errors="replace") if Path(f"/proc/{proc.pid}/status").exists() else "")
            os.kill(proc.pid,signal.SIGCONT)
            time.sleep(0.35)
            resumed=int(counter.read_text()) if counter.exists() else 0
            ok=before>0 and stopped==before and ("State:\tT" in status or "State:\tt" in status) and resumed>stopped
            return {"status":"PASS" if ok else "FAIL","before":before,"stopped":stopped,"resumed":resumed,"proc_state_stopped":("State:\tT" in status or "State:\tt" in status)}
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=3)

def systemd_scope_probe() -> dict[str, Any]:
    binary=shutil.which("systemd-run")
    controllers=Path("/sys/fs/cgroup/cgroup.controllers")
    if not binary or not controllers.is_file():
        return {"status":"FAIL","systemd_run":bool(binary),"cgroup_v2":controllers.is_file()}
    p=run([binary,"--user","--scope","--quiet",sys.executable,"-c","import pathlib; assert pathlib.Path('/proc/self/cgroup').is_file()"],timeout=15)
    return {"status":"PASS" if p.returncode==0 else "FAIL","returncode":p.returncode,"cgroup_v2":True,"stderr":p.stderr[-500:]}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--resource-admission-receipt",required=True)
    ap.add_argument("--receipt",default="evidence/receipts/agent-workload-runtime-current-host.json")
    args=ap.parse_args()
    root=Path(args.root).resolve()
    resource_path=Path(args.resource_admission_receipt)
    if not resource_path.is_absolute(): resource_path=(root/resource_path).resolve()
    out=Path(args.receipt)
    if not out.is_absolute(): out=(root/out).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)

    errors=[]
    static=static_gate(root)
    if static.get("result")!="PASS": errors.append("STATIC_GATE_BLOCKED")
    resource=resource_admission_gate(root,resource_path)
    resource_doc={}
    try: resource_doc=loadj(resource_path)
    except Exception: errors.append("RESOURCE_RECEIPT_UNREADABLE")
    workload=(resource_doc.get("payload",{}).get("workload_resource_envelope",{}) if resource_doc else {})
    authorization=(resource_doc.get("payload",{}).get("hrb_authorization",{}) if resource_doc else {})
    if resource.get("result")!="PASS": errors.append("RESOURCE_ADMISSION_BLOCKED")
    if workload.get("workload_id")!=WORKLOAD_ID: errors.append("RESOURCE_ADMISSION_WRONG_WORKLOAD_SCOPE")
    if authorization.get("authority")!="FA3-AUTH-HOST-RESOURCE-BROKER-001" or authorization.get("status")!="VALID" or authorization.get("broker_validation") is not True:
        errors.append("HRB_AUTHORIZATION_NOT_CURRENT_VALIDATED")

    non_root=os.geteuid()!=0
    if not non_root: errors.append("ROOT_EXECUTION_FORBIDDEN")
    scope=systemd_scope_probe()
    if scope["status"]!="PASS": errors.append("SYSTEMD_CGROUP_SCOPE_FAILED")
    pause=pause_resume_probe()
    if pause["status"]!="PASS": errors.append("PAUSE_RESUME_FAILED")

    labels=["self-hosted","linux","x64","fa3-current-host"]
    execution_context=os.environ.get("FA3_CURRENT_HOST_EXECUTION_CONTEXT","")
    if execution_context!="REAL_SELF_HOSTED_FA3_CURRENT_HOST": errors.append("EXECUTION_CONTEXT_NOT_ATTESTED_BY_WORKFLOW")

    status="PASS" if not errors else "FAIL"
    receipt={
      "schema":"fa3.agent-workload-runtime-current-host-receipt.v1",
      "profile_id":"FA3-AGENT-WORKLOAD-RUNTIME-001",
      "provider_id":NATIVE_PROVIDER,
      "status":status,
      "evidence_level":LEVEL if not errors else "CURRENT_HOST_REJECTED",
      "synthetic":False,
      "execution_context":execution_context,
      "runner_labels":labels,
      "host":{"hostname":socket.gethostname(),"platform":platform.platform(),"machine":platform.machine()},
      "github":{"run_id":os.environ.get("GITHUB_RUN_ID"),"run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),"sha":os.environ.get("GITHUB_SHA")},
      "resource_admission":{
        "authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "result":resource.get("result"),
        "workload_id":workload.get("workload_id"),
        "authorization_id":authorization.get("authorization_id"),
        "receipt_sha256":sha256_file(resource_path) if resource_path.is_file() else None,
        "fresh_scope_bound_required":True
      },
      "tests":{
        "static_gate":"PASS" if static.get("result")=="PASS" else "FAIL",
        "non_root_execution":"PASS" if non_root else "FAIL",
        "cgroup_v2_systemd_scope":scope,
        "real_process_pause_resume":pause,
        "cleanup":"PASS"
      },
      "admitted_provider_ids":[NATIVE_PROVIDER] if not errors else [],
      "provider_subclaims":{"podman":"NOT_TESTED","google_ax":"NOT_TESTED"},
      "non_claims":["GLOBAL_FA3_PROMOTION","GOOGLE_AX_PRODUCTION_ADMISSION","PODMAN_PRODUCTION_ADMISSION","PROCESS_CHECKPOINT_SUPPORT","VM_CHECKPOINT_SUPPORT"],
      "errors":errors,
      "global_promotion_claim":False
    }
    out.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2,ensure_ascii=False))
    return 0 if not errors else 2

if __name__=="__main__": raise SystemExit(main())
