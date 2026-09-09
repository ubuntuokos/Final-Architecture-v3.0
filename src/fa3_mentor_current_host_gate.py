#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_mentor_current_host import CAPABILITY_COUNT, GATE_ID, PROFILE_ID, EVIDENCE_LEVEL, receipt_digest, validate_receipt

RECEIPT_REL = Path("evidence/receipts/mentor-current-host.json")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    path = receipt_path or (root / RECEIPT_REL)
    findings: list[dict[str, Any]] = []
    try:
        receipt = loadj(path)
        findings.extend(validate_receipt(receipt))
        claimed = receipt.get("receipt_sha256")
        actual = receipt_digest(receipt)
        if claimed != actual:
            findings.append({"code": "MENTOR-HOST-GATE-001", "severity": "P0", "message": "receipt digest mismatch", "claimed": claimed, "actual": actual})
    except Exception as exc:
        receipt = {}
        findings = [{"code": "MENTOR-HOST-GATE-000", "severity": "P0", "message": "current-host receipt missing/unreadable", "error": repr(exc)}]

    report = {
        "schema": "fa3.mentor-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "result": "PASS" if not findings else "FAIL",
        "evidence_level": receipt.get("evidence_level"),
        "required_evidence_level": EVIDENCE_LEVEL,
        "capability_count": CAPABILITY_COUNT,
        "findings": findings,
        "promotion_effect": "COMPONENT_CURRENT_HOST_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED"
    }
    writej(root / "reports/mentor-current-host-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--receipt")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    rp = Path(args.receipt).resolve() if args.receipt else None
    report = gate(root, rp)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
