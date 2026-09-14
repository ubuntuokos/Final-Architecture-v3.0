#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from fa3_dependency_qualification import staging_receipt  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 dependency staging simulator. Never produces current-host or production authority.")
    parser.add_argument("identity_json", type=Path)
    parser.add_argument("--tests-passed", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/dependency-gate/simulation/staging-receipt.json")
    args = parser.parse_args()
    identity = json.loads(args.identity_json.read_text(encoding="utf-8"))
    receipt = staging_receipt(identity, args.tests_passed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
