#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

WORKLOAD_SCHEMA="fa3.workload-resource-envelope.v1"
AUTH_SCHEMA="fa3.hrb-admission-authorization.v1"
HELPER=Path("/usr/local/libexec/fa3-host-resource-broker-admission-root")

class ClientError(RuntimeError):
    pass

def _atomic_write_private(path: Path, data: bytes) -> None:
    path=path.expanduser().resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f".{path.name}.",dir=path.parent)
    tmp=Path(name)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as h:
            h.write(data); h.flush(); os.fsync(h.fileno())
        os.replace(tmp,path); os.chmod(path,0o600)
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass

def _run_helper(action: str, path: Path, helper: Path=HELPER) -> subprocess.CompletedProcess[str]:
    if os.geteuid()==0:
        raise ClientError("admission client must run as non-root")
    if not helper.is_file() or not os.access(helper,os.X_OK):
        raise ClientError("privileged HRB admission helper missing")
    try:
        return subprocess.run(
            ["sudo","-n",str(helper),action,str(path.resolve())],
            text=True,capture_output=True,stdin=subprocess.DEVNULL,timeout=20,check=False,
            env={**os.environ,"PATH":"/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"},
        )
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ClientError("privileged HRB admission bridge unavailable") from exc

def authorize(workload_path: Path, output_path: Path, *, helper: Path=HELPER) -> dict[str,Any]:
    try:
        workload_bytes=workload_path.read_bytes()
        workload=json.loads(workload_bytes)
    except Exception as exc:
        raise ClientError("workload unreadable") from exc
    if not isinstance(workload,dict) or workload.get("schema")!=WORKLOAD_SCHEMA or not str(workload.get("workload_id","")).strip():
        raise ClientError("workload identity invalid")
    proc=_run_helper("authorize",workload_path,helper)
    if proc.returncode!=0:
        detail=(proc.stderr or "").strip().splitlines()[-1:] or [""]
        token=detail[0].removeprefix("DENIED:") if detail[0].startswith("DENIED:") else "ADMISSION_DENIED"
        token=token if token.replace("_","").isalnum() and token.upper()==token else "ADMISSION_DENIED"
        raise ClientError(f"HRB admission bridge denied authorization ({token})")
    try:
        doc=json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ClientError("HRB admission bridge returned invalid JSON") from exc
    if not isinstance(doc,dict) or doc.get("schema")!=AUTH_SCHEMA:
        raise ClientError("HRB admission bridge returned wrong schema")
    if doc.get("workload_id")!=str(workload["workload_id"]).strip() or doc.get("workload_envelope_sha256")!=hashlib.sha256(workload_bytes).hexdigest():
        raise ClientError("HRB admission authorization workload binding mismatch")
    _atomic_write_private(output_path,(json.dumps(doc,indent=2,ensure_ascii=False)+"\n").encode())
    return doc

def validate(authorization_path: Path, *, helper: Path=HELPER) -> bool:
    proc=_run_helper("validate",authorization_path,helper)
    return proc.returncode==0 and proc.stdout.strip().splitlines()[-1:]==["VALID"]

def doctor(helper: Path=HELPER) -> int:
    if os.geteuid()==0:
        print("BLOCKED: admission client must run as non-root",file=sys.stderr); return 2
    if not helper.is_file() or not os.access(helper,os.X_OK):
        print("BLOCKED: privileged HRB admission helper missing",file=sys.stderr); return 2
    try:
        proc=subprocess.run(["sudo","-n","-l",str(helper),"authorize","/dev/null"],text=True,capture_output=True,stdin=subprocess.DEVNULL,timeout=10,check=False)
    except (OSError,subprocess.TimeoutExpired):
        return 2
    if proc.returncode!=0:
        print("BLOCKED: non-interactive HRB admission bridge unavailable",file=sys.stderr); return 2
    try:
        with tempfile.TemporaryDirectory(prefix="fa3-hrb-admission-doctor-") as td:
            workload=Path(td)/"workload.json"
            workload.write_text(json.dumps({"schema":WORKLOAD_SCHEMA,"workload_id":"hrb-admission-doctor","requirements":[{"metric":"cpu.physical_cores","operator":">=","value":1}]},separators=(",",":"))+"\n",encoding="utf-8")
            os.chmod(workload,0o600)
            issued=_run_helper("authorize",workload,helper)
    except (OSError,ClientError):
        print("BLOCKED: HRB admission functional probe unavailable",file=sys.stderr); return 2
    if issued.returncode!=0:
        detail=(issued.stderr or "").strip().splitlines()[-1:] or [""]
        token=detail[0].removeprefix("DENIED:") if detail[0].startswith("DENIED:") else "ADMISSION_DENIED"
        token=token if token.replace("_","").isalnum() and token.upper()==token else "ADMISSION_DENIED"
        print(f"BLOCKED: HRB admission functional probe denied ({token})",file=sys.stderr); return 2
    try:
        doc=json.loads(issued.stdout)
    except json.JSONDecodeError:
        print("BLOCKED: HRB admission functional probe returned invalid JSON",file=sys.stderr); return 2
    if not isinstance(doc,dict) or doc.get("schema")!=AUTH_SCHEMA or doc.get("workload_id")!="hrb-admission-doctor":
        print("BLOCKED: HRB admission functional probe returned invalid authorization",file=sys.stderr); return 2
    print("FA3 HRB ADMISSION BRIDGE: READY"); return 0

def main() -> int:
    ap=argparse.ArgumentParser(description="Non-root FA3 HRB admission authorization client")
    ap.add_argument("--doctor",action="store_true")
    sub=ap.add_subparsers(dest="command")
    a=sub.add_parser("authorize"); a.add_argument("--workload",required=True); a.add_argument("--output",required=True)
    v=sub.add_parser("validate"); v.add_argument("--authorization",required=True)
    args=ap.parse_args()
    if args.doctor: return doctor()
    try:
        if args.command=="authorize":
            authorize(Path(args.workload),Path(args.output)); print(str(Path(args.output).resolve())); return 0
        if args.command=="validate":
            return 0 if validate(Path(args.authorization)) else 2
    except ClientError as exc:
        print(f"BLOCKED: {exc}",file=sys.stderr); return 2
    ap.error("command required")
    return 3

if __name__=="__main__":
    raise SystemExit(main())
