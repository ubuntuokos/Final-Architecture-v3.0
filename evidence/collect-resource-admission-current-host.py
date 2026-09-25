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
BROKER_DEFAULT = "/usr/local/bin/fa3-host-resource-broker-validator"
AUTH_BROKER_DEFAULT = "/usr/local/bin/fa3-host-resource-broker-admission"
LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
AUTH_SCHEMA = "fa3.hrb-admission-authorization.v1"
COLLECTOR_ID = "FA3-RESOURCE-ADMISSION-CURRENT-HOST-COLLECTOR-001"
COLLECTOR_VERSION = "2.1.0"
_BDF_RE = re.compile(r"^(?P<domain>[0-9a-fA-F]{4,8}):(?P<bus>[0-9a-fA-F]{2}):(?P<device>[0-9a-fA-F]{2})\.(?P<function>[0-7])$")


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


def normalize_bdf(value: Any) -> str:
    text = str(value or "").strip().lower()
    match = _BDF_RE.fullmatch(text)
    if not match:
        return text
    return f"{match.group('domain')[-4:].lower()}:{match.group('bus').lower()}:{match.group('device').lower()}.{match.group('function')}"


def purpose_matches_workload(purpose: Any, workload_id: Any) -> bool:
    purpose_text = str(purpose or "").strip().lower()
    workload_text = str(workload_id or "").strip().lower()
    return bool(workload_text) and (purpose_text == workload_text or workload_text in purpose_text)


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
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value.strip().strip('"')
    return result


def cpu_info() -> dict[str, Any]:
    rc, stdout, _ = run(["lscpu", "-J"])
    fields: dict[str, str] = {}
    if rc == 0:
        try:
            for item in json.loads(stdout).get("lscpu", []):
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
    return {
        "model": fields.get("Model name", platform.processor() or "UNKNOWN"),
        "architecture": fields.get("Architecture", platform.machine()),
        "sockets": sockets,
        "physical_cores": sockets * cores_per_socket if sockets and cores_per_socket else 0,
        "logical_cpus": integer("CPU(s)", os.cpu_count() or 0),
        "threads_per_core": integer("Thread(s) per core", 0),
        "numa_nodes": integer("NUMA node(s)", 0),
        "microcode": sorted(set(re.findall(r"^microcode\s*:\s*(\S+)", read_text(Path("/proc/cpuinfo")), re.M))) or ["UNKNOWN"],
    }


def memory_total_bytes() -> int:
    match = re.search(r"^MemTotal:\s+(\d+)\s+kB", read_text(Path("/proc/meminfo")), re.M)
    return int(match.group(1)) * 1024 if match else 0


def nvidia_accelerators() -> list[dict[str, Any]]:
    if shutil.which("nvidia-smi") is None:
        return []
    query = "index,uuid,pci.bus_id,name,driver_version,memory.total,temperature.gpu,compute_cap"
    rc, stdout, _ = run(["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    if rc != 0:
        return []
    result: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 8:
            continue
        try:
            result.append({
                "index_observed": int(parts[0]),
                "uuid": parts[1],
                "pci_bdf": normalize_bdf(parts[2]),
                "name": parts[3],
                "vendor": "NVIDIA",
                "driver_version": parts[4],
                "memory_total_bytes": int(float(parts[5]) * 1024 * 1024),
                "temperature_c": float(parts[6]),
                "cuda_compute_capability": float(parts[7]),
            })
        except ValueError:
            continue
    return result


def storage_identity() -> Any:
    rc, stdout, _ = run(["lsblk", "-J", "-o", "NAME,KNAME,TYPE,SIZE,FSTYPE,UUID,WWN,MOUNTPOINTS"])
    if rc != 0:
        return {"status": "UNAVAILABLE"}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"status": "UNPARSEABLE"}


def collect_host_attestation(*, collect_accelerators: bool) -> tuple[dict[str, Any], str]:
    cpu = cpu_info()
    accelerators = nvidia_accelerators() if collect_accelerators else []
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
        "runtime_versions": {"python": platform.python_version(), "nvidia_driver": accelerators[0]["driver_version"] if accelerators else None},
        "pcie_topology": [{"uuid": a["uuid"], "pci_bdf": a["pci_bdf"]} for a in accelerators],
        "storage_identity": storage_identity(),
        "thermal_power_state": {"gpu_temperature_c": {a["uuid"]: a["temperature_c"] for a in accelerators}},
        "collector_version": COLLECTOR_VERSION,
        "secret_collection": "PROHIBITED",
    }
    return attestation, sha256_obj(attestation)


def load_workload(path: Path) -> tuple[dict[str, Any] | None, list[str], list[str], bool]:
    from fa3_resource_admission_policy import classify_requirements, validate_workload_requirements
    try:
        workload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"WORKLOAD_UNREADABLE:{exc!r}"], [], False
    errors: list[str] = []
    if workload.get("schema") != "fa3.workload-resource-envelope.v1":
        errors.append("WORKLOAD_SCHEMA_MISMATCH")
    if not str(workload.get("workload_id", "")).strip():
        errors.append("WORKLOAD_ID_MISSING")
    errors.extend(validate_workload_requirements(workload.get("requirements")))
    classes, accelerator_required = classify_requirements(workload.get("requirements", []))
    return workload, errors, classes, accelerator_required


def validate_accelerator_lease(path: Path, broker: str, accelerators: list[dict[str, Any]], workload: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        lease = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"LEASE_UNREADABLE:{exc!r}"]
    required = ["schema", "lease_id", "issuer", "accelerator_uuid", "memory_max_bytes", "expires_epoch", "issued_epoch", "purpose", "host", "status", "nonce", "placement", "enforcement", "signature"]
    missing = [key for key in required if key not in lease]
    if missing:
        errors.append("LEASE_MISSING_FIELDS:" + ",".join(missing))
    if lease.get("schema") != LEASE_SCHEMA:
        errors.append("LEASE_SCHEMA_MISMATCH")
    if lease.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001":
        errors.append("LEASE_ISSUER_MISMATCH")
    if lease.get("status") != "ACTIVE":
        errors.append("LEASE_NOT_ACTIVE")
    if str(lease.get("host", "")) != socket.gethostname():
        errors.append("LEASE_HOST_MISMATCH")
    try:
        if int(lease.get("expires_epoch", 0)) <= int(time.time()):
            errors.append("LEASE_EXPIRED")
    except (TypeError, ValueError):
        errors.append("LEASE_EXPIRY_INVALID")
    workload_id = workload.get("workload_id")
    if not purpose_matches_workload(lease.get("purpose"), workload_id):
        errors.append("LEASE_WORKLOAD_SCOPE_MISMATCH")
    try:
        memory_max_bytes = int(lease.get("memory_max_bytes", 0))
        if memory_max_bytes <= 0:
            errors.append("LEASE_MEMORY_BUDGET_INVALID")
    except (TypeError, ValueError):
        memory_max_bytes = 0
        errors.append("LEASE_MEMORY_BUDGET_INVALID")
    placement = lease.get("placement") if isinstance(lease.get("placement"), dict) else {}
    uuid = str(lease.get("accelerator_uuid", ""))
    bdf = normalize_bdf(placement.get("pci_bus_id"))
    matches = [a for a in accelerators if a.get("uuid") == uuid and normalize_bdf(a.get("pci_bdf")) == bdf]
    if len(matches) != 1:
        errors.append("LEASE_ACCELERATOR_NOT_BOUND_TO_LIVE_UUID_BDF")
    elif memory_max_bytes > int(matches[0].get("memory_total_bytes", 0)):
        errors.append("LEASE_MEMORY_BUDGET_EXCEEDS_PHYSICAL_VRAM")
    signature = lease.get("signature")
    if not isinstance(signature, dict) or signature.get("alg") != "HMAC-SHA256" or signature.get("key_id") != "host-local-v1" or not re.fullmatch(r"[0-9a-f]{64}", str(signature.get("value", ""))):
        errors.append("LEASE_SIGNATURE_DESCRIPTOR_INVALID")
    broker_path = shutil.which(broker) if "/" not in broker else broker
    if not broker_path or not Path(broker_path).is_file():
        errors.append("HRB_BROKER_UNAVAILABLE")
    else:
        rc, stdout, _ = run([str(broker_path), "validate-lease", str(path)], timeout=20)
        if rc != 0 or stdout.strip().splitlines()[-1:] != ["VALID"]:
            errors.append("HRB_BROKER_VALIDATION_FAILED")
    return lease, errors



def validate_admission_authorization(
    path: Path,
    broker: str,
    workload_path: Path,
    workload: dict[str, Any],
    requested_classes: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        authorization = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"AUTHORIZATION_UNREADABLE:{exc!r}"]
    if not isinstance(authorization, dict):
        return None, ["AUTHORIZATION_NOT_OBJECT"]
    required = [
        "schema", "authorization_id", "authority", "issuer", "status", "host", "workload_id",
        "workload_envelope_sha256", "requested_resource_classes", "accelerator_required",
        "issued_epoch", "expires_epoch", "semantics", "authentication",
    ]
    missing = [key for key in required if key not in authorization]
    if missing:
        errors.append("AUTHORIZATION_MISSING_FIELDS:" + ",".join(missing))
    if authorization.get("schema") != AUTH_SCHEMA:
        errors.append("AUTHORIZATION_SCHEMA_MISMATCH")
    if authorization.get("authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001" or authorization.get("issuer") != "FA3-HOST-RESOURCE-BROKER-001":
        errors.append("AUTHORIZATION_AUTHORITY_MISMATCH")
    if authorization.get("status") != "ACTIVE":
        errors.append("AUTHORIZATION_NOT_ACTIVE")
    if str(authorization.get("host", "")) != socket.gethostname():
        errors.append("AUTHORIZATION_HOST_MISMATCH")
    if str(authorization.get("workload_id", "")) != str(workload.get("workload_id", "")):
        errors.append("AUTHORIZATION_WORKLOAD_SCOPE_MISMATCH")
    if authorization.get("workload_envelope_sha256") != sha256_file(workload_path):
        errors.append("AUTHORIZATION_WORKLOAD_DIGEST_MISMATCH")
    if authorization.get("requested_resource_classes") != requested_classes:
        errors.append("AUTHORIZATION_RESOURCE_CLASSES_MISMATCH")
    if authorization.get("accelerator_required") is not ("accelerator" in requested_classes):
        errors.append("AUTHORIZATION_ACCELERATOR_FLAG_MISMATCH")
    try:
        if int(authorization.get("expires_epoch", 0)) <= int(time.time()):
            errors.append("AUTHORIZATION_EXPIRED")
    except (TypeError, ValueError):
        errors.append("AUTHORIZATION_EXPIRY_INVALID")
    semantics = authorization.get("semantics", {})
    if not isinstance(semantics, dict) or semantics.get("authorization_is_not_resource_lease") is not True or semantics.get("durable_evidence_signature") is not False:
        errors.append("AUTHORIZATION_SEMANTICS_INVALID")
    broker_path = shutil.which(broker) if "/" not in broker else broker
    if not broker_path or not Path(broker_path).is_file():
        errors.append("HRB_AUTHORIZATION_BROKER_UNAVAILABLE")
    else:
        rc, stdout, _ = run([str(broker_path), "validate", "--authorization", str(path)], timeout=20)
        if rc != 0:
            errors.append("HRB_AUTHORIZATION_BROKER_VALIDATION_FAILED")
    return authorization, errors


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
        lease_bdf = normalize_bdf((lease.get("placement") or {}).get("pci_bus_id") if isinstance(lease.get("placement"), dict) else "")
        selected = [a for a in attestation.get("accelerators", []) if a.get("uuid") == uuid and normalize_bdf(a.get("pci_bdf")) == lease_bdf]
        if len(selected) == 1:
            physical_bytes = int(selected[0].get("memory_total_bytes", 0))
            try:
                lease_bytes = max(0, int(lease.get("memory_max_bytes", 0)))
            except (TypeError, ValueError):
                lease_bytes = 0
            effective_bytes = min(physical_bytes, lease_bytes)
            metrics.update({
                "gpu.physical_vram_gib": round(physical_bytes / (1024 ** 3), 3),
                "gpu.lease_memory_gib": round(lease_bytes / (1024 ** 3), 3),
                "gpu.vram_gib": round(effective_bytes / (1024 ** 3), 3),
                "gpu.vendor": selected[0].get("vendor"),
                "gpu.cuda_compute_capability": float(selected[0].get("cuda_compute_capability", 0.0)),
                "gpu.device_uuid": selected[0].get("uuid"),
                "gpu.pci_bdf": normalize_bdf(selected[0].get("pci_bdf")),
            })
    return {
        "schema": "fa3.compute-profile.v1",
        "host_attestation_sha256": attestation_sha,
        "metrics": metrics,
        "selected_accelerator_set": [{"uuid": a["uuid"], "pci_bdf": normalize_bdf(a["pci_bdf"])} for a in selected],
        "diagnostic_aggregates": {},
        "measurement_semantics": "LIVE_DISCOVERY_WITH_WORKLOAD_CONDITIONAL_HRB_ACCELERATOR_LEASE_BOUNDING",
    }


def release_manifest_digest(root: Path) -> str:
    path = root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
    return "sha256:" + sha256_file(path)


def collect(
    root: Path,
    workload_path: Path,
    lease_path: Path | None,
    authorization_path: Path | None,
    receipt_path: Path,
    broker: str,
    authorization_broker: str,
) -> dict[str, Any]:
    from fa3_resource_evidence_normalization_gate import _canonical_payload_hash, evaluate_resource_admission

    workload, workload_errors, requested_classes, accelerator_required = load_workload(workload_path)
    attestation, attestation_sha = collect_host_attestation(collect_accelerators=accelerator_required)
    lease: dict[str, Any] | None = None
    authorization: dict[str, Any] | None = None
    lease_errors: list[str] = []
    authorization_errors: list[str] = []
    if accelerator_required:
        if lease_path is None:
            lease_errors.append("ACCELERATOR_WORKLOAD_REQUIRES_HRB_LEASE")
        elif workload is not None:
            lease, lease_errors = validate_accelerator_lease(lease_path, broker, attestation.get("accelerators", []), workload)
    else:
        if authorization_path is None:
            authorization_errors.append("CPU_ONLY_WORKLOAD_REQUIRES_HRB_ADMISSION_AUTHORIZATION")
        elif workload is not None:
            authorization, authorization_errors = validate_admission_authorization(
                authorization_path, authorization_broker, workload_path, workload, requested_classes
            )

    profile = build_compute_profile(attestation, attestation_sha, lease)
    errors = workload_errors + lease_errors + authorization_errors
    admission = None
    authorization_for_evaluation: dict[str, Any] | None = None
    if lease is not None and not lease_errors:
        authorization_for_evaluation = {"status": "VALID", "authorization_id": lease.get("lease_id")}
    elif authorization is not None and not authorization_errors:
        authorization_for_evaluation = {"status": "VALID", "authorization_id": authorization.get("authorization_id")}
    if not errors and workload is not None and authorization_for_evaluation is not None:
        admission = evaluate_resource_admission(profile["metrics"], workload["requirements"], authorization_for_evaluation)
        if admission.get("result") != "PASS":
            errors.append("RESOURCE_REQUIREMENTS_BLOCKED")

    lease_identity = {}
    hrb_authorization = {}
    if lease is not None:
        lease_identity = {
            "schema": lease.get("schema"),
            "lease_id": lease.get("lease_id"),
            "issuer": lease.get("issuer"),
            "status": lease.get("status"),
            "host": lease.get("host"),
            "accelerator_uuid": lease.get("accelerator_uuid"),
            "pci_bus_id": normalize_bdf(lease.get("placement", {}).get("pci_bus_id")) if isinstance(lease.get("placement"), dict) else None,
            "numa_node": lease.get("placement", {}).get("numa_node") if isinstance(lease.get("placement"), dict) else None,
            "memory_max_bytes": lease.get("memory_max_bytes"),
            "purpose": lease.get("purpose"),
            "issued_epoch": lease.get("issued_epoch"),
            "expires_epoch": lease.get("expires_epoch"),
            "lease_file_sha256": sha256_file(lease_path) if lease_path and lease_path.is_file() else None,
            "broker_validation": not lease_errors,
        }
        hrb_authorization = {
            "authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "authorization_id": lease.get("lease_id"),
            "status": "VALID" if not lease_errors else "INVALID",
            "workload_id": workload.get("workload_id") if isinstance(workload, dict) else None,
            "workload_envelope_sha256": sha256_file(workload_path) if workload_path.is_file() else None,
            "requested_resource_classes": requested_classes,
            "accelerator_required": True,
            "host": lease.get("host"),
            "issued_epoch": lease.get("issued_epoch"),
            "expires_epoch": lease.get("expires_epoch"),
            "broker_validation": not lease_errors,
            "source": "ACCELERATOR_EXECUTION_LEASE",
        }
    elif authorization is not None:
        hrb_authorization = {
            "schema": authorization.get("schema"),
            "authority": authorization.get("authority"),
            "authorization_id": authorization.get("authorization_id"),
            "status": "VALID" if not authorization_errors else "INVALID",
            "workload_id": authorization.get("workload_id"),
            "workload_envelope_sha256": authorization.get("workload_envelope_sha256"),
            "requested_resource_classes": authorization.get("requested_resource_classes"),
            "accelerator_required": authorization.get("accelerator_required"),
            "host": authorization.get("host"),
            "issued_epoch": authorization.get("issued_epoch"),
            "expires_epoch": authorization.get("expires_epoch"),
            "broker_validation": not authorization_errors,
            "source": "ADMISSION_AUTHORIZATION",
        }

    payload = {
        "schema": "fa3.resource-admission-current-host.payload.v1",
        "host_attestation": attestation,
        "host_attestation_sha256": attestation_sha,
        "compute_profile": profile,
        "workload_resource_envelope": workload,
        "workload_resource_envelope_sha256": sha256_file(workload_path) if workload_path.is_file() else None,
        "requested_resource_classes": requested_classes,
        "accelerator_required": accelerator_required,
        "hrb_authorization": hrb_authorization,
        "hrb_lease_identity": lease_identity,
        "admission": admission,
        "errors": errors,
        "cross_metric_compensation": False,
        "cu_tu_admission_authority": False,
    }
    passed = not errors and admission is not None and admission.get("result") == "PASS"
    artifact_digests = [
        {"kind": "host_attestation", "sha256": attestation_sha},
        {"kind": "workload_resource_envelope", "sha256": sha256_file(workload_path) if workload_path.is_file() else None},
    ]
    if lease_path and lease_path.is_file():
        artifact_digests.append({"kind": "hrb_lease", "sha256": sha256_file(lease_path)})
    if authorization_path and authorization_path.is_file():
        artifact_digests.append({"kind": "hrb_admission_authorization", "sha256": sha256_file(authorization_path)})
    envelope = {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": f"FA3-RESOURCE-ADMISSION-CURRENT-HOST-{int(time.time())}",
        "evidence_class": "CURRENT_HOST_ADMISSION",
        "subject": {"profile_id": "FA3-RESOURCE-ADMISSION-CONTRACTS-001", "provider_id": None, "gate_id": "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001"},
        "canonical_context": {
            "architecture_release": "2026-08-23/v3.0.11",
            "release_baseline_id": "FA3-RELEASE-CAPABILITY-BASELINE-001",
            "release_manifest_digest": release_manifest_digest(root),
        },
        "execution_context": {
            "host_attestation_ref": attestation["host_attestation_id"],
            "compute_profile_ref": "INLINE_SHA256:" + sha256_obj(profile),
            "workload_resource_envelope_ref": str(workload_path.resolve()),
            "hrb_authorization_ref": str(authorization_path.resolve()) if authorization_path else None,
            "hrb_lease_ref": str(lease_path.resolve()) if lease_path else None,
            "diagnostics": {},
        },
        "provenance": {"collector_id": COLLECTOR_ID, "collector_revision": COLLECTOR_VERSION, "generated_at": now(), "artifact_digests": artifact_digests},
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
    parser.add_argument("--hrb-lease")
    parser.add_argument("--hrb-authorization")
    parser.add_argument("--receipt", default=str(RECEIPT_DEFAULT))
    parser.add_argument("--broker", default=BROKER_DEFAULT)
    parser.add_argument("--authorization-broker", default=AUTH_BROKER_DEFAULT)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    sys_path = str(root / "src")
    if sys_path not in os.sys.path:
        os.sys.path.insert(0, sys_path)
    lease_path = Path(args.hrb_lease) if args.hrb_lease else None
    authorization_path = Path(args.hrb_authorization) if args.hrb_authorization else None
    envelope = collect(root, Path(args.workload_envelope), lease_path, authorization_path, Path(args.receipt), args.broker, args.authorization_broker)
    print(json.dumps({
        "evidence_id": envelope["evidence_id"],
        "status": envelope["result"]["status"],
        "claims": envelope["result"]["claims"],
        "non_claims": envelope["result"]["non_claims"],
        "requested_resource_classes": envelope["payload"]["requested_resource_classes"],
        "accelerator_required": envelope["payload"]["accelerator_required"],
        "receipt": str(Path(args.receipt).resolve()),
    }, indent=2))
    return 0 if envelope["result"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
