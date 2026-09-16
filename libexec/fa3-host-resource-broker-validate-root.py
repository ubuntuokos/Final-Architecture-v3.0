#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
AUTH_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/ResourceAdmissionAuthorization@1"
AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
ISSUER = "FA3-HOST-RESOURCE-BROKER-001"
REAL_BROKER = Path("/usr/local/bin/fa3-host-resource-broker")
KEY_PATH = Path("/etc/fa3/host-resource-broker/lease-hmac.key")
RUNTIME_DIR = Path("/run/fa3-hrb-validator")
MAX_INPUT_BYTES = 1024 * 1024


class BridgeError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read_candidate(path_text: str, caller_uid: int, expected_schema: str = LEASE_SCHEMA) -> bytes:
    path = Path(path_text)
    if not path.is_absolute():
        raise BridgeError("candidate path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise BridgeError("candidate file cannot be opened safely") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise BridgeError("candidate input must be a regular file")
        if st.st_uid != caller_uid:
            raise BridgeError("candidate input must be owned by the invoking user")
        if st.st_mode & 0o022:
            raise BridgeError("candidate input must not be group/world writable")
        if st.st_size <= 0 or st.st_size > MAX_INPUT_BYTES:
            raise BridgeError("candidate input size outside allowed range")
        data = b""
        while len(data) <= MAX_INPUT_BYTES:
            block = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - len(data)))
            if not block:
                break
            data += block
        if len(data) > MAX_INPUT_BYTES:
            raise BridgeError("candidate input exceeds maximum size")
    finally:
        os.close(fd)

    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BridgeError("candidate input is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != expected_schema:
        raise BridgeError("candidate schema mismatch")
    return data


def ensure_secure_runtime_dir(path: Path = RUNTIME_DIR) -> None:
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise BridgeError("cannot create validator runtime directory") from exc
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise BridgeError("cannot inspect validator runtime directory") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise BridgeError("validator runtime path is not a real directory")
    if st.st_uid != 0 or st.st_mode & 0o077:
        raise BridgeError("validator runtime directory ownership/mode invalid")


def validate_real_broker(path: Path = REAL_BROKER) -> None:
    try:
        st = path.stat()
    except OSError as exc:
        raise BridgeError("real HRB broker unavailable") from exc
    if st.st_uid != 0 or st.st_mode & 0o022 or not stat.S_ISREG(st.st_mode):
        raise BridgeError("real HRB broker ownership/mode invalid")
    if not os.access(path, os.X_OK):
        raise BridgeError("real HRB broker is not executable")


def read_key(path: Path = KEY_PATH) -> bytes:
    try:
        st = path.stat()
    except OSError as exc:
        raise BridgeError("HRB HMAC key unavailable") from exc
    if st.st_uid != 0 or not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
        raise BridgeError("HRB HMAC key ownership/mode invalid")
    try:
        key = path.read_bytes()
    except OSError as exc:
        raise BridgeError("HRB HMAC key unreadable") from exc
    if len(key) < 32:
        raise BridgeError("HRB HMAC key too short")
    return key


def invoke_lease_validation(data: bytes, broker: Path = REAL_BROKER) -> bool:
    validate_real_broker(broker)
    ensure_secure_runtime_dir()
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=RUNTIME_DIR, prefix="lease-", suffix=".json", delete=False) as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temp_name = handle.name
        proc = subprocess.run(
            [str(broker), "validate-lease", temp_name],
            text=True, capture_output=True, stdin=subprocess.DEVNULL,
            timeout=20, check=False, env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
        )
        return proc.returncode == 0 and proc.stdout.strip().splitlines()[-1:] == ["VALID"]
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def validate_generic_authorization(data: bytes, key: bytes | None = None, now_epoch: int | None = None, host: str | None = None) -> bool:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or payload.get("schema") != AUTH_SCHEMA:
        return False
    if payload.get("issuer") != ISSUER or payload.get("authority") != AUTHORITY or payload.get("status") != "ACTIVE":
        return False
    if not str(payload.get("authorization_id", "")).strip() or not str(payload.get("workload_id", "")).strip():
        return False
    classes = payload.get("requested_resource_classes")
    if not isinstance(classes, list) or not classes or any(item not in {"cpu", "memory"} for item in classes):
        return False
    if sorted(set(classes)) != classes:
        return False
    current = int(time.time()) if now_epoch is None else int(now_epoch)
    try:
        issued = int(payload.get("issued_epoch", 0))
        expires = int(payload.get("expires_epoch", 0))
    except (TypeError, ValueError):
        return False
    if issued <= 0 or issued > current + 30 or expires <= current or expires <= issued:
        return False
    expected_host = socket.gethostname() if host is None else host
    if str(payload.get("host", "")) != expected_host:
        return False
    signature = payload.get("signature")
    if not isinstance(signature, dict) or signature.get("alg") != "HMAC-SHA256" or signature.get("key_id") != "host-local-v1":
        return False
    value = str(signature.get("value", ""))
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        return False
    body = dict(payload)
    body.pop("signature", None)
    secret = read_key() if key is None else key
    expected = hmac.new(secret, canonical_bytes(body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, value)


def main() -> int:
    if os.geteuid() != 0 or len(sys.argv) != 3 or sys.argv[1] not in {"validate-lease", "validate-authorization"}:
        print("DENIED", file=sys.stderr)
        return 2
    try:
        caller_uid = int(os.environ.get("SUDO_UID", "-1"))
    except ValueError:
        caller_uid = -1
    if caller_uid <= 0:
        print("DENIED", file=sys.stderr)
        return 2
    action = sys.argv[1]
    schema = LEASE_SCHEMA if action == "validate-lease" else AUTH_SCHEMA
    try:
        data = read_candidate(sys.argv[2], caller_uid, schema)
        valid = invoke_lease_validation(data) if action == "validate-lease" else validate_generic_authorization(data)
    except BridgeError:
        valid = False
    if valid:
        print("VALID")
        return 0
    print("DENIED", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
