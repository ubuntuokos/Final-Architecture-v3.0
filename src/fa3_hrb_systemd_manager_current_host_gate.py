#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RECEIPT = "evidence/receipts/hrb-systemd-manager-current-host.json"
GATE_ID = "FA3-GATE-HRB-SYSTEMD-MANAGER-CURRENT-HOST-001"
EVIDENCE_LEVEL = "CURRENT_HOST_HRB_SYSTEMD_MANAGER_NEUTRALITY_PASS"
CAPABILITY_COUNT = 143
DIRECT_FORBIDDEN_KEYS = {"CPUAffinity", "NUMAPolicy", "NUMAMask"}
GUARDED_MANAGER_KEYS = {
    "DefaultLimitNOFILE", "DefaultRestartSec", "DefaultTimeoutStartSec",
    "DefaultTimeoutStopSec", "DefaultTimeoutAbortSec",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "")


def _is_operator_source(source: str) -> bool:
    return source.startswith("/etc/systemd/") or source.startswith("/run/systemd/")


def _survival_receipt_valid(policy: dict[str, Any], key: str, value: str) -> bool:
    if not (
        policy.get("schema") == "fa3.host-survival-policy-receipt.v1"
        and policy.get("status") == "PASS"
        and policy.get("approved") is True
        and policy.get("hrb_noninterference_verified") is True
    ):
        return False
    expires = policy.get("expires_at")
    if not isinstance(expires, str):
        return False
    try:
        expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            return False
    except ValueError:
        return False
    return any(
        isinstance(item, dict)
        and item.get("key") == key
        and str(item.get("value", "")).strip() == str(value).strip()
        for item in policy.get("allowed_manager_overrides", [])
    )


def manager_violations(assignments: list[dict[str, Any]], host_survival_policy: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    host_survival_policy = host_survival_policy or {}
    violations: list[dict[str, Any]] = []
    for item in assignments:
        key = str(item.get("key", "")).strip()
        value = str(item.get("value", "")).strip()
        source = str(item.get("source", ""))
        if not _is_operator_source(source):
            continue
        norm = _norm(value)
        reason = None
        if key in DIRECT_FORBIDDEN_KEYS and value:
            reason = "GLOBAL_CPU_OR_NUMA_PLACEMENT_MUST_NOT_REPLACE_HRB"
        elif key == "DefaultTasksMax" and norm == "infinity":
            reason = "GLOBAL_UNBOUNDED_TASK_DEFAULT_FORBIDDEN"
        elif key == "DefaultLimitMEMLOCK" and "infinity" in norm:
            reason = "GLOBAL_UNBOUNDED_MEMLOCK_DEFAULT_FORBIDDEN"
        elif key == "DefaultLimitNPROC" and "infinity" in norm:
            reason = "GLOBAL_UNBOUNDED_NPROC_DEFAULT_FORBIDDEN"
        elif key == "DefaultOOMPolicy" and norm == "continue":
            reason = "GLOBAL_OOM_CONTINUE_AI_BASELINE_FORBIDDEN"
        elif key == "DefaultMemoryPressureWatch" and norm == "no":
            reason = "GLOBAL_MEMORY_PRESSURE_WATCH_DISABLE_FORBIDDEN"
        elif key == "DefaultTimerAccuracySec" and norm in {"1ms", "0.001s"}:
            reason = "GLOBAL_LOW_LATENCY_TIMER_AI_BASELINE_FORBIDDEN"
        elif key in GUARDED_MANAGER_KEYS and not _survival_receipt_valid(host_survival_policy, key, value):
            reason = "HOST_GLOBAL_LIFECYCLE_OR_FD_OVERRIDE_REQUIRES_SURVIVAL_POLICY_RECEIPT"
        if reason:
            violations.append({"key": key, "value": value, "source": source, "reason": reason})
    return violations


def hardware_floor_valid(discovery: dict[str, Any]) -> bool:
    cpu = discovery.get("cpu", {})
    gpu = discovery.get("gpu", {})
    counts = cpu.get("physical_cores_by_package", {})
    if not isinstance(counts, dict) or not counts:
        return False
    try:
        package_count = int(cpu.get("package_count", 0))
        per_package = [int(v) for v in counts.values()]
    except (TypeError, ValueError):
        return False
    qualifying = [d for d in gpu.get("devices", []) if isinstance(d, dict) and d.get("qualifies_portable_floor") is True]
    return (
        package_count >= 1
        and len(per_package) == package_count
        and min(per_package) >= 8
        and len(qualifying) >= 1
        and discovery.get("cardinality_semantics") == "DYNAMIC_1_TO_N"
        and discovery.get("host_identity_semantics") == "EVIDENCE_ONLY_NOT_CANONICAL_IDENTITY"
    )


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    def fail(code: str, message: str, **extra: Any) -> None:
        findings.append({"code": code, "severity": "P0", "message": message, **extra})

    if receipt.get("schema") != "fa3.hrb-systemd-manager-current-host-receipt.v1" or receipt.get("status") != "PASS" or receipt.get("evidence_level") != EVIDENCE_LEVEL:
        fail("HRB-SYSD-HOST-001", "receipt identity/status/evidence-level mismatch")
    discovery = receipt.get("hardware_discovery", {})
    if not hardware_floor_valid(discovery):
        fail("HRB-SYSD-HOST-002", "live hardware discovery does not satisfy the portable FA3 hardware floor")
    if any(key in discovery for key in ("expected_machine", "expected_cpu_model", "expected_gpu_sku")):
        fail("HRB-SYSD-HOST-003", "machine/SKU pin leaked into portable current-host admission")
    manager = receipt.get("systemd_manager", {})
    if not (manager.get("source") == "SYSTEMD_ANALYZE_CAT_CONFIG" and manager.get("returncode") == 0 and isinstance(manager.get("assignments"), list)):
        fail("HRB-SYSD-HOST-004", "effective systemd Manager config evidence is incomplete")
    violations = manager_violations(manager.get("assignments", []), receipt.get("host_survival_policy", {}))
    if violations:
        fail("HRB-SYSD-HOST-005", "operator systemd Manager defaults violate HRB neutrality", violations=violations)
    cgroup = receipt.get("cgroup_v2", {})
    if not (cgroup.get("unified") is True and cgroup.get("cgroup_path") and isinstance(cgroup.get("controllers"), list) and cgroup.get("effective_cpus") and cgroup.get("effective_memory_nodes")):
        fail("HRB-SYSD-HOST-006", "unified cgroup v2 projection substrate is incomplete")
    if not (
        receipt.get("hardware_profile_id") == "FA3-HARDWARE-BASELINE-001"
        and receipt.get("hardware_discovery_contract_id") == "FA3-HARDWARE-DISCOVERY-CONTRACTS-001"
        and receipt.get("resource_authority_id") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        and receipt.get("systemd_provider_id") == "FA3-PROVIDER-SYSTEMD-CGROUPV2-001"
    ):
        fail("HRB-SYSD-HOST-007", "canonical hardware/HRB/systemd bindings are incomplete")
    if not (receipt.get("capability_count_after") == CAPABILITY_COUNT and receipt.get("new_capabilities") == 0 and receipt.get("new_architectural_authorities") == 0 and receipt.get("global_promotion_claim") is False):
        fail("HRB-SYSD-HOST-008", "capability/authority/promotion invariant drift")
    negatives = receipt.get("negative_tests", {})
    required = {
        "global_cpu_affinity_denied", "global_numa_policy_denied", "global_unbounded_memlock_denied",
        "global_oom_continue_denied", "global_memory_pressure_disable_denied", "global_1ms_timer_denied",
        "guarded_timeout_without_survival_receipt_denied",
    }
    if set(negatives) != required or not all(negatives.values()):
        fail("HRB-SYSD-HOST-009", "manager-neutrality negative tests are incomplete")
    return findings


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    path = receipt_path or (root / RECEIPT)
    try:
        receipt = _load(path)
        findings = validate_receipt(receipt)
    except Exception as exc:
        receipt = {}
        findings = [{"code": "HRB-SYSD-HOST-000", "severity": "P0", "message": "current-host HRB/systemd receipt missing or unreadable", "error": repr(exc)}]
    report = {
        "schema": "fa3.hrb-systemd-manager-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "evidence_level": receipt.get("evidence_level"),
        "hardware_semantics": "PORTABLE_CAPABILITY_BASED_CURRENT_HOST_DISCOVERY",
        "promotion_effect": "COMPONENT_CURRENT_HOST_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
    }
    _write(root / "reports/hrb-systemd-manager-current-host-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate portable FA3 current-host HRB/systemd manager-neutrality evidence")
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
