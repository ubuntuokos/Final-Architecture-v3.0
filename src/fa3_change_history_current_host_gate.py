#!/usr/bin/env python3
"""Validate real physical Current Host evidence for CHIF."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")
GATESET = "FA3-CHANGE-HISTORY-CURRENT-HOST-GATESET-001"
RECEIPT = "reports/change-history-current-host.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = receipt.get("source_binding", {})
    host = receipt.get("host", {})
    cases = receipt.get("cases", [])
    required_ids = {
        "CHIF-CH-POS", "CHIF-CH-NEG", "CHIF-CH-ROLLBACK", "CHIF-CH-READONLY",
        "CHIF-CH-AI-OFF", "CHIF-CH-AI-ADVISORY", "CHIF-CH-DETERMINISM",
    }
    if receipt.get("schema") != "fa3.change-history-current-host-receipt.v1":
        errors.append("receipt schema drift")
    if receipt.get("gate_id") != GATESET:
        errors.append("gate id drift")
    if receipt.get("result") != "PASS":
        errors.append("receipt is not PASS")
    if receipt.get("evidence_level") != "CURRENT_HOST_POSITIVE_NEGATIVE_ROLLBACK_PASS":
        errors.append("insufficient evidence level")
    if source.get("repository") != "ubuntuokos/Final-Architecture-v3.0":
        errors.append("repository binding drift")
    if not SHA40.fullmatch(str(source.get("source_commit", ""))) or source.get("exact") is not True:
        errors.append("exact source commit not proven")
    if host.get("runner_class") != "fa3-current-host" or host.get("non_root") is not True:
        errors.append("real non-root current-host runner not proven")
    if receipt.get("capability_count") != 175 or receipt.get("new_capabilities") != 0:
        errors.append("capability baseline drift")
    if receipt.get("new_architectural_authorities") != 0:
        errors.append("authority delta drift")
    if receipt.get("hardware_mutation") is not False or receipt.get("global_promotion_claim") is not False:
        errors.append("receipt overclaims hardware/global promotion")
    passed = {row.get("id") for row in cases if isinstance(row, dict) and row.get("result") == "PASS"}
    if not required_ids <= passed:
        errors.append("positive/negative/rollback/currentness test set incomplete")
    if receipt.get("findings"):
        errors.append("receipt contains findings")
    return errors


def gate(root: Path, receipt_path: Path | None = None, require_evidence: bool = True) -> dict[str, Any]:
    root = root.resolve()
    path = receipt_path or root / RECEIPT
    if not path.is_file():
        errors = ["real current-host CHIF receipt missing"] if require_evidence else []
        state = "PENDING_REAL_CURRENT_HOST_EVIDENCE"
    else:
        errors = validate(load(path))
        state = "CURRENT_HOST_PASS" if not errors else "CURRENT_HOST_FAIL"
    report = {
        "schema": "fa3.change-history-current-host-gate-report.v1",
        "gate_id": GATESET,
        "result": "PASS" if not errors and path.is_file() else "PENDING" if not errors else "FAIL",
        "runtime_evidence_status": state,
        "findings": errors,
        "capability_count": 175,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
    }
    out = root / "reports/change-history-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    report = gate(
        Path(args.root),
        Path(args.receipt).resolve() if args.receipt else None,
        require_evidence=not args.allow_pending,
    )
    print(json.dumps(report, indent=2))
    return 0 if report["result"] in ({"PASS", "PENDING"} if args.allow_pending else {"PASS"}) else 2


if __name__ == "__main__":
    raise SystemExit(main())
