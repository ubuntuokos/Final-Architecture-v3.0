#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REQUEST_SCHEMA = "fa3.hrb-acquire-request.v1"
LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
BROKER = Path("/usr/local/bin/fa3-host-resource-broker")
RUNTIME_DIR = Path("/run/fa3-hrb-acquire")
MAX_REQUEST_BYTES = 64 * 1024
MAX_LEASE_BYTES = 1024 * 1024
WORKLOAD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
GPU_UUID_RE = re.compile(r"^GPU-[A-Fa-f0-9-]{16,64}$")


class AcquireError(RuntimeError):
    pass


def _read_regular_caller_file(path_text: str, caller_uid: int, max_bytes: int) -> bytes:
    path = Path(path_text)
    if not path.is_absolute():
        raise AcquireError("request path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise AcquireError("request file cannot be opened safely") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise AcquireError("request must be a regular file")
        if st.st_uid != caller_uid:
            raise AcquireError("request must be owned by the invoking user")
        if st.st_mode & 0o022:
            raise AcquireError("request must not be group/world writable")
        if st.st_size <= 0 or st.st_size > max_bytes:
            raise AcquireError("request size outside allowed range")
        data = b""
        while len(data) <= max_bytes:
            block = os.read(fd, min(65536, max_bytes + 1 - len(data)))
            if not block:
                break
            data += block
        if len(data) > max_bytes:
            raise AcquireError("request exceeds maximum size")
        return data
    finally:
        os.close(fd)


def parse_request(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcquireError("request is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != REQUEST_SCHEMA:
        raise AcquireError("request schema mismatch")

    workload_id = str(value.get("workload_id", "")).strip()
    accelerator_uuid = str(value.get("accelerator_uuid", "")).strip()
    memory_bytes = value.get("memory_bytes")
    if not WORKLOAD_RE.fullmatch(workload_id):
        raise AcquireError("invalid workload_id")
    if not GPU_UUID_RE.fullmatch(accelerator_uuid):
        raise AcquireError("invalid accelerator_uuid")
    if isinstance(memory_bytes, bool):
        raise AcquireError("invalid memory_bytes")
    try:
        memory_bytes = int(memory_bytes)
    except (TypeError, ValueError) as exc:
        raise AcquireError("invalid memory_bytes") from exc
    if memory_bytes <= 0 or memory_bytes > (1 << 60):
        raise AcquireError("memory_bytes outside allowed range")
    return {
        "schema": REQUEST_SCHEMA,
        "workload_id": workload_id,
        "accelerator_uuid": accelerator_uuid,
        "memory_bytes": memory_bytes,
    }


def ensure_secure_runtime_dir(path: Path = RUNTIME_DIR) -> None:
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise AcquireError("cannot create acquire runtime directory") from exc
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise AcquireError("cannot inspect acquire runtime directory") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise AcquireError("acquire runtime path is not a real directory")
    if st.st_uid != 0 or st.st_mode & 0o077:
        raise AcquireError("acquire runtime directory ownership/mode invalid")


def validate_broker(path: Path = BROKER) -> None:
    try:
        st = path.stat()
    except OSError as exc:
        raise AcquireError("real HRB broker unavailable") from exc
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
        raise AcquireError("real HRB broker ownership/mode invalid")
    if not os.access(path, os.X_OK):
        raise AcquireError("real HRB broker is not executable")


def _load_lease(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AcquireError("broker did not produce readable lease") from exc
    if not raw or len(raw) > MAX_LEASE_BYTES:
        raise AcquireError("broker lease size outside allowed range")
    try:
        lease = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcquireError("broker lease is not valid UTF-8 JSON") from exc
    if not isinstance(lease, dict):
        raise AcquireError("broker lease must be an object")
    return lease


def issue_lease(request: dict[str, Any], broker: Path = BROKER) -> dict[str, Any]:
    validate_broker(broker)
    ensure_secure_runtime_dir()
    lease_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=RUNTIME_DIR,
            prefix="lease-",
            suffix=".json",
            delete=False,
        ) as handle:
            os.fchmod(handle.fileno(), 0o600)
            lease_path = Path(handle.name)

        issue = subprocess.run(
            [
                str(broker),
                "issue-lease",
                "--accelerator-uuid",
                request["accelerator_uuid"],
                "--memory-bytes",
                str(request["memory_bytes"]),
                "--purpose",
                request["workload_id"],
                "--output",
                str(lease_path),
            ],
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=20,
            check=False,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
        )
        if issue.returncode != 0:
            raise AcquireError("HRB issue-lease denied request")

        validate = subprocess.run(
            [str(broker), "validate-lease", str(lease_path)],
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=20,
            check=False,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
        )
        if validate.returncode != 0 or validate.stdout.strip().splitlines()[-1:] != ["VALID"]:
            raise AcquireError("HRB validate-lease rejected issued lease")

        lease = _load_lease(lease_path)
        if lease.get("schema") != LEASE_SCHEMA:
            raise AcquireError("issued lease schema mismatch")
        if lease.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001":
            raise AcquireError("issued lease issuer mismatch")
        if lease.get("status") != "ACTIVE":
            raise AcquireError("issued lease is not ACTIVE")
        if str(lease.get("accelerator_uuid", "")) != request["accelerator_uuid"]:
            raise AcquireError("issued lease accelerator binding mismatch")
        if str(lease.get("purpose", "")).strip().lower() != request["workload_id"].lower():
            raise AcquireError("issued lease workload binding mismatch")
        try:
            lease_memory = int(lease.get("memory_max_bytes", 0))
        except (TypeError, ValueError) as exc:
            raise AcquireError("issued lease memory budget invalid") from exc
        if lease_memory < request["memory_bytes"]:
            raise AcquireError("issued lease memory budget below request")
        return lease
    except subprocess.TimeoutExpired as exc:
        raise AcquireError("HRB operation timed out") from exc
    finally:
        if lease_path is not None:
            try:
                lease_path.unlink()
            except FileNotFoundError:
                pass


def main() -> int:
    if os.geteuid() != 0:
        print("DENIED", file=sys.stderr)
        return 2
    if len(sys.argv) != 2:
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
        data = _read_regular_caller_file(sys.argv[1], caller_uid, MAX_REQUEST_BYTES)
        request = parse_request(data)
        lease = issue_lease(request)
    except AcquireError:
        print("DENIED", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(lease, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
