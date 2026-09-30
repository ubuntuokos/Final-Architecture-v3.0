#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]

REQUIRED_PROTOCOLS=("smtp","imap_or_jmap","carddav","tls_certificate_validation")
REQUIRED_ROUNDTRIPS=("send_receive","contact")
REQUIRED_SECURITY=(
    "secret_broker_used",
    "attachment_security_pass",
    "malware_scanner_pass",
    "dlp_pass",
    "software_coexistence_pass",
    "hardware_safety_pass",
    "authorization_context_pass",
)

FORBIDDEN_VALUE_KEYS={
    "password","password_value","token","token_value","access_token","refresh_token",
    "secret","secret_value","credential","credential_value","api_key","private_key",
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def _assert_no_secret_values(obj: Any, path: str="root") -> None:
    if isinstance(obj, dict):
        for key,value in obj.items():
            normalized=str(key).lower()
            if normalized in FORBIDDEN_VALUE_KEYS:
                raise ValueError(f"provider receipt contains forbidden secret-bearing field: {path}.{key}")
            _assert_no_secret_values(value,f"{path}.{key}")
    elif isinstance(obj, list):
        for i,value in enumerate(obj):
            _assert_no_secret_values(value,f"{path}[{i}]")

def validate_provider_receipt(receipt: dict[str,Any]) -> list[str]:
    failures=[]
    if receipt.get("status")!="PASS":
        failures.append("provider-status")
    if receipt.get("current_host") is not True:
        failures.append("current-host")
    if receipt.get("physical_execution") is not True:
        failures.append("physical-execution")
    if receipt.get("production_e2e") is not True:
        failures.append("production-e2e")
    if receipt.get("synthetic") is not False:
        failures.append("synthetic-evidence-forbidden")
    if receipt.get("historical_only") is True:
        failures.append("historical-only-forbidden")
    protocols=receipt.get("protocols") or {}
    failures.extend(f"protocol:{name}" for name in REQUIRED_PROTOCOLS if protocols.get(name) is not True)
    roundtrips=receipt.get("roundtrips") or {}
    failures.extend(f"roundtrip:{name}" for name in REQUIRED_ROUNDTRIPS if roundtrips.get(name) is not True)
    security=receipt.get("security") or {}
    failures.extend(f"security:{name}" for name in REQUIRED_SECURITY if security.get(name) is not True)
    provider_id=receipt.get("provider_id")
    if not isinstance(provider_id,str) or not provider_id:
        failures.append("provider-id")
    evidence_refs=receipt.get("evidence_refs")
    if not isinstance(evidence_refs,list) or not evidence_refs:
        failures.append("evidence-refs")
    _assert_no_secret_values(receipt)
    return failures

def main() -> int:
    ap=argparse.ArgumentParser(description="Aggregate physical FA3 Communications & Contacts current-host provider evidence")
    ap.add_argument("--provider-receipt",required=True,help="Physical provider E2E receipt; never pass credentials here")
    ap.add_argument("--output",default=str(ROOT/"evidence/receipts/communications-contacts-current-host.json"))
    args=ap.parse_args()

    if os.environ.get("GITHUB_ACTIONS","").lower()=="true" and os.environ.get("FA3_CURRENT_HOST_RUNNER")!="1":
        raise SystemExit("CURRENT_HOST evidence is forbidden on non-designated GitHub runners")

    provider_path=Path(args.provider_receipt).expanduser().resolve()
    receipt=json.loads(provider_path.read_text(encoding="utf-8"))
    failures=validate_provider_receipt(receipt)
    if failures:
        raise SystemExit("COMMUNICATIONS CURRENT-HOST BLOCKED: "+", ".join(failures))

    combined={
        "schema":"fa3.communications-contacts-current-host-receipt.v1",
        "status":"PASS",
        "evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS",
        "profile_id":"FA3-COMMUNICATIONS-CONTACTS-SHARED-001",
        "current_host":True,
        "physical_execution":True,
        "production_e2e":True,
        "synthetic":False,
        "historical_only":False,
        "collected_at":now(),
        "host":{
            "hostname":socket.gethostname(),
            "platform":platform.platform(),
            "machine":platform.machine(),
            "python":platform.python_version(),
            "effective_uid":os.geteuid(),
        },
        "provider":{
            "provider_id":receipt["provider_id"],
            "provider_receipt_path":str(provider_path),
            "provider_receipt_sha256":sha256(provider_path),
        },
        "protocols":{name:True for name in REQUIRED_PROTOCOLS},
        "roundtrips":{name:True for name in REQUIRED_ROUNDTRIPS},
        "security":{name:True for name in REQUIRED_SECURITY},
        "evidence_refs":list(receipt["evidence_refs"]),
        "secret_values_recorded":False,
        "runtime_promotion_claim":"EVIDENCE_ONLY_NORMAL_PROMOTION_GATES_STILL_REQUIRED",
    }
    out=Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(combined,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(combined,indent=2,ensure_ascii=False))
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print(f"COMMUNICATIONS CURRENT-HOST EVIDENCE FAILED: {exc}",file=sys.stderr)
        raise SystemExit(2)
