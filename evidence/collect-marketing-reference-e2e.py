#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_marketing_reference import run_reference_e2e

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    report = run_reference_e2e()
    report_path = root / "reports/marketing-reference-e2e-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": "fa3.marketing-ci-reference-e2e-receipt.v1",
        "status": report["result"],
        "profile_id": "FA3-MARKETING-001",
        "gate_id": "FA3-GATE-MARKETING-001",
        "current_host_provider_runtime_claim": False,
        "report": "reports/marketing-reference-e2e-report.json",
    }
    receipt_path = root / "evidence/receipts/marketing-ci-reference-e2e.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
