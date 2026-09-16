#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REQUEST_SCHEMA = "fa3.hrb-acquire-request.v1"
AUTH_REQUEST_SCHEMA = "fa3.hrb-resource-admission-authorization-request.v1"
WORKLOAD_SCHEMA = "fa3.workload-resource-envelope.v1"
LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
AUTH_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/ResourceAdmissionAuthorization@1"
HELPER = Path("/usr/local/libexec/fa3-host-resource-broker-acquire-root")
FORBIDDEN_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}
GPU_UUID_RE = re.compile(r"^GPU-[A-Fa-f0-9-]{16,64}$")


class ClientError(RuntimeError):
    pass


def load_workload(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClientError("workload envelope is unreadable") from exc
    if not isinstance(value, dict) or value.get("schema") != WORKLOAD_SCHEMA:
        raise ClientError("workload schema mismatch")
    if not str(value.get("workload_id", "")).strip():
        raise ClientError("workload_id missing")
    requirements = value.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ClientError("workload requirements missing")
    for item in requirements:
        if not isinstance(item, dict):
            raise ClientError("workload requirement must be an object")
        metric = str(item.get("metric", "")).strip().lower()
        if metric in FORBIDDEN_METRICS:
            raise ClientError("CU/TU admission metric forbidden")
    return value


def required_gpu_memory_bytes(workload: dict[str, Any]) -> int:
    candidates: list[float] = []
    for item in workload.get("requirements", []):
        metric = str(item.get("metric", "")).strip().lower()
        if metric != "gpu.vram_gib":
            continue
        if item.get("operator") != ">=":
            raise ClientError("gpu.vram_gib must use >= for lease acquisition")
        try:
            gib = float(item.get("value"))
        except (TypeError, ValueError) as exc:
            raise ClientError("gpu.vram_gib value invalid") from exc
        if not math.isfinite(gib) or gib <= 0:
            raise ClientError("gpu.vram_gib value invalid")
        candidates.append(gib)
    if not candidates:
        raise ClientError("explicit gpu.vram_gib >= requirement is required")
    return int(math.ceil(max(candidates) * (1024 ** 3)))


def generic_requirements(workload: dict[str, Any]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for item in workload.get("requirements", []):
        metric = str(item.get("metric", "")).strip().lower()
        if not metric.startswith(("cpu.", "memory.")):
            raise ClientError("generic authorization is restricted to CPU/memory workloads")
        operator = str(item.get("operator", "")).strip()
        value = item.get("value")
        if operator not in {">=", "<=", "=="} or isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ClientError("generic resource requirement invalid")
        requirements.append({"metric": metric, "operator": operator, "value": value})
    return requirements


def _atomic_write_private(path: Path, data: bytes) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _invoke(request: dict[str, Any], helper: Path) -> dict[str, Any]:
    if os.geteuid() == 0:
        raise ClientError("acquire client must run as non-root")
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/tmp/fa3-hrb-acquire-{os.getuid()}"))
    runtime_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(runtime_dir, 0o700)
    fd, request_name = tempfile.mkstemp(prefix="request-", suffix=".json", dir=runtime_dir)
    request_path = Path(request_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(request, handle, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            proc = subprocess.run(["sudo", "-n", str(helper), str(request_path.resolve())], text=True, capture_output=True,
                                  stdin=subprocess.DEVNULL, timeout=30, check=False,
                                  env={**os.environ, "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"})
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ClientError("privileged HRB acquire bridge unavailable") from exc
        if proc.returncode != 0:
            raise ClientError("HRB acquire bridge denied request")
        try:
            record = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ClientError("HRB acquire bridge returned invalid JSON") from exc
        if not isinstance(record, dict):
            raise ClientError("HRB acquire bridge returned invalid record")
        return record
    finally:
        try:
            request_path.unlink()
        except FileNotFoundError:
            pass


def acquire(workload_path: Path, accelerator_uuid: str, output_path: Path, *, helper: Path = HELPER) -> dict[str, Any]:
    if not GPU_UUID_RE.fullmatch(accelerator_uuid):
        raise ClientError("invalid accelerator UUID")
    workload = load_workload(workload_path)
    memory_bytes = required_gpu_memory_bytes(workload)
    request = {"schema": REQUEST_SCHEMA, "workload_id": str(workload["workload_id"]).strip(), "accelerator_uuid": accelerator_uuid, "memory_bytes": memory_bytes}
    lease = _invoke(request, helper)
    if lease.get("schema") != LEASE_SCHEMA:
        raise ClientError("HRB acquire bridge returned wrong lease schema")
    if str(lease.get("accelerator_uuid", "")) != accelerator_uuid or str(lease.get("purpose", "")).strip().lower() != request["workload_id"].lower():
        raise ClientError("lease binding mismatch")
    try:
        if int(lease.get("memory_max_bytes", 0)) < memory_bytes:
            raise ClientError("lease memory budget below workload requirement")
    except (TypeError, ValueError) as exc:
        raise ClientError("lease memory budget invalid") from exc
    _atomic_write_private(output_path, (json.dumps(lease, indent=2, ensure_ascii=False) + "\n").encode())
    return lease


def acquire_authorization(workload_path: Path, output_path: Path, *, helper: Path = HELPER) -> dict[str, Any]:
    workload = load_workload(workload_path)
    requirements = generic_requirements(workload)
    request = {"schema": AUTH_REQUEST_SCHEMA, "workload_id": str(workload["workload_id"]).strip(), "requirements": requirements}
    record = _invoke(request, helper)
    if record.get("schema") != AUTH_SCHEMA or record.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001" or record.get("status") != "ACTIVE":
        raise ClientError("HRB acquire bridge returned wrong authorization identity")
    if str(record.get("workload_id", "")).strip().lower() != request["workload_id"].lower():
        raise ClientError("authorization workload binding mismatch")
    if record.get("resource_requirements") != requirements:
        raise ClientError("authorization resource binding mismatch")
    _atomic_write_private(output_path, (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode())
    return record


def doctor(helper: Path = HELPER) -> int:
    if os.geteuid() == 0:
        print("BLOCKED: acquire client must run as non-root", file=sys.stderr)
        return 2
    if not helper.is_file() or not os.access(helper, os.X_OK):
        print("BLOCKED: privileged HRB acquire helper missing", file=sys.stderr)
        return 2
    try:
        proc = subprocess.run(["sudo", "-n", "-l", str(helper), "/dev/null"], text=True, capture_output=True,
                              stdin=subprocess.DEVNULL, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        print("BLOCKED: cannot verify acquire sudo policy", file=sys.stderr)
        return 2
    if proc.returncode != 0:
        print("BLOCKED: non-interactive acquire bridge unavailable", file=sys.stderr)
        return 2
    print("FA3 HRB ACQUIRE BRIDGE: READY")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Non-root FA3 HRB acquisition client")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--workload")
    parser.add_argument("--lease-output")
    parser.add_argument("--authorization-output")
    parser.add_argument("--accelerator-uuid")
    args = parser.parse_args()
    if args.doctor:
        return doctor()
    if not args.workload:
        parser.error("--workload is required")
    if bool(args.lease_output) == bool(args.authorization_output):
        parser.error("exactly one of --lease-output or --authorization-output is required")
    try:
        if args.lease_output:
            if not args.accelerator_uuid:
                parser.error("--accelerator-uuid is required with --lease-output")
            acquire(Path(args.workload), args.accelerator_uuid, Path(args.lease_output))
            output = args.lease_output
        else:
            if args.accelerator_uuid:
                parser.error("--accelerator-uuid is forbidden with --authorization-output")
            acquire_authorization(Path(args.workload), Path(args.authorization_output))
            output = args.authorization_output
    except ClientError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(str(Path(output).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
