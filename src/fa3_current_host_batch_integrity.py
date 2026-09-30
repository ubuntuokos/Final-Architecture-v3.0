#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from fa3_current_host_batch_planner import build_plan


def validate_selection(
    root: Path,
    *,
    batch_id: str,
    subjects: list[str],
    selection_sha256: str,
    batch_size: int = 5,
) -> dict[str, Any]:
    root = root.resolve()
    plan = build_plan(root, batch_size=batch_size)
    findings: list[str] = []

    if batch_id == "FULL-525":
        expected_subjects = plan.get("execution_ready_capabilities", [])
        expected_digest = plan.get("execution_ready_selection_sha256")
        expected_obligations = plan.get("materialized_obligation_count")
        if len(expected_subjects) != plan.get("capability_count"):
            findings.append("FULL-525 does not cover every active capability")
        if expected_obligations != plan.get("required_test_obligation_count"):
            findings.append("FULL-525 does not cover every active obligation")
    else:
        batch = next(
            (row for row in plan.get("execution_batches", []) if row.get("batch_id") == batch_id),
            None,
        )
        if not isinstance(batch, dict):
            findings.append("unknown execution batch")
            expected_subjects = []
            expected_digest = None
            expected_obligations = None
        else:
            expected_subjects = batch.get("capabilities", [])
            expected_digest = batch.get("selection_sha256")
            expected_obligations = batch.get("obligation_count")

    if subjects != expected_subjects:
        findings.append("selected subjects do not exactly match the digest-bound batch plan")
    if not isinstance(selection_sha256, str) or selection_sha256 != expected_digest:
        findings.append("selection SHA-256 does not match the current registry-bound batch plan")
    if len(subjects) != len(set(subjects)):
        findings.append("selected subjects contain duplicates")
    if plan.get("registry_integrity") != "PASS":
        findings.append("current-host registry integrity is not PASS")

    result = "PASS" if not findings else "FAIL"
    return {
        "schema": "fa3.current-host-batch-integrity.v1",
        "result": result,
        "batch_id": batch_id,
        "subjects": subjects,
        "subject_count": len(subjects),
        "obligation_count": expected_obligations,
        "selection_sha256": selection_sha256,
        "expected_selection_sha256": expected_digest,
        "registry_sha256": plan.get("registry_sha256", {}),
        "registry_integrity": plan.get("registry_integrity"),
        "global_promotion_claim": False,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a digest-bound FA3 current-host execution batch")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--batch-id", default=os.environ.get("FA3_CURRENT_HOST_BATCH_ID", ""))
    parser.add_argument("--subjects", default=os.environ.get("FA3_CURRENT_HOST_SUBJECTS", ""))
    parser.add_argument(
        "--selection-sha256",
        default=os.environ.get("FA3_CURRENT_HOST_SELECTION_SHA256", ""),
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--output", default="reports/current-host-batch-integrity.json")
    args = parser.parse_args()

    subjects = [value for value in args.subjects.split(",") if value]
    report = validate_selection(
        Path(args.root),
        batch_id=args.batch_id,
        subjects=subjects,
        selection_sha256=args.selection_sha256,
        batch_size=args.batch_size,
    )
    out = Path(args.root).resolve() / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
