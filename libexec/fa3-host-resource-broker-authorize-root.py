#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

AUTH_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/ResourceAdmissionAuthorization@1"
WORKLOAD_SCHEMA = "fa3.workload-resource-envelope.v1"
ISSUER = "FA3-HOST-RESOURCE-BROKER-001"
AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
KEY_PATH = Path("/etc/fa3/host-resource-broker/lease-hmac.key")
MAX_INPUT_BYTES = 1024 * 1024
DEFAULT_TTL_SECONDS = 300
MAX_TTL_SECONDS = 900
SUPPORTED_METRICS = {"cpu.physical_cores", "memory.total_gib", "numa.nodes"}
SUPPORTED_OPERATORS = {">=", ">", "<=", "<", "=="}


class AuthorizationError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read_owned_json(path_text: str, caller_uid: int) -> dict[str, Any]:
    path = Path(path_text)
    if not path.is_absolute():
        raise AuthorizationError("workload path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise AuthorizationError("workload file cannot be opened safely") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise AuthorizationError("workload input must be a regular file")
        if st.st_uid != caller_uid:
            raise AuthorizationError("workload input must be owned by the invoking user")
        if st.st_mode & 0o022:
            raise AuthorizationError("workload input must not be group/world writable")
        if st.st_size <= 0 or st.st_size > MAX_INPUT_BYTES:
            raise AuthorizationError("workload input size outside allowed range")
        data = b""
        while len(data) <= MAX_INPUT_BYTES:
            block = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - len(data)))
            if not block:
                break
            data += block
        if len(data) > MAX_INPUT_BYTES:
            raise AuthorizationError("workload input exceeds maximum size")
    finally:
        os.close(fd)
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorizationError("workload input is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != WORKLOAD_SCHEMA:
        raise AuthorizationError("workload schema mismatch")
    if not str(payload.get("workload_id", "")).strip():
        raise AuthorizationError("workload id missing")
    return payload


def read_key(path: Path = KEY_PATH) -> bytes:
    try:
        st = path.stat()
    except OSError as exc:
        raise AuthorizationError("HRB HMAC key unavailable") from exc
    if st.st_uid != 0 or not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
        raise AuthorizationError("HRB HMAC key ownership/mode invalid")
    try:
        key = path.read_bytes()
    except OSError as exc:
        raise AuthorizationError("HRB HMAC key unreadable") from exc
    if len(key) < 32:
        raise AuthorizationError("HRB HMAC key too short")
    return key


def _lscpu_fields() -> dict[str, str]:
    try:
        proc = subprocess.run(
            ["lscpu", "-J"], text=True, capture_output=True, timeout=10,
            check=False, env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuthorizationError("CPU topology discovery failed") from exc
    if proc.returncode != 0:
        raise AuthorizationError("CPU topology discovery failed")
    try:
        items = json.loads(proc.stdout).get("lscpu", [])
    except json.JSONDecodeError as exc:
        raise AuthorizationError("CPU topology output invalid") from exc
    return {str(item.get("field", "")).rstrip(":"): str(item.get("data", "")) for item in items}


def host_metrics() -> dict[str, float]:
    fields = _lscpu_fields()
    try:
        sockets = int(fields.get("Socket(s)", "0"))
        cores_per_socket = int(fields.get("Core(s) per socket", "0"))
        numa_nodes = int(fields.get("NUMA node(s)", "0"))
    except ValueError as exc:
        raise AuthorizationError("CPU topology values invalid") from exc
    physical_cores = sockets * cores_per_socket
    if physical_cores <= 0:
        raise AuthorizationError("physical CPU core count unavailable")
    try:
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
        mem_kib = int(next(line.split()[1] for line in meminfo.splitlines() if line.startswith("MemTotal:")))
    except (OSError, StopIteration, ValueError, IndexError) as exc:
        raise AuthorizationError("memory capacity unavailable") from exc
    return {
        "cpu.physical_cores": float(physical_cores),
        "memory.total_gib": mem_kib * 1024 / (1024 ** 3),
        "numa.nodes": float(numa_nodes),
    }


def _compare(observed: float, operator: str, required: float) -> bool:
    if operator == ">=": return observed >= required
    if operator == ">": return observed > required
    if operator == "<=": return observed <= required
    if operator == "<": return observed < required
    if operator == "==": return observed == required
    return False


def validate_requirements(workload: dict[str, Any], metrics: dict[str, float]) -> tuple[list[str], list[dict[str, Any]]]:
    requirements = workload.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise AuthorizationError("workload requirements missing")
    classes: set[str] = set()
    decisions: list[dict[str, Any]] = []
    for requirement in requirements:
        if not isinstance(requirement, dict):
            raise AuthorizationError("workload requirement is not an object")
        metric = str(requirement.get("metric", ""))
        operator = str(requirement.get("operator", ""))
        if metric not in SUPPORTED_METRICS:
            raise AuthorizationError("non-CPU/memory resource requested from generic authorizer")
        if operator not in SUPPORTED_OPERATORS:
            raise AuthorizationError("unsupported requirement operator")
        try:
            required = float(requirement.get("value"))
        except (TypeError, ValueError) as exc:
            raise AuthorizationError("requirement value invalid") from exc
        observed = float(metrics[metric])
        passed = _compare(observed, operator, required)
        decisions.append({"metric": metric, "operator": operator, "required": required, "observed": observed, "pass": passed})
        classes.add("cpu" if metric.startswith("cpu.") or metric.startswith("numa.") else "memory")
        if not passed:
            raise AuthorizationError(f"resource requirement not satisfied: {metric}")
    return sorted(classes), decisions


def sign_body(body: dict[str, Any], key: bytes) -> dict[str, str]:
    return {
        "alg": "HMAC-SHA256",
        "key_id": "host-local-v1",
        "value": hmac.new(key, canonical_bytes(body), hashlib.sha256).hexdigest(),
    }


def issue_authorization(
    workload: dict[str, Any], metrics: dict[str, float], key: bytes, *,
    host: str, now_epoch: int, ttl_seconds: int = DEFAULT_TTL_SECONDS,
    nonce: str | None = None,
) -> dict[str, Any]:
    if ttl_seconds <= 0 or ttl_seconds > MAX_TTL_SECONDS:
        raise AuthorizationError("authorization TTL outside allowed range")
    classes, decisions = validate_requirements(workload, metrics)
    if not classes or "accelerator" in classes:
        raise AuthorizationError("generic authorization resource classes invalid")
    nonce_value = nonce or secrets.token_hex(16)
    body: dict[str, Any] = {
        "schema": AUTH_SCHEMA,
        "authorization_id": "hrb-auth-" + hashlib.sha256(f"{host}|{workload['workload_id']}|{now_epoch}|{nonce_value}".encode()).hexdigest()[:24],
        "issuer": ISSUER,
        "authority": AUTHORITY,
        "status": "ACTIVE",
        "host": host,
        "workload_id": str(workload["workload_id"]),
        "requested_resource_classes": classes,
        "issued_epoch": int(now_epoch),
        "expires_epoch": int(now_epoch) + int(ttl_seconds),
        "nonce": nonce_value,
        "resource_decisions": decisions,
    }
    body["signature"] = sign_body(body, key)
    return body


def main() -> int:
    if os.geteuid() != 0 or len(sys.argv) not in (2, 3):
        print("DENIED", file=sys.stderr)
        return 2
    try:
        caller_uid = int(os.environ.get("SUDO_UID", "-1"))
    except ValueError:
        caller_uid = -1
    if caller_uid <= 0:
        print("DENIED", file=sys.stderr)
        return 2
    ttl = DEFAULT_TTL_SECONDS
    if len(sys.argv) == 3:
        try:
            ttl = int(sys.argv[2])
        except ValueError:
            print("DENIED", file=sys.stderr)
            return 2
    try:
        workload = read_owned_json(sys.argv[1], caller_uid)
        authorization = issue_authorization(
            workload, host_metrics(), read_key(), host=socket.gethostname(),
            now_epoch=int(time.time()), ttl_seconds=ttl,
        )
    except AuthorizationError:
        print("DENIED", file=sys.stderr)
        return 2
    print(json.dumps(authorization, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
