#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cpu_thread_budget import AdmissionDenied, build_thread_plan, discover_live_topology

EVIDENCE_LEVEL = "CURRENT_HOST_CPU_NUMA_THREADING_E2E_PASS"
EXPECTED_MACHINE = "Dell Precision Tower 7910"
EXPECTED_CPU_TOKEN = "E5-2696 v4"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def writej(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_cpu_list(value: str) -> list[int]:
    cpus: set[int] = set()
    for token in value.strip().split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start, end = (int(part) for part in token.split("-", 1))
            cpus.update(range(start, end + 1))
        else:
            cpus.add(int(token))
    return sorted(cpus)


def cpu_model_names() -> dict[int, str]:
    result: dict[int, str] = {}
    current: int | None = None
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("processor"):
            current = int(line.split(":", 1)[1].strip())
        elif current is not None and line.startswith("model name"):
            result[current] = line.split(":", 1)[1].strip()
    return result


def topology_entries(cpus: Iterable[int]) -> list[dict[str, int]]:
    entries: list[dict[str, int]] = []
    for cpu in cpus:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}")
        topo = base / "topology"
        socket_id = int((topo / "physical_package_id").read_text().strip())
        core_id = int((topo / "core_id").read_text().strip())
        nodes = sorted(base.glob("node[0-9]*"))
        node = int(nodes[0].name[4:]) if nodes else -1
        entries.append({"cpu_id": cpu, "socket_id": socket_id, "core_id": core_id, "numa_node": node})
    return entries


def machine_name() -> str:
    vendor = Path("/sys/class/dmi/id/sys_vendor")
    product = Path("/sys/class/dmi/id/product_name")
    if vendor.is_file() and product.is_file():
        return f"{vendor.read_text().strip()} {product.read_text().strip()}".replace("Dell Inc. ", "Dell ")
    return platform.node()


def unified_cgroup() -> dict[str, Any]:
    mount = Path("/sys/fs/cgroup")
    cgroup_v2 = any(" - cgroup2 " in line for line in Path("/proc/self/mountinfo").read_text().splitlines())
    relative = None
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            relative = line[3:].lstrip("/")
            break
    current = mount / relative if relative else mount
    cpu_file = current / "cpuset.cpus.effective"
    mem_file = current / "cpuset.mems.effective"
    controllers = current / "cgroup.controllers"
    if not controllers.is_file():
        controllers = mount / "cgroup.controllers"
    effective_cpus = parse_cpu_list(cpu_file.read_text()) if cpu_file.is_file() else []
    effective_mems = parse_cpu_list(mem_file.read_text()) if mem_file.is_file() else []
    return {
        "cgroup_v2": cgroup_v2,
        "cgroup_path": "/" + relative if relative else "/",
        "effective_cpus": effective_cpus,
        "effective_memory_nodes": effective_mems,
        "controllers": controllers.read_text().split() if controllers.is_file() else [],
    }


def accelerator_locality() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for device in sorted(Path("/sys/bus/pci/devices").glob("*")):
        class_path = device / "class"
        vendor_path = device / "vendor"
        if not class_path.is_file() or not vendor_path.is_file():
            continue
        pci_class = class_path.read_text().strip().lower()
        vendor = vendor_path.read_text().strip().lower()
        if not (pci_class.startswith("0x03") or vendor in {"0x10de", "0x1002", "0x8086"} and pci_class.startswith("0x12")):
            continue
        node_path = device / "numa_node"
        node = int(node_path.read_text().strip()) if node_path.is_file() else -1
        rows.append({"pci_address": device.name, "pci_class": pci_class, "vendor": vendor, "numa_node": node})
    return rows


def denied(fn) -> bool:
    try:
        fn()
    except AdmissionDenied:
        return True
    return False


def valid_external_evidence(performance: dict[str, Any], rollback: dict[str, Any], fingerprint: str) -> bool:
    digest = re.compile(r"[0-9a-f]{64}")
    return bool(
        performance.get("schema") == "fa3.cpu-numa-performance-evidence.v1"
        and performance.get("status") == "PASS"
        and performance.get("hardware_fingerprint_sha256") == fingerprint
        and int(performance.get("iterations", 0)) >= 3
        and performance.get("selected_profile") in {"PHYSICAL_CORE_FIRST", "NUMA_LOCAL_MULTI_INSTANCE"}
        and digest.fullmatch(str(performance.get("benchmark_command_sha256", "")))
        and rollback.get("schema") == "fa3.cpu-numa-rollback-evidence.v1"
        and rollback.get("status") == "PASS"
        and rollback.get("failure_injection_denied") is True
        and rollback.get("pre_environment_sha256") == rollback.get("post_environment_sha256")
        and rollback.get("pre_cgroup_sha256") == rollback.get("post_cgroup_sha256")
        and digest.fullmatch(str(rollback.get("pre_environment_sha256", "")))
        and digest.fullmatch(str(rollback.get("pre_cgroup_sha256", "")))
    )


def collect(performance_path: Path | None, rollback_path: Path | None) -> dict[str, Any]:
    online = parse_cpu_list(Path("/sys/devices/system/cpu/online").read_text())
    global_entries = topology_entries(online)
    model_names = cpu_model_names()
    physical = {(item["socket_id"], item["core_id"]) for item in global_entries}
    packages = {item["socket_id"] for item in global_entries}
    numa_nodes = {item["numa_node"] for item in global_entries if item["numa_node"] >= 0}
    smt_width = max(
        sum(1 for item in global_entries if (item["socket_id"], item["core_id"]) == core)
        for core in physical
    )
    models = sorted({model_names.get(cpu, "") for cpu in online})
    summary = {
        "machine": machine_name(),
        "models": models,
        "packages": len(packages),
        "physical_cores": len(physical),
        "logical_cpus": len(online),
        "numa_domains": len(numa_nodes),
        "smt_width": smt_width,
    }
    fingerprint = digest_json(summary)
    hardware = {
        "source": "LIVE_SYSFS_PROCFS",
        **summary,
        "cpu_model_match": bool(models) and all(EXPECTED_CPU_TOKEN in model for model in models),
        "fingerprint_sha256": fingerprint,
    }

    live = discover_live_topology()
    cgroup = unified_cgroup()
    affinity = set(live["allowed_cpus"])
    effective = set(cgroup["effective_cpus"])
    visible_nodes = sorted({item["numa_node"] for item in live["logical_cpus"] if item["numa_node"] >= 0})
    placement = {
        "topology_source": live["source"],
        **cgroup,
        "visible_numa_nodes": visible_nodes,
        "affinity_matches_effective_cpuset": affinity == effective,
        "hrb_authority_receipt": "HRB_PLACEMENT_RECEIPT",
    }
    request = {"authority_receipt": "HRB_PLACEMENT_RECEIPT", "workload_class": "CURRENT_HOST_VALIDATION"}
    plan = build_thread_plan(live, request)
    node_plans: list[dict[str, Any]] = []
    for node in visible_nodes:
        node_cpus = [item["cpu_id"] for item in live["logical_cpus"] if item["numa_node"] == node]
        node_plans.append(build_thread_plan(live, {**request, "allowed_cpus": node_cpus, "numa_node": node}))

    physical_budget = int(plan["visible_physical_cores"])
    logical_budget = int(plan["visible_logical_cpus"])
    smt_request = min(logical_budget, physical_budget + 1)
    negatives = {
        "missing_hrb_receipt_denied": denied(lambda: build_thread_plan(live, {})),
        "physical_core_oversubscription_denied": denied(lambda: build_thread_plan(live, {**request, "requested_threads": smt_request})),
        "smt_without_evidence_denied": denied(lambda: build_thread_plan(live, {**request, "requested_threads": logical_budget})),
        "interleave_without_benchmark_denied": denied(lambda: build_thread_plan(live, {**request, "numa_policy": "interleave_all"})),
        "spread_without_benchmark_denied": denied(lambda: build_thread_plan(live, {**request, "omp_proc_bind": "spread"})),
    }
    performance = loadj(performance_path) if performance_path and performance_path.is_file() else {}
    rollback = loadj(rollback_path) if rollback_path and rollback_path.is_file() else {}
    external_ok = valid_external_evidence(performance, rollback, fingerprint)
    hardware_ok = (
        hardware["machine"] == EXPECTED_MACHINE
        and hardware["cpu_model_match"]
        and hardware["packages"] == 2
        and hardware["physical_cores"] == 44
        and hardware["logical_cpus"] == 88
        and hardware["numa_domains"] == 2
        and hardware["smt_width"] == 2
    )
    accelerators = accelerator_locality()
    placement_ok = (
        cgroup["cgroup_v2"]
        and bool(cgroup["effective_cpus"])
        and bool(cgroup["effective_memory_nodes"])
        and placement["affinity_matches_effective_cpuset"]
        and all(item["numa_node"] >= 0 for item in accelerators)
    )
    status = "PASS" if hardware_ok and placement_ok and all(negatives.values()) and external_ok else "FAIL"
    return {
        "schema": "fa3.cpu-numa-threading-current-host-receipt.v1",
        "status": status,
        "evidence_level": EVIDENCE_LEVEL if status == "PASS" else "CURRENT_HOST_CPU_NUMA_THREADING_E2E_INCOMPLETE",
        "collected_at": utc_now(),
        "host": {"hostname_sha256": hashlib.sha256(socket.gethostname().encode()).hexdigest(), "kernel": platform.release()},
        "hardware": hardware,
        "hardware_semantics": "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT",
        "placement": placement,
        "thread_plan": plan,
        "numa_local_plans": node_plans,
        "accelerator_locality_source": "LIVE_PCI_SYSFS_NO_STATIC_MAPPING",
        "accelerator_locality": accelerators,
        "negative_tests": negatives,
        "performance_evidence": performance,
        "rollback_evidence": rollback,
        "capability_count_after": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
        "blocking_reasons": [] if status == "PASS" else [
            reason for reason, ok in {
                "REFERENCE_HARDWARE_MISMATCH": hardware_ok,
                "CGROUP_AFFINITY_OR_ACCELERATOR_LOCALITY_INCOMPLETE": placement_ok,
                "NEGATIVE_TEST_FAILURE": all(negatives.values()),
                "PERFORMANCE_OR_ROLLBACK_EVIDENCE_MISSING_OR_INVALID": external_ok,
            }.items() if not ok
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real FA3 T7910 CPU/NUMA threading evidence")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--receipt", default="evidence/receipts/cpu-numa-threading-current-host.json")
    parser.add_argument("--performance-evidence", required=True)
    parser.add_argument("--rollback-evidence", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = Path(args.receipt)
    if not receipt.is_absolute():
        receipt = root / receipt
    result = collect(Path(args.performance_evidence).resolve(), Path(args.rollback_evidence).resolve())
    writej(receipt, result)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
