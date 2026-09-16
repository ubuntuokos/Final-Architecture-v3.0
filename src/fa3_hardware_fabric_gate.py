#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BLOCKED = 2
GATE_ID = "FA3-HARDWARE-FABRIC-GATESET-001"

REQUIRED_REPOSITORY_PATHS = (
    "canonical/profiles/FA3-HW-001.json",
    "canonical/FA3-COMPUTE-PROFILE-001.json",
    "canonical/FA3-ACCEL-GUARD-001.json",
    "canonical/FA3-HARDWARE-FABRIC-RECONCILIATION-001.json",
    "canonical/FA3-HARDWARE-FABRIC-CONFORMANCE-001.json",
    "src/fa3_accelerator_guard.py",
    "src/fa3_hardware_fabric_gate.py",
    "src/fa3_hardware_fabric_current_host_gate.py",
    "tests/test_accelerator_guard.py",
    "tests/test_hardware_fabric_gate.py",
    "evidence/reference/hardware-fabric-reconciliation-2026-09-16.json",
    "evidence/collect-hardware-fabric-current-host.py",
    ".github/workflows/fa3-hardware-fabric.yml",
)


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def current_host_claim_valid(status: str, receipt: dict[str, Any] | None) -> bool:
    if status != "PASS":
        return True
    if not isinstance(receipt, dict):
        return False
    return (
        receipt.get("schema") == "fa3.hardware-fabric-current-host-receipt.v1"
        and receipt.get("executed") is True
        and receipt.get("result") == "PASS"
        and receipt.get("guard_default_mode") == "RECOMMEND"
        and receipt.get("destructive_action_performed") is False
    )


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    checks: list[dict[str, Any]] = []

    missing = [rel for rel in REQUIRED_REPOSITORY_PATHS if not (root / rel).is_file()]
    checks.append(_check("required-materialization", not missing, f"missing={missing}"))
    if missing:
        return {
            "schema": "fa3.hardware-fabric-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "checks": checks,
            "blocking_findings": len(missing),
        }

    hw = loadj(root / "canonical/profiles/FA3-HW-001.json")
    compute = loadj(root / "canonical/FA3-COMPUTE-PROFILE-001.json")
    guard = loadj(root / "canonical/FA3-ACCEL-GUARD-001.json")
    reconciliation = loadj(root / "canonical/FA3-HARDWARE-FABRIC-RECONCILIATION-001.json")
    conformance = loadj(root / "canonical/FA3-HARDWARE-FABRIC-CONFORMANCE-001.json")
    baseline = loadj(root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json")

    checks.extend([
        _check(
            "hardware-root-authority",
            hw.get("id") == "FA3-HW-001" and hw.get("canonical_root") is True and hw.get("status") == "CANONICAL",
            "FA3-HW-001 must remain the canonical hardware capability root",
        ),
        _check(
            "compute-profile-role",
            compute.get("id") == "FA3-COMPUTE-PROFILE-001"
            and compute.get("status") == "CANONICAL_POLICY"
            and compute.get("purpose") == "DESCRIBE_MEASURED_RESOURCE_CAPABILITY_WITHOUT_NAMED_HARDWARE_ADMISSION",
            "measured compute profile is a measurement policy, not a competing hardware root",
        ),
        _check(
            "authority-reconciliation",
            reconciliation.get("authority_resolution", {}).get("hardware_capability_root", {}).get("repository_presence") == "VERIFIED_PRESENT"
            and reconciliation.get("authority_resolution", {}).get("hardware_capability_root", {}).get("retraction_required") is False
            and reconciliation.get("authority_delta") == 0,
            "verified repository authority model must be preserved without invented retraction",
        ),
        _check(
            "accelerator-guard-binding",
            guard.get("canonical_hardware_root") == "FA3-HW-001"
            and guard.get("measured_compute_profile") == "FA3-COMPUTE-PROFILE-001"
            and guard.get("authority_delta") == 0,
            "accelerator guard is subordinate to existing hardware/admission authorities",
        ),
        _check(
            "recommend-default",
            guard.get("default_mode") == "RECOMMEND"
            and guard.get("automatic_enforcement_default") is False
            and guard.get("user_arbitration_default") is True,
            "default behavior is recommendation plus user arbitration",
        ),
        _check(
            "bidirectional-contention",
            set(guard.get("scope", {}).get("observation_directions", [])) == {
                "PRE_EXISTING_EXTERNAL_OCCUPANCY_AT_FA3_START",
                "NEW_EXTERNAL_CONTENTION_DURING_FA3_RUNTIME",
            },
            "both contention directions are mandatory",
        ),
        _check(
            "no-default-destructive-action",
            guard.get("decision_contract", {}).get("external_process_kill_by_default") == "FORBIDDEN"
            and guard.get("decision_contract", {}).get("external_process_preemption_by_default") == "FORBIDDEN"
            and guard.get("decision_contract", {}).get("silent_priority_override") == "FORBIDDEN",
            "kill, preemption and silent priority override are forbidden by default",
        ),
        _check(
            "release-count-invariant",
            baseline.get("current_release_capability_count") == hw.get("capability_count")
            and guard.get("capability_delta") == 0
            and reconciliation.get("capability_delta") == 0
            and conformance.get("capability_delta") == 0,
            "hardware reconciliation adds no canonical capability",
        ),
    ])

    matrix = reconciliation.get("traceability_matrix", [])
    row_ids = {row.get("requirement") for row in matrix if isinstance(row, dict)}
    expected = {f"HF-{index:03d}" for index in range(1, 11)}
    complete_rows = all(
        isinstance(row, dict)
        and row.get("canonical")
        and row.get("gate")
        and row.get("evidence")
        for row in matrix
    )
    checks.append(_check("traceability-complete", row_ids == expected and complete_rows, f"requirements={sorted(row_ids)}"))

    status = conformance.get("current_host_runtime")
    receipt_path = root / str(conformance.get("runtime_receipt", ".fa3-current-host/hardware-fabric-receipt.json"))
    receipt = None
    if receipt_path.is_file():
        try:
            receipt = loadj(receipt_path)
        except Exception:
            receipt = None
    checks.append(_check(
        "no-false-current-host-pass",
        current_host_claim_valid(str(status), receipt),
        "CURRENT_HOST_RUNTIME=PASS is legal only with an executed PASS receipt",
    ))

    failed = [item for item in checks if item["status"] != "PASS"]
    return {
        "schema": "fa3.hardware-fabric-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not failed else "FAIL",
        "fail_closed": True,
        "capability_delta": 0,
        "authority_delta": 0,
        "checks": checks,
        "blocking_findings": len(failed),
    }


def gate(root: Path) -> dict[str, Any]:
    return evaluate(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    report = evaluate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else BLOCKED


if __name__ == "__main__":
    raise SystemExit(main())
