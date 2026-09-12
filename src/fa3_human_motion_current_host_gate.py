#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_human_motion_current_host import CAPABILITY_COUNT, CONFORMANCE_ID, GATE_ID, validate_receipt

RECEIPT = "evidence/receipts/human-motion-current-host.json"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = Path(root)
    path = receipt_path or root / RECEIPT
    try:
        receipt = loadj(path)
        findings = validate_receipt(receipt)
        if receipt.get("fixture_semantics") == "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST":
            findings.append({"code": "HM-HOST-025", "severity": "P0", "message": "synthetic fixture cannot satisfy current-host production admission"})
    except Exception as exc:
        receipt = {}
        findings = [{"code": "HM-HOST-000", "severity": "P0", "message": "current-host receipt missing/unreadable", "error": repr(exc)}]
    report = {
        "schema": "fa3.human-motion-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "conformance_id": CONFORMANCE_ID,
        "result": "PASS" if not findings else "FAIL",
        "capability_count": CAPABILITY_COUNT,
        "evidence_level": receipt.get("evidence_level"),
        "blocking_findings": len(findings),
        "findings": findings,
        "promotion_effect": "HUMAN_MOTION_COMPONENT_RUNTIME_ONLY_GLOBAL_CAPABILITY_AND_AUTHORITY_COUNTS_UNCHANGED"
    }
    out = root / "reports/human-motion-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--receipt")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    receipt = Path(a.receipt).resolve() if a.receipt else None
    report = gate(root, receipt)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
