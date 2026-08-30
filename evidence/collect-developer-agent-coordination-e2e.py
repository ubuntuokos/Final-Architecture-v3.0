#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_developer_agent_coordination import run_reference_e2e


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect FA3 developer-agent coordination reference-runtime E2E evidence")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--output", default="evidence/receipts/developer-agent-coordination-ci-e2e.json")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    receipt = run_reference_e2e()
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = root / "reports/developer-agent-coordination-e2e-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
