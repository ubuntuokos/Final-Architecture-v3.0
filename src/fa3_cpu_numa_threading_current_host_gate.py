#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

RECEIPT = "evidence/receipts/cpu-numa-threading-current-host.json"
GATE_ID = "FA3-GATE-CPU-NUMA-THREADING-CURRENT-HOST-001"
EVIDENCE_LEVEL = "CURRENT_HOST_CPU_NUMA_THREADING_E2E_PASS"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str, **extra: Any) -> None:
        findings.append({"code": code, "severity": "P0", "message": message, **extra})

    if (
        receipt.get("schema") != "fa3.cpu-numa-threading-current-host-receipt.v1"
        or receipt.get("status") != "PASS"
        or receipt.get("evidence_level") != EVIDENCE_LEVEL
    ):
        fail("CPU-NUMA-HOST-001", "current-host receipt identity, status or evidence level mismatch")

    hardware = receipt.get("hardware", {})
    if not (
        hardware.get("source") == "LIVE_SYSFS_PROCFS"
        and hardware.get("machine") == "Dell Precision Tower 7910"
        and hardware.get("cpu_model_match") is True
        and hardware.get("packages") == 2
        and hardware.get("physical_cores") == 44
        and hardware.get("logical_cpus") == 88
        and hardware.get("numa_domains") == 2
        and hardware.get("smt_width") == 2
        and _digest(hardware.get("fingerprint_sha256"))
    ):
        fail("CPU-NUMA-HOST-002", "live T7910 2x E5-2696 v4 / 44C / 88T / two-NUMA evidence mismatch")

    if receipt.get("hardware_semantics") != "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT":
        fail("CPU-NUMA-HOST-003", "reference hardware values were promoted to portable defaults")

    placement = receipt.get("placement", {})
    if not (
        placement.get("topology_source") == "LIVE_OS_AFFINITY_AND_SYSFS"
        and placement.get("cgroup_v2") is True
        and placement.get("cgroup_path")
        and placement.get("effective_cpus")
        and placement.get("effective_memory_nodes")
        and placement.get("affinity_matches_effective_cpuset") is True
        and placement.get("hrb_authority_receipt") == "HRB_PLACEMENT_RECEIPT"
    ):
        fail("CPU-NUMA-HOST-004", "live affinity/cgroup v2 HRB placement receipt is incomplete")

    plan = receipt.get("thread_plan", {})
    env = plan.get("environment", {})
    budget = int(plan.get("thread_budget", 0) or 0)
    physical = int(plan.get("visible_physical_cores", 0) or 0)
    bounded = all(
        str(env.get(key, "")).isdigit() and int(env[key]) <= budget
        for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    )
    if not (
        plan.get("status") == "ADMITTED"
        and 1 <= budget <= physical <= 44
        and plan.get("uses_smt_above_physical_budget") is False
        and env.get("OMP_PLACES") == "cores"
        and env.get("OMP_PROC_BIND") == "close"
        and bounded
    ):
        fail("CPU-NUMA-HOST-005", "physical-core-first admitted math-runtime plan is invalid")

    numa_plans = receipt.get("numa_local_plans", [])
    visible_nodes = set(placement.get("visible_numa_nodes", []))
    planned_nodes = {item.get("numa_node") for item in numa_plans if item.get("status") == "ADMITTED"}
    if not visible_nodes or planned_nodes != visible_nodes or any(
        int(item.get("thread_budget", 0)) > int(item.get("visible_physical_cores", 0))
        for item in numa_plans
    ):
        fail("CPU-NUMA-HOST-006", "NUMA-local plan set does not match the live visible domains")

    accelerators = receipt.get("accelerator_locality", [])
    if any(item.get("numa_node") is None or int(item.get("numa_node", -1)) < 0 for item in accelerators):
        fail("CPU-NUMA-HOST-007", "an accelerator has no live-resolved NUMA locality")
    if receipt.get("accelerator_locality_source") != "LIVE_PCI_SYSFS_NO_STATIC_MAPPING":
        fail("CPU-NUMA-HOST-008", "accelerator locality source is not live PCI sysfs")

    negatives = receipt.get("negative_tests", {})
    required_negatives = {
        "missing_hrb_receipt_denied",
        "physical_core_oversubscription_denied",
        "smt_without_evidence_denied",
        "interleave_without_benchmark_denied",
        "spread_without_benchmark_denied",
    }
    if set(negatives) != required_negatives or not all(negatives.values()):
        fail("CPU-NUMA-HOST-009", "oversubscription/policy negative tests are incomplete")

    performance = receipt.get("performance_evidence", {})
    if not (
        performance.get("schema") == "fa3.cpu-numa-performance-evidence.v1"
        and performance.get("status") == "PASS"
        and performance.get("hardware_fingerprint_sha256") == hardware.get("fingerprint_sha256")
        and int(performance.get("iterations", 0)) >= 3
        and performance.get("selected_profile") in {"PHYSICAL_CORE_FIRST", "NUMA_LOCAL_MULTI_INSTANCE"}
        and _digest(performance.get("benchmark_command_sha256"))
    ):
        fail("CPU-NUMA-HOST-010", "workload-specific performance evidence is absent or invalid")

    rollback = receipt.get("rollback_evidence", {})
    if not (
        rollback.get("schema") == "fa3.cpu-numa-rollback-evidence.v1"
        and rollback.get("status") == "PASS"
        and rollback.get("failure_injection_denied") is True
        and rollback.get("pre_environment_sha256") == rollback.get("post_environment_sha256")
        and rollback.get("pre_cgroup_sha256") == rollback.get("post_cgroup_sha256")
        and _digest(rollback.get("pre_environment_sha256"))
        and _digest(rollback.get("pre_cgroup_sha256"))
    ):
        fail("CPU-NUMA-HOST-011", "rollback/failure-injection evidence is absent or invalid")

    if not (
        receipt.get("capability_count_after") == 143
        and receipt.get("new_capabilities") == 0
        and receipt.get("new_architectural_authorities") == 0
        and receipt.get("global_promotion_claim") is False
    ):
        fail("CPU-NUMA-HOST-012", "capability/authority/promotion invariant drift")
    return findings


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    path = receipt_path or (root / RECEIPT)
    try:
        receipt = _load(path)
        findings = validate_receipt(receipt)
    except Exception as exc:
        receipt = {}
        findings = [{
            "code": "CPU-NUMA-HOST-000",
            "severity": "P0",
            "message": "current-host CPU/NUMA receipt missing or unreadable",
            "error": repr(exc),
        }]
    report = {
        "schema": "fa3.cpu-numa-threading-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "evidence_level": receipt.get("evidence_level"),
        "promotion_effect": "COMPONENT_CURRENT_HOST_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
    }
    _write(root / "reports/cpu-numa-threading-current-host-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FA3 CPU/NUMA current-host evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt).resolve() if args.receipt else None
    report = gate(root, receipt_path)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
