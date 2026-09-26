#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fa3_current_host_capability_qualification_constituent_producer_audit import (
    EXECUTION_MODE,
    PRODUCER_REGISTRY,
    audit as audit_producers,
)
from fa3_current_host_capability_test_qualification_audit import CONSTITUENT_SCHEMA

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
REPORT_SCHEMA = "fa3.current-host-capability-qualification-constituent-orchestrator-report.v1"
ORCHESTRATOR_ID = "FA3-CURRENT-HOST-QUALIFICATION-CONSTITUENT-ORCHESTRATOR-001"
HOST_FINGERPRINT = ".fa3-current-host/global-closure/host/host-fingerprint.json"
SOURCE_ROOT = ".fa3-current-host/qualification-source-artifacts"
CONSTITUENT_ROOT = ".fa3-current-host/qualification-constituents"
REJECTION_SCHEMA = "fa3.qualification-producer-rejection.v1"
REJECTION_STAGES = {"COLLECTOR", "GATE", "PRODUCER"}
REJECTION_REASON_CODES = {
    "CAP006_CPU_BASELINE_UNPROVEN", "CAP006_ACCELERATOR_INVENTORY_INVALID",
    "CAP006_MANAGER_COLLECTION_FAILED", "CAP006_MANAGER_NEUTRALITY_VIOLATION",
    "CAP006_CGROUP_V2_UNPROVEN", "CAP006_EFFECTIVE_CPUSET_UNRESOLVED",
    "CAP006_EFFECTIVE_MEMSET_UNRESOLVED", "CAP006_NEGATIVE_MATRIX_FAILED",
    "CAP006_RECEIPT_UNAVAILABLE", "CAP006_CHECK_SUMMARY_UNAVAILABLE",
    "CAP006_COLLECTOR_REJECTED", "CAP006_GATE_REPORT_UNAVAILABLE",
    "CAP006_GATE_REPORT_INVALID", "CAP006_GATE_REJECTED", "MAT002_EXECUTION_REJECTED",
    "HRB-SYSD-HOST-000", "HRB-SYSD-HOST-001", "HRB-SYSD-HOST-002", "HRB-SYSD-HOST-003",
    "HRB-SYSD-HOST-004", "HRB-SYSD-HOST-005", "HRB-SYSD-HOST-006", "HRB-SYSD-HOST-007",
    "HRB-SYSD-HOST-008", "HRB-SYSD-HOST-009",
}
REJECTION_SUMMARY_KEYS = {
    "cpu_baseline_pass", "accelerator_inventory_schema_pass", "manager_collection_pass",
    "manager_neutrality_pass", "cgroup_v2_pass", "negative_tests_pass", "failed_check_codes",
    "cpu_package_count", "minimum_physical_cores", "accelerator_device_count",
    "effective_cpu_set_present", "effective_memory_nodes_present", "failed_negative_test_codes",
}


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


def _structured_rejection_findings(stderr: str, entry: dict[str, Any]) -> list[str]:
    """Extract only schema-bound codes and bounded scalar summaries from a registered producer."""
    for raw in reversed(stderr.splitlines()):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("schema") != REJECTION_SCHEMA or obj.get("status") != "REJECTED":
            continue
        if any(obj.get(key) != entry.get(key) for key in ("producer_id","qualification_id","constituent_id","subject_id")):
            return []
        if obj.get("stage") not in REJECTION_STAGES:
            return []
        codes=obj.get("reason_codes")
        if not isinstance(codes,list) or not 1 <= len(codes) <= 8 or any(code not in REJECTION_REASON_CODES for code in codes):
            return []
        summary=obj.get("summary",{})
        if not isinstance(summary,dict) or any(key not in REJECTION_SUMMARY_KEYS for key in summary):
            return []
        for value in summary.values():
            if isinstance(value,list):
                if len(value)>8 or any(not isinstance(item,str) or len(item)>80 for item in value):return []
            elif value is not None and not isinstance(value,(bool,int)):
                return []
        safe=[f"producer stage: {obj['stage']}"]
        safe.extend(f"producer reason code: {code}" for code in codes)
        if summary:safe.append("producer summary: "+json.dumps(summary,sort_keys=True,separators=(",",":")))
        return safe
    return []


def _repo_file(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "path missing or absolute"
    unresolved = root / rel
    if unresolved.is_symlink():
        return None, "symlink paths are forbidden"
    path = unresolved.resolve()
    if path == root or root not in path.parents:
        return None, "path escapes repository"
    if not path.is_file():
        return None, f"file missing: {rel}"
    return path, None


def _scope_rel(entry: dict[str, Any]) -> str:
    return f"{SOURCE_ROOT}/{entry['qualification_id']}/{entry['constituent_id']}"


def _scope(root: Path, entry: dict[str, Any]) -> Path:
    return (root / _scope_rel(entry)).resolve()


def _prepare_scope(root: Path, entry: dict[str, Any]) -> Path:
    scope = _scope(root, entry)
    parent = (root / SOURCE_ROOT).resolve()
    if parent not in scope.parents:
        raise RuntimeError("producer source-artifact scope escaped canonical root")
    shutil.rmtree(scope, ignore_errors=True)
    scope.mkdir(parents=True, exist_ok=False)
    return scope


def _command(root: Path, entry: dict[str, Any]) -> tuple[list[str] | None, str | None]:
    adapter, error = _repo_file(root, entry.get("adapter_path"))
    if error or adapter is None:
        return None, error or "adapter missing"
    expected = entry.get("adapter_sha256")
    if not isinstance(expected, str) or _sha256(adapter) != expected:
        return None, "adapter digest mismatch"
    argv = entry.get("argv", [])
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        return None, "argv must be a list of strings"
    if any(item in {"sudo", "sh", "bash", "-c", "--shell"} for item in argv):
        return None, "shell/privilege escalation token in argv"
    if adapter.suffix == ".py":
        return [sys.executable, str(adapter), *argv], None
    if not os.access(adapter, os.X_OK):
        return None, "non-Python adapter is not executable"
    return [str(adapter), *argv], None


def _env(
    root: Path,
    entry: dict[str, Any],
    host_digest: str,
    scope: Path,
) -> dict[str, str]:
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env.update({
        "FA3_CURRENT_HOST": "1",
        "FA3_EXECUTION_SCOPE": "CURRENT_HOST",
        "FA3_QUALIFICATION_ID": str(entry["qualification_id"]),
        "FA3_CONSTITUENT_ID": str(entry["constituent_id"]),
        "FA3_CAPABILITY_ID": str(entry["subject_id"]),
        "FA3_TEST_KIND": str(entry["test_kind"]),
        "FA3_TEST_ID": str(entry["test_id"]),
        "FA3_SOURCE_EVIDENCE_CLASS": str(entry["source_evidence_class"]),
        "FA3_COVERS_SOURCE_DECISION_IDS_JSON": json.dumps(entry["covers_source_decision_ids"], separators=(",", ":")),
        "FA3_HOST_FINGERPRINT_PATH": HOST_FINGERPRINT,
        "FA3_HOST_FINGERPRINT_SHA256": host_digest,
        "FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR": str(scope),
        "FA3_QUALIFICATION_SOURCE_ARTIFACT_REL_DIR": scope.relative_to(root).as_posix(),
        "FA3_REPOSITORY_ROOT": str(root),
        "PYTHONNOUSERSITE": "1",
    })
    return env


def _validate_verdict(
    root: Path,
    entry: dict[str, Any],
    verdict: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    for key, expected in (
        ("schema", VERDICT_SCHEMA),
        ("producer_id", entry.get("producer_id")),
        ("qualification_id", entry.get("qualification_id")),
        ("constituent_id", entry.get("constituent_id")),
        ("subject_id", entry.get("subject_id")),
        ("test_kind", entry.get("test_kind")),
        ("test_id", entry.get("test_id")),
        ("status", "PASS"),
        ("execution_scope", "CURRENT_HOST"),
        ("current_host", True),
        ("synthetic", False),
        ("ci_reference_only", False),
        ("provider_receipt_only", False),
        ("component_receipt_only", False),
        ("generic_host_collection_only", False),
        ("global_promotion_claim", False),
        ("source_evidence_class", entry.get("source_evidence_class")),
        ("covers_source_decision_ids", entry.get("covers_source_decision_ids")),
    ):
        if verdict.get(key) != expected:
            findings.append(f"{key} mismatch: expected {expected!r}")

    artifact_rel = verdict.get("source_artifact_path")
    artifact_digest = verdict.get("source_artifact_sha256")
    artifact, error = _repo_file(root, artifact_rel)
    if error:
        findings.append(f"source artifact {error}")
    elif artifact is not None:
        if not isinstance(artifact_digest, str) or _sha256(artifact) != artifact_digest:
            findings.append("source artifact digest mismatch")
        scope = _scope(root, entry)
        if scope not in artifact.parents:
            findings.append("source artifact must be inside exact qualification constituent scope")

    if findings:
        return None, findings
    return {
        "source_artifact_path": artifact_rel,
        "source_artifact_sha256": artifact_digest,
    }, []


def _execute(
    root: Path,
    entry: dict[str, Any],
    host_digest: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    command, command_error = _command(root, entry)
    if command_error or command is None:
        return None, [command_error or "producer command unavailable"]

    timeout = entry.get("timeout_seconds", 300)
    ttl = entry.get("ttl_seconds", 86400)
    if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
        return None, ["timeout_seconds outside 1..3600"]
    if not isinstance(ttl, int) or ttl < 60 or ttl > 604800:
        return None, ["ttl_seconds outside 60..604800"]

    try:
        scope = _prepare_scope(root, entry)
    except Exception as exc:
        return None, [f"source artifact scope preparation failed: {exc}"]

    started = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            command,
            cwd=root,
            env=_env(root, entry, host_digest, scope),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, ["producer adapter timed out"]
    finished = datetime.now(timezone.utc)

    if proc.returncode != 0:
        findings = [f"producer adapter returncode {proc.returncode}"]
        findings.extend(
            f"producer rejection: {detail}"
            for detail in _structured_rejection_findings(proc.stderr, entry)
        )
        return None, findings
    try:
        verdict = json.loads(proc.stdout)
    except Exception as exc:
        return None, [f"producer stdout is not a single JSON verdict: {exc}"]
    if not isinstance(verdict, dict):
        return None, ["producer verdict is not an object"]

    source, verdict_findings = _validate_verdict(root, entry, verdict)
    if verdict_findings or source is None:
        return None, verdict_findings

    manifest = {
        "schema": CONSTITUENT_SCHEMA,
        "qualification_id": entry["qualification_id"],
        "constituent_id": entry["constituent_id"],
        "subject_id": entry["subject_id"],
        "test_kind": entry["test_kind"],
        "test_id": entry["test_id"],
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "provider_receipt_only": False,
        "component_receipt_only": False,
        "generic_host_collection_only": False,
        "global_promotion_claim": False,
        "evidence_authority_id": "FA3-AUTH-OBS-EVIDENCE-001",
        "source_evidence_class": entry["source_evidence_class"],
        "covers_source_decision_ids": entry["covers_source_decision_ids"],
        "host_fingerprint_path": HOST_FINGERPRINT,
        "host_fingerprint_sha256": host_digest,
        "collected_at": finished.isoformat(),
        "expires_at": (finished + timedelta(seconds=ttl)).isoformat(),
        "source_artifact_path": source["source_artifact_path"],
        "source_artifact_sha256": source["source_artifact_sha256"],
        "producer": {
            "orchestrator_id": ORCHESTRATOR_ID,
            "producer_registry": PRODUCER_REGISTRY,
            "producer_id": entry["producer_id"],
            "execution_mode": EXECUTION_MODE,
            "adapter_path": entry["adapter_path"],
            "adapter_sha256": entry["adapter_sha256"],
            "artifact_scope": _scope_rel(entry),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        },
    }
    return manifest, []


def orchestrate(root: Path, *, execute: bool, subjects: set[str] | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    producer_audit = audit_producers(root)
    blocking: list[dict[str, Any]] = []
    if producer_audit.get("audit_integrity") != "PASS":
        blocking.append({
            "code": "QCPO-001",
            "message": "Qualification constituent producer audit failed",
            "findings": producer_audit.get("blocking_findings", []),
        })

    registry = _load(root / PRODUCER_REGISTRY)
    accepted_keys = {
        (row.get("qualification_id"), row.get("constituent_id"))
        for row in producer_audit.get("accepted_producers", [])
        if isinstance(row, dict)
    }
    entries = [
        entry for entry in registry.get("entries", [])
        if isinstance(entry, dict)
        and (entry.get("qualification_id"), entry.get("constituent_id")) in accepted_keys
    ]
    available_subjects = {str(entry.get("subject_id")) for entry in entries}
    requested_subjects = sorted(
        subjects or [],
        key=lambda x: (int(x.split("-", 1)[1]) if x.startswith("CAP-") and x.split("-", 1)[1].isdigit() else 10**9, x),
    )
    if subjects is not None:
        unknown = sorted(set(subjects) - available_subjects)
        if unknown:
            blocking.append({
                "code": "QCPO-007",
                "message": "Requested batch contains subjects without registered constituent producers",
                "subjects": unknown,
            })
        entries = [entry for entry in entries if entry.get("subject_id") in subjects]

    host_path = root / HOST_FINGERPRINT
    host_digest: str | None = None
    if execute and entries and not blocking:
        if platform.system() != "Linux":
            blocking.append({"code": "QCPO-002", "message": "Real constituent producer execution requires Linux"})
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            blocking.append({"code": "QCPO-003", "message": "Real constituent producer execution must be non-root"})
        if not host_path.is_file():
            blocking.append({"code": "QCPO-004", "message": "Fresh current-host fingerprint missing"})
        else:
            host_digest = _sha256(host_path)

    materialized: list[str] = []
    executions: list[dict[str, Any]] = []
    if execute and entries and not blocking and host_digest is not None:
        shutil.rmtree(root / CONSTITUENT_ROOT, ignore_errors=True)
        shutil.rmtree(root / SOURCE_ROOT, ignore_errors=True)
        for entry in entries:
            key = f"{entry.get('qualification_id')}:{entry.get('constituent_id')}"
            manifest, findings = _execute(root, entry, host_digest)
            if findings or manifest is None:
                blocking.append({
                    "code": "QCPO-005",
                    "message": "Qualification constituent producer execution rejected",
                    "constituent": key,
                    "findings": findings,
                })
                executions.append({"constituent": key, "status": "REJECTED", "findings": findings})
                break
            out = root / CONSTITUENT_ROOT / entry["qualification_id"] / f"{entry['constituent_id']}.json"
            if out.is_file():
                blocking.append({
                    "code": "QCPO-006",
                    "message": "Qualification constituent manifest collision",
                    "constituent": key,
                })
                executions.append({"constituent": key, "status": "REJECTED", "findings": ["manifest collision"]})
                break
            _write(out, manifest)
            materialized.append(key)
            executions.append({"constituent": key, "status": "PASS", "findings": []})

    if blocking and execute:
        shutil.rmtree(root / CONSTITUENT_ROOT, ignore_errors=True)
        shutil.rmtree(root / SOURCE_ROOT, ignore_errors=True)
        materialized = []

    if blocking:
        integrity = "FAIL"
        status = "BLOCKED_QUALIFICATION_CONSTITUENT_PRODUCTION"
    elif execute and materialized:
        integrity = "PASS"
        status = "EXECUTED_REGISTERED_CONSTITUENT_PRODUCERS"
    elif entries:
        integrity = "PASS"
        status = "REGISTERED_CONSTITUENT_PRODUCERS_NOT_EXECUTED"
    elif producer_audit.get("required_constituent_count", 0) == 0:
        integrity = "PASS"
        status = "PENDING_CAPABILITY_QUALIFICATION_DEFINITIONS"
    else:
        integrity = "PASS"
        status = "PENDING_CONSTITUENT_PRODUCER_REGISTRATION"

    report = {
        "schema": REPORT_SCHEMA,
        "id": ORCHESTRATOR_ID,
        "orchestrator_integrity": integrity,
        "status": status,
        "execution_requested": execute,
        "required_constituent_count": producer_audit.get("required_constituent_count", 0),
        "registered_producer_count": producer_audit.get("registered_producer_count", 0),
        "selected_producer_count": len(entries),
        "requested_subjects": requested_subjects,
        "pending_producer_count": producer_audit.get("pending_producer_count", 0),
        "constituents_materialized": len(materialized),
        "materialized_constituents": materialized,
        "executions": executions,
        "blocking_findings": blocking,
        "provider_receipts_promoted": 0,
        "component_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "automatic_promotion": False,
        "truth_constraints": {
            "unregistered_constituent_manifest_allowed": False,
            "typed_producer_verdict_required": True,
            "adapter_digest_revalidated_before_execution": True,
            "shell_execution_allowed": False,
            "host_fingerprint_bound_by_orchestrator": True,
            "obligation_scoped_fresh_source_artifact_required": True,
            "partial_constituents_survive_failed_run": False,
            "structured_registered_producer_rejection_findings_preserved": True,
            "hosted_ci_may_produce_current_host_constituents": False,
        },
    }
    _write(root / "reports/current-host-capability-qualification-constituent-orchestrator.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute registered FA3 current-host qualification constituent producers")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--subjects", default="", help="Comma-separated capability IDs to execute as one batch")
    args = parser.parse_args()
    subjects = {item.strip() for item in args.subjects.split(",") if item.strip()} if args.subjects else None
    report = orchestrate(Path(args.root), execute=args.execute, subjects=subjects)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["orchestrator_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
