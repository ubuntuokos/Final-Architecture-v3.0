#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import platform
import re
import socket
import subprocess
from pathlib import Path
from typing import Any

from fa3_hardware_discovery import discover_accelerator_devices, discover_cpu_topology


ATTESTATION_SCHEMA = "fa3.host-attestation.v1"
ARTIFACT_SCHEMA = "fa3.host-attestation-artifact.v1"
COLLECTOR_ID = "FA3-HOST-ATTESTATION-CURRENT-HOST-COLLECTOR-001"
COLLECTOR_VERSION = "1.0.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_IDENTITY = (
    "host_attestation_id",
    "captured_at",
    "kernel",
    "os_release",
    "cpu_model",
    "cpu_microcode",
    "cpu_topology",
    "numa_topology",
    "memory_total_bytes",
    "accelerators",
    "driver_versions",
    "runtime_versions",
    "pcie_topology",
    "storage_identity",
    "thermal_power_state",
    "collector_version",
)


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def attestation_ref(attestation: dict[str, Any]) -> str:
    return "sha256:" + canonical_sha256(attestation)


def _fresh(value: Any, max_age_hours: int = 24) -> bool:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        age = dt.datetime.now(dt.timezone.utc) - parsed.astimezone(dt.timezone.utc)
        return dt.timedelta(0) <= age <= dt.timedelta(hours=max_age_hours)
    except Exception:
        return False


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _command(argv: list[str], timeout: int = 15) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, (proc.stdout or proc.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, repr(exc)


def _os_release() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read(Path("/etc/os-release")).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value.strip().strip('"')
    return result


def _cpu_identity() -> tuple[str, list[str]]:
    text = _read(Path("/proc/cpuinfo"))
    models = sorted(set(re.findall(r"^(?:model name|Hardware)\s*:\s*(.+)$", text, re.M)))
    microcode = sorted(set(re.findall(r"^microcode\s*:\s*(\S+)$", text, re.M)))
    return (models[0] if models else platform.processor() or "UNKNOWN", microcode or ["UNKNOWN"])


def _memory_total_bytes() -> int:
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", _read(Path("/proc/meminfo")), re.M)
    return int(match.group(1)) * 1024 if match else 0


def _storage_identity() -> dict[str, Any]:
    rc, output = _command(["lsblk", "-J", "-o", "NAME,KNAME,TYPE,SIZE,FSTYPE,UUID,WWN,MOUNTPOINTS"])
    if rc != 0:
        return {"status": "UNAVAILABLE", "collector": "lsblk"}
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        return {"status": "UNPARSEABLE", "collector": "lsblk"}
    return {"status": "OBSERVED", "collector": "lsblk", "value": value}


def _thermal_power_state() -> dict[str, Any]:
    zones: list[dict[str, Any]] = []
    for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        raw = _read(zone / "temp")
        try:
            temperature_millic = int(raw)
        except ValueError:
            continue
        zones.append({
            "zone": zone.name,
            "type": _read(zone / "type") or "UNKNOWN",
            "temperature_millicelsius": temperature_millic,
        })
    return {"status": "OBSERVED" if zones else "UNAVAILABLE", "thermal_zones": zones}


def _runtime_versions() -> dict[str, Any]:
    versions: dict[str, Any] = {"python": platform.python_version()}
    for name, argv in {
        "podman": ["podman", "--version"],
        "runsc": ["runsc", "--version"],
        "wasmtime": ["wasmtime", "--version"],
    }.items():
        rc, output = _command(argv)
        versions[name] = output.splitlines()[0] if rc == 0 and output else None
    return versions


def collect_live_attestation() -> dict[str, Any]:
    topology = discover_cpu_topology()
    model, microcode = _cpu_identity()
    accelerator_rows = [device.as_dict() for device in discover_accelerator_devices()]
    driver_versions = {
        row["pci_bdf"]: {"kernel_driver": row.get("kernel_driver"), "vendor": row.get("vendor")}
        for row in accelerator_rows
        if row.get("pci_bdf")
    }
    return {
        "schema": ATTESTATION_SCHEMA,
        "host_attestation_id": f"FA3-HOST-{socket.gethostname()}-{int(dt.datetime.now().timestamp())}",
        "captured_at": utcnow(),
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "os_release": _os_release(),
        "cpu_model": model,
        "cpu_microcode": microcode,
        "cpu_topology": topology,
        "numa_topology": {
            "nodes": topology.get("summary", {}).get("numa_domains_total"),
            "source": topology.get("source"),
        },
        "memory_total_bytes": _memory_total_bytes(),
        "accelerators": accelerator_rows,
        "driver_versions": driver_versions,
        "runtime_versions": _runtime_versions(),
        "pcie_topology": [
            {
                "discovery_id": row.get("discovery_id"),
                "pci_bdf": row.get("pci_bdf"),
                "numa_node": row.get("numa_node"),
            }
            for row in accelerator_rows
        ],
        "storage_identity": _storage_identity(),
        "thermal_power_state": _thermal_power_state(),
        "collector_id": COLLECTOR_ID,
        "collector_version": COLLECTOR_VERSION,
        "secret_collection": "PROHIBITED",
    }


def build_artifact(attestation: dict[str, Any]) -> dict[str, Any]:
    digest = canonical_sha256(attestation)
    return {
        "schema": ARTIFACT_SCHEMA,
        "host_attestation_ref": "sha256:" + digest,
        "host_attestation_sha256": digest,
        "attestation": attestation,
    }


def validate_attestation(
    attestation: Any,
    *,
    require_fresh: bool = True,
    require_current_host: bool = True,
) -> list[str]:
    if not isinstance(attestation, dict):
        return ["host attestation must be an object"]
    findings: list[str] = []
    if attestation.get("schema") != ATTESTATION_SCHEMA:
        findings.append("host attestation schema mismatch")
    for key in REQUIRED_IDENTITY:
        if key not in attestation or attestation.get(key) in (None, ""):
            findings.append(f"host attestation required identity missing: {key}")
    if attestation.get("secret_collection") != "PROHIBITED":
        findings.append("host attestation secret boundary mismatch")
    if not isinstance(attestation.get("accelerators"), list):
        findings.append("host attestation accelerators must be a 0..N list")
    if not isinstance(attestation.get("memory_total_bytes"), int) or int(attestation.get("memory_total_bytes", 0)) <= 0:
        findings.append("host attestation memory_total_bytes invalid")
    if require_fresh and not _fresh(attestation.get("captured_at")):
        findings.append("host attestation timestamp is stale or invalid")
    if require_current_host:
        if attestation.get("host") != socket.gethostname():
            findings.append("host attestation hostname does not match current host")
        if attestation.get("kernel") != platform.release():
            findings.append("host attestation kernel does not match current host")
    return findings


def validate_artifact(
    artifact: Any,
    *,
    require_fresh: bool = True,
    require_current_host: bool = True,
) -> tuple[list[str], str, dict[str, Any]]:
    if not isinstance(artifact, dict):
        return ["host attestation artifact must be an object"], "", {}
    findings: list[str] = []
    if artifact.get("schema") != ARTIFACT_SCHEMA:
        findings.append("host attestation artifact schema mismatch")
    attestation = artifact.get("attestation")
    findings.extend(validate_attestation(
        attestation,
        require_fresh=require_fresh,
        require_current_host=require_current_host,
    ))
    if not isinstance(attestation, dict):
        return findings, "", {}
    digest = canonical_sha256(attestation)
    expected_ref = "sha256:" + digest
    declared_digest = str(artifact.get("host_attestation_sha256") or "")
    declared_ref = str(artifact.get("host_attestation_ref") or "")
    if not SHA256_RE.fullmatch(declared_digest):
        findings.append("host attestation artifact digest format invalid")
    if not REF_RE.fullmatch(declared_ref):
        findings.append("host attestation reference must be sha256:<64 lowercase hex>")
    if declared_digest != digest:
        findings.append("host attestation artifact digest mismatch")
    if declared_ref != expected_ref:
        findings.append("host attestation reference does not bind the canonical attestation digest")
    return findings, expected_ref, attestation


def load_artifact(
    path: Path,
    *,
    require_fresh: bool = True,
    require_current_host: bool = True,
) -> tuple[list[str], str, dict[str, Any], dict[str, Any]]:
    if not path.is_file():
        return ["host attestation artifact missing"], "", {}, {}
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"host attestation artifact unreadable: {exc}"], "", {}, {}
    findings, reference, attestation = validate_artifact(
        artifact,
        require_fresh=require_fresh,
        require_current_host=require_current_host,
    )
    return findings, reference, attestation, artifact
