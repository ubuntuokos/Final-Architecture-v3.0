#!/usr/bin/env python3
from __future__ import annotations
from fa3_release_baseline import load_active_release_baseline, module_active_capability_count
from fa3_evidence_validation import git_head as _git_head, validate_capability_receipt

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = module_active_capability_count(__file__)
RELEASE = load_active_release_baseline(Path(__file__).resolve().parents[1]).release
COMPONENT_REFERENCE = "evidence/reference/hrb-cuda-current-host-2026-08-28.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_receipt(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    return validate_capability_receipt(root, record)


def _activation_class(record: dict[str, Any]) -> str:
    activation = str(record.get("activation", "")).upper()
    obligation = str(record.get("obligation", "")).upper()
    if "CONDITIONAL" in activation or "IF_USED" in activation or "OPTIONAL" in obligation:
        return "CONDITIONAL_OR_OPTIONAL"
    if "ALWAYS" in activation or obligation == "MANDATORY":
        return "MANDATORY_OR_ALWAYS_ON"
    return "OTHER_DECLARED"


def audit(root: Path, apply_reconciliation: bool = False) -> dict[str, Any]:
    root = Path(root).resolve()
    registry_path = root / "evidence/evidence-registry.json"
    registry = _load(registry_path)
    records = registry.get("records", [])
    findings: list[dict[str, Any]] = []

    expected_ids = [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    actual_ids = [r.get("subject_id") for r in records]
    if registry.get("architecture_release") != RELEASE:
        findings.append({"code": "EVAUD-001", "message": "Evidence Registry release mismatch"})
    if registry.get("record_count") != CAPABILITY_COUNT or len(records) != CAPABILITY_COUNT or actual_ids != expected_ids:
        findings.append({"code": "EVAUD-002", "message": f"Evidence Registry is not the exact {CAPABILITY_COUNT} capability set"})

    rows: list[dict[str, Any]] = []
    invalid_pass_claims: list[str] = []
    candidates: list[str] = []
    activation_counts: Counter[str] = Counter()

    for record in records:
        validation = validate_receipt(root, record)
        cap = record.get("subject_id")
        status = str(record.get("status", "")).upper()
        activation_class = _activation_class(record)
        activation_counts[activation_class] += 1
        if status == "PASS" and not validation["qualified"]:
            invalid_pass_claims.append(str(cap))
        if status != "PASS" and validation["qualified"]:
            candidates.append(str(cap))
        rows.append({
            "subject_id": cap,
            "subject": record.get("subject"),
            "obligation": record.get("obligation"),
            "activation": record.get("activation"),
            "activation_class": activation_class,
            "registry_status": status,
            "runtime_conformance": record.get("runtime_conformance"),
            "required_positive_test": record.get("required_positive_test"),
            "required_negative_test": record.get("required_negative_test"),
            "rollback_requirement": record.get("rollback_requirement"),
            "existing_reference_artifacts": record.get("evidence_artifacts", []),
            "qualified_current_host_receipt": validation["qualified"],
            "current_host_receipt": validation["receipt"],
            "receipt_findings": validation["findings"],
        })

    if invalid_pass_claims:
        findings.append({
            "code": "EVAUD-003",
            "message": "Registry contains PASS claims without qualified current-host receipts",
            "capability_ids": invalid_pass_claims,
        })

    applied: list[str] = []
    if apply_reconciliation and not findings:
        by_id = {r.get("subject_id"): r for r in records}
        for cap in candidates:
            record = by_id[cap]
            validation = validate_receipt(root, record)
            if not validation["qualified"]:
                continue
            record["status"] = "PASS"
            record["runtime_conformance"] = "CURRENT_HOST_EVIDENCE_PASS"
            record["promotion_state"] = "RUNTIME_EVIDENCE_QUALIFIED"
            record["expires_at"] = validation["expires_at"]
            artifacts = list(record.get("evidence_artifacts", []))
            if validation["receipt"] not in artifacts:
                artifacts.append(validation["receipt"])
            record["evidence_artifacts"] = artifacts
            record["current_host_receipt_sha256"] = validation["receipt_sha256"]
            applied.append(cap)

        pass_count_after = sum(str(r.get("status", "")).upper() == "PASS" for r in records)
        registry["status"] = "PASS" if pass_count_after == CAPABILITY_COUNT else "PENDING_CURRENT_HOST"
        registry["last_current_host_reconciled_at"] = datetime.now(timezone.utc).isoformat()
        _write(registry_path, registry)

    pass_count = sum(str(r.get("status", "")).upper() == "PASS" for r in records)
    qualified_count = sum(1 for row in rows if row["qualified_current_host_receipt"])
    runtime_complete = not findings and pass_count == CAPABILITY_COUNT and qualified_count == CAPABILITY_COUNT

    component = {}
    component_path = root / COMPONENT_REFERENCE
    if component_path.is_file():
        ref = _load(component_path)
        component = {
            "path": COMPONENT_REFERENCE,
            "status": ref.get("status"),
            "global_promotion_claim": ref.get("global_promotion_claim"),
            "interpretation": "COMPONENT_SCOPE_ONLY_NOT_A_CANONICAL_CAPABILITY_RECEIPT",
        }

    report = {
        "schema": "fa3.current-host-evidence-audit-report.v2",
        "release": RELEASE,
        "repository_head": _git_head(root),
        "capability_count": CAPABILITY_COUNT,
        "audit_integrity": "PASS" if not findings else "FAIL",
        "runtime_closure": "PASS" if runtime_complete else "FAIL",
        "registry_pass_count": pass_count,
        "registry_pending_count": CAPABILITY_COUNT - pass_count,
        "qualified_current_host_receipt_count": qualified_count,
        "activation_class_counts": dict(sorted(activation_counts.items())),
        "reconciliation_candidates": candidates,
        "reconciliation_applied": applied,
        "blocking_findings": findings,
        "component_scope_reference_evidence": component,
        "promotion_eligible": runtime_complete,
        "truth_constraints": {
            "ci_reference_pass_is_runtime_pass": False,
            "synthetic_receipt_can_promote": False,
            "component_scope_pass_is_global_pass": False,
            "document_only_promotion_forbidden": True,
        },
        "capabilities": rows,
    }
    _write(root / "reports/current-host-evidence-audit.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=f"FA3 {CAPABILITY_COUNT}-capability current-host Evidence Registry audit")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--apply-reconciliation", action="store_true")
    args = ap.parse_args()
    report = audit(Path(args.root), apply_reconciliation=args.apply_reconciliation)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["audit_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
