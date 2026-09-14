#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_DEFAULT = ROOT / "evidence/receipts/resource-admission-current-host.json"
BROKER_DEFAULT = "/usr/local/bin/fa3-host-resource-broker"
LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
FORBIDDEN_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}
COLLECTOR_ID = "FA3-RESOURCE-ADMISSION-CURRENT-HOST-COLLECTOR-001"
COLLECTOR_VERSION = "1.0.0"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_obj(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(command: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, "", repr(exc)


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return default


def os_release() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in read_text(Path("/etc/os-release")).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip().strip('"')
    return result


def cpu_info() -> dict[str, Any]:
    rc, stdout, _ = run(["lscpu", "-J"])
    fields: dict[str, str] = {}
    if rc == 0:
        try:
            data = json.loads(stdout)
            for item in data.get("lscpu", []):
                fields[str(item.get("field", "")).rstrip(":")] = str(item.get("data", ""))
        except json.JSONDecodeError:
            pass
    def integer(name: str, default: int = 0) -> int:
        try:
            return int(fields.get(name, default))
        except ValueError:
            return default
    sockets = integer("Socket(s)", 0)
    cores_per_socket = integer("Core(s) per socket", 0)
    physical = sockets * cores_per_socket if sockets and cores_per_socket else 0
    microcodes = sorted(set(re.findall(r"^microcode\s*:\s*(\S+)", read_text(Path("/proc/cpuinfo")), re.M)))
    return {
        "model": fields.get("Model name", platform.processor() or "UNKNOWN"),
        "architecture": fields.get("Architecture", platform.machine()),
        "sockets": sockets,
        "cores_per_socket": cores_per_socket,
        "physical_cores": physical,
        "logical_cpus": integer("CPU(s)", os.cpu_count() or 0),
        "threads_per_core": integer("Thread(s) per core", 0),
        "numa_nodes": integer("NUMA node(s)", 0),
        "microcode": microcodes or ["UNKNOWN"],
    }


def memory_total_bytes() -> int:
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", read_text(Path("/proc/meminfo")), re.M)
    return int(match.group(1)) * 1024 if match else 0


def nvidia_accelerators() -> list[dict[str, Any]]:
    if shutil.which("nvidia-smi") is None:
        return []
    query = "index,uuid,pci.bus_id,name,driver_version,memory.total,temperature.gpu"
    rc, stdout, _ = run(["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    if rc != 0:
        return []
    result: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 7:
            continue
        try:
            index = int(parts[0]); memory_mib = float(parts[5]); temperature = float(parts[6])
        except ValueError:
            continue
        bdf = parts[2].lower()
        if bdf.startswith("00000000:"):
            bdf = bdf[5:]
        result.append({
            "index_observed": index,
            "uuid": parts[1],
            "pci_bdf": bdf,
            "name": parts[3],
            "driver_version": parts[4],
            "memory_total_bytes": int(memory_mib * 1024 * 1024),
            "temperature_c": temperature,
        })
    return result


def storage_identity() -> Any:
    rc, stdout, _ = run(["lsblk", "-J", "-o", "NAME,KNAME,TYPE,SIZE,FSTYPE,UUID,WWN,MOUNTPOINTS"])
    if rc != 0:
        return {"status": "UNAVAILABLE"}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"status": "UNPARSEABLE"}


def runtime_versions(accelerators: list[dict[str, Any]]) -> dict[str, Any]:
    systemd_rc, systemd_out, _ = run(["systemd", "--version"])
    return {
        "python": platform.python_version(),
        "systemd": systemd_out.splitlines()[0] if systemd_rc == 0 and systemd_out else "UNKNOWN",
        "nvidia_driver": accelerators[0]["driver_version"] if accelerators else None,
    }


def collect_host_attestation() -> tuple[dict[str, Any], str]:
    cpu = cpu_info()
    accelerators = nvidia_accelerators()
    attestation = {
        "schema": "fa3.host-attestation.v1",
        "host_attestation_id": f"FA3-HOST-{socket.gethostname()}-{int(time.time())}",
        "captured_at": now(),
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "os_release": os_release(),
        "cpu_model": cpu["model"],
        "cpu_microcode": cpu["microcode"],
        "cpu_topology": {
            "architecture": cpu["architecture"],
            "sockets": cpu["sockets"],
            "physical_cores": cpu["physical_cores"],
            "logical_cpus": cpu["logical_cpus"],
            "threads_per_core": cpu["threads_per_core"],
        },
        "numa_topology": {"nodes": cpu["numa_nodes"]},
        "memory_total_bytes": memory_total_bytes(),
        "accelerators": accelerators,
        "driver_versions": {"nvidia": accelerators[0]["driver_version"] if accelerators else None},
        "runtime_versions": runtime_versions(accelerators),
        "pcie_topology": [{"uuid": a["uuid"], "pci_bdf": a["pci_bdf"]} for a in accelerators],
        "storage_identity": storage_identity(),
        "thermal_power_state": {"gpu_temperature_c": {a["uuid"]: a["temperature_c"] for a in accelerators}},
        "collector_version": COLLECTOR_VERSION,
        "secret_collection": "PROHIBITED",
    }
    return attestation, sha256_obj(attestation)


def validate_lease(path: Path, broker: str, accelerators: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        lease = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"LEASE_UNREADABLE:{exc!r}"]
    required = ["schema", "lease_id", "issuer", "accelerator_uuid", "expires_epoch", "purpose", "status", "placement", "signature"]
    missing = [key for key in required if key not in lease]
    if missing:
        errors.append("LEASE_MISSING_FIELDS:" + ",".join(missing))
    if lease.get("schema") != LEASE_SCHEMA:
        errors.append("LEASE_SCHEMA_MISMATCH")
    if lease.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001":
        errors.append("LEASE_ISSUER_MISMATCH")
    if lease.get("status") != "ACTIVE":
        errors.append("LEASE_NOT_ACTIVE")
    try:
        if int(lease.get("expires_epoch", 0)) <= int(time.time()):
            errors.append("LEASE_EXPIRED")
    except (TypeError, ValueError):
        errors.append("LEASE_EXPIRY_INVALID")
    uuid = str(lease.get("accelerator_uuid", ""))
    placement = lease.get("placement") if isinstance(lease.get("placement"), dict) else {}
    bdf = str(placement.get("pci_bus_id", "")).lower()
    if bdf.startswith("00000000:"):
        bdf = bdf[5:]
    matches = [a for a in accelerators if a["uuid"] == uuid and a["pci_bdf"] == bdf]
    if len(matches) != 1:
        errors.append("LEASE_ACCELERATOR_NOT_BOUND_TO_LIVE_UUID_BDF")
    signature = lease.get("signature")
    if not isinstance(signature, dict) or signature.get("alg") != "HMAC-SHA256" or not re.fullmatch(r"[0-9a-f]{64}", str(signature.get("value", ""))):
        errors.append("LEASE_SIGNATURE_DESCRIPTOR_INVALID")
    broker_path = shutil.which(broker) if "/" not in broker else broker
    if not broker_path or not Path(broker_path).is_file():
        errors.append("HRB_BROKER_UNAVAILABLE")
    else:
        rc, stdout, _ = run([str(broker_path), "validate-lease", str(path)], timeout=20)
        if rc != 0 or stdout.strip().splitlines()[-1:] != ["VALID"]:
            errors.append("HRB_BROKER_VALIDATION_FAILED")
    return lease, errors


def load_workload(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        workload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"WORKLOAD_UNREADABLE:{exc!r}"]
    errors: list[str] = []
    if workload.get("schema") != "fa3.workload-resource-envelope.v1":
        errors.append("WORKLOAD_SCHEMA_MISMATCH")
    requirements = workload.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        errors.append("WORKLOAD_REQUIREMENTS_EMPTY")
        requirements = []
    for item in requirements:
        metric = item.get("metric") if isinstance(item, dict) else None
        if metric in FORBIDDEN_METRICS:
            errors.append(f"FORBIDDEN_ADMISSION_METRIC:{metric}")
    return workload, errors


def build_compute_profile(attestation: dict[str, Any], attestation_sha: str, lease: dict[str, Any] | None) -> dict[str, Any]:
    cpu_topology = attestation.get("cpu_topology", {})
    metrics: dict[str, Any] = {
        "cpu.physical_cores": int(cpu_topology.get("physical_cores", 0)),
        "memory.total_gib": round(int(attestation.get("memory_total_bytes", 0)) / (1024 ** 3), 3),
        "numa.nodes": int(attestation.get("numa_topology", {}).get("nodes", 0)),
    }
    selected: list[dict[str, Any]] = []
    if lease:
        uuid = str(lease.get("accelerator_uuid", ""))
        selected = [a for a in attestation.get("accelerators", []) if a.get("uuid") == uuid]
        if len(selected) == 1:
            metrics["gpu.vram_gib"] = round(int(selected[0].get("memory_total_bytes", 0)) / (1024 ** 3), 3)
            metrics["gpu.device_uuid"] = selected[0].get("uuid")
            metrics["gpu.pci_bdf"] = selected[0].get("pci_bdf")
    return {
        "schema": "fa3.compute-profile.v1",
        "host_attestation_sha256": attestation_sha,
        "metrics": metrics,
        "selected_accelerator_set": [{"uuid": a["uuid"], "pci_bdf": a["pci_bdf"]} for a in selected],
        "diagnostic_aggregates": {},
        "measurement_semantics": "LIVE_DISCOVERY_ONLY_NO_SYNTHETIC_PERFORMANCE_SCORE",
    }


def release_manifest_digest(root: Path) -> str:
    path = root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
    return "sha256:" + sha256_file(path)


def collect(root: Path, workload_path: Path, lease_path: Path, receipt_path: Path, broker: str) -> dict[str, Any]:
    from fa3_resource_evidence_normalization_gate import _canonical_payload_hash, evaluate_resource_admission

    attestation, attestation_sha = collect_host_attestation()
    workload, workload_errors = load_workload(workload_path)
    lease, lease_errors = validate_lease(lease_path, broker, attestation.get("accelerators", []))
    profile = build_compute_profile(attestation, attestation_sha, lease)

    errors = workload_errors + lease_errors
    admission = None
    if not errors and workload is not None and lease is not None:
        admission = evaluate_resource_admission(
            profile["metrics"],
            workload["requirements"],
            {"status": "VALID", "lease_id": lease.get("lease_id")},
        )
        if admission.get("result") != "PASS":
            errors.append("RESOURCE_REQUIREMENTS_BLOCKED")

    payload = {
        "schema": "fa3.resource-admission-current-host.payload.v1",
        "host_attestation": attestation,
        "host_attestation_sha256": attestation_sha,
        "compute_profile": profile,
        "workload_resource_envelope": workload,
        "workload_resource_envelope_sha256": sha256_file(workload_path) if workload_path.is_file() else None,
        "hrb_lease_identity": {
            "schema": lease.get("schema") if lease else None,
            "lease_id": lease.get("lease_id") if lease else None,
            "issuer": lease.get("issuer") if lease else None,
            "accelerator_uuid": lease.get("accelerator_uuid") if lease else None,
            "pci_bus_id": lease.get("placement", {}).get("pci_bus_id") if lease and isinstance(lease.get("placement"), dict) else None,
            "purpose": lease.get("purpose") if lease else None,
            "expires_epoch": lease.get("expires_epoch") if lease else None,
            "lease_file_sha256": sha256_file(lease_path) if lease_path.is_file() else None,
            "broker_validation": not lease_errors,
        },
        "admission": admission,
        "errors": errors,
        "cross_metric_compensation": False,
        "cu_tu_admission_authority": False,
    }
    passed = not errors and admission is not None and admission.get("result") == "PASS"
    envelope = {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": f"FA3-RESOURCE-ADMISSION-CURRENT-HOST-{int(time.time())}",
        "evidence_class": "CURRENT_HOST_ADMISSION",
        "subject": {
            "profile_id": "FA3-RESOURCE-ADMISSION-CONTRACTS-001",
            "provider_id": None,
            "gate_id": "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001",
        },
        "canonical_context": {
            "architecture_release": "2026-08-23/v3.0.11",
            "release_baseline_id": "FA3-RELEASE-CAPABILITY-BASELINE-001",
            "release_manifest_digest": release_manifest_digest(root),
        },
        "execution_context": {
            "host_attestation_ref": attestation["host_attestation_id"],
            "compute_profile_ref": "INLINE_SHA256:" + sha256_obj(profile),
            "workload_resource_envelope_ref": str(workload_path.resolve()),
            "hrb_lease_ref": str(lease_path.resolve()),
            "diagnostics": {},
        },
        "provenance": {
            "collector_id": COLLECTOR_ID,
            "collector_revision": COLLECTOR_VERSION,
            "generated_at": now(),
            "artifact_digests": [
                {"kind": "host_attestation", "sha256": attestation_sha},
                {"kind": "workload_resource_envelope", "sha256": sha256_file(workload_path) if workload_path.is_file() else None},
                {"kind": "hrb_lease", "sha256": sha256_file(lease_path) if lease_path.is_file() else None},
            ],
        },
        "integrity": {"payload_sha256": _canonical_payload_hash(payload)},
        "result": {
            "status": "PASS" if passed else "BLOCKED",
            "scope": "COMPONENT_CURRENT_HOST_RESOURCE_ADMISSION",
            "claims": ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"] if passed else [],
            "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E", "END_TO_END_ZERO_COPY"],
        },
        "payload_schema_id": "fa3.resource-admission-current-host.payload.v1",
        "payload": payload,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return envelope


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real FA3 current-host resource-admission evidence")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--workload-envelope", required=True)
    parser.add_argument("--hrb-lease", required=True)
    parser.add_argument("--receipt", default=str(RECEIPT_DEFAULT))
    parser.add_argument("--broker", default=BROKER_DEFAULT)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    sys_path = str(root / "src")
    if sys_path not in os.sys.path:
        os.sys.path.insert(0, sys_path)
    envelope = collect(root, Path(args.workload_envelope), Path(args.hrb_lease), Path(args.receipt), args.broker)
    print(json.dumps({
        "evidence_id": envelope["evidence_id"],
        "status": envelope["result"]["status"],
        "claims": envelope["result"]["claims"],
        "non_claims": envelope["result"]["non_claims"],
        "receipt": str(Path(args.receipt).resolve()),
    }, indent=2))
    return 0 if envelope["result"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
