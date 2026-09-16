#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
AUTH_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/ResourceAdmissionAuthorization@1"
REAL_BROKER = Path("/usr/local/bin/fa3-host-resource-broker")
AUTH_BACKEND = Path("/usr/local/libexec/fa3-host-resource-broker-authorization")
RUNTIME_DIR = Path("/run/fa3-hrb-validator")
MAX_RECORD_BYTES = 1024 * 1024


class BridgeError(RuntimeError):
    pass


def read_candidate(path_text: str, caller_uid: int, expected_schema: str = LEASE_SCHEMA) -> bytes:
    path = Path(path_text)
    if not path.is_absolute():
        raise BridgeError("record path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise BridgeError("record file cannot be opened safely") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise BridgeError("record input must be a regular file")
        if st.st_uid != caller_uid:
            raise BridgeError("record input must be owned by the invoking user")
        if st.st_mode & 0o022:
            raise BridgeError("record input must not be group/world writable")
        if st.st_size <= 0 or st.st_size > MAX_RECORD_BYTES:
            raise BridgeError("record input size outside allowed range")
        data = b""
        while len(data) <= MAX_RECORD_BYTES:
            block = os.read(fd, min(65536, MAX_RECORD_BYTES + 1 - len(data)))
            if not block:
                break
            data += block
        if len(data) > MAX_RECORD_BYTES:
            raise BridgeError("record input exceeds maximum size")
    finally:
        os.close(fd)
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BridgeError("record input is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != expected_schema:
        raise BridgeError("record schema mismatch")
    return data


def ensure_secure_runtime_dir(path: Path = RUNTIME_DIR) -> None:
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise BridgeError("validator runtime directory ownership/mode invalid")


def validate_backend(path: Path) -> None:
    try:
        st = path.stat()
    except OSError as exc:
        raise BridgeError("HRB validation backend unavailable") from exc
    if st.st_uid != 0 or st.st_mode & 0o022 or not stat.S_ISREG(st.st_mode) or not os.access(path, os.X_OK):
        raise BridgeError("HRB validation backend ownership/mode invalid")


def invoke_validation(data: bytes, operation: str = "validate-lease") -> bool:
    if operation == "validate-lease":
        backend, schema, prefix = REAL_BROKER, LEASE_SCHEMA, "lease-"
    elif operation == "validate-authorization":
        backend, schema, prefix = AUTH_BACKEND, AUTH_SCHEMA, "authorization-"
    else:
        raise BridgeError("unsupported validation operation")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BridgeError("record input is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise BridgeError("record type does not match validation operation")
    validate_backend(backend)
    ensure_secure_runtime_dir()
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=RUNTIME_DIR, prefix=prefix, suffix=".json", delete=False) as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temp_name = handle.name
        proc = subprocess.run([str(backend), operation, temp_name], text=True, capture_output=True,
                              stdin=subprocess.DEVNULL, timeout=20, check=False,
                              env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
        return proc.returncode == 0 and proc.stdout.strip().splitlines()[-1:] == ["VALID"]
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def main() -> int:
    if os.geteuid() != 0 or len(sys.argv) != 3:
        print("DENIED", file=sys.stderr)
        return 2
    operation, path_text = sys.argv[1], sys.argv[2]
    expected = LEASE_SCHEMA if operation == "validate-lease" else AUTH_SCHEMA if operation == "validate-authorization" else None
    if expected is None:
        print("DENIED", file=sys.stderr)
        return 2
    try:
        caller_uid = int(os.environ.get("SUDO_UID", "-1"))
    except ValueError:
        caller_uid = -1
    if caller_uid <= 0:
        print("DENIED", file=sys.stderr)
        return 2
    try:
        data = read_candidate(path_text, caller_uid, expected)
        valid = invoke_validation(data, operation)
    except (BridgeError, OSError):
        valid = False
    if valid:
        print("VALID")
        return 0
    print("DENIED", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
