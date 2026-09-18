#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from fa3_hardware_portability_gate import evaluate as hardware_portability_evaluate
from fa3_hardware_portability_gate import portable_hardware_floor_valid
from fa3_hrb_deterministic_locality_gate import evaluate as hrb_locality_evaluate
from fa3_page_cache_prefetch_gate import evaluate as page_cache_prefetch_evaluate

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-001"
MODES = ("positive", "negative", "rollback")
GPU_CC_MIN = 8.6


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_cpu_list(value: str) -> list[int]:
    cpus: set[int] = set()
    for token in value.strip().split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            lo_s, hi_s = token.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if lo > hi:
                raise ValueError("invalid CPU range")
            cpus.update(range(lo, hi + 1))
        else:
            cpus.add(int(token))
    return sorted(cpus)


def _read_int(path: Path) -> int:
    return int(path.read_text(encoding="utf-8").strip())


def _cpu_topology() -> dict[str, Any]:
    online_path = Path("/sys/devices/system/cpu/online")
    if not online_path.is_file():
        raise RuntimeError("live CPU online topology is unavailable")
    online = _parse_cpu_list(online_path.read_text(encoding="utf-8"))
    if not online:
        raise RuntimeError("no online CPUs discovered")

    packages: dict[int, set[int]] = {}
    numa_nodes: set[int] = set()
    for cpu in online:
        top = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        package = _read_int(top / "physical_package_id")
        core = _read_int(top / "core_id")
        packages.setdefault(package, set()).add(core)
        cpu_path = Path(f"/sys/devices/system/cpu/cpu{cpu}")
        for node in cpu_path.glob("node[0-9]*"):
            match = re.fullmatch(r"node(\d+)", node.name)
            if match:
                numa_nodes.add(int(match.group(1)))

    physical_per_package = {str(pkg): len(cores) for pkg, cores in sorted(packages.items())}
    return {
        "source": "LIVE_SYSFS",
        "package_count": len(packages),
        "logical_cpu_count": len(online),
        "physical_cores_per_package": physical_per_package,
        "minimum_physical_cores_per_package": min(physical_per_package.values()),
        "numa_node_count": max(1, len(numa_nodes)),
    }


def _gpu_topology() -> dict[str, Any]:
    proc = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=uuid,pci.bus_id,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError("nvidia-smi capability discovery failed")

    devices: list[dict[str, Any]] = []
    for raw in proc.stdout.splitlines():
        parts = [item.strip() for item in raw.split(",")]
        if len(parts) != 3:
            raise RuntimeError("unexpected nvidia-smi discovery row")
        uuid, pci_bdf, compute_cap_s = parts
        compute_cap = float(compute_cap_s)
        if not uuid or not pci_bdf:
            raise RuntimeError("accelerator stable identity is incomplete")
        devices.append({
            "uuid": uuid,
            "pci_bdf": pci_bdf,
            "compute_capability": compute_cap,
            "qualifies_for_baseline": compute_cap >= GPU_CC_MIN,
        })
    if not devices:
        raise RuntimeError("no NVIDIA accelerators discovered")
    qualifying = [row for row in devices if row["qualifies_for_baseline"]]
    return {
        "source": "LIVE_NVIDIA_SMI",
        "device_count": len(devices),
        "qualifying_device_count": len(qualifying),
        "minimum_qualifying_compute_capability": min(
            (row["compute_capability"] for row in qualifying),
            default=0.0,
        ),
        "identity_semantics": "UUID_AND_PCI_BDF_NOT_RUNTIME_ORDINAL",
        "devices": devices,
    }


def probe_current_host() -> dict[str, Any]:
    cpu = _cpu_topology()
    gpu = _gpu_topology()
    cgroup_v2 = Path("/sys/fs/cgroup/cgroup.controllers").is_file()
    meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    vmstat = Path("/proc/vmstat").read_text(encoding="utf-8")
    page_cache_observable = "\nCached:" in "\n" + meminfo and "\npgmajfault " in "\n" + vmstat
    return {
        "schema": "fa3.cap001-host-foundation-live-snapshot.v1",
        "cpu": cpu,
        "gpu": gpu,
        "cgroup_v2": cgroup_v2,
        "page_cache_observable": page_cache_observable,
        "placement_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "portable_host_identity_policy": "DYNAMIC_DISCOVERY_NO_MACHINE_MODEL_PIN",
    }


def validate_host_snapshot(snapshot: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    cpu = snapshot.get("cpu", {})
    gpu = snapshot.get("gpu", {})
    package_count = int(cpu.get("package_count", 0) or 0)
    min_cores = int(cpu.get("minimum_physical_cores_per_package", 0) or 0)
    qualifying_gpu_count = int(gpu.get("qualifying_device_count", 0) or 0)
    qualifying_cc = float(gpu.get("minimum_qualifying_compute_capability", 0.0) or 0.0)

    if not portable_hardware_floor_valid(
        cpu_packages=package_count,
        physical_cores_per_qualifying_cpu=min_cores,
        gpu_count=qualifying_gpu_count,
        gpu_compute_capability=qualifying_cc,
        gpu_vendor="NVIDIA",
    ):
        findings.append("portable hardware floor not satisfied by live discovery")
    if snapshot.get("cgroup_v2") is not True:
        findings.append("unified cgroup v2 runtime is unavailable")
    if snapshot.get("page_cache_observable") is not True:
        findings.append("Linux page-cache observability is incomplete")
    if snapshot.get("placement_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        findings.append("Host Resource Broker authority binding drift")
    if snapshot.get("portable_host_identity_policy") != "DYNAMIC_DISCOVERY_NO_MACHINE_MODEL_PIN":
        findings.append("host identity was promoted into portable admission policy")
    if gpu.get("identity_semantics") != "UUID_AND_PCI_BDF_NOT_RUNTIME_ORDINAL":
        findings.append("accelerator identity semantics drift")
    devices = gpu.get("devices", [])
    if not isinstance(devices, list) or not devices:
        findings.append("accelerator discovery returned no devices")
    elif any(not row.get("uuid") or not row.get("pci_bdf") for row in devices if isinstance(row, dict)):
        findings.append("accelerator stable UUID/BDF identity incomplete")
    return findings


def validate_canonical_foundation(root: Path) -> dict[str, Any]:
    hardware = hardware_portability_evaluate(root)
    locality = hrb_locality_evaluate(root)
    page_cache = page_cache_prefetch_evaluate(root)
    if hardware.get("result") != "PASS":
        raise RuntimeError("hardware portability gate is not PASS")
    if locality.get("status") != "PASS":
        raise RuntimeError("HRB deterministic-locality gate is not PASS")
    if page_cache.get("status") != "PASS":
        raise RuntimeError("page-cache/prefetch policy gate is not PASS")
    if any(
        report.get("current_host_runtime_promotion_claim") is not False
        for report in (hardware, locality, page_cache)
    ):
        raise RuntimeError("reference gate attempted current-host promotion")
    return {
        "hardware_portability": hardware.get("result"),
        "hrb_deterministic_locality": locality.get("status"),
        "page_cache_prefetch": page_cache.get("status"),
        "reference_runtime_promotion_claim": False,
    }


def _fixture_snapshot() -> dict[str, Any]:
    return {
        "schema": "fa3.cap001-host-foundation-live-snapshot.v1",
        "cpu": {
            "source": "LIVE_SYSFS",
            "package_count": 1,
            "logical_cpu_count": 16,
            "physical_cores_per_package": {"0": 8},
            "minimum_physical_cores_per_package": 8,
            "numa_node_count": 1,
        },
        "gpu": {
            "source": "LIVE_NVIDIA_SMI",
            "device_count": 1,
            "qualifying_device_count": 1,
            "minimum_qualifying_compute_capability": 8.6,
            "identity_semantics": "UUID_AND_PCI_BDF_NOT_RUNTIME_ORDINAL",
            "devices": [{
                "uuid": "GPU-00000000-0000-0000-0000-000000000001",
                "pci_bdf": "0000:01:00.0",
                "compute_capability": 8.6,
                "qualifies_for_baseline": True,
            }],
        },
        "cgroup_v2": True,
        "page_cache_observable": True,
        "placement_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "portable_host_identity_policy": "DYNAMIC_DISCOVERY_NO_MACHINE_MODEL_PIN",
    }


def _run_positive(root: Path, scope: Path, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    canonical = validate_canonical_foundation(root)
    live = snapshot if snapshot is not None else probe_current_host()
    findings = validate_host_snapshot(live)
    if findings:
        raise RuntimeError("current-host foundation validation failed: " + "; ".join(findings))
    artifact = scope / "host-foundation-positive-snapshot.json"
    _write_json(artifact, live)
    return {
        "mode": "positive",
        "status": "PASS",
        "canonical": canonical,
        "live_snapshot_sha256": _sha256(artifact),
        "dynamic_cpu_cardinality": True,
        "stable_accelerator_identity": True,
        "cgroup_v2": True,
        "page_cache_observable": True,
        "hrb_authority_preserved": True,
    }


def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    baseline = _fixture_snapshot()
    cases: dict[str, dict[str, Any]] = {}

    under_core = json.loads(json.dumps(baseline))
    under_core["cpu"]["minimum_physical_cores_per_package"] = 7
    cases["under_core_rejected"] = under_core

    no_gpu = json.loads(json.dumps(baseline))
    no_gpu["gpu"]["qualifying_device_count"] = 0
    no_gpu["gpu"]["minimum_qualifying_compute_capability"] = 0.0
    cases["missing_qualifying_gpu_rejected"] = no_gpu

    old_gpu = json.loads(json.dumps(baseline))
    old_gpu["gpu"]["minimum_qualifying_compute_capability"] = 8.0
    cases["old_compute_capability_rejected"] = old_gpu

    missing_identity = json.loads(json.dumps(baseline))
    missing_identity["gpu"]["devices"][0]["uuid"] = ""
    cases["missing_stable_gpu_identity_rejected"] = missing_identity

    no_cgroup = json.loads(json.dumps(baseline))
    no_cgroup["cgroup_v2"] = False
    cases["missing_cgroup_v2_rejected"] = no_cgroup

    no_page_cache = json.loads(json.dumps(baseline))
    no_page_cache["page_cache_observable"] = False
    cases["missing_page_cache_observability_rejected"] = no_page_cache

    evidence = {name: bool(validate_host_snapshot(snapshot)) for name, snapshot in cases.items()}
    if not all(evidence.values()):
        raise RuntimeError("one or more host-foundation negative injections were admitted")
    _write_json(scope / "host-foundation-negative-evidence.json", evidence)
    return {"mode": "negative", "status": "PASS", **evidence}


def _policy_descriptor() -> dict[str, Any]:
    return {
        "cpu_package_count_min": 1,
        "physical_cores_per_qualifying_cpu_min": 8,
        "gpu_vendor": "NVIDIA",
        "gpu_compute_capability_min": 8.6,
        "dynamic_cpu_gpu_cardinality": True,
        "stable_accelerator_identity": ["DEVICE_UUID", "PCI_BDF"],
        "cgroup_v2_runtime_projection": True,
        "page_cache_primary": True,
        "prefetch_provider_optional": True,
        "hrb_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "machine_model_pin": False,
        "global_promotion_claim": False,
    }


def _policy_descriptor_valid(value: dict[str, Any]) -> bool:
    return value == _policy_descriptor()


def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    descriptor = scope / "host-foundation-policy.rollback.json"
    baseline = _policy_descriptor()
    original = (json.dumps(baseline, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor.write_bytes(original)
    pre_hash = _sha256_bytes(original)
    if not _policy_descriptor_valid(json.loads(descriptor.read_text(encoding="utf-8"))):
        raise RuntimeError("rollback baseline descriptor is invalid")

    faulted = dict(baseline)
    faulted["gpu_compute_capability_min"] = 8.0
    _write_json(descriptor, faulted)
    mutated_hash = _sha256(descriptor)
    if _policy_descriptor_valid(json.loads(descriptor.read_text(encoding="utf-8"))):
        raise RuntimeError("rollback fault descriptor remained admissible")

    descriptor.write_bytes(original)
    post_hash = _sha256(descriptor)
    if pre_hash != post_hash:
        raise RuntimeError("rollback did not restore exact descriptor bytes")
    if mutated_hash == pre_hash:
        raise RuntimeError("fault injection did not change descriptor digest")
    if not _policy_descriptor_valid(json.loads(descriptor.read_text(encoding="utf-8"))):
        raise RuntimeError("restored descriptor is not admissible")
    return {
        "mode": "rollback",
        "status": "PASS",
        "fault_rejected": True,
        "rollback_hash_equal": True,
        "pre_sha256": pre_hash,
        "mutated_sha256": mutated_hash,
        "post_sha256": post_hash,
        "restored_policy_admitted": True,
    }


def run_mode(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    root = root.resolve()
    scope = scope.resolve()
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")
    if root not in scope.parents:
        raise RuntimeError("source artifact scope escapes repository")
    scope.mkdir(parents=True, exist_ok=True)
    if mode == "positive":
        return _run_positive(root, scope)
    if mode == "negative":
        return _run_negative(root, scope)
    return _run_rollback(root, scope)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="CAP-001 current-host Host/Foundation qualification producer")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-001")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap001-host-foundation-evidence.json"
        payload = {
            "schema": "fa3.cap001-host-foundation-current-host-evidence.v1",
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "global_promotion_claim": False,
            "result": result,
        }
        _write_json(artifact, payload)
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "source_evidence_class": _required_env("FA3_SOURCE_EVIDENCE_CLASS"),
            "covers_source_decision_ids": json.loads(_required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON")),
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": _sha256(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
