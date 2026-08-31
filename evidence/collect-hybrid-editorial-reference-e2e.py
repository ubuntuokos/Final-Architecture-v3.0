#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_hybrid_editorial_reference import run_reference_e2e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect FA3 hybrid editorial CI reference E2E evidence"
    )
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--request",
        default="examples/hybrid-editorial-reference-request.json",
    )
    parser.add_argument(
        "--receipt",
        default="evidence/receipts/hybrid-editorial-ci-reference-e2e.json",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    request_path = root / args.request
    request = (
        json.loads(request_path.read_text(encoding="utf-8"))
        if request_path.is_file()
        else {}
    )
    reference = run_reference_e2e(request)
    receipt = {
        "schema": "fa3.hybrid-editorial-reference-e2e-receipt.v1",
        "status": reference["result"],
        "profile_id": "FA3-HYBRID-EDITORIAL-001",
        "gate_id": "FA3-GATE-HYBRID-EDITORIAL-001",
        "collected_at": (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "reference_e2e": reference,
        "current_host_krita_runtime_claim": False,
        "current_host_kdenlive_runtime_claim": False,
    }

    output = root / args.receipt
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
