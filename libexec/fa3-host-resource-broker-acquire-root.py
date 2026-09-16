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
AUTH_REQUEST_SCHEMA = "fa3.hrb-resource-admission-authorization-request.v1"
LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
AUTH_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/ResourceAdmissionAuthorization@1"
BROKER = Path("/usr/local/bin/fa3-host-resource-broker")
AUTH_BACKEND = Path("/usr/local/libexec/fa3-host-resource-broker-authorization")
RUNTIME_DIR = Path("/run/fa3-hrb-acquire")
MAX_REQUEST_BYTES = 64 * 1024
MAX_RECORD_BYTES = 1024 * 1024
WORKLOAD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
GPU_UUID_RE = re.compile(r"^GPU-[A-Fa-f0-9-]{16,64}$")
FORBIDDEN_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}


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


def _normalize_generic_requirement(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AcquireError("resource requirement must be an object")
    metric = str(item.get("metric", "")).strip().lower()
    if not metric or metric in FORBIDDEN_METRICS:
        raise AcquireError("resource metric invalid")
    if not metric.startswith(("cpu.", "memory.")):
        raise AcquireError("generic authorization request may contain CPU/memory resources only")
    operator = str(item.get("operator", "")).strip()
    if operator not in {">=", "<=", "=="}:
        raise AcquireError("unsupported resource requirement operator")
    value = item.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise AcquireError("resource requirement value invalid")
    return {"metric": metric, "operator": operator, "value": value}


def parse_request(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcquireError("request is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise AcquireError("request must be an object")
    workload_id = str(value.get("workload_id", "")).strip()
    if not WORKLOAD_RE.fullmatch(workload_id):
        raise AcquireError("invalid workload_id")

    schema = value.get("schema")
    if schema == REQUEST_SCHEMA:
        accelerator_uuid = str(value.get("accelerator_uuid", "")).strip()
        memory_bytes = value.get("memory_bytes")
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
        return {"schema": REQUEST_SCHEMA, "workload_id": workload_id, "accelerator_uuid": accelerator_uuid, "memory_bytes": memory_bytes}

    if schema == AUTH_REQUEST_SCHEMA:
        raw = value.get("requirements")
        if not isinstance(raw, list) or not raw:
            raise AcquireError("generic resource requirements missing")
        requirements = [_normalize_generic_requirement(item) for item in raw]
        return {"schema": AUTH_REQUEST_SCHEMA, "workload_id": workload_id, "requirements": requirements}
    raise AcquireError("request schema mismatch")


def ensure_secure_runtime_dir(path: Path = RUNTIME_DIR) -> None:
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise AcquireError("cannot create acquire runtime directory") from exc
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise AcquireError("acquire runtime directory ownership/mode invalid")


def validate_executable(path: Path, label: str) -> None:
    try:
        st = path.stat()
    except OSError as exc:
        raise AcquireError(f"{label} unavailable") from exc
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022 or not os.access(path, os.X_OK):
        raise AcquireError(f"{label} ownership/mode invalid")


def validate_broker(path: Path = BROKER) -> None:
    validate_executable(path, "real HRB broker")


def _load_record(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AcquireError("broker did not produce readable record") from exc
    if not raw or len(raw) > MAX_RECORD_BYTES:
        raise AcquireError("broker record size outside allowed range")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcquireError("broker record is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise AcquireError("broker record must be an object")
    return value


def issue_lease(request: dict[str, Any], broker: Path = BROKER) -> dict[str, Any]:
    validate_broker(broker)
    ensure_secure_runtime_dir()
    record_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=RUNTIME_DIR, prefix="lease-", suffix=".json", delete=False) as handle:
            os.fchmod(handle.fileno(), 0o600)
            record_path = Path(handle.name)
        issue = subprocess.run([
            str(broker), "issue-lease", "--accelerator-uuid", request["accelerator_uuid"],
            "--memory-bytes", str(request["memory_bytes"]), "--purpose", request["workload_id"],
            "--output", str(record_path),
        ], text=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=20, check=False,
           env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
        if issue.returncode != 0:
            raise AcquireError("HRB issue-lease denied request")
        validate = subprocess.run([str(broker), "validate-lease", str(record_path)], text=True, capture_output=True,
                                  stdin=subprocess.DEVNULL, timeout=20, check=False,
                                  env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
        if validate.returncode != 0 or validate.stdout.strip().splitlines()[-1:] != ["VALID"]:
            raise AcquireError("HRB validate-lease rejected issued lease")
        lease = _load_record(record_path)
        if lease.get("schema") != LEASE_SCHEMA or lease.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001" or lease.get("status") != "ACTIVE":
            raise AcquireError("issued lease identity mismatch")
        if str(lease.get("accelerator_uuid", "")) != request["accelerator_uuid"]:
            raise AcquireError("issued lease accelerator binding mismatch")
        if str(lease.get("purpose", "")).strip().lower() != request["workload_id"].lower():
            raise AcquireError("issued lease workload binding mismatch")
        try:
            if int(lease.get("memory_max_bytes", 0)) < request["memory_bytes"]:
                raise AcquireError("issued lease memory budget below request")
        except (TypeError, ValueError) as exc:
            raise AcquireError("issued lease memory budget invalid") from exc
        return lease
    except subprocess.TimeoutExpired as exc:
        raise AcquireError("HRB operation timed out") from exc
    finally:
        if record_path is not None:
            try:
                record_path.unlink()
            except FileNotFoundError:
                pass


def issue_authorization(request: dict[str, Any], backend: Path = AUTH_BACKEND) -> dict[str, Any]:
    validate_executable(backend, "HRB generic authorization backend")
    ensure_secure_runtime_dir()
    request_path: Path | None = None
    record_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=RUNTIME_DIR, prefix="auth-request-", suffix=".json", delete=False) as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(request, handle, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            request_path = Path(handle.name)
        with tempfile.NamedTemporaryFile(mode="wb", dir=RUNTIME_DIR, prefix="authorization-", suffix=".json", delete=False) as handle:
            os.fchmod(handle.fileno(), 0o600)
            record_path = Path(handle.name)
        issue = subprocess.run([str(backend), "issue-authorization", "--request", str(request_path), "--output", str(record_path)],
                               text=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=20, check=False,
                               env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
        if issue.returncode != 0:
            raise AcquireError("HRB issue-authorization denied request")
        validate = subprocess.run([str(backend), "validate-authorization", str(record_path)], text=True, capture_output=True,
                                  stdin=subprocess.DEVNULL, timeout=20, check=False,
                                  env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
        if validate.returncode != 0 or validate.stdout.strip().splitlines()[-1:] != ["VALID"]:
            raise AcquireError("HRB validate-authorization rejected issued authorization")
        record = _load_record(record_path)
        if record.get("schema") != AUTH_SCHEMA or record.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001" or record.get("status") != "ACTIVE":
            raise AcquireError("issued authorization identity mismatch")
        if str(record.get("workload_id", "")).strip().lower() != request["workload_id"].lower():
            raise AcquireError("issued authorization workload binding mismatch")
        if record.get("resource_requirements") != request["requirements"]:
            raise AcquireError("issued authorization resource binding mismatch")
        return record
    except subprocess.TimeoutExpired as exc:
        raise AcquireError("HRB authorization operation timed out") from exc
    finally:
        for path in (request_path, record_path):
            if path is not None:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass


def main() -> int:
    if os.geteuid() != 0 or len(sys.argv) != 2:
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
        record = issue_lease(request) if request["schema"] == REQUEST_SCHEMA else issue_authorization(request)
    except (AcquireError, OSError):
        print("DENIED", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
