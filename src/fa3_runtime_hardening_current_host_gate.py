#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_runtime_hardening_current_host import (
    CAPABILITY_COUNT,
    CURRENT_HOST_CONFORMANCE_ID,
    CURRENT_HOST_GATESET_ID,
    validate_current_host_envelope,
)

DEFAULT_RECEIPT = "evidence/receipts/runtime-hardening-current-host.json"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    path = receipt_path or (root / DEFAULT_RECEIPT)
    try:
        envelope = loadj(path)
        findings = validate_current_host_envelope(envelope)
    except Exception as exc:
        envelope = {}
        findings = [{
            "code": "RUNTIME-HARDENING-HOST-000",
            "severity": "P0",
            "message": "Current-host runtime-hardening receipt missing or unreadable",
            "error": repr(exc),
        }]

    passed = not findings
    report = {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "schema_version": "1.0.0",
        "gate": {"id": CURRENT_HOST_GATESET_ID, "mode": "CURRENT_HOST"},
        "result": "PASS" if passed else "BLOCKED",
        "decision": {
            "reason_code": "RUNTIME_HARDENING_CURRENT_HOST_PASS" if passed else "RUNTIME_HARDENING_CURRENT_HOST_BLOCKED",
            "promotion_effect": "COMPONENT_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
            "exit_code": 0 if passed else 2,
        },
        "findings": findings,
        "evidence_refs": [str(path)],
        "conformance_id": CURRENT_HOST_CONFORMANCE_ID,
        "capability_count": CAPABILITY_COUNT,
        "capability_delta": 0,
        "architectural_authority_delta": 0,
        "global_promotion_claim": False,
        "evidence_level": envelope.get("result", {}).get("claims", []) if passed else None,
    }
    out = root / "reports/runtime-hardening-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 runtime-hardening current-host fail-closed gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = Path(args.receipt).resolve() if args.receipt else None
    report = gate(root, receipt)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(report["decision"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
