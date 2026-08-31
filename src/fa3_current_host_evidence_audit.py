#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
RELEASE = "2026-08-23/v3.0.11"
RECEIPT_SCHEMA = "fa3.capability-current-host-evidence.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
COMPONENT_REFERENCE = "evidence/reference/hrb-cuda-current-host-2026-08-28.json"

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def _test_ok(test: Any, expected_id: str) -> tuple[bool, str | None]:
    if not isinstance(test, dict):
        return False, "test result missing"
    if test.get("id") != expected_id:
        return False, f"test id mismatch: expected {expected_id}"
    if test.get("status") != "PASS":
        return False, f"{expected_id} is not PASS"
    digest = test.get("artifact_sha256")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        return False, f"{expected_id} artifact_sha256 missing/invalid"
    return True, None

def validate_receipt(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    cap = record.get("subject_id")
    rel = f"evidence/receipts/capabilities/{cap}.json"
    path = root / rel
    findings: list[str] = []
    if not path.is_file():
        return {"qualified": False, "receipt": rel, "findings": ["receipt missing"]}

    try:
        receipt = _load(path)
    except Exception as exc:
        return {"qualified": False, "receipt": rel, "findings": [f"receipt unreadable: {exc}"]}

    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("receipt schema mismatch")
    if receipt.get("subject_id") != cap:
        findings.append("receipt subject_id mismatch")
    if receipt.get("status") != "PASS":
        findings.append("receipt status is not PASS")
    if receipt.get("execution_scope") != "CURRENT_HOST":
        findings.append("execution_scope is not CURRENT_HOST")
    if receipt.get("current_host") is not True:
        findings.append("current_host flag is not true")
    if receipt.get("synthetic") is not False:
        findings.append("synthetic evidence cannot promote a capability")
    if receipt.get("ci_reference_only") is not False:
        findings.append("CI/reference-only evidence cannot promote a capability")

    fingerprint = receipt.get("host_fingerprint_sha256")
    if not isinstance(fingerprint, str) or not HEX64.fullmatch(fingerprint):
        findings.append("host_fingerprint_sha256 missing/invalid")

    collected = _parse_time(receipt.get("collected_at"))
    expires = _parse_time(receipt.get("expires_at"))
    if collected is None:
        findings.append("collected_at missing/invalid")
    if expires is None:
        findings.append("expires_at missing/invalid")
    elif collected is not None and expires <= collected:
        findings.append("expires_at must be after collected_at")
    elif expires <= datetime.now(timezone.utc):
        findings.append("receipt expired")

    tests = receipt.get("tests", {})
    for key, expected in (
        ("positive", record.get("required_positive_test")),
        ("negative", record.get("required_negative_test")),
        ("rollback", record.get("rollback_requirement")),
    ):
        ok, why = _test_ok(tests.get(key), str(expected or ""))
        if not ok:
            findings.append(why or f"{key} test invalid")

    artifacts = receipt.get("evidence_artifacts")
    artifact_hashes: set[str] = set()
    artifact_paths: set[str] = set()
    if not isinstance(artifacts, list) or not artifacts:
        findings.append("evidence_artifacts must be non-empty")
    else:
        for item in artifacts:
            if not isinstance(item, dict):
                findings.append("evidence_artifact entry invalid")
                continue
            rel = item.get("path")
            digest = item.get("sha256")
            if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
                findings.append("evidence_artifact path missing/absolute")
                continue
            if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                findings.append("evidence_artifact sha256 invalid")
                continue
            candidate = (root / rel).resolve()
            if candidate == root or root not in candidate.parents:
                findings.append("evidence_artifact path escapes repository")
                continue
            if not candidate.is_file():
                findings.append(f"evidence_artifact missing: {rel}")
                continue
            actual = _sha256_file(candidate)
            if actual != digest:
                findings.append(f"evidence_artifact digest mismatch: {rel}")
                continue
            artifact_hashes.add(digest)
            artifact_paths.add(rel)

    host_rel = receipt.get("host_fingerprint_path")
    if not isinstance(host_rel, str) or not host_rel or Path(host_rel).is_absolute():
        findings.append("host_fingerprint_path missing/absolute")
    else:
        host_path = (root / host_rel).resolve()
        if host_path == root or root not in host_path.parents or not host_path.is_file():
            findings.append("host_fingerprint_path missing or escapes repository")
        elif _sha256_file(host_path) != fingerprint:
            findings.append("host fingerprint file digest mismatch")
        elif host_rel not in artifact_paths or fingerprint not in artifact_hashes:
            findings.append("host fingerprint must be a verified evidence artifact")

    for key in ("positive", "negative", "rollback"):
        test = tests.get(key)
        digest = test.get("artifact_sha256") if isinstance(test, dict) else None
        if isinstance(digest, str) and HEX64.fullmatch(digest) and digest not in artifact_hashes:
            findings.append(f"{key} test artifact hash is not bound to a verified evidence artifact")

    return {
        "qualified": not findings,
        "receipt": rel,
        "receipt_sha256": _sha256_file(path),
        "expires_at": receipt.get("expires_at"),
        "findings": findings,
    }

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
        findings.append({"code": "EVAUD-002", "message": "Evidence Registry is not the exact 143 capability set"})

    rows: list[dict[str, Any]] = []
    invalid_pass_claims: list[str] = []
    candidates: list[str] = []

    for record in records:
        validation = validate_receipt(root, record)
        cap = record.get("subject_id")
        status = str(record.get("status", "")).upper()
        if status == "PASS" and not validation["qualified"]:
            invalid_pass_claims.append(str(cap))
        if status != "PASS" and validation["qualified"]:
            candidates.append(str(cap))
        rows.append({
            "subject_id": cap,
            "subject": record.get("subject"),
            "obligation": record.get("obligation"),
            "activation": record.get("activation"),
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
    runtime_complete = (
        not findings
        and pass_count == CAPABILITY_COUNT
        and qualified_count == CAPABILITY_COUNT
    )

    component = {}
    component_path = root / COMPONENT_REFERENCE
    if component_path.is_file():
        ref = _load(component_path)
        component = {
            "path": COMPONENT_REFERENCE,
            "status": ref.get("status"),
            "global_promotion_claim": ref.get("global_promotion_claim"),
            "interpretation": "COMPONENT_SCOPE_ONLY_NOT_A_143_CAPABILITY_RECEIPT",
        }

    report = {
        "schema": "fa3.current-host-evidence-audit-report.v1",
        "release": RELEASE,
        "capability_count": CAPABILITY_COUNT,
        "audit_integrity": "PASS" if not findings else "FAIL",
        "runtime_closure": "PASS" if runtime_complete else "FAIL",
        "registry_pass_count": pass_count,
        "registry_pending_count": CAPABILITY_COUNT - pass_count,
        "qualified_current_host_receipt_count": qualified_count,
        "reconciliation_candidates": candidates,
        "reconciliation_applied": applied,
        "blocking_findings": findings,
        "component_scope_reference_evidence": component,
        "promotion_eligible": runtime_complete,
        "capabilities": rows,
    }
    _write(root / "reports/current-host-evidence-audit.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 143-capability current-host Evidence Registry audit")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--apply-reconciliation", action="store_true")
    args = ap.parse_args()
    report = audit(Path(args.root), apply_reconciliation=args.apply_reconciliation)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["audit_integrity"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
