#!/usr/bin/env python3
from __future__ import annotations

from fa3_release_baseline import module_active_capability_count

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = module_active_capability_count(__file__)
OBLIGATION_COUNT = CAPABILITY_COUNT * 3
REGISTRY_SCHEMA = "fa3.current-host-capability-test-executor-registry.v1"
REPORT_SCHEMA = "fa3.current-host-capability-test-executor-audit.v1"
AUDITOR_ID = "FA3-CURRENT-HOST-CAPABILITY-TEST-EXECUTOR-AUDIT-001"
EXECUTOR_REGISTRY = "canonical/current-host-capability-test-executors.json"
EVIDENCE_REGISTRY = "evidence/evidence-registry.json"
KINDS = ("positive", "negative", "rollback")
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


def _expected_test_id(record: dict[str, Any], kind: str) -> Any:
    return {
        "positive": record.get("required_positive_test"),
        "negative": record.get("required_negative_test"),
        "rollback": record.get("rollback_requirement"),
    }[kind]


def _repo_adapter(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "adapter_path missing or absolute"
    candidate = (root / rel).resolve()
    if candidate == root or root not in candidate.parents:
        return None, "adapter_path escapes repository"
    if not candidate.is_file():
        return None, f"adapter missing: {rel}"
    if not rel.startswith(("bin/", "src/", "evidence/", "tools/")):
        return None, "adapter_path is outside approved executable source roots"
    return candidate, None


def audit(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    evidence = _load(root / EVIDENCE_REGISTRY)
    executors = _load(root / EXECUTOR_REGISTRY)
    findings: list[dict[str, Any]] = []

    records = evidence.get("records", [])
    expected_ids = [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    actual_ids = [row.get("subject_id") for row in records]
    if (
        evidence.get("record_count") != CAPABILITY_COUNT
        or len(records) != CAPABILITY_COUNT
        or actual_ids != expected_ids
    ):
        findings.append({"code": "CHEX-001", "message": "Evidence Registry is not the exact active capability set"})

    if executors.get("schema") != REGISTRY_SCHEMA:
        findings.append({"code": "CHEX-002", "message": "Executor registry schema mismatch"})
    if executors.get("capability_count") != CAPABILITY_COUNT:
        findings.append({"code": "CHEX-003", "message": "Executor registry capability_count mismatch"})
    if executors.get("required_test_obligation_count") != OBLIGATION_COUNT:
        findings.append({"code": "CHEX-004", "message": "Executor registry obligation count mismatch"})
    if executors.get("execution_scope") != "CURRENT_HOST":
        findings.append({"code": "CHEX-005", "message": "Executor registry execution_scope must be CURRENT_HOST"})
    if executors.get("registration_semantics") != "EXPLICIT_ONLY_NO_INFERENCE":
        findings.append({"code": "CHEX-006", "message": "Executor registration must be explicit-only"})

    invariants = executors.get("invariants")
    required_false = (
        "provider_receipt_substitution_allowed",
        "generic_host_evidence_substitution_allowed",
        "hosted_ci_substitution_allowed",
        "synthetic_executor_allowed",
        "shell_command_registration_allowed",
        "automatic_capability_promotion",
        "automatic_global_promotion",
    )
    if not isinstance(invariants, dict):
        findings.append({"code": "CHEX-007", "message": "Executor registry invariants missing"})
    else:
        for key in required_false:
            if invariants.get(key) is not False:
                findings.append({"code": "CHEX-008", "message": f"Invariant must remain false: {key}"})
        if invariants.get("repository_local_adapter_required") is not True:
            findings.append({"code": "CHEX-009", "message": "repository_local_adapter_required must be true"})
        if invariants.get("exact_registry_test_identity_required") is not True:
            findings.append({"code": "CHEX-010", "message": "exact_registry_test_identity_required must be true"})
        if invariants.get("duplicate_test_registration_allowed") is not False:
            findings.append({"code": "CHEX-011", "message": "duplicate registrations must remain forbidden"})

    obligation_map: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        cap = record.get("subject_id")
        if cap not in expected_ids:
            continue
        for kind in KINDS:
            test_id = _expected_test_id(record, kind)
            obligation_map[(cap, kind)] = {
                "subject_id": cap,
                "subject": record.get("subject"),
                "test_kind": kind,
                "test_id": test_id,
            }
            if not isinstance(test_id, str) or not test_id:
                findings.append({
                    "code": "CHEX-012",
                    "message": "Capability test obligation lacks exact test identity",
                    "subject_id": cap,
                    "test_kind": kind,
                })

    entries = executors.get("entries")
    if not isinstance(entries, list):
        findings.append({"code": "CHEX-013", "message": "Executor registry entries must be a list"})
        entries = []

    registered: dict[tuple[str, str], dict[str, Any]] = {}
    entry_reports: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        entry_findings: list[str] = []
        if not isinstance(entry, dict):
            findings.append({"code": "CHEX-014", "message": "Executor entry is not an object", "index": index})
            continue
        cap = entry.get("subject_id")
        kind = entry.get("test_kind")
        key = (cap, kind)
        obligation = obligation_map.get(key)
        if not isinstance(cap, str) or not CAP_ID.fullmatch(cap):
            entry_findings.append("subject_id invalid")
        if kind not in KINDS:
            entry_findings.append("test_kind invalid")
        if obligation is None:
            entry_findings.append("entry does not map to an active capability test obligation")
        elif entry.get("test_id") != obligation.get("test_id"):
            entry_findings.append(f"test_id mismatch: expected {obligation.get('test_id')}")
        if key in registered:
            entry_findings.append("duplicate capability/test-kind registration")

        if entry.get("execution_mode") != "REAL_CURRENT_HOST_EXECUTION":
            entry_findings.append("execution_mode is not REAL_CURRENT_HOST_EXECUTION")
        if entry.get("evidence_class") != "CAPABILITY_SPECIFIC_EXECUTABLE_TEST":
            entry_findings.append("evidence_class is not CAPABILITY_SPECIFIC_EXECUTABLE_TEST")
        if entry.get("synthetic") is not False:
            entry_findings.append("synthetic must be false")
        if entry.get("ci_reference_only") is not False:
            entry_findings.append("ci_reference_only must be false")
        if entry.get("provider_receipt_only") is not False:
            entry_findings.append("provider_receipt_only must be false")
        if entry.get("generic_host_collection_only") is not False:
            entry_findings.append("generic_host_collection_only must be false")
        if entry.get("global_promotion_claim") is not False:
            entry_findings.append("global_promotion_claim must be false")

        adapter, adapter_err = _repo_adapter(root, entry.get("adapter_path"))
        if adapter_err:
            entry_findings.append(adapter_err)
        digest = entry.get("adapter_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            entry_findings.append("adapter_sha256 missing/invalid")
        elif adapter is not None and _sha256(adapter) != digest:
            entry_findings.append("adapter digest mismatch")

        args = entry.get("argv", [])
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            entry_findings.append("argv must be a list of strings")
        if isinstance(args, list) and any(item in {"sudo", "sh", "bash", "-c", "--shell"} for item in args):
            entry_findings.append("shell/privilege escalation tokens are forbidden in argv")

        status = "REGISTERED" if not entry_findings else "REJECTED"
        entry_reports.append({
            "index": index,
            "subject_id": cap,
            "test_kind": kind,
            "test_id": entry.get("test_id"),
            "adapter_path": entry.get("adapter_path"),
            "status": status,
            "findings": entry_findings,
        })
        if entry_findings:
            findings.append({
                "code": "CHEX-015",
                "message": "Executor registration rejected",
                "index": index,
                "subject_id": cap,
                "test_kind": kind,
                "findings": entry_findings,
            })
        else:
            registered[key] = entry

    pending = [
        obligation
        for key, obligation in obligation_map.items()
        if key not in registered
    ]
    registered_rows = [
        obligation_map[key] | {
            "adapter_path": entry.get("adapter_path"),
            "adapter_sha256": entry.get("adapter_sha256"),
        }
        for key, entry in sorted(registered.items())
    ]

    if findings:
        integrity = "FAIL"
        coverage = "BLOCKED_INVALID_EXECUTOR_REGISTRY"
    elif len(registered) == OBLIGATION_COUNT:
        integrity = "PASS"
        coverage = "COMPLETE_429_OF_429"
    elif registered:
        integrity = "PASS"
        coverage = "PARTIAL_EXPLICIT_EXECUTOR_COVERAGE"
    else:
        integrity = "PASS"
        coverage = "PENDING_EXECUTOR_REGISTRATION"

    report = {
        "schema": REPORT_SCHEMA,
        "id": AUDITOR_ID,
        "executor_registry": EXECUTOR_REGISTRY,
        "capability_count": CAPABILITY_COUNT,
        "required_test_obligation_count": OBLIGATION_COUNT,
        "audit_integrity": integrity,
        "coverage_status": coverage,
        "registered_executor_count": len(registered),
        "pending_executor_count": len(pending),
        "coverage_percent": round((len(registered) / OBLIGATION_COUNT) * 100, 6),
        "registered_obligations": registered_rows,
        "pending_obligations": pending,
        "entry_audit": entry_reports,
        "blocking_findings": findings,
        "provider_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "truth_constraints": {
            "executor_mapping_may_be_inferred_from_provider": False,
            "executor_mapping_may_be_inferred_from_current_host_collector": False,
            "unregistered_test_may_emit_pass_result": False,
            "hosted_ci_may_satisfy_current_host_test": False,
            "synthetic_executor_may_satisfy_current_host_test": False,
            "executor_registry_is_promotion_authority": False,
        },
    }
    _write(root / "reports/current-host-capability-test-executor-audit.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit explicit FA3 current-host capability test executor coverage")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = audit(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["audit_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
