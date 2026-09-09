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
from fa3_hrb_systemd_manager_current_host_gate import manager_violations

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


def rtx_series_class(name: str) -> int | None:
    m = re.search(r"\bGeForce\s+RTX\s+(\d{4})\b", name, re.I)
    if m:
        return int(m.group(1)[:2])
    lower = name.lower()
    if "rtx" in lower and "blackwell" in lower:
        return 50
    if "rtx" in lower and "ada" in lower:
        return 40
    return None


def discover_gpu() -> dict[str, Any]:
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=uuid,pci.bus_id,name,driver_version,memory.total", "--format=csv,noheader,nounits"],
        text=True, capture_output=True, check=False,
    )
    devices: list[dict[str, Any]] = []
    if proc.returncode == 0:
        for row in csv.reader(proc.stdout.splitlines()):
            if len(row) != 5:
                continue
            uuid, bdf, name, driver, memory = (x.strip() for x in row)
            series = rtx_series_class(name)
            devices.append({
                "device_uuid": uuid,
                "pci_bdf": bdf,
                "name_evidence_only": name,
                "driver_version": driver,
                "vram_mib_evidence_only": int(float(memory)),
                "rtx_series_class": series,
                "qualifies_portable_floor": series is not None and series >= 30,
                "identity_semantics": "UUID_PLUS_PCI_BDF_WHEN_AVAILABLE",
            })
    return {
        "source": "NVIDIA_SMI_LIVE_DISCOVERY",
        "returncode": proc.returncode,
        "stderr": proc.stderr[-2000:],
        "device_count": len(devices),
        "devices": devices,
    }


def hardware_discovery() -> dict[str, Any]:
    obj = {
        "schema": "fa3.hardware-discovery-receipt.v1",
        "source": "LIVE_CURRENT_HOST",
        "cardinality_semantics": "DYNAMIC_1_TO_N",
        "host_identity_semantics": "EVIDENCE_ONLY_NOT_CANONICAL_IDENTITY",
        "cpu": discover_cpu(),
        "gpu": discover_gpu(),
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


def collect_cgroup_v2() -> dict[str, Any]:
    mount = Path("/sys/fs/cgroup")
    unified = any(" - cgroup2 " in line for line in Path("/proc/self/mountinfo").read_text().splitlines())
    relative = ""
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            relative = line[3:].strip().lstrip("/")
            break
    current = mount / relative if relative else mount
    cpus = current / "cpuset.cpus.effective"
    mems = current / "cpuset.mems.effective"
    controllers = current / "cgroup.controllers"
    if not controllers.is_file():
        controllers = mount / "cgroup.controllers"
    return {
        "unified": unified,
        "cgroup_path": "/" + relative if relative else "/",
        "controllers": controllers.read_text().split() if controllers.is_file() else [],
        "effective_cpus": cpus.read_text().strip() if cpus.is_file() else "",
        "effective_memory_nodes": mems.read_text().strip() if mems.is_file() else "",
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
    qualifying_gpu = [d for d in hardware.get("gpu", {}).get("devices", []) if d.get("qualifies_portable_floor")]
    hardware_ok = bool(cpu_counts) and min(cpu_counts.values()) >= 8 and len(qualifying_gpu) >= 1
    negatives = negative_tests()
    status = "PASS" if hardware_ok and manager.get("returncode") == 0 and not violations and cgroup.get("unified") and cgroup.get("effective_cpus") and cgroup.get("effective_memory_nodes") and all(negatives.values()) else "FAIL"
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
        "capability_count_after": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
    }
    writej(receipt_path, receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
