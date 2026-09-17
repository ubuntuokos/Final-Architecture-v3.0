#!/usr/bin/env python3
from __future__ import annotations

from fa3_release_baseline import module_active_capability_count

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fa3_current_host_capability_test_executor_audit import audit as audit_executors

CAPABILITY_COUNT = module_active_capability_count(__file__)
OBLIGATION_COUNT = CAPABILITY_COUNT * 3
EXECUTOR_REGISTRY = "canonical/current-host-capability-test-executors.json"
VERDICT_SCHEMA = "fa3.capability-current-host-test-verdict.v1"
RESULT_SCHEMA = "fa3.capability-current-host-test-result.v1"
REPORT_SCHEMA = "fa3.current-host-capability-test-orchestrator-report.v2"
ORCHESTRATOR_ID = "FA3-CURRENT-HOST-CAPABILITY-TEST-ORCHESTRATOR-002"
HOST_FINGERPRINT = ".fa3-current-host/global-closure/host/host-fingerprint.json"
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


def _repo_file(root: Path, rel: Any) -> tuple[Path | None, str | None]:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None, "path missing or absolute"
    path = (root / rel).resolve()
    if path == root or root not in path.parents:
        return None, "path escapes repository"
    if not path.is_file():
        return None, f"file missing: {rel}"
    return path, None


def _command_for_adapter(root: Path, entry: dict[str, Any]) -> tuple[list[str] | None, str | None]:
    adapter, error = _repo_file(root, entry.get("adapter_path"))
    if error or adapter is None:
        return None, error or "adapter missing"
    expected = entry.get("adapter_sha256")
    if _sha256(adapter) != expected:
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


def _validate_verdict(
    root: Path,
    entry: dict[str, Any],
    verdict: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    findings: list[str] = []
    for key, expected in (
        ("schema", VERDICT_SCHEMA),
        ("subject_id", entry.get("subject_id")),
        ("test_kind", entry.get("test_kind")),
        ("test_id", entry.get("test_id")),
        ("status", "PASS"),
        ("execution_scope", "CURRENT_HOST"),
        ("current_host", True),
        ("synthetic", False),
        ("ci_reference_only", False),
        ("global_promotion_claim", False),
        ("evidence_class", "CAPABILITY_SPECIFIC_EXECUTABLE_TEST"),
    ):
        if verdict.get(key) != expected:
            findings.append(f"{key} mismatch: expected {expected!r}")

    artifact_rel = verdict.get("artifact_path")
    artifact_digest = verdict.get("artifact_sha256")
    artifact, error = _repo_file(root, artifact_rel)
    if error:
        findings.append(f"artifact {error}")
    if not isinstance(artifact_digest, str) or len(artifact_digest) != 64:
        findings.append("artifact_sha256 missing/invalid")
    elif artifact is not None and _sha256(artifact) != artifact_digest:
        findings.append("artifact digest mismatch")

    if findings:
        return None, findings
    return {
        "artifact_path": artifact_rel,
        "artifact_sha256": artifact_digest,
    }, []


def _sanitized_env(root: Path, entry: dict[str, Any], host_digest: str) -> dict[str, str]:
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")
    env = {key: os.environ[key] for key in keep if key in os.environ}
    env.update({
        "FA3_CURRENT_HOST": "1",
        "FA3_EXECUTION_SCOPE": "CURRENT_HOST",
        "FA3_CAPABILITY_ID": str(entry["subject_id"]),
        "FA3_TEST_KIND": str(entry["test_kind"]),
        "FA3_TEST_ID": str(entry["test_id"]),
        "FA3_HOST_FINGERPRINT_PATH": HOST_FINGERPRINT,
        "FA3_HOST_FINGERPRINT_SHA256": host_digest,
        "FA3_REPOSITORY_ROOT": str(root),
        "PYTHONNOUSERSITE": "1",
    })
    return env


def _execute_entry(
    root: Path,
    entry: dict[str, Any],
    host_digest: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    command, command_error = _command_for_adapter(root, entry)
    if command_error or command is None:
        return None, [command_error or "adapter command unavailable"]

    timeout = entry.get("timeout_seconds", 300)
    if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
        return None, ["timeout_seconds outside 1..3600"]
    ttl = entry.get("ttl_seconds", 86400)
    if not isinstance(ttl, int) or ttl < 60 or ttl > 604800:
        return None, ["ttl_seconds outside 60..604800"]

    started = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            command,
            cwd=root,
            env=_sanitized_env(root, entry, host_digest),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, ["adapter timed out"]
    finished = datetime.now(timezone.utc)
    if proc.returncode != 0:
        return None, [f"adapter returncode {proc.returncode}"]
    try:
        verdict = json.loads(proc.stdout)
    except Exception as exc:
        return None, [f"adapter stdout is not a single JSON verdict: {exc}"]
    if not isinstance(verdict, dict):
        return None, ["adapter verdict is not an object"]

    evidence, findings = _validate_verdict(root, entry, verdict)
    if findings or evidence is None:
        return None, findings

    result = {
        "schema": RESULT_SCHEMA,
        "subject_id": entry["subject_id"],
        "test_kind": entry["test_kind"],
        "test_id": entry["test_id"],
        "status": "PASS",
        "execution_scope": "CURRENT_HOST",
        "current_host": True,
        "synthetic": False,
        "ci_reference_only": False,
        "global_promotion_claim": False,
        "collected_at": finished.isoformat(),
        "expires_at": (finished + timedelta(seconds=ttl)).isoformat(),
        "host_fingerprint_path": HOST_FINGERPRINT,
        "host_fingerprint_sha256": host_digest,
        "artifact_path": evidence["artifact_path"],
        "artifact_sha256": evidence["artifact_sha256"],
        "executor": {
            "id": ORCHESTRATOR_ID,
            "mode": "REAL_CURRENT_HOST_EXECUTION",
            "synthetic": False,
            "executor_registry": EXECUTOR_REGISTRY,
            "adapter_path": entry["adapter_path"],
            "adapter_sha256": entry["adapter_sha256"],
            "verdict_schema": VERDICT_SCHEMA,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        },
    }
    return result, []


def orchestrate(root: Path, *, execute: bool) -> dict[str, Any]:
    root = Path(root).resolve()
    coverage = audit_executors(root)
    blocking: list[dict[str, Any]] = []
    if coverage.get("audit_integrity") != "PASS":
        blocking.append({
            "code": "CHOR-001",
            "message": "Executor registry audit failed",
            "findings": coverage.get("blocking_findings", []),
        })

    executor_registry = _load(root / EXECUTOR_REGISTRY)
    entries = executor_registry.get("entries", []) if isinstance(executor_registry.get("entries"), list) else []
    host_path = root / HOST_FINGERPRINT
    host_digest: str | None = None
    if execute and entries and not blocking:
        if platform.system() != "Linux":
            blocking.append({"code": "CHOR-002", "message": "Real current-host execution requires Linux"})
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            blocking.append({"code": "CHOR-003", "message": "Real current-host execution must be non-root"})
        if not host_path.is_file():
            blocking.append({"code": "CHOR-004", "message": "Fresh current-host fingerprint missing"})
        else:
            host_digest = _sha256(host_path)

    materialized: list[str] = []
    executed: list[dict[str, Any]] = []
    if execute and entries and not blocking and host_digest is not None:
        for entry in entries:
            key = f"{entry.get('subject_id')}:{entry.get('test_kind')}"
            result, findings = _execute_entry(root, entry, host_digest)
            if findings or result is None:
                blocking.append({
                    "code": "CHOR-005",
                    "message": "Capability current-host test execution rejected",
                    "obligation": key,
                    "findings": findings,
                })
                executed.append({"obligation": key, "status": "REJECTED", "findings": findings})
                continue
            out = root / f".fa3-current-host/test-results/capabilities/{entry['subject_id']}/{entry['test_kind']}.json"
            if out.is_file():
                blocking.append({
                    "code": "CHOR-006",
                    "message": "Current-host test result collision",
                    "obligation": key,
                })
                executed.append({"obligation": key, "status": "REJECTED", "findings": ["result collision"]})
                continue
            _write(out, result)
            materialized.append(key)
            executed.append({"obligation": key, "status": "PASS", "findings": []})

    if blocking:
        integrity = "FAIL"
        status = "BLOCKED_CURRENT_HOST_TEST_EXECUTION"
    elif execute and materialized:
        integrity = "PASS"
        status = "EXECUTED_REGISTERED_CAPABILITY_TESTS"
    elif entries:
        integrity = "PASS"
        status = "REGISTERED_EXECUTORS_NOT_EXECUTED"
    else:
        integrity = "PASS"
        status = "PENDING_EXECUTOR_REGISTRATION"

    report = {
        "schema": REPORT_SCHEMA,
        "id": ORCHESTRATOR_ID,
        "orchestrator_integrity": integrity,
        "status": status,
        "execution_requested": execute,
        "capability_count": CAPABILITY_COUNT,
        "required_test_obligation_count": OBLIGATION_COUNT,
        "registered_executor_count": coverage.get("registered_executor_count", 0),
        "pending_executor_count": coverage.get("pending_executor_count", OBLIGATION_COUNT),
        "results_materialized": len(materialized),
        "materialized_obligations": materialized,
        "executions": executed,
        "blocking_findings": blocking,
        "provider_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "automatic_promotion": False,
        "truth_constraints": {
            "canonical_executor_registry_is_single_source": True,
            "parallel_test_registry_forbidden": True,
            "exit_code_alone_is_pass": False,
            "typed_verdict_required": True,
            "adapter_digest_revalidated_before_execution": True,
            "shell_execution_allowed": False,
            "host_fingerprint_bound_by_orchestrator": True,
            "unregistered_test_execution_allowed": False,
            "provider_pass_is_capability_test_result": False,
            "generic_host_collection_is_capability_test_result": False,
            "hosted_ci_pass_is_current_host_test_result": False,
        },
    }
    _write(root / "reports/current-host-capability-test-orchestrator.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute only explicitly registered FA3 capability tests on the real current host")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    report = orchestrate(Path(args.root), execute=args.execute)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["orchestrator_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
