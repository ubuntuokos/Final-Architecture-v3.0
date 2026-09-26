#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_hrb_systemd_manager_current_host_gate import CAPABILITY_COUNT, manager_violations

EVIDENCE_LEVEL = "CURRENT_HOST_HRB_SYSTEMD_MANAGER_NEUTRALITY_PASS"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def writej(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_cpu_list(value: str) -> list[int]:
    cpus: set[int] = set()
    for token in value.strip().split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start, end = (int(x) for x in token.split("-", 1))
            cpus.update(range(start, end + 1))
        else:
            cpus.add(int(token))
    return sorted(cpus)


def discover_cpu() -> dict[str, Any]:
    online = parse_cpu_list(Path("/sys/devices/system/cpu/online").read_text())
    cores_by_package: dict[str, set[int]] = {}
    numa_nodes: set[int] = set()
    for cpu in online:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}")
        topo = base / "topology"
        package = int((topo / "physical_package_id").read_text().strip())
        core = int((topo / "core_id").read_text().strip())
        cores_by_package.setdefault(str(package), set()).add(core)
        nodes = sorted(base.glob("node[0-9]*"))
        if nodes:
            numa_nodes.add(int(nodes[0].name[4:]))
    counts = {k: len(v) for k, v in sorted(cores_by_package.items(), key=lambda x: int(x[0]))}
    return {
        "source": "LIVE_SYSFS",
        "package_count": len(counts),
        "physical_cores_by_package": counts,
        "logical_cpu_count": len(online),
        "numa_node_count": len(numa_nodes) if numa_nodes else 1,
    }


def parse_cuda_compute_capability(value: str) -> float | None:
    try:
        parsed = float(value.strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _normalize_bdf(value: str) -> str:
    text = str(value or "").strip().lower()
    if len(text.split(":")) == 2:
        text = "0000:" + text
    if len(text.split(":")[0]) > 4:
        text = text[-12:]
    return text


def parse_gpu_rows(text: str) -> list[dict[str, Any]]:
    """Optional NVIDIA enrichment; never defines the global hardware floor."""
    devices: list[dict[str, Any]] = []
    for row in csv.reader(text.splitlines()):
        if len(row) != 6:
            continue
        uuid, bdf, name, driver, memory, compute_cap = (x.strip() for x in row)
        capability = parse_cuda_compute_capability(compute_cap)
        try:
            vram_mib = int(float(memory))
        except ValueError:
            vram_mib = 0
        canonical_bdf = _normalize_bdf(bdf)
        devices.append({
            "stable_id": uuid or ("pci:" + canonical_bdf),
            "device_uuid": uuid or None,
            "pci_bdf": canonical_bdf,
            "vendor": "NVIDIA",
            "vendor_id": "0x10de",
            "name_evidence_only": name,
            "driver_version": driver,
            "vram_mib_evidence_only": vram_mib,
            "runtime_apis": ["CUDA"],
            "cuda_compute_capability": capability,
            "eligible_for_workload_admission": bool(uuid or canonical_bdf),
            "admission_semantics": "PROVIDER_CAPABILITIES_ARE_WORKLOAD_SCOPED_NOT_GLOBAL_FLOOR",
            "identity_semantics": "STABLE_DEVICE_ID_PLUS_PCI_BDF_WHEN_AVAILABLE",
        })
    return devices


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _pci_vendor_name(vendor_id: str) -> str:
    return {
        "0x10de": "NVIDIA",
        "0x1002": "AMD",
        "0x8086": "INTEL",
    }.get(vendor_id.lower(), "PCI_" + vendor_id.lower().removeprefix("0x").upper())


def discover_accelerators() -> dict[str, Any]:
    devices_by_bdf: dict[str, dict[str, Any]] = {}
    pci_root = Path("/sys/bus/pci/devices")
    if pci_root.is_dir():
        for dev in sorted(pci_root.iterdir()):
            class_code = _read_text(dev / "class").lower()
            if not (
                class_code.startswith("0x03")
                or class_code.startswith("0x0b40")
                or class_code.startswith("0x12")
            ):
                continue
            bdf = _normalize_bdf(dev.name)
            vendor_id = _read_text(dev / "vendor").lower()
            device_id = _read_text(dev / "device").lower()
            driver = ""
            try:
                driver = (dev / "driver").resolve().name
            except OSError:
                pass
            devices_by_bdf[bdf] = {
                "stable_id": "pci:" + bdf,
                "device_uuid": None,
                "pci_bdf": bdf,
                "vendor": _pci_vendor_name(vendor_id),
                "vendor_id": vendor_id,
                "device_id": device_id,
                "driver": driver,
                "runtime_apis": [],
                "eligible_for_workload_admission": True,
                "admission_semantics": "PROVIDER_CAPABILITIES_ARE_WORKLOAD_SCOPED_NOT_GLOBAL_FLOOR",
                "identity_semantics": "STABLE_DEVICE_ID_PLUS_PCI_BDF_WHEN_AVAILABLE",
            }

    nvidia_rc = None
    nvidia_stderr = ""
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=uuid,pci.bus_id,name,driver_version,memory.total,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            text=True, capture_output=True, check=False,
        )
        nvidia_rc = proc.returncode
        nvidia_stderr = proc.stderr[-2000:]
        if proc.returncode == 0:
            for enriched in parse_gpu_rows(proc.stdout):
                bdf = enriched["pci_bdf"]
                base = devices_by_bdf.get(bdf, {})
                devices_by_bdf[bdf] = {**base, **enriched}
    except OSError as exc:
        nvidia_rc = 127
        nvidia_stderr = repr(exc)

    devices = sorted(devices_by_bdf.values(), key=lambda x: str(x.get("pci_bdf", "")))
    return {
        "source": "PCI_SYSFS_LIVE_DISCOVERY_WITH_OPTIONAL_PROVIDER_ENRICHMENT",
        "query_semantics": "OPTIONAL_0_TO_N_VENDOR_NEUTRAL_INVENTORY_PROVIDER_RUNTIME_CAPABILITIES_WORKLOAD_SCOPED",
        "nvidia_enrichment_returncode": nvidia_rc,
        "nvidia_enrichment_stderr": nvidia_stderr,
        "device_count": len(devices),
        "devices": devices,
    }


def discover_gpu() -> dict[str, Any]:
    """Compatibility alias for older receipt consumers."""
    return discover_accelerators()

def hardware_discovery() -> dict[str, Any]:
    obj = {
        "schema": "fa3.hardware-discovery-receipt.v1",
        "source": "LIVE_CURRENT_HOST",
        "cpu_cardinality_semantics": "DYNAMIC_1_TO_N",
        "accelerator_cardinality_semantics": "DYNAMIC_0_TO_N",
        "host_identity_semantics": "EVIDENCE_ONLY_NOT_CANONICAL_IDENTITY",
        "cpu": discover_cpu(),
        "accelerators": discover_accelerators(),
    }
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    obj["fingerprint_sha256"] = hashlib.sha256(raw).hexdigest()
    return obj


def parse_systemd_cat_config(text: str) -> list[dict[str, str]]:
    source = "UNKNOWN"
    section = None
    assignments: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# /"):
            source = line[2:].strip()
            continue
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section == "Manager" and "=" in line:
            key, value = line.split("=", 1)
            assignments.append({"source": source, "key": key.strip(), "value": value.strip()})
    return assignments


def collect_systemd_manager() -> dict[str, Any]:
    proc = subprocess.run(
        ["systemd-analyze", "cat-config", "systemd/system.conf"],
        text=True, capture_output=True, check=False,
    )
    return {
        "source": "SYSTEMD_ANALYZE_CAT_CONFIG",
        "returncode": proc.returncode,
        "stderr": proc.stderr[-2000:],
        "assignments": parse_systemd_cat_config(proc.stdout) if proc.returncode == 0 else [],
    }


def nearest_nonempty_cgroup_value(current: Path, mount: Path, filename: str) -> tuple[str, str]:
    current = current.resolve()
    mount = mount.resolve()
    if current != mount and mount not in current.parents:
        raise RuntimeError("current cgroup path escapes cgroup v2 mount")
    probe = current
    while True:
        candidate = probe / filename
        if candidate.is_file():
            value = candidate.read_text().strip()
            if value:
                rel = probe.relative_to(mount).as_posix()
                return value, "/" if rel == "." else "/" + rel
        if probe == mount:
            return "", ""
        probe = probe.parent


def collect_cgroup_v2() -> dict[str, Any]:
    mount = Path("/sys/fs/cgroup")
    unified = any(" - cgroup2 " in line for line in Path("/proc/self/mountinfo").read_text().splitlines())
    relative = ""
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            relative = line[3:].strip().lstrip("/")
            break
    current = mount / relative if relative else mount
    controllers = current / "cgroup.controllers"
    if not controllers.is_file():
        controllers = mount / "cgroup.controllers"
    effective_cpus, effective_cpus_source = nearest_nonempty_cgroup_value(
        current, mount, "cpuset.cpus.effective"
    )
    effective_mems, effective_mems_source = nearest_nonempty_cgroup_value(
        current, mount, "cpuset.mems.effective"
    )
    return {
        "unified": unified,
        "cgroup_path": "/" + relative if relative else "/",
        "controllers": controllers.read_text().split() if controllers.is_file() else [],
        "effective_cpus": effective_cpus,
        "effective_cpus_source_cgroup": effective_cpus_source,
        "effective_memory_nodes": effective_mems,
        "effective_memory_nodes_source_cgroup": effective_mems_source,
        "cpuset_resolution_semantics": "NEAREST_NONEMPTY_EFFECTIVE_ANCESTOR_WHEN_LEAF_EMPTY",
    }


def negative_tests() -> dict[str, bool]:
    def denied(key: str, value: str) -> bool:
        return bool(manager_violations([{"source": "/etc/systemd/system.conf.d/90-ai.conf", "key": key, "value": value}], {}))
    return {
        "global_cpu_affinity_denied": denied("CPUAffinity", "0-7"),
        "global_numa_policy_denied": denied("NUMAPolicy", "preferred"),
        "global_unbounded_memlock_denied": denied("DefaultLimitMEMLOCK", "infinity"),
        "global_oom_continue_denied": denied("DefaultOOMPolicy", "continue"),
        "global_memory_pressure_disable_denied": denied("DefaultMemoryPressureWatch", "no"),
        "global_1ms_timer_denied": denied("DefaultTimerAccuracySec", "1ms"),
        "guarded_timeout_without_survival_receipt_denied": denied("DefaultTimeoutStartSec", "10s"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect portable current-host HRB/systemd manager-neutrality evidence")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--receipt", default="evidence/receipts/hrb-systemd-manager-current-host.json")
    parser.add_argument("--host-survival-policy")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    survival: dict[str, Any] = {}
    if args.host_survival_policy:
        survival = json.loads(Path(args.host_survival_policy).read_text(encoding="utf-8"))

    hardware = hardware_discovery()
    manager = collect_systemd_manager()
    cgroup = collect_cgroup_v2()
    violations = manager_violations(manager.get("assignments", []), survival)
    cpu_counts = hardware.get("cpu", {}).get("physical_cores_by_package", {})
    accelerator_devices = hardware.get("accelerators", {}).get("devices", [])
    accelerator_inventory_ok = isinstance(accelerator_devices, list) and all(
        isinstance(device, dict)
        and bool(device.get("stable_id") or device.get("device_uuid") or device.get("pci_bdf"))
        for device in accelerator_devices
    )
    hardware_ok = bool(cpu_counts) and min(cpu_counts.values()) >= 8 and accelerator_inventory_ok
    negatives = negative_tests()
    checks = {
        "cpu_baseline_pass": bool(cpu_counts) and min(cpu_counts.values()) >= 8,
        "accelerator_inventory_schema_pass": accelerator_inventory_ok,
        "manager_collection_pass": manager.get("returncode") == 0,
        "manager_neutrality_pass": not violations,
        "cgroup_v2_pass": bool(
            cgroup.get("unified")
            and cgroup.get("effective_cpus")
            and cgroup.get("effective_memory_nodes")
        ),
        "negative_tests_pass": all(negatives.values()),
    }
    failure_codes = {
        "cpu_baseline_pass": "CAP006_CPU_BASELINE_UNPROVEN",
        "accelerator_inventory_schema_pass": "CAP006_ACCELERATOR_INVENTORY_INVALID",
        "manager_collection_pass": "CAP006_MANAGER_COLLECTION_FAILED",
        "manager_neutrality_pass": "CAP006_MANAGER_NEUTRALITY_VIOLATION",
        "cgroup_v2_pass": "CAP006_CGROUP_V2_UNPROVEN",
        "negative_tests_pass": "CAP006_NEGATIVE_MATRIX_FAILED",
    }
    failed_check_codes = [failure_codes[key] for key, passed in checks.items() if not passed]
    if cgroup.get("unified") and not cgroup.get("effective_cpus"):
        failed_check_codes.append("CAP006_EFFECTIVE_CPUSET_UNRESOLVED")
    if cgroup.get("unified") and not cgroup.get("effective_memory_nodes"):
        failed_check_codes.append("CAP006_EFFECTIVE_MEMSET_UNRESOLVED")
    per_package = [int(value) for value in cpu_counts.values()] if isinstance(cpu_counts, dict) else []
    check_summary = {
        **checks,
        "failed_check_codes": failed_check_codes,
        "cpu_package_count": hardware.get("cpu", {}).get("package_count"),
        "minimum_physical_cores": min(per_package) if per_package else None,
        "accelerator_device_count": len(accelerator_devices) if isinstance(accelerator_devices, list) else None,
        "effective_cpu_set_present": bool(cgroup.get("effective_cpus")),
        "effective_memory_nodes_present": bool(cgroup.get("effective_memory_nodes")),
        "failed_negative_test_codes": sorted(key for key, passed in negatives.items() if not passed),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    receipt = {
        "schema": "fa3.hrb-systemd-manager-current-host-receipt.v1",
        "status": status,
        "evidence_level": EVIDENCE_LEVEL if status == "PASS" else "CURRENT_HOST_HRB_SYSTEMD_MANAGER_NEUTRALITY_INCOMPLETE",
        "collected_at": utc_now(),
        "hardware_profile_id": "FA3-HARDWARE-BASELINE-001",
        "hardware_discovery_contract_id": "FA3-HARDWARE-DISCOVERY-CONTRACTS-001",
        "resource_authority_id": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "systemd_provider_id": "FA3-PROVIDER-SYSTEMD-CGROUPV2-001",
        "hardware_discovery": hardware,
        "systemd_manager": manager,
        "host_survival_policy": survival,
        "manager_violations": violations,
        "cgroup_v2": cgroup,
        "negative_tests": negatives,
        "check_summary": check_summary,
        "capability_count_after": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
        "accelerator_inventory_semantics": "OPTIONAL_0_TO_N_CPU_ONLY_HOST_CONFORMANT",
    }
    writej(receipt_path, receipt)
    print(json.dumps(receipt, indent=2))
    if status != "PASS":
        failures: list[str] = []
        if not hardware_ok:
            failures.append(
                "portable hardware baseline not proven "
                f"(cpu_cores_by_package={cpu_counts}, accelerator_inventory_valid={accelerator_inventory_ok})"
            )
        if manager.get("returncode") != 0:
            failures.append(
                f"systemd-analyze cat-config failed rc={manager.get('returncode')}: "
                f"{str(manager.get('stderr') or '').strip()[:500]}"
            )
        for violation in violations[:8]:
            failures.append(
                "systemd manager neutrality violation "
                f"{violation.get('key')}={violation.get('value')} "
                f"source={violation.get('source')} reason={violation.get('reason')}"
            )
        if not cgroup.get("unified"):
            failures.append("unified cgroup v2 not proven")
        if not cgroup.get("effective_cpus"):
            failures.append("effective cgroup cpuset is empty")
        if not cgroup.get("effective_memory_nodes"):
            failures.append("effective cgroup memory-node set is empty")
        failed_negatives = sorted(k for k, ok in negatives.items() if not ok)
        if failed_negatives:
            failures.append(f"manager-neutrality negative tests failed: {failed_negatives}")
        if not failures:
            failures.append("HRB/systemd manager current-host receipt did not satisfy PASS criteria")
        print("; ".join(failures), file=sys.stderr)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
