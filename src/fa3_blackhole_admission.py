#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKLOAD_ID = "FA3-BLACKHOLE-API-001"
LEASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class AdmissionDenied(RuntimeError):
    code: str
    message: str
    http_status: int = 403

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdmissionDenied("HRB_LEASE_EXPIRY_INVALID", "HRB lease expiry is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdmissionDenied("HRB_LEASE_EXPIRY_INVALID", "HRB lease expiry is invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise AdmissionDenied("RESOURCE_PROFILE_INVALID", f"{name} must be a positive integer", 422)
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise AdmissionDenied("RESOURCE_PROFILE_INVALID", f"{name} must be a positive integer", 422) from exc
    if number <= 0:
        raise AdmissionDenied("RESOURCE_PROFILE_INVALID", f"{name} must be a positive integer", 422)
    return number


def validate_hrb_lease(lease_id: str, lease_root: str | Path, requested: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    if not LEASE_ID_RE.fullmatch(str(lease_id or "")):
        raise AdmissionDenied("HRB_LEASE_ID_INVALID", "HRB lease id is invalid", 422)
    root = Path(lease_root).resolve()
    path = (root / f"{lease_id}.json").resolve()
    if path.parent != root:
        raise AdmissionDenied("HRB_LEASE_PATH_ESCAPE", "HRB lease path escaped the configured lease root")
    try:
        lease = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdmissionDenied("HRB_LEASE_MISSING", "HRB lease is missing or unreadable") from exc
    if not isinstance(lease, dict):
        raise AdmissionDenied("HRB_LEASE_INVALID", "HRB lease is not an object")
    if lease.get("status") not in {"ADMITTED", "ACTIVE", "PASS"}:
        raise AdmissionDenied("HRB_LEASE_NOT_ACTIVE", "HRB lease is not active")
    if lease.get("workload_id") != WORKLOAD_ID:
        raise AdmissionDenied("HRB_LEASE_SUBJECT_MISMATCH", "HRB lease was issued for another workload")
    if lease.get("lease_id") != lease_id:
        raise AdmissionDenied("HRB_LEASE_ID_MISMATCH", "HRB lease identity mismatch")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if _parse_time(lease.get("expires_at")) <= current:
        raise AdmissionDenied("HRB_LEASE_EXPIRED", "HRB lease has expired")

    granted = lease.get("resources")
    if not isinstance(granted, dict):
        raise AdmissionDenied("HRB_RESOURCES_MISSING", "HRB lease resources are missing")
    for key in ("cpu_threads", "ram_mb", "vram_mb"):
        if _positive_int(granted.get(key, 0), f"lease.resources.{key}") < _positive_int(requested.get(key, 0), f"resource_profile.{key}"):
            raise AdmissionDenied("HRB_RESOURCE_EXCEEDED", f"requested {key} exceeds the HRB lease")

    requested_devices = [str(x) for x in requested.get("gpu_devices", [])]
    granted_devices = {str(x) for x in granted.get("gpu_devices", [])}
    if any(device not in granted_devices for device in requested_devices):
        raise AdmissionDenied("HRB_GPU_NOT_GRANTED", "requested GPU identity is not present in the HRB lease")

    requested_virtual = requested.get("virtual_profile") or {}
    granted_virtual = lease.get("virtual_limits") or {}
    for key in ("cu", "tu"):
        requested_value = _positive_int(requested_virtual.get(key, 0), f"virtual_profile.{key}")
        granted_value = _positive_int(granted_virtual.get(key, 0), f"lease.virtual_limits.{key}")
        if requested_value > granted_value:
            raise AdmissionDenied("VIRTUAL_PROFILE_EXCEEDED", f"requested {key} exceeds the HRB virtual limit")
    return lease


def validate_request(payload: dict[str, Any], lease_root: str | Path, now: datetime | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AdmissionDenied("REQUEST_NOT_OBJECT", "request must be a JSON object", 422)
    required = {"input_media", "output_dir", "hrb_lease_id", "resource_profile"}
    missing = sorted(required - set(payload))
    if missing:
        raise AdmissionDenied("REQUEST_FIELDS_MISSING", f"missing required fields: {', '.join(missing)}", 422)

    input_media = Path(str(payload.get("input_media", "")))
    output_dir = Path(str(payload.get("output_dir", "")))
    if not input_media.is_absolute() or not output_dir.is_absolute():
        raise AdmissionDenied("PATH_NOT_ABSOLUTE", "input_media and output_dir must be absolute paths", 422)

    profile = payload.get("resource_profile")
    if not isinstance(profile, dict):
        raise AdmissionDenied("RESOURCE_PROFILE_INVALID", "resource_profile must be an object", 422)
    normalized = {
        "cpu_threads": _positive_int(profile.get("cpu_threads"), "resource_profile.cpu_threads"),
        "ram_mb": _positive_int(profile.get("ram_mb"), "resource_profile.ram_mb"),
        "vram_mb": _positive_int(profile.get("vram_mb"), "resource_profile.vram_mb"),
        "gpu_devices": [str(x) for x in profile.get("gpu_devices", [])],
        "virtual_profile": profile.get("virtual_profile") or {},
    }
    if not isinstance(normalized["virtual_profile"], dict):
        raise AdmissionDenied("VIRTUAL_PROFILE_INVALID", "virtual_profile must be an object", 422)
    _positive_int(normalized["virtual_profile"].get("cu"), "virtual_profile.cu")
    _positive_int(normalized["virtual_profile"].get("tu"), "virtual_profile.tu")
    lease = validate_hrb_lease(str(payload.get("hrb_lease_id")), lease_root, normalized, now=now)
    return {"result": "PASS", "workload_id": WORKLOAD_ID, "lease": lease, "resource_profile": normalized}
