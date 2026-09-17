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
RESULT_SCHEMA = "fa3.capability-current-host-test-result.v1"
BUNDLE_SCHEMA = "fa3.capability-current-host-test-bundle.v1"
REPORT_SCHEMA = "fa3.current-host-capability-test-bundle-assembler-report.v1"
PLAN_SCHEMA = "fa3.current-host-capability-test-plan.v1"
ASSEMBLER_ID = "FA3-CURRENT-HOST-CAPABILITY-TEST-BUNDLE-ASSEMBLER-001"
CAP_ID = re.compile(r"^CAP-\d{3}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
KINDS = ("positive", "negative", "rollback")


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


def _expected_test_id(record: dict[str, Any], kind: str) -> Any:
    return {
        "positive": record.get("required_positive_test"),
        "negative": record.get("required_negative_test"),
        "rollback": record.get("rollback_requirement"),
    }[kind]


def _validate_result(
    root: Path,
    record: dict[str, Any],
    kind: str,
    path: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    try:
        result = _load(path)
    except Exception as exc:
        return None, [f"result unreadable: {exc}"]

    cap = record.get("subject_id")
    expected_id = _expected_test_id(record, kind)
    if result.get("schema") != RESULT_SCHEMA:
        findings.append("result schema mismatch")
    if result.get("subject_id") != cap:
        findings.append("result subject_id mismatch")
    if result.get("test_kind") != kind:
        findings.append(f"test_kind mismatch: expected {kind}")
    if result.get("test_id") != expected_id:
        findings.append(f"test_id mismatch: expected {expected_id}")
    if result.get("status") != "PASS":
        findings.append("result status is not PASS")
    if result.get("execution_scope") != "CURRENT_HOST":
        findings.append("execution_scope is not CURRENT_HOST")
    if result.get("current_host") is not True:
        findings.append("current_host flag is not true")
    if result.get("synthetic") is not False:
        findings.append("synthetic result cannot produce a bundle")
    if result.get("ci_reference_only") is not False:
        findings.append("CI/reference-only result cannot produce a bundle")
    if result.get("global_promotion_claim") is not False:
        findings.append("test result must not claim global promotion")

    executor = result.get("executor")
    if not isinstance(executor, dict):
        findings.append("executor missing/invalid")
    else:
        if not isinstance(executor.get("id"), str) or not executor.get("id"):
            findings.append("executor.id missing/invalid")
        if executor.get("mode") != "REAL_CURRENT_HOST_EXECUTION":
            findings.append("executor.mode is not REAL_CURRENT_HOST_EXECUTION")
        if executor.get("synthetic") is not False:
            findings.append("executor synthetic flag is not false")

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

    artifact_rel = result.get("artifact_path")
    artifact_digest = result.get("artifact_sha256")
    artifact_path, artifact_err = _repo_file(root, artifact_rel)
    if artifact_err:
        findings.append(f"test artifact {artifact_err}")
    if not isinstance(artifact_digest, str) or not HEX64.fullmatch(artifact_digest):
        findings.append("artifact_sha256 missing/invalid")
    elif artifact_path is not None and _sha256(artifact_path) != artifact_digest:
        findings.append("test artifact digest mismatch")

    host_rel = result.get("host_fingerprint_path")
    host_digest = result.get("host_fingerprint_sha256")
    host_path, host_err = _repo_file(root, host_rel)
    if host_err:
        findings.append(f"host_fingerprint {host_err}")
    if not isinstance(host_digest, str) or not HEX64.fullmatch(host_digest):
        findings.append("host_fingerprint_sha256 missing/invalid")
    elif host_path is not None and _sha256(host_path) != host_digest:
        findings.append("host fingerprint digest mismatch")

    if findings:
        return None, findings
    return {
        "kind": kind,
        "test_id": result["test_id"],
        "collected_at": result["collected_at"],
        "expires_at": result["expires_at"],
        "artifact_path": artifact_rel,
        "artifact_sha256": artifact_digest,
        "host_fingerprint_path": host_rel,
        "host_fingerprint_sha256": host_digest,
        "executor": executor,
        "result_manifest_path": path.resolve().relative_to(root).as_posix(),
        "result_manifest_sha256": _sha256(path),
    }, []


def _bundle_from_results(cap: str, rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    host_paths = {row["host_fingerprint_path"] for row in rows.values()}
    host_digests = {row["host_fingerprint_sha256"] for row in rows.values()}
    if len(host_paths) != 1 or len(host_digests) != 1:
        raise ValueError("positive/negative/rollback results must bind to one host fingerprint")

    collected = max(_parse_time(row["collected_at"]) for row in rows.values())
    expires = min(_parse_time(row["expires_at"]) for row in rows.values())
    assert collected is not None and expires is not None
    if expires <= collected:
        raise ValueError("combined result validity window is empty")

    artifacts: dict[str, str] = {}
    for row in rows.values():
        artifacts[row["artifact_path"]] = row["artifact_sha256"]
        artifacts[row["result_manifest_path"]] = row["result_manifest_sha256"]
    host_path = next(iter(host_paths))
    host_digest = next(iter(host_digests))
    artifacts[host_path] = host_digest

    return {
        "schema": BUNDLE_SCHEMA,
        "subject_id": cap,
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "global_promotion_claim": False,
        "collected_at": collected.isoformat(),
        "expires_at": expires.isoformat(),
        "host_fingerprint_path": host_path,
        "host_fingerprint_sha256": host_digest,
        "tests": {
            kind: {
                "id": rows[kind]["test_id"],
                "status": "PASS",
                "artifact_path": rows[kind]["artifact_path"],
                "artifact_sha256": rows[kind]["artifact_sha256"],
            }
            for kind in KINDS
        },
        "evidence_artifacts": [
            {"path": path, "sha256": digest}
            for path, digest in sorted(artifacts.items())
        ],
        "assembler": {
            "id": ASSEMBLER_ID,
            "source_result_schema": RESULT_SCHEMA,
            "provider_receipt_is_test_result": False,
            "generic_host_collection_is_test_result": False,
            "automatic_promotion": False,
        },
    }


def materialize(root: Path) -> dict[str, Any]:
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
            "code": "CHB-001",
            "message": "Evidence Registry is not the exact active capability set",
        })

    input_root = root / ".fa3-current-host/test-results/capabilities"
    output_root = root / ".fa3-current-host/test-bundles/capabilities"
    plan_rows: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    bundles: dict[str, dict[str, Any]] = {}
    pending_caps: list[str] = []

    known_paths = {
        (input_root / cap / f"{kind}.json").resolve()
        for cap in expected_ids
        for kind in KINDS
    }
    if input_root.is_dir():
        for path in input_root.rglob("*.json"):
            if path.resolve() not in known_paths:
                blocking.append({
                    "code": "CHB-002",
                    "message": "Unknown current-host capability test result manifest",
                    "path": path.resolve().relative_to(root).as_posix(),
                })

    for record in records if not blocking else []:
        cap = record["subject_id"]
        expected = {
            kind: {
                "test_id": _expected_test_id(record, kind),
                "result_manifest": (input_root / cap / f"{kind}.json").relative_to(root).as_posix(),
            }
            for kind in KINDS
        }
        plan_rows.append({
            "subject_id": cap,
            "subject": record.get("subject"),
            "obligation": record.get("obligation"),
            "activation": record.get("activation"),
            "tests": expected,
        })

        existing = {kind: input_root / cap / f"{kind}.json" for kind in KINDS}
        present = {kind: path.is_file() for kind, path in existing.items()}
        if not any(present.values()):
            pending_caps.append(cap)
            report_rows.append({
                "subject_id": cap,
                "status": "PENDING_TEST_RESULTS",
                "present_test_kinds": [],
                "missing_test_kinds": list(KINDS),
                "findings": [],
            })
            continue
        if not all(present.values()):
            pending_caps.append(cap)
            report_rows.append({
                "subject_id": cap,
                "status": "PENDING_TEST_RESULTS",
                "present_test_kinds": [k for k in KINDS if present[k]],
                "missing_test_kinds": [k for k in KINDS if not present[k]],
                "findings": [],
            })
            continue

        validated: dict[str, dict[str, Any]] = {}
        findings: list[str] = []
        for kind, path in existing.items():
            row, row_findings = _validate_result(root, record, kind, path)
            if row is not None:
                validated[kind] = row
            findings.extend(f"{kind}: {item}" for item in row_findings)
        if findings:
            blocking.append({
                "code": "CHB-003",
                "message": "Current-host capability test result rejected",
                "subject_id": cap,
                "findings": findings,
            })
            report_rows.append({
                "subject_id": cap,
                "status": "REJECTED",
                "present_test_kinds": list(KINDS),
                "missing_test_kinds": [],
                "findings": findings,
            })
            continue
        try:
            bundles[cap] = _bundle_from_results(cap, validated)
        except ValueError as exc:
            findings = [str(exc)]
            blocking.append({
                "code": "CHB-004",
                "message": "Capability test results cannot form one provenance-bound bundle",
                "subject_id": cap,
                "findings": findings,
            })
            report_rows.append({
                "subject_id": cap,
                "status": "REJECTED",
                "present_test_kinds": list(KINDS),
                "missing_test_kinds": [],
                "findings": findings,
            })
            continue
        report_rows.append({
            "subject_id": cap,
            "status": "QUALIFIED_FOR_BUNDLE",
            "present_test_kinds": list(KINDS),
            "missing_test_kinds": [],
            "findings": [],
        })

    materialized: list[str] = []
    if not blocking:
        for cap, bundle in sorted(bundles.items()):
            out = output_root / f"{cap}.json"
            if out.is_file():
                try:
                    existing = _load(out)
                except Exception as exc:
                    blocking.append({
                        "code": "CHB-005",
                        "message": "Existing capability test bundle unreadable",
                        "subject_id": cap,
                        "error": str(exc),
                    })
                    continue
                if existing != bundle:
                    blocking.append({
                        "code": "CHB-006",
                        "message": "Existing capability test bundle collision",
                        "subject_id": cap,
                    })
        if not blocking:
            for cap, bundle in sorted(bundles.items()):
                _write(output_root / f"{cap}.json", bundle)
                materialized.append(cap)

    plan = {
        "schema": PLAN_SCHEMA,
        "id": "FA3-CURRENT-HOST-CAPABILITY-TEST-PLAN-001",
        "capability_count": CAPABILITY_COUNT,
        "result_schema": RESULT_SCHEMA,
        "bundle_schema": BUNDLE_SCHEMA,
        "execution_scope": "CURRENT_HOST",
        "synthetic_results_allowed": False,
        "ci_reference_results_allowed": False,
        "provider_receipt_substitution_allowed": False,
        "generic_host_evidence_substitution_allowed": False,
        "capabilities": plan_rows,
    }
    _write(root / ".fa3-current-host/test-plan/capabilities.json", plan)

    if blocking:
        integrity = "FAIL"
        status = "BLOCKED"
    elif materialized and pending_caps:
        integrity = "PASS"
        status = "PARTIAL_CURRENT_HOST_TEST_BUNDLES_MATERIALIZED"
    elif materialized and len(materialized) == CAPABILITY_COUNT:
        integrity = "PASS"
        status = "ALL_CURRENT_HOST_TEST_BUNDLES_MATERIALIZED"
    else:
        integrity = "PASS"
        status = "PENDING_CURRENT_HOST_TEST_RESULTS"

    report = {
        "schema": REPORT_SCHEMA,
        "id": ASSEMBLER_ID,
        "capability_count": CAPABILITY_COUNT,
        "assembler_integrity": integrity,
        "materialization_status": status,
        "qualified_bundle_count": len(bundles),
        "bundles_materialized": len(materialized),
        "materialized_capability_ids": materialized,
        "pending_capability_count": len(pending_caps),
        "pending_capability_ids": pending_caps,
        "provider_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "automatic_promotion": False,
        "capabilities": report_rows,
        "blocking_findings": blocking,
        "truth_constraints": {
            "provider_pass_is_capability_test_result": False,
            "generic_host_collection_is_capability_test_result": False,
            "ci_reference_pass_is_current_host_test_result": False,
            "exact_registry_test_ids_required": True,
            "positive_negative_rollback_required_for_bundle": True,
            "single_host_fingerprint_required_per_bundle": True,
            "all_artifacts_must_be_hash_bound": True,
        },
    }
    _write(root / "reports/current-host-capability-test-bundle-assembler.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble FA3 capability test bundles only from explicit real current-host test results"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = materialize(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["assembler_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
