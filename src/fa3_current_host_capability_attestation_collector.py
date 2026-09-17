#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

CAPABILITY_COUNT = module_active_capability_count(__file__)
RESULT_SCHEMA = "fa3.capability-current-host-test-result.v1"
ATTESTATION_SCHEMA = "fa3.capability-current-host-attestation.v1"
EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"
COLLECTOR_ID = "FA3-CURRENT-HOST-CAPABILITY-ATTESTATION-COLLECTOR-001"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CAP_ID = re.compile(r"^CAP-\d{3}$")
KINDS = ("positive", "negative", "rollback")
EXPECTED_FIELDS = {
    "positive": "required_positive_test",
    "negative": "required_negative_test",
    "rollback": "rollback_requirement",
}
BLOCKED = 2


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


def _validate_bound_artifacts(
    root: Path, artifacts: Any
) -> tuple[list[str], list[dict[str, str]], set[str], set[str]]:
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


def _validate_result(
    root: Path,
    record: dict[str, Any],
    kind: str,
    result_path: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    try:
        result = _load(result_path)
    except Exception as exc:
        return None, [f"test result unreadable: {exc}"]

    subject_id = record.get("subject_id")
    expected_id = record.get(EXPECTED_FIELDS[kind])
    if result.get("schema") != RESULT_SCHEMA:
        findings.append("test result schema mismatch")
    if result.get("subject_id") != subject_id:
        findings.append("test result subject_id mismatch")
    if result.get("test_kind") != kind:
        findings.append(f"test_kind mismatch: expected {kind}")
    if result.get("test_id") != expected_id:
        findings.append(f"test id mismatch: expected {expected_id}")
    if result.get("status") != "PASS":
        findings.append("test result status is not PASS")
    if result.get("execution_scope") != "CURRENT_HOST":
        findings.append("execution_scope is not CURRENT_HOST")
    if result.get("current_host") is not True:
        findings.append("current_host flag is not true")
    if result.get("synthetic") is not False:
        findings.append("synthetic test result cannot create an attestation")
    if result.get("ci_reference_only") is not False:
        findings.append("CI/reference-only test result cannot create an attestation")
    if result.get("evidence_authority") != EVIDENCE_AUTHORITY:
        findings.append("evidence authority mismatch")
    if result.get("global_promotion_claim") is not False:
        findings.append("test result must not claim global promotion")

    collected = _parse_time(result.get("collected_at"))
    expires = _parse_time(result.get("expires_at"))
    if collected is None:
        findings.append("collected_at missing/invalid")
    if expires is None:
        findings.append("expires_at missing/invalid")
    elif collected is not None and expires <= collected:
        findings.append("expires_at must be after collected_at")
    elif expires <= datetime.now(timezone.utc):
        findings.append("test result expired")

    artifact_findings, artifacts, artifact_paths, artifact_hashes = _validate_bound_artifacts(
        root, result.get("evidence_artifacts")
    )
    findings.extend(artifact_findings)

    result_artifact = result.get("result_artifact")
    if not isinstance(result_artifact, dict):
        findings.append("result_artifact missing/invalid")
        result_artifact = {}
    result_rel = result_artifact.get("path")
    result_digest = result_artifact.get("sha256")
    if result_rel not in artifact_paths or result_digest not in artifact_hashes:
        findings.append("result_artifact must be bound to evidence_artifacts")

    host_rel = result.get("host_fingerprint_path")
    host_digest = result.get("host_fingerprint_sha256")
    host_path, host_error = _repo_file(root, host_rel)
    if host_error:
        findings.append(f"host_fingerprint {host_error}")
    if not isinstance(host_digest, str) or not HEX64.fullmatch(host_digest):
        findings.append("host_fingerprint_sha256 missing/invalid")
    elif host_path is not None and _sha256_file(host_path) != host_digest:
        findings.append("host fingerprint digest mismatch")
    elif host_rel not in artifact_paths or host_digest not in artifact_hashes:
        findings.append("host fingerprint must be bound to evidence_artifacts")

    if findings:
        return None, findings

    return {
        "kind": kind,
        "id": expected_id,
        "status": "PASS",
        "artifact_sha256": result_digest,
        "collected_at": result["collected_at"],
        "expires_at": result["expires_at"],
        "host_fingerprint_path": host_rel,
        "host_fingerprint_sha256": host_digest,
        "evidence_artifacts": artifacts,
        "source_result_path": result_path.resolve().relative_to(root).as_posix(),
        "source_result_sha256": _sha256_file(result_path),
    }, []


def _merge_artifacts(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_path: dict[str, str] = {}
    for result in results:
        for artifact in result["evidence_artifacts"]:
            path = artifact["path"]
            digest = artifact["sha256"]
            existing = by_path.get(path)
            if existing is not None and existing != digest:
                raise ValueError(f"artifact path has conflicting digests: {path}")
            by_path[path] = digest
        by_path[result["source_result_path"]] = result["source_result_sha256"]
    return [{"path": path, "sha256": by_path[path]} for path in sorted(by_path)]


def _attestation_from_results(
    record: dict[str, Any], results: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    rows = [results[kind] for kind in KINDS]
    host_pairs = {
        (row["host_fingerprint_path"], row["host_fingerprint_sha256"])
        for row in rows
    }
    if len(host_pairs) != 1:
        findings.append("positive/negative/rollback results do not bind the same host fingerprint")

    collected_times = [_parse_time(row["collected_at"]) for row in rows]
    expiry_times = [_parse_time(row["expires_at"]) for row in rows]
    if any(value is None for value in collected_times + expiry_times):
        findings.append("validated result timestamps unexpectedly invalid")

    try:
        artifacts = _merge_artifacts(rows)
    except ValueError as exc:
        findings.append(str(exc))
        artifacts = []

    if findings:
        return None, findings

    host_rel, host_digest = next(iter(host_pairs))
    collected = max(value for value in collected_times if value is not None)
    expires = min(value for value in expiry_times if value is not None)
    if expires <= collected:
        return None, ["combined attestation validity window is empty"]

    tests = {
        kind: {
            "id": results[kind]["id"],
            "status": "PASS",
            "artifact_sha256": results[kind]["artifact_sha256"],
        }
        for kind in KINDS
    }
    return {
        "schema": ATTESTATION_SCHEMA,
        "subject_id": record["subject_id"],
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "attestation_authority": EVIDENCE_AUTHORITY,
        "global_promotion_claim": False,
        "host_fingerprint_path": host_rel,
        "host_fingerprint_sha256": host_digest,
        "collected_at": collected.isoformat(),
        "expires_at": expires.isoformat(),
        "tests": tests,
        "evidence_artifacts": artifacts,
        "collector": {
            "id": COLLECTOR_ID,
            "source_test_result_schema": RESULT_SCHEMA,
            "test_execution_is_external_and_must_be_explicit": True,
            "missing_test_result_is_pass": False,
        },
    }, []


def materialize(root: Path, test_results_dir: Path | None = None) -> dict[str, Any]:
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
            "code": "CHA-001",
            "message": "Evidence Registry is not the exact active capability set",
        })

    input_dir = Path(test_results_dir) if test_results_dir is not None else (
        root / ".fa3-current-host/input/capability-test-results"
    )
    if not input_dir.is_absolute():
        input_dir = (root / input_dir).resolve()
    else:
        input_dir = input_dir.resolve()
    if input_dir != root and root not in input_dir.parents:
        integrity_findings.append({
            "code": "CHA-002",
            "message": "Test-results directory must remain inside repository workspace",
        })

    output_dir = root / ".fa3-current-host/attestations/capabilities"
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("CAP-*.json"):
        stale.unlink()

    known_ids = set(expected_ids)
    if input_dir.is_dir() and not integrity_findings:
        for child in input_dir.iterdir():
            if child.name.startswith("."):
                continue
            if child.is_dir() and (not CAP_ID.fullmatch(child.name) or child.name not in known_ids):
                integrity_findings.append({
                    "code": "CHA-003",
                    "message": "Unknown capability test-result directory",
                    "path": child.relative_to(root).as_posix(),
                })

    by_id = {record["subject_id"]: record for record in records if record.get("subject_id") in known_ids}
    rows: list[dict[str, Any]] = []
    attestations = 0
    pending = 0

    for cap in expected_ids:
        record = by_id.get(cap)
        cap_dir = input_dir / cap
        present = [kind for kind in KINDS if (cap_dir / f"{kind}.json").is_file()]
        if not present:
            rows.append({
                "subject_id": cap,
                "status": "PENDING_TEST_RESULTS",
                "present_test_results": [],
                "findings": [],
            })
            pending += 1
            continue
        if len(present) != len(KINDS):
            rows.append({
                "subject_id": cap,
                "status": "PENDING_INCOMPLETE_TEST_RESULTS",
                "present_test_results": present,
                "findings": [],
            })
            pending += 1
            continue
        if record is None:
            integrity_findings.append({"code": "CHA-004", "message": "Registry record missing", "subject_id": cap})
            continue

        validated: dict[str, dict[str, Any]] = {}
        cap_findings: list[str] = []
        for kind in KINDS:
            value, findings = _validate_result(root, record, kind, cap_dir / f"{kind}.json")
            if findings:
                cap_findings.extend(f"{kind}: {item}" for item in findings)
            elif value is not None:
                validated[kind] = value

        if cap_findings:
            rows.append({
                "subject_id": cap,
                "status": "REJECTED_TEST_RESULTS",
                "present_test_results": list(KINDS),
                "findings": cap_findings,
            })
            integrity_findings.append({
                "code": "CHA-005",
                "message": "Capability test-result bundle rejected",
                "subject_id": cap,
                "findings": cap_findings,
            })
            continue

        attestation, findings = _attestation_from_results(record, validated)
        if findings or attestation is None:
            rows.append({
                "subject_id": cap,
                "status": "REJECTED_ATTESTATION_ASSEMBLY",
                "present_test_results": list(KINDS),
                "findings": findings,
            })
            integrity_findings.append({
                "code": "CHA-006",
                "message": "Capability attestation assembly rejected",
                "subject_id": cap,
                "findings": findings,
            })
            continue

        _write(output_dir / f"{cap}.json", attestation)
        rows.append({
            "subject_id": cap,
            "status": "ATTESTATION_MATERIALIZED",
            "present_test_results": list(KINDS),
            "findings": [],
        })
        attestations += 1

    integrity = "PASS" if not integrity_findings else "FAIL"
    if integrity != "PASS":
        status = "FAIL"
    elif attestations == CAPABILITY_COUNT:
        status = "COMPLETE_CURRENT_HOST_ATTESTATIONS"
    else:
        status = "PENDING_CURRENT_HOST_TEST_RESULTS"

    report = {
        "schema": "fa3.current-host-capability-attestation-collector-report.v1",
        "collector_id": COLLECTOR_ID,
        "result": integrity,
        "materialization_status": status,
        "capability_count": CAPABILITY_COUNT,
        "attestations_materialized": attestations,
        "pending_capabilities": CAPABILITY_COUNT - attestations,
        "synthetic_results_accepted": 0,
        "ci_reference_results_accepted": 0,
        "provider_authority_results_accepted": 0,
        "global_promotion_claim": False,
        "test_execution_fabricated": False,
        "test_results_dir": input_dir.relative_to(root).as_posix() if root in input_dir.parents else str(input_dir),
        "blocking_findings": integrity_findings,
        "capabilities": rows,
    }
    _write(root / ".fa3-current-host/reports/capability-attestation-collector.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize capability attestations only from explicit real current-host test-result bundles"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--test-results-dir")
    args = parser.parse_args()
    report = materialize(
        Path(args.root), Path(args.test_results_dir) if args.test_results_dir else None
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else BLOCKED


if __name__ == "__main__":
    raise SystemExit(main())
