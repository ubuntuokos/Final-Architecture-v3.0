#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_secret_broker_current_host_gate import REQUIRED_CHECKS, validate

RAW_SCHEMA = "fa3.secret-broker-current-host-receipt.v1"
GATE_SCHEMA = "fa3.secret-broker-current-host-gate-report.v1"
REF_SCHEMA = "fa3.current-host-evidence-reference.v1"
REF_ID = "FA3-SECRET-BROKER-CURRENT-HOST-EVIDENCE-2026-09-24"
SUPERSEDED = "evidence/reference/secret-broker-current-host-2026-09-21.json"


class CollectionDenied(RuntimeError):
    pass


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CollectionDenied(f"JSON object required: {path}")
    return value


def git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def collect(root: Path, receipt_path: Path, gate_path: Path) -> dict[str, Any]:
    receipt = loadj(receipt_path)
    report = loadj(gate_path)
    head = git_head(root)

    findings = validate(receipt)
    if findings:
        raise CollectionDenied("raw Secret Broker receipt failed validation: " + ",".join(findings))
    if receipt.get("schema") != RAW_SCHEMA:
        raise CollectionDenied("raw receipt schema mismatch")
    if receipt.get("bridge_source_commit") != head:
        raise CollectionDenied("privileged bridge source commit does not match repository HEAD")
    if report.get("schema") != GATE_SCHEMA:
        raise CollectionDenied("current-host gate report schema mismatch")
    if (
        report.get("result") != "PASS"
        or report.get("status") != "CURRENT_HOST_PASS"
        or report.get("findings") not in ([], None)
    ):
        raise CollectionDenied("current-host gate report is not PASS")
    checks = receipt.get("checks", {})
    if any(checks.get(name) is not True for name in REQUIRED_CHECKS):
        raise CollectionDenied("required current-host check matrix incomplete")
    if set(receipt.get("mount_options", [])) != {"rw", "nodev", "nosuid", "noexec"}:
        raise CollectionDenied("writable hardened mount evidence missing")
    if receipt.get("secret_values_collected") is not False:
        raise CollectionDenied("secret value exclusion not proven")

    return {
        "schema": REF_SCHEMA,
        "id": REF_ID,
        "conformance_id": "FA3-SECRET-BROKER-RUNTIME-CONFORMANCE-001",
        "profile_id": "FA3-SECRET-BROKER-001",
        "gate_id": "FA3-GATE-SECRET-BROKER-CURRENT-HOST-001",
        "component_scope": "FA3_SECRET_BROKER_CORE_CURRENT_HOST_ONLY",
        "result": "PASS",
        "status": "CURRENT_HOST_ADMITTED",
        "production_admitted": True,
        "global_promotion_claim": False,
        "captured_at": receipt.get("executed_at"),
        "source": {
            "execution_mode": "MANUAL_COMMIT_BOUND_PRIVILEGED_BRIDGE",
            "tested_repository_head": head,
            "bridge_source_commit": receipt.get("bridge_source_commit"),
            "current_host_gate_result": report.get("result"),
            "current_host_gate_status": report.get("status"),
            "findings": report.get("findings", []),
        },
        "runtime": {
            "real_execution": receipt.get("real_execution"),
            "synthetic": receipt.get("synthetic"),
            "luks2": receipt.get("luks2"),
            "filesystem": receipt.get("filesystem"),
            "mount_options": receipt.get("mount_options"),
            "broker_unprivileged": receipt.get("broker_unprivileged"),
            "broker_user": receipt.get("broker_user"),
            "test_unlock_key_ephemeral": receipt.get("test_unlock_key_ephemeral"),
            "secret_values_collected": receipt.get("secret_values_collected"),
        },
        "checks": {name: True for name in REQUIRED_CHECKS},
        "promotion": {
            "component_runtime_promotion_eligible": True,
            "component_runtime_admitted": True,
            "global_promotion_claim": False,
            "global_fa3_promotion_state": "UNCHANGED_PENDING_OTHER_CURRENT_HOST_EVIDENCE",
        },
        "invariants": {
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "capability_count_after": 143,
            "exact_current_host_hardware": "EVIDENCE_ONLY_NON_NORMATIVE",
            "document_only_global_promotion_forbidden": True,
        },
        "provenance": {
            "supersedes_for_runtime_promotion": SUPERSEDED,
            "historical_evidence_retained": True,
            "requalification_decision": "FA3-DEC-SECRET-BROKER-REQUALIFICATION-2026-09-24",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument(
        "--receipt",
        default="evidence/receipts/secret-broker-current-host.json",
    )
    ap.add_argument(
        "--gate-report",
        default="reports/secret-broker-current-host-gate-report.json",
    )
    ap.add_argument(
        "--output",
        default="reports/secret-broker-current-host-reference-candidate.json",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    receipt = Path(args.receipt)
    gate_report = Path(args.gate_report)
    output = Path(args.output)
    if not receipt.is_absolute():
        receipt = root / receipt
    if not gate_report.is_absolute():
        gate_report = root / gate_report
    if not output.is_absolute():
        output = root / output

    try:
        reference = collect(root, receipt.resolve(), gate_report.resolve())
    except (CollectionDenied, FileNotFoundError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "FAIL", "reason": str(exc)}, indent=2))
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reference, indent=2) + "\n", encoding="utf-8")
    output.chmod(0o600)
    print(json.dumps(reference, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
