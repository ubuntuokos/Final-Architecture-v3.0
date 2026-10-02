#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_external_discovery_reconciler import build_reconciliation, validate_reconciliation


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 external discovery reconciliation")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest="command", required=True)

    p_reconcile = sub.add_parser("reconcile")
    p_reconcile.add_argument("--store", required=True)
    p_reconcile.add_argument("--output")

    p_check = sub.add_parser("check")
    p_check.add_argument("--projection", required=True)

    p_candidate = sub.add_parser("candidate")
    p_candidate.add_argument("--projection", required=True)
    p_candidate.add_argument("--candidate-id", required=True)

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.command == "reconcile":
        projection = build_reconciliation(root, _load(Path(args.store)))
        findings = validate_reconciliation(projection)
        if findings:
            print(json.dumps({"result": "FAIL", "findings": findings}, ensure_ascii=False, indent=2))
            return 2
        if args.output:
            _write(Path(args.output), projection)
        print(json.dumps({
            "result": "PASS",
            "projection_digest": projection["projection_digest"],
            "result_count": projection["result_count"],
            "summary": projection["summary"],
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "check":
        projection = _load(Path(args.projection))
        findings = validate_reconciliation(projection)
        print(json.dumps({"result": "PASS" if not findings else "FAIL", "findings": findings}, ensure_ascii=False, indent=2))
        return 0 if not findings else 2

    if args.command == "candidate":
        projection = _load(Path(args.projection))
        findings = validate_reconciliation(projection)
        if findings:
            print(json.dumps({"result": "FAIL", "findings": findings}, ensure_ascii=False, indent=2))
            return 2
        row = next((item for item in projection["results"] if item["candidate_id"] == args.candidate_id), None)
        if row is None:
            parser.error("candidate id not found")
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0

    return 3


if __name__ == "__main__":
    raise SystemExit(main())
