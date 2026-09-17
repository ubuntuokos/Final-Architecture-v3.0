#!/usr/bin/env python3
from __future__ import annotations

from fa3_release_baseline import module_active_capability_count

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = module_active_capability_count(__file__)
ATTESTATION_SCHEMA = "fa3.capability-current-host-attestation.v1"
RECEIPT_SCHEMA = "fa3.capability-current-host-evidence.v1"
EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"
HANDOFF_ID = "FA3-CURRENT-HOST-CAPABILITY-HANDOFF-001"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CAP_ID = re.compile(r"^CAP-\d{3}$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _repo_file(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "path missing/absolute"
    candidate = (root / rel).resolve()
    if candidate == root or root not in candidate.parents:
        return None, "path escapes repository"
    if not candidate.is_file():
        return None, f"file missing: {rel}"
    return candidate, None


def _validate_artifacts(root: Path, artifacts: Any) -> tuple[list[str], list[dict[str, str]], set[str], set[str]]:
    findings: list[str] = []
    normalized: list[dict[str, str]] = []
    paths: set[str] = set()
    digests: set[str] = set()
    if not isinstance(artifacts, list) or not artifacts:
        return ["evidence_artifacts must be non-empty"], normalized, paths, digests

    for item in artifacts:
        if not isinstance(item, dict):
            findings.append("evidence_artifact entry invalid")
            continue
        rel = item.get("path")
        digest = item.get("sha256")
        path, path_error = _repo_file(root, rel)
        if path_error:
            findings.append(f"evidence_artifact {path_error}")
            continue
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            findings.append(f"evidence_artifact sha256 invalid: {rel}")
            continue
        actual = _sha256_file(path)
        if actual != digest:
            findings.append(f"evidence_artifact digest mismatch: {rel}")
            continue
        if rel in paths:
            findings.append(f"duplicate evidence_artifact path: {rel}")
            continue
        paths.add(rel)
        digests.add(digest)
        normalized.append({"path": rel, "sha256": digest})
    return findings, normalized, paths, digests


def validate_attestation(
    root: Path,
    record: dict[str, Any],
    attestation_path: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    try:
        attestation = _load(attestation_path)
    except Exception as exc:
        return None, [f"attestation unreadable: {exc}"]

    subject_id = record.get("subject_id")
    if attestation_path.stem != subject_id:
        findings.append("attestation filename/subject mismatch")
    if attestation.get("schema") != ATTESTATION_SCHEMA:
        findings.append("attestation schema mismatch")
    if attestation.get("subject_id") != subject_id:
        findings.append("attestation subject_id mismatch")
    if attestation.get("status") != "PASS":
        findings.append("attestation status is not PASS")
    if attestation.get("execution_scope") != "CURRENT_HOST":
        findings.append("execution_scope is not CURRENT_HOST")
    if attestation.get("current_host") is not True:
        findings.append("current_host flag is not true")
    if attestation.get("synthetic") is not False:
        findings.append("synthetic attestation cannot materialize a capability receipt")
    if attestation.get("ci_reference_only") is not False:
        findings.append("CI/reference-only attestation cannot materialize a capability receipt")
    if attestation.get("attestation_authority") != EVIDENCE_AUTHORITY:
        findings.append("attestation authority mismatch")
    if attestation.get("global_promotion_claim") is not False:
        findings.append("attestation must not claim global promotion")

    collected = _parse_time(attestation.get("collected_at"))
    expires = _parse_time(attestation.get("expires_at"))
    if collected is None:
        findings.append("collected_at missing/invalid")
    if expires is None:
        findings.append("expires_at missing/invalid")
    elif collected is not None and expires <= collected:
        findings.append("expires_at must be after collected_at")
    elif expires <= datetime.now(timezone.utc):
        findings.append("attestation expired")

    artifact_findings, artifacts, artifact_paths, artifact_hashes = _validate_artifacts(
        root, attestation.get("evidence_artifacts")
    )
    findings.extend(artifact_findings)

    host_rel = attestation.get("host_fingerprint_path")
    host_digest = attestation.get("host_fingerprint_sha256")
    host_path, host_error = _repo_file(root, host_rel)
    if host_error:
        findings.append(f"host_fingerprint {host_error}")
    if not isinstance(host_digest, str) or not HEX64.fullmatch(host_digest):
        findings.append("host_fingerprint_sha256 missing/invalid")
    elif host_path is not None and _sha256_file(host_path) != host_digest:
        findings.append("host fingerprint digest mismatch")
    elif isinstance(host_rel, str) and (
        host_rel not in artifact_paths or host_digest not in artifact_hashes
    ):
        findings.append("host fingerprint must be bound to evidence_artifacts")

    tests = attestation.get("tests")
    if not isinstance(tests, dict):
        findings.append("tests missing/invalid")
        tests = {}
    normalized_tests: dict[str, dict[str, str]] = {}
    for key, expected in (
        ("positive", record.get("required_positive_test")),
        ("negative", record.get("required_negative_test")),
        ("rollback", record.get("rollback_requirement")),
    ):
        test = tests.get(key)
        if not isinstance(test, dict):
            findings.append(f"{key} test missing")
            continue
        if test.get("id") != expected:
            findings.append(f"{key} test id mismatch: expected {expected}")
        if test.get("status") != "PASS":
            findings.append(f"{key} test is not PASS")
        digest = test.get("artifact_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            findings.append(f"{key} test artifact_sha256 missing/invalid")
        elif digest not in artifact_hashes:
            findings.append(f"{key} test artifact hash is not bound to evidence_artifacts")
        normalized_tests[key] = {
            "id": str(test.get("id", "")),
            "status": str(test.get("status", "")),
            "artifact_sha256": str(digest or ""),
        }

    if findings:
        return None, findings

    rel_attestation = attestation_path.resolve().relative_to(root).as_posix()
    attestation_sha = _sha256_file(attestation_path)
    receipt_artifacts = list(artifacts)
    receipt_artifacts.append({"path": rel_attestation, "sha256": attestation_sha})

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "subject_id": subject_id,
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "host_fingerprint_path": host_rel,
        "host_fingerprint_sha256": host_digest,
        "collected_at": attestation["collected_at"],
        "expires_at": attestation["expires_at"],
        "tests": normalized_tests,
        "evidence_artifacts": receipt_artifacts,
        "attestation": {
            "schema": ATTESTATION_SCHEMA,
            "authority": EVIDENCE_AUTHORITY,
            "path": rel_attestation,
            "sha256": attestation_sha,
        },
        "handoff": {
            "id": HANDOFF_ID,
            "provider_receipt_is_capability_authority": False,
            "generic_host_evidence_is_capability_pass": False,
            "global_promotion_claim": False,
        },
    }
    return receipt, []


def materialize(root: Path, attestation_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    registry = _load(root / "evidence/evidence-registry.json")
    records = registry.get("records", [])
    expected_ids = [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    actual_ids = [record.get("subject_id") for record in records]
    integrity_findings: list[dict[str, Any]] = []

    if (
        registry.get("record_count") != CAPABILITY_COUNT
        or len(records) != CAPABILITY_COUNT
        or actual_ids != expected_ids
    ):
        integrity_findings.append({
            "code": "CHH-001",
            "message": "Evidence Registry is not the exact active capability set",
        })

    input_dir = (
        Path(attestation_dir)
        if attestation_dir is not None
        else root / ".fa3-current-host/attestations/capabilities"
    )
    if not input_dir.is_absolute():
        input_dir = (root / input_dir).resolve()
    else:
        input_dir = input_dir.resolve()
    if input_dir != root and root not in input_dir.parents:
        integrity_findings.append({
            "code": "CHH-002",
            "message": "Attestation directory must remain inside repository workspace",
        })

    by_id = {record.get("subject_id"): record for record in records}
    candidates: dict[str, dict[str, Any]] = {}
    attestation_rows: list[dict[str, Any]] = []

    paths = sorted(input_dir.glob("*.json")) if input_dir.is_dir() and not integrity_findings else []
    for path in paths:
        cap = path.stem
        if not CAP_ID.fullmatch(cap) or cap not in by_id:
            row = {"path": path.relative_to(root).as_posix(), "subject_id": cap, "qualified": False,
                   "findings": ["unknown capability attestation"]}
            attestation_rows.append(row)
            integrity_findings.append({"code": "CHH-003", "message": "Unknown capability attestation", **row})
            continue
        receipt, findings = validate_attestation(root, by_id[cap], path)
        rel = path.relative_to(root).as_posix()
        attestation_rows.append({
            "path": rel,
            "subject_id": cap,
            "qualified": receipt is not None,
            "findings": findings,
        })
        if receipt is None:
            integrity_findings.append({
                "code": "CHH-004",
                "message": "Capability attestation rejected",
                "subject_id": cap,
                "path": rel,
                "findings": findings,
            })
        else:
            candidates[cap] = receipt

    output_dir = root / "evidence/receipts/capabilities"
    if not integrity_findings:
        for cap, receipt in candidates.items():
            out = output_dir / f"{cap}.json"
            if out.is_file():
                try:
                    existing = _load(out)
                except Exception as exc:
                    integrity_findings.append({
                        "code": "CHH-005",
                        "message": "Existing capability receipt unreadable",
                        "subject_id": cap,
                        "error": str(exc),
                    })
                    continue
                if existing != receipt:
                    integrity_findings.append({
                        "code": "CHH-006",
                        "message": "Existing capability receipt collision",
                        "subject_id": cap,
                    })

    materialized: list[str] = []
    if not integrity_findings:
        for cap, receipt in sorted(candidates.items()):
            _write(output_dir / f"{cap}.json", receipt)
            materialized.append(cap)

    if integrity_findings:
        handoff_integrity = "FAIL"
        materialization_status = "BLOCKED"
    elif materialized:
        handoff_integrity = "PASS"
        materialization_status = "MATERIALIZED_EXPLICIT_ATTESTATIONS"
    else:
        handoff_integrity = "PASS"
        materialization_status = "PENDING_CURRENT_HOST_ATTESTATIONS"

    report = {
        "schema": "fa3.current-host-capability-handoff-report.v1",
        "id": HANDOFF_ID,
        "capability_count": CAPABILITY_COUNT,
        "handoff_integrity": handoff_integrity,
        "materialization_status": materialization_status,
        "attestation_count": len(paths),
        "qualified_attestation_count": len(candidates),
        "receipts_materialized": len(materialized),
        "materialized_capability_ids": materialized,
        "provider_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "automatic_promotion": False,
        "attestations": attestation_rows,
        "blocking_findings": integrity_findings,
        "truth_constraints": {
            "provider_pass_is_capability_pass": False,
            "generic_host_collection_is_capability_pass": False,
            "ci_reference_pass_is_current_host_pass": False,
            "explicit_capability_attestation_required": True,
            "evidence_authority": EVIDENCE_AUTHORITY,
        },
    }
    _write(root / "reports/current-host-capability-handoff.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize FA3 current-host capability receipts only from explicit capability attestations"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--attestation-dir")
    args = parser.parse_args()

    report = materialize(
        Path(args.root),
        Path(args.attestation_dir) if args.attestation_dir else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["handoff_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
