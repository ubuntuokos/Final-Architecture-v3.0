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
BUNDLE_SCHEMA = "fa3.capability-current-host-test-bundle.v1"
ATTESTATION_SCHEMA = "fa3.capability-current-host-attestation.v1"
EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"
PRODUCER_ID = "FA3-CURRENT-HOST-CAPABILITY-ATTESTATION-PRODUCER-001"
CAP_ID = re.compile(r"^CAP-\d{3}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None


def _repo_file(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "path missing/absolute"
    candidate = (root / rel).resolve()
    if candidate == root or root not in candidate.parents:
        return None, "path escapes repository"
    if not candidate.is_file():
        return None, f"file missing: {rel}"
    return candidate, None


def _validated_artifacts(
    root: Path, artifacts: Any
) -> tuple[list[str], list[dict[str, str]], dict[str, str]]:
    findings: list[str] = []
    normalized: list[dict[str, str]] = []
    by_path: dict[str, str] = {}
    if not isinstance(artifacts, list) or not artifacts:
        return ["evidence_artifacts must be non-empty"], normalized, by_path
    for item in artifacts:
        if not isinstance(item, dict):
            findings.append("evidence_artifact entry invalid")
            continue
        rel = item.get("path")
        digest = item.get("sha256")
        path, err = _repo_file(root, rel)
        if err:
            findings.append(f"evidence_artifact {err}")
            continue
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            findings.append(f"evidence_artifact sha256 invalid: {rel}")
            continue
        actual = _sha256(path)
        if actual != digest:
            findings.append(f"evidence_artifact digest mismatch: {rel}")
            continue
        if rel in by_path:
            findings.append(f"duplicate evidence_artifact path: {rel}")
            continue
        by_path[rel] = digest
        normalized.append({"path": rel, "sha256": digest})
    return findings, normalized, by_path


def validate_bundle(
    root: Path,
    record: dict[str, Any],
    bundle_path: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    try:
        bundle = _load(bundle_path)
    except Exception as exc:
        return None, [f"bundle unreadable: {exc}"]

    subject_id = record.get("subject_id")
    if bundle_path.stem != subject_id:
        findings.append("bundle filename/subject mismatch")
    if bundle.get("schema") != BUNDLE_SCHEMA:
        findings.append("bundle schema mismatch")
    if bundle.get("subject_id") != subject_id:
        findings.append("bundle subject_id mismatch")
    if bundle.get("status") != "PASS":
        findings.append("bundle status is not PASS")
    if bundle.get("execution_scope") != "CURRENT_HOST":
        findings.append("execution_scope is not CURRENT_HOST")
    if bundle.get("current_host") is not True:
        findings.append("current_host flag is not true")
    if bundle.get("synthetic") is not False:
        findings.append("synthetic bundle cannot produce an attestation")
    if bundle.get("ci_reference_only") is not False:
        findings.append("CI/reference-only bundle cannot produce an attestation")
    if bundle.get("global_promotion_claim") is not False:
        findings.append("bundle must not claim global promotion")

    collected = _parse_time(bundle.get("collected_at"))
    expires = _parse_time(bundle.get("expires_at"))
    if collected is None:
        findings.append("collected_at missing/invalid")
    if expires is None:
        findings.append("expires_at missing/invalid")
    elif collected is not None and expires <= collected:
        findings.append("expires_at must be after collected_at")
    elif expires <= datetime.now(timezone.utc):
        findings.append("bundle expired")

    artifact_findings, artifacts, artifact_map = _validated_artifacts(
        root, bundle.get("evidence_artifacts")
    )
    findings.extend(artifact_findings)

    host_rel = bundle.get("host_fingerprint_path")
    host_digest = bundle.get("host_fingerprint_sha256")
    host_path, host_err = _repo_file(root, host_rel)
    if host_err:
        findings.append(f"host_fingerprint {host_err}")
    if not isinstance(host_digest, str) or not HEX64.fullmatch(host_digest):
        findings.append("host_fingerprint_sha256 missing/invalid")
    elif host_path is not None and _sha256(host_path) != host_digest:
        findings.append("host fingerprint digest mismatch")
    elif isinstance(host_rel, str) and artifact_map.get(host_rel) != host_digest:
        findings.append("host fingerprint must be bound to evidence_artifacts")

    tests = bundle.get("tests")
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
        rel = test.get("artifact_path")
        digest = test.get("artifact_sha256")
        if not isinstance(rel, str) or artifact_map.get(rel) != digest:
            findings.append(f"{key} test artifact is not bound to evidence_artifacts")
        normalized_tests[key] = {
            "id": str(test.get("id", "")),
            "status": str(test.get("status", "")),
            "artifact_sha256": str(digest or ""),
        }

    if findings:
        return None, findings

    attestation = {
        "schema": ATTESTATION_SCHEMA,
        "subject_id": subject_id,
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "attestation_authority": EVIDENCE_AUTHORITY,
        "global_promotion_claim": False,
        "host_fingerprint_path": host_rel,
        "host_fingerprint_sha256": host_digest,
        "collected_at": bundle["collected_at"],
        "expires_at": bundle["expires_at"],
        "tests": normalized_tests,
        "evidence_artifacts": artifacts,
        "producer": {
            "id": PRODUCER_ID,
            "source_bundle_path": bundle_path.resolve().relative_to(root).as_posix(),
            "source_bundle_sha256": _sha256(bundle_path),
            "provider_receipt_is_attestation_authority": False,
            "generic_host_collection_is_capability_pass": False,
            "automatic_promotion": False,
        },
    }
    return attestation, []


def materialize(root: Path, bundle_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    registry = _load(root / "evidence/evidence-registry.json")
    records = registry.get("records", [])
    expected_ids = [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    actual_ids = [record.get("subject_id") for record in records]
    blocking: list[dict[str, Any]] = []

    if (
        registry.get("record_count") != CAPABILITY_COUNT
        or len(records) != CAPABILITY_COUNT
        or actual_ids != expected_ids
    ):
        blocking.append({
            "code": "CHA-001",
            "message": "Evidence Registry is not the exact active capability set",
        })

    input_dir = (
        Path(bundle_dir)
        if bundle_dir is not None
        else root / ".fa3-current-host/test-bundles/capabilities"
    )
    input_dir = (root / input_dir).resolve() if not input_dir.is_absolute() else input_dir.resolve()
    if input_dir != root and root not in input_dir.parents:
        blocking.append({
            "code": "CHA-002",
            "message": "Bundle directory must remain inside repository workspace",
        })

    by_id = {record.get("subject_id"): record for record in records}
    rows: list[dict[str, Any]] = []
    candidates: dict[str, dict[str, Any]] = {}
    paths = sorted(input_dir.glob("*.json")) if input_dir.is_dir() and not blocking else []

    for path in paths:
        cap = path.stem
        rel = path.resolve().relative_to(root).as_posix()
        if not CAP_ID.fullmatch(cap) or cap not in by_id:
            row = {"path": rel, "subject_id": cap, "qualified": False,
                   "findings": ["unknown capability bundle"]}
            rows.append(row)
            blocking.append({"code": "CHA-003", "message": "Unknown capability bundle", **row})
            continue
        attestation, findings = validate_bundle(root, by_id[cap], path)
        rows.append({
            "path": rel,
            "subject_id": cap,
            "qualified": attestation is not None,
            "findings": findings,
        })
        if attestation is None:
            blocking.append({
                "code": "CHA-004",
                "message": "Capability test bundle rejected",
                "subject_id": cap,
                "path": rel,
                "findings": findings,
            })
        else:
            candidates[cap] = attestation

    output_dir = root / ".fa3-current-host/attestations/capabilities"
    materialized: list[str] = []
    if not blocking:
        for cap, attestation in sorted(candidates.items()):
            out = output_dir / f"{cap}.json"
            if out.is_file():
                try:
                    existing = _load(out)
                except Exception as exc:
                    blocking.append({
                        "code": "CHA-005",
                        "message": "Existing attestation unreadable",
                        "subject_id": cap,
                        "error": str(exc),
                    })
                    continue
                if existing != attestation:
                    blocking.append({
                        "code": "CHA-006",
                        "message": "Existing attestation collision",
                        "subject_id": cap,
                    })
        if not blocking:
            for cap, attestation in sorted(candidates.items()):
                _write(output_dir / f"{cap}.json", attestation)
                materialized.append(cap)

    if blocking:
        integrity = "FAIL"
        status = "BLOCKED"
    elif materialized:
        integrity = "PASS"
        status = "MATERIALIZED_EXPLICIT_CURRENT_HOST_ATTESTATIONS"
    else:
        integrity = "PASS"
        status = "PENDING_CAPABILITY_TEST_BUNDLES"

    report = {
        "schema": "fa3.current-host-capability-attestation-producer-report.v1",
        "id": PRODUCER_ID,
        "capability_count": CAPABILITY_COUNT,
        "producer_integrity": integrity,
        "materialization_status": status,
        "bundle_count": len(paths),
        "qualified_bundle_count": len(candidates),
        "attestations_materialized": len(materialized),
        "materialized_capability_ids": materialized,
        "provider_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "automatic_promotion": False,
        "bundles": rows,
        "blocking_findings": blocking,
        "truth_constraints": {
            "provider_pass_is_capability_attestation": False,
            "generic_host_collection_is_capability_attestation": False,
            "ci_reference_pass_is_current_host_attestation": False,
            "exact_registry_test_ids_required": True,
            "all_test_artifacts_must_be_hash_bound": True,
            "attestation_authority": EVIDENCE_AUTHORITY,
        },
    }
    _write(root / "reports/current-host-capability-attestation-producer.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Produce FA3 current-host capability attestations only from explicit test bundles"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--bundle-dir")
    args = parser.parse_args()
    report = materialize(
        Path(args.root),
        Path(args.bundle_dir) if args.bundle_dir else None,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["producer_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
