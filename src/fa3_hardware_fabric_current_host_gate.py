#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BLOCKED = 2
DEFAULT_RECEIPT = ".fa3-current-host/hardware-fabric-receipt.json"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_receipt(receipt: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if receipt.get("schema") != "fa3.hardware-fabric-current-host-receipt.v1":
        findings.append("receipt schema mismatch")
    if receipt.get("executed") is not True:
        findings.append("receipt is not marked executed")
    if receipt.get("result") != "PASS":
        findings.append("executed receipt result is not PASS")
    if receipt.get("hardware_root") != "FA3-HW-001":
        findings.append("hardware root binding mismatch")
    if receipt.get("compute_profile") != "FA3-COMPUTE-PROFILE-001":
        findings.append("compute profile binding mismatch")
    if receipt.get("guard") != "FA3-ACCEL-GUARD-001":
        findings.append("accelerator guard binding mismatch")
    if receipt.get("guard_default_mode") != "RECOMMEND":
        findings.append("guard default mode is not RECOMMEND")
    if receipt.get("destructive_action_performed") is not False:
        findings.append("destructive action was performed")
    if receipt.get("automatic_external_process_preemption_performed") is not False:
        findings.append("automatic external process preemption was performed")
    decision = receipt.get("decision", {})
    if decision.get("destructive_action_authorized") is not False:
        findings.append("receipt implies destructive authorization")
    if decision.get("automatic_resolution") is not False:
        findings.append("default current-host run unexpectedly auto-resolved contention")
    if decision.get("mode") != "RECOMMEND":
        findings.append("default current-host run did not preserve RECOMMEND mode")
    baseline = receipt.get("baseline", {})
    current = receipt.get("current", {})
    if baseline.get("observable") is not True or current.get("observable") is not True:
        findings.append("typed accelerator observability is insufficient")
    if receipt.get("contention_state") not in {
        "NO_CONTENTION",
        "PRE_EXISTING_EXTERNAL_OCCUPANCY",
        "RUNTIME_EXTERNAL_CONTENTION",
    }:
        findings.append("contention state is not runtime-promotable")
    return findings


def evaluate(root: Path, receipt_path: str = DEFAULT_RECEIPT) -> dict[str, Any]:
    root = root.resolve()
    path = root / receipt_path
    if not path.is_file():
        return {
            "schema": "fa3.hardware-fabric-current-host-gate-report.v1",
            "result": "FAIL",
            "runtime_status": "RUNTIME_EVIDENCE_PENDING",
            "blocking_findings": 1,
            "findings": [f"executed receipt missing: {receipt_path}"],
        }
    try:
        receipt = loadj(path)
    except Exception as exc:
        return {
            "schema": "fa3.hardware-fabric-current-host-gate-report.v1",
            "result": "FAIL",
            "runtime_status": "RUNTIME_EVIDENCE_INVALID",
            "blocking_findings": 1,
            "findings": [f"receipt unreadable: {exc}"],
        }
    findings = validate_receipt(receipt)
    passed = not findings
    return {
        "schema": "fa3.hardware-fabric-current-host-gate-report.v1",
        "result": "PASS" if passed else "FAIL",
        "runtime_status": "PASS" if passed else "RUNTIME_EVIDENCE_INVALID",
        "blocking_findings": len(findings),
        "findings": findings,
        "receipt": receipt_path,
        "contention_state": receipt.get("contention_state"),
    }


def gate(root: Path, receipt_path: str = DEFAULT_RECEIPT) -> dict[str, Any]:
    return evaluate(root, receipt_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    report = evaluate(Path(args.root), args.receipt)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else BLOCKED


if __name__ == "__main__":
    raise SystemExit(main())
