#!/usr/bin/env python3
"""Non-promoting, read-only real-host observation of an optional disabled Terax."""
from __future__ import annotations
import argparse
import getpass
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REQUIRED_LABELS={"self-hosted","linux","x64","fa3-current-host"}
ZERO=("resident_process_count","worker_thread_count","ram_resident_bytes","network_session_count")
MISSING_PHYSICAL_PROOFS=[
    "PROVIDER_PROCESS_AND_UNNAMED_HELPER_OWNERSHIP",
    "AUTHORITATIVE_HRB_LEASE_AND_RESERVATION_INVENTORY",
    "UPSTREAM_AND_FA3_CONCURRENT_EXECUTION_PORT_SOCKET_SERVICE_INSPECTION",
    "APPLICABLE_INSTALL_REBOOT_ROLLBACK_AND_REMOVAL_PROOFS",
    "SIGNED_HOST_BOUND_EVIDENCE_ENVELOPE",
]

def utc(value: Any) -> datetime:
    if not isinstance(value,str):
        raise ValueError("timestamp absent")
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("naive timestamp")
    return dt.astimezone(timezone.utc)

def fingerprint() -> str:
    data=f"{platform.system()}|{platform.release()}|{platform.machine()}|{os.getuid()}"
    return hashlib.sha256(data.encode()).hexdigest()

def validate(doctor:dict[str,Any],receipt:dict[str,Any],*,source_sha:str,
             expected_sha:str="",now:datetime|None=None,
             effective_uid:int|None=None) -> dict[str,Any]:
    now=now or datetime.now(timezone.utc)
    uid=os.geteuid() if effective_uid is None else effective_uid
    errors=[]
    if not re.fullmatch(r"[a-f0-9]{40}",source_sha) or (expected_sha and source_sha!=expected_sha):
        errors.append("TERAX-OBS-001: source SHA invalid or checkout mismatch")
    if doctor.get("schema")!="fa3.current-host-runner-doctor-receipt.v1" or doctor.get("result")!="PASS":
        errors.append("TERAX-OBS-002: missing validated runner doctor")
    if doctor.get("repository")!="ubuntuokos/Final-Architecture-v3.0" or doctor.get("runner_status")!="online":
        errors.append("TERAX-OBS-003: runner repository/online mismatch")
    if not REQUIRED_LABELS.issubset({str(x).lower() for x in doctor.get("labels",[])}):
        errors.append("TERAX-OBS-004: missing runner labels")
    if doctor.get("host")!=socket.gethostname() or doctor.get("user")!=getpass.getuser() or uid==0:
        errors.append("TERAX-OBS-005: host, user or non-root identity mismatch")
    if not all(doctor.get(x) is True for x in (
        "required_labels_present","systemd_user_service_active",
        "hrb_validator_bridge_ready","hrb_acquire_bridge_ready")):
        errors.append("TERAX-OBS-006: runner/HRB preflight incomplete")
    if receipt.get("schema")!="fa3.terax-current-host.v2" or receipt.get("provider_id")!="FA3-PROVIDER-TERAX-001":
        errors.append("TERAX-OBS-007: Terax receipt identity drift")
    if receipt.get("status")!="OBSERVATIONAL_ONLY" or receipt.get("physical_attestation") is not False:
        errors.append("TERAX-OBS-008: forged process-snapshot physical PASS")
    if receipt.get("provider_state")!="DISABLED_REFERENCE_ONLY" or receipt.get("host_scope")!="CURRENT_HOST" or receipt.get("host_fingerprint_sha256")!=fingerprint():
        errors.append("TERAX-OBS-009: host/scope mismatch")
    if receipt.get("workload_execution_requested") is not False or receipt.get("requested_resource_classes")!=[]:
        errors.append("TERAX-OBS-010: disabled provider requested resources")
    if receipt.get("accelerator_discovery_performed") is not False or receipt.get("accelerator_lease_required") is not False or receipt.get("gpu_telemetry")!="NOT_APPLICABLE_NO_ACCELERATOR_RESOURCE_CLASS":
        errors.append("TERAX-OBS-011: unrequested accelerator discovery/lease")
    if any(receipt.get(x) is not False for x in (
        "provider_receipt_substitution_allowed","capability_promotion_claim","global_promotion_claim")):
        errors.append("TERAX-OBS-012: forbidden promotion claim")
    metrics=receipt.get("metrics")
    if not isinstance(metrics,dict) or any(type(metrics.get(x)) is not int or metrics.get(x)!=0 for x in ZERO) or metrics.get("active_polling") is not False or metrics.get("background_inference") is not False:
        errors.append("TERAX-OBS-013: nonzero or unknown provider-owned resource usage")
    try:
        dtime,rtime,expiry=utc(doctor["observed_at"]),utc(receipt["collected_at"]),utc(receipt["expires_at"])
        if any(t>now+timedelta(minutes=2) or now-t>timedelta(minutes=20) for t in (dtime,rtime)) or not(now<expiry<=now+timedelta(days=8)):
            errors.append("TERAX-OBS-014: stale/invalid source evidence")
    except (KeyError,TypeError,ValueError,OverflowError):
        errors.append("TERAX-OBS-015: missing evidence timestamp")
    return {
        "schema":"fa3.terax-host-observation.v1",
        "provider_id":"FA3-PROVIDER-TERAX-001",
        "result":"FAIL" if errors else "OBSERVATIONAL_ONLY",
        "physical_current_host_pass_claim":False,
        "global_promotion_claim":False,
        "capability_promotion_claim":False,
        "coexistence_current_host_status":"PENDING_CURRENT_HOST",
        "source_head_sha":source_sha,
        "missing_for_physical_pass":MISSING_PHYSICAL_PROOFS,
        "findings":errors,
    }

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--runner-doctor",default=".fa3-current-host/runner/doctor.json")
    ap.add_argument("--terax-receipt",default="evidence/receipts/terax-current-host.json")
    ap.add_argument("--output",default="reports/terax-host-observation.json")
    args=ap.parse_args()
    root=args.root.resolve()
    def confined(name:str)->Path:
        p=(root/name).resolve()
        if not p.is_relative_to(root):
            raise ValueError("evidence path escapes repository")
        return p
    sha=subprocess.run(["git","rev-parse","HEAD"],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
    try:
        doctor=json.loads(confined(args.runner_doctor).read_text(encoding="utf-8"))
        receipt=json.loads(confined(args.terax_receipt).read_text(encoding="utf-8"))
        obj=validate(doctor,receipt,source_sha=sha,expected_sha=os.environ.get("GITHUB_SHA",""))
    except (OSError,ValueError,KeyError):
        obj={"schema":"fa3.terax-host-observation.v1","result":"FAIL","physical_current_host_pass_claim":False,
             "global_promotion_claim":False,"coexistence_current_host_status":"PENDING_CURRENT_HOST",
             "findings":["TERAX-OBS-016: missing, invalid or escaping host evidence"]}
    out=confined(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(obj,indent=2,ensure_ascii=False))
    return 0 if obj["result"]=="OBSERVATIONAL_ONLY" else 2
if __name__=="__main__":
    raise SystemExit(main())
