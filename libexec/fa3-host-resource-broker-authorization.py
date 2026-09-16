#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
import uuid
from pathlib import Path
from typing import Any

AUTHORITY = "FA3-HOST-RESOURCE-BROKER-001"
AUTH_SCHEMA = f"{AUTHORITY}/ResourceAdmissionAuthorization@1"
REQUEST_SCHEMA = "fa3.hrb-resource-admission-authorization-request.v1"
KEY_PATH = Path("/etc/fa3/host-resource-broker/lease-hmac.key")
KEY_ID = "host-local-v1"
DEFAULT_TTL_SECONDS = 300
MAX_TTL_SECONDS = 3600
MAX_FILE_BYTES = 1024 * 1024
WORKLOAD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
SIGNATURE_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_RESOURCE_PREFIXES = ("cpu.", "memory.")
FORBIDDEN_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}


class BrokerError(RuntimeError):
    pass


def _require_root() -> None:
    if os.geteuid() != 0:
        raise BrokerError("root execution required")


def _read_json(path: Path, *, max_bytes: int = MAX_FILE_BYTES) -> dict[str, Any]:
    try:
        st = path.stat()
    except OSError as exc:
        raise BrokerError("input unavailable") from exc
    if not stat.S_ISREG(st.st_mode) or st.st_size <= 0 or st.st_size > max_bytes:
        raise BrokerError("input file outside allowed bounds")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BrokerError("input is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise BrokerError("input must be a JSON object")
    return value


def _load_key(path: Path = KEY_PATH) -> bytes:
    try:
        st = path.stat()
    except OSError as exc:
        raise BrokerError("HRB HMAC key unavailable") from exc
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise BrokerError("HRB HMAC key ownership/mode invalid")
    try:
        key = path.read_bytes()
    except OSError as exc:
        raise BrokerError("HRB HMAC key unreadable") from exc
    if len(key) < 32:
        raise BrokerError("HRB HMAC key too short")
    return key


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _unsigned(record: dict[str, Any]) -> dict[str, Any]:
    value = dict(record)
    value.pop("signature", None)
    return value


def _sign(record: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical_bytes(_unsigned(record)), hashlib.sha256).hexdigest()


def _normalize_requirement(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise BrokerError("resource requirement must be an object")
    metric = str(item.get("metric", "")).strip().lower()
    operator = str(item.get("operator", "")).strip()
    value = item.get("value")
    if not metric or metric in FORBIDDEN_METRICS:
        raise BrokerError("resource metric is forbidden or missing")
    if not metric.startswith(ALLOWED_RESOURCE_PREFIXES):
        raise BrokerError("generic authorization is restricted to CPU/memory resources")
    if operator not in {">=", "<=", "=="}:
        raise BrokerError("resource requirement operator is unsupported")
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise BrokerError("resource requirement value is invalid")
    return {"metric": metric, "operator": operator, "value": value}


def parse_request(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema") != REQUEST_SCHEMA:
        raise BrokerError("request schema mismatch")
    workload_id = str(value.get("workload_id", "")).strip()
    if not WORKLOAD_RE.fullmatch(workload_id):
        raise BrokerError("invalid workload_id")
    raw_requirements = value.get("requirements")
    if not isinstance(raw_requirements, list) or not raw_requirements:
        raise BrokerError("resource requirements missing")
    requirements = [_normalize_requirement(item) for item in raw_requirements]
    return {"schema": REQUEST_SCHEMA, "workload_id": workload_id, "requirements": requirements}


def issue_authorization(request: dict[str, Any], *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict[str, Any]:
    _require_root()
    request = parse_request(request)
    if ttl_seconds <= 0 or ttl_seconds > MAX_TTL_SECONDS:
        raise BrokerError("authorization TTL outside allowed range")
    now = int(time.time())
    record: dict[str, Any] = {
        "schema": AUTH_SCHEMA,
        "authorization_id": f"FA3-HRB-AUTH-{uuid.uuid4()}",
        "issuer": AUTHORITY,
        "status": "ACTIVE",
        "host": socket.gethostname(),
        "workload_id": request["workload_id"],
        "resource_requirements": request["requirements"],
        "issued_epoch": now,
        "expires_epoch": now + ttl_seconds,
        "nonce": secrets.token_hex(16),
        "signature": {"alg": "HMAC-SHA256", "key_id": KEY_ID, "value": ""},
    }
    record["signature"]["value"] = _sign(record, _load_key())
    return record


def validate_authorization(record: dict[str, Any]) -> bool:
    _require_root()
    required = {
        "schema", "authorization_id", "issuer", "status", "host", "workload_id",
        "resource_requirements", "issued_epoch", "expires_epoch", "nonce", "signature",
    }
    if required - set(record):
        return False
    if record.get("schema") != AUTH_SCHEMA or record.get("issuer") != AUTHORITY or record.get("status") != "ACTIVE":
        return False
    if str(record.get("host", "")) != socket.gethostname():
        return False
    workload_id = str(record.get("workload_id", "")).strip()
    if not WORKLOAD_RE.fullmatch(workload_id):
        return False
    try:
        requirements = [_normalize_requirement(item) for item in record.get("resource_requirements", [])]
    except BrokerError:
        return False
    if not requirements or requirements != record.get("resource_requirements"):
        return False
    try:
        issued = int(record.get("issued_epoch", 0))
        expires = int(record.get("expires_epoch", 0))
    except (TypeError, ValueError):
        return False
    now = int(time.time())
    if issued <= 0 or issued > now + 30 or expires <= now or expires <= issued or expires - issued > MAX_TTL_SECONDS:
        return False
    signature = record.get("signature")
    if not isinstance(signature, dict) or signature.get("alg") != "HMAC-SHA256" or signature.get("key_id") != KEY_ID:
        return False
    supplied = str(signature.get("value", ""))
    if not SIGNATURE_RE.fullmatch(supplied):
        return False
    try:
        expected = _sign(record, _load_key())
    except BrokerError:
        return False
    return hmac.compare_digest(supplied, expected)


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 HRB generic CPU/memory admission authorization backend")
    sub = parser.add_subparsers(dest="command", required=True)
    issue = sub.add_parser("issue-authorization")
    issue.add_argument("--request", required=True)
    issue.add_argument("--output", required=True)
    issue.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    validate = sub.add_parser("validate-authorization")
    validate.add_argument("authorization")
    args = parser.parse_args()
    try:
        _require_root()
        if args.command == "issue-authorization":
            request = _read_json(Path(args.request))
            record = issue_authorization(request, ttl_seconds=args.ttl_seconds)
            _atomic_write(Path(args.output), record)
            print(str(Path(args.output).resolve()))
            return 0
        record = _read_json(Path(args.authorization))
        if validate_authorization(record):
            print("VALID")
            return 0
    except BrokerError:
        pass
    print("DENIED", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
