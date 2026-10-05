#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import socket
import stat
import sys
import time
from pathlib import Path
from typing import Any

WORKLOAD_SCHEMA = "fa3.workload-resource-envelope.v1"
AUTH_SCHEMA = "fa3.hrb-admission-authorization.v1"
AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
ISSUER = "FA3-HOST-RESOURCE-BROKER-001"
HMAC_ALG = "HMAC-SHA256"
HMAC_SCOPE = "HRB_INTERNAL_EPHEMERAL_ADMISSION_AUTH"
KEY_FILE = Path("/etc/fa3/host-resource-broker/admission-hmac-keys.json")
MAX_BYTES = 64 * 1024
DEFAULT_TTL_SECONDS = 300
WORKLOAD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
FORBIDDEN_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}

class AdmissionError(RuntimeError):
    pass

def _denial_code(exc: AdmissionError) -> str:
    message=str(exc)
    if message.startswith("HRB admission keyring"): return "KEYRING_INVALID"
    if message.startswith("workload"): return "WORKLOAD_INVALID"
    if message.startswith("input"): return "INPUT_INVALID"
    if message.startswith("authorization"): return "AUTHORIZATION_INVALID"
    return "ADMISSION_INVALID"

def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _read_caller_file(path_text: str, caller_uid: int) -> bytes:
    path = Path(path_text)
    if not path.is_absolute():
        raise AdmissionError("input path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise AdmissionError("input cannot be opened safely") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != caller_uid or st.st_mode & 0o022:
            raise AdmissionError("input ownership or mode invalid")
        if st.st_size <= 0 or st.st_size > MAX_BYTES:
            raise AdmissionError("input size outside allowed range")
        data = b""
        while len(data) <= MAX_BYTES:
            block = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not block:
                break
            data += block
        if len(data) > MAX_BYTES:
            raise AdmissionError("input exceeds maximum size")
        return data
    finally:
        os.close(fd)

def _resource_class(metric: str) -> str:
    metric = metric.lower()
    if metric.startswith(("gpu.", "npu.", "accelerator.")):
        return "accelerator"
    for prefix, name in (("cpu.","cpu"),("memory.","memory"),("storage.","storage"),("numa.","numa"),("pcie.","pcie")):
        if metric.startswith(prefix):
            return name
    return "other"

def _parse_workload(data: bytes) -> tuple[dict[str, Any], list[str]]:
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdmissionError("workload is not valid UTF-8 JSON") from exc
    if not isinstance(obj, dict) or obj.get("schema") != WORKLOAD_SCHEMA:
        raise AdmissionError("workload schema mismatch")
    workload_id = str(obj.get("workload_id", "")).strip()
    if not WORKLOAD_RE.fullmatch(workload_id):
        raise AdmissionError("workload_id invalid")
    reqs = obj.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        raise AdmissionError("workload requirements missing")
    classes = set()
    for item in reqs:
        if not isinstance(item, dict):
            raise AdmissionError("workload requirement invalid")
        metric = str(item.get("metric", "")).strip().lower()
        if not metric or metric in FORBIDDEN_METRICS:
            raise AdmissionError("workload metric invalid or forbidden")
        if item.get("operator") not in {">=", "<=", "==", "contains"} or "value" not in item:
            raise AdmissionError("workload requirement operator/value invalid")
        classes.add(_resource_class(metric))
    return obj, sorted(classes)

def _load_keyring(path: Path = KEY_FILE) -> tuple[str, bytes]:
    try:
        st = path.lstat()
    except OSError as exc:
        raise AdmissionError("HRB admission keyring unavailable") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise AdmissionError("HRB admission keyring ownership/mode invalid")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdmissionError("HRB admission keyring unreadable") from exc
    if not isinstance(doc, dict) or doc.get("scope") != HMAC_SCOPE:
        raise AdmissionError("HRB admission keyring scope mismatch")
    active = str(doc.get("active_key_id", ""))
    for item in doc.get("keys", []):
        if isinstance(item, dict) and str(item.get("key_id", "")) == active:
            try:
                secret = bytes.fromhex(str(item.get("secret_hex", "")))
            except ValueError as exc:
                raise AdmissionError("HRB admission key invalid") from exc
            if len(secret) < 32:
                raise AdmissionError("HRB admission key too short")
            return active, secret
    raise AdmissionError("active HRB admission key missing")

def _sign(doc: dict[str, Any], key_id: str, secret: bytes) -> dict[str, str]:
    unsigned = {k:v for k,v in doc.items() if k != "authentication"}
    mac = hmac.new(secret, _canonical(unsigned), hashlib.sha256).hexdigest()
    return {"alg":HMAC_ALG,"key_id":key_id,"scope":HMAC_SCOPE,"mac":mac}

def issue_authorization(workload_bytes: bytes) -> dict[str, Any]:
    workload, classes = _parse_workload(workload_bytes)
    key_id, secret = _load_keyring()
    now = int(time.time())
    doc = {
        "schema": AUTH_SCHEMA,
        "authorization_id": "hrb-auth-" + secrets.token_hex(16),
        "authority": AUTHORITY,
        "issuer": ISSUER,
        "status": "ACTIVE",
        "host": socket.gethostname(),
        "workload_id": str(workload["workload_id"]).strip(),
        "workload_envelope_sha256": hashlib.sha256(workload_bytes).hexdigest(),
        "requested_resource_classes": classes,
        "accelerator_required": "accelerator" in classes,
        "issued_epoch": now,
        "expires_epoch": now + DEFAULT_TTL_SECONDS,
        "nonce": secrets.token_hex(16),
        "semantics": {
            "authorization_is_not_resource_lease": True,
            "accelerator_lease_still_required_when_accelerator_required": True,
            "durable_evidence_signature": False,
        },
    }
    doc["authentication"] = _sign(doc, key_id, secret)
    return doc

def validate_authorization_bytes(data: bytes) -> dict[str, Any]:
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdmissionError("authorization is not valid UTF-8 JSON") from exc
    if not isinstance(doc, dict):
        raise AdmissionError("authorization must be object")
    required = {
        "schema","authorization_id","authority","issuer","status","host","workload_id",
        "workload_envelope_sha256","requested_resource_classes","accelerator_required",
        "issued_epoch","expires_epoch","nonce","semantics","authentication"
    }
    if not required.issubset(doc):
        raise AdmissionError("authorization fields missing")
    if doc.get("schema") != AUTH_SCHEMA or doc.get("authority") != AUTHORITY or doc.get("issuer") != ISSUER:
        raise AdmissionError("authorization identity mismatch")
    if doc.get("status") != "ACTIVE" or str(doc.get("host","")) != socket.gethostname():
        raise AdmissionError("authorization status/host mismatch")
    if not WORKLOAD_RE.fullmatch(str(doc.get("workload_id",""))):
        raise AdmissionError("authorization workload invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(doc.get("workload_envelope_sha256",""))):
        raise AdmissionError("authorization workload digest invalid")
    classes = doc.get("requested_resource_classes")
    if not isinstance(classes, list) or not classes or classes != sorted(set(str(x) for x in classes)):
        raise AdmissionError("authorization resource classes invalid")
    if doc.get("accelerator_required") is not ("accelerator" in classes):
        raise AdmissionError("authorization accelerator flag invalid")
    try:
        issued = int(doc.get("issued_epoch"))
        expires = int(doc.get("expires_epoch"))
    except (TypeError, ValueError) as exc:
        raise AdmissionError("authorization timestamps invalid") from exc
    now = int(time.time())
    if issued <= 0 or expires <= issued or expires <= now or expires - issued > DEFAULT_TTL_SECONDS:
        raise AdmissionError("authorization expired or TTL invalid")
    semantics = doc.get("semantics", {})
    if not isinstance(semantics, dict) or semantics.get("authorization_is_not_resource_lease") is not True or semantics.get("durable_evidence_signature") is not False:
        raise AdmissionError("authorization semantics invalid")
    auth = doc.get("authentication", {})
    if not isinstance(auth, dict) or auth.get("alg") != HMAC_ALG or auth.get("scope") != HMAC_SCOPE:
        raise AdmissionError("authorization authentication descriptor invalid")
    key_id, secret = _load_keyring()
    if auth.get("key_id") != key_id:
        raise AdmissionError("authorization key id invalid")
    expected = _sign(doc, key_id, secret)["mac"]
    if not hmac.compare_digest(expected, str(auth.get("mac",""))):
        raise AdmissionError("authorization MAC invalid")
    return doc

def main() -> int:
    if os.geteuid() != 0 or len(sys.argv) != 3:
        print("DENIED", file=sys.stderr)
        return 2
    try:
        caller_uid = int(os.environ.get("SUDO_UID", "-1"))
    except ValueError:
        caller_uid = -1
    if caller_uid <= 0:
        print("DENIED", file=sys.stderr)
        return 2
    action, path = sys.argv[1], sys.argv[2]
    try:
        data = _read_caller_file(path, caller_uid)
        if action == "authorize":
            sys.stdout.write(json.dumps(issue_authorization(data), separators=(",",":"), ensure_ascii=False) + "\n")
            return 0
        if action == "validate":
            validate_authorization_bytes(data)
            print("VALID")
            return 0
    except AdmissionError as exc:
        print(f"DENIED:{_denial_code(exc)}", file=sys.stderr)
        return 2
    print("DENIED:ACTION_INVALID", file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
