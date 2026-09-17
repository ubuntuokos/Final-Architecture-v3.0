#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

CAPABILITY_COUNT = module_active_capability_count(__file__)
REGISTRY_SCHEMA = "fa3.current-host-capability-test-registry.v1"
BUNDLE_SCHEMA = "fa3.capability-current-host-test-bundle.v1"
ORCHESTRATOR_ID = "FA3-CURRENT-HOST-CAPABILITY-TEST-ORCHESTRATOR-001"
PHASES = ("positive", "negative", "rollback")


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


def _repo_path(root: Path, rel: Any) -> Path | None:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None
    candidate = (root / rel).resolve()
    if candidate == root or root not in candidate.parents:
        return None
    return candidate


def _validate_plan(
    root: Path,
    plan: dict[str, Any],
    record: dict[str, Any],
) -> list[str]:
    findings: list[str] = []
    cap = record.get("subject_id")
    if plan.get("subject_id") != cap:
        findings.append("subject_id mismatch")
    if plan.get("enabled") is not True:
        findings.append("registered plan must be enabled=true")
    if plan.get("execution_scope") != "CURRENT_HOST":
        findings.append("execution_scope must be CURRENT_HOST")
    if plan.get("shell") not in (None, False):
        findings.append("shell execution is forbidden")
    workdir = plan.get("working_directory", ".")
    path = _repo_path(root, workdir) if workdir != "." else root
    if path is None or not path.is_dir():
        findings.append("working_directory missing/outside repository")
    tests = plan.get("tests")
    if not isinstance(tests, dict):
        return findings + ["tests missing/invalid"]
    expected = {
        "positive": record.get("required_positive_test"),
        "negative": record.get("required_negative_test"),
        "rollback": record.get("rollback_requirement"),
    }
    for phase in PHASES:
        test = tests.get(phase)
        if not isinstance(test, dict):
            findings.append(f"{phase} test missing")
            continue
        if test.get("id") != expected[phase]:
            findings.append(f"{phase} test id mismatch: expected {expected[phase]}")
        argv = test.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            findings.append(f"{phase} argv missing/invalid")
        timeout = test.get("timeout_seconds", 300)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
            findings.append(f"{phase} timeout_seconds outside 1..3600")
    return findings


def _run_test(
    root: Path,
    cap: str,
    phase: str,
    test: dict[str, Any],
    workdir: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    argv = list(test["argv"])
    timeout = int(test.get("timeout_seconds", 300))
    artifact_rel = f".fa3-current-host/test-artifacts/{cap}/{phase}.json"
    artifact = root / artifact_rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            argv,
            cwd=workdir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
            check=False,
        )
        rc = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timed_out = True
    finished = datetime.now(timezone.utc)
    result = {
        "schema": "fa3.current-host-capability-test-result.v1",
        "subject_id": cap,
        "phase": phase,
        "test_id": test["id"],
        "execution_scope": "CURRENT_HOST",
        "argv": argv,
        "shell": False,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "returncode": rc,
        "status": "PASS" if rc == 0 else "FAIL",
        "stdout": stdout,
        "stderr": stderr,
    }
    _write(artifact, result)
    digest = _sha256(artifact)
    test_binding = {
        "id": str(test["id"]),
        "status": result["status"],
        "artifact_path": artifact_rel,
        "artifact_sha256": digest,
    }
    evidence = {"path": artifact_rel, "sha256": digest}
    return test_binding, evidence


def orchestrate(root: Path, *, execute: bool) -> dict[str, Any]:
    root = Path(root).resolve()
    evidence_registry = _load(root / "evidence/evidence-registry.json")
    plan_registry = _load(root / "canonical/current-host-capability-test-registry.json")
    records = evidence_registry.get("records", [])
    expected_ids = [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    actual_ids = [r.get("subject_id") for r in records]
    blocking: list[dict[str, Any]] = []

    if (
        evidence_registry.get("record_count") != CAPABILITY_COUNT
        or len(records) != CAPABILITY_COUNT
        or actual_ids != expected_ids
    ):
        blocking.append({"code": "CHT-001", "message": "Evidence Registry is not exact 143 capability set"})
    if plan_registry.get("schema") != REGISTRY_SCHEMA:
        blocking.append({"code": "CHT-002", "message": "Capability test registry schema mismatch"})
    if plan_registry.get("canonical_capability_count") != CAPABILITY_COUNT:
        blocking.append({"code": "CHT-003", "message": "Capability test registry count drift"})
    if plan_registry.get("execution_scope") != "CURRENT_HOST":
        blocking.append({"code": "CHT-004", "message": "Capability test registry scope drift"})

    by_id = {r.get("subject_id"): r for r in records}
    plans = plan_registry.get("records", [])
    if not isinstance(plans, list):
        plans = []
        blocking.append({"code": "CHT-005", "message": "Capability test registry records invalid"})

    seen: set[str] = set()
    validated: list[tuple[dict[str, Any], dict[str, Any]]] = []
    plan_rows: list[dict[str, Any]] = []
    for plan in plans:
        if not isinstance(plan, dict):
            blocking.append({"code": "CHT-006", "message": "Non-object test plan"})
            continue
        cap = plan.get("subject_id")
        if cap in seen:
            blocking.append({"code": "CHT-007", "message": "Duplicate capability test plan", "subject_id": cap})
            continue
        seen.add(cap)
        record = by_id.get(cap)
        if record is None:
            blocking.append({"code": "CHT-008", "message": "Unknown capability test plan", "subject_id": cap})
            continue
        findings = _validate_plan(root, plan, record)
        plan_rows.append({"subject_id": cap, "valid": not findings, "findings": findings})
        if findings:
            blocking.append({"code": "CHT-009", "message": "Invalid capability test plan", "subject_id": cap, "findings": findings})
        else:
            validated.append((plan, record))

    if execute and validated:
        if platform.system() != "Linux":
            blocking.append({"code": "CHT-010", "message": "Current-host execution requires Linux"})
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            blocking.append({"code": "CHT-011", "message": "Current-host capability tests must not run as root"})
        host_path = root / ".fa3-current-host/global-closure/host/host-fingerprint.json"
        if not host_path.is_file():
            blocking.append({"code": "CHT-012", "message": "Fresh global-closure host fingerprint missing"})
    else:
        host_path = root / ".fa3-current-host/global-closure/host/host-fingerprint.json"

    bundles: list[str] = []
    failed_caps: list[str] = []
    if execute and validated and not blocking:
        host_rel = host_path.relative_to(root).as_posix()
        host_digest = _sha256(host_path)
        for plan, record in validated:
            cap = str(record["subject_id"])
            workdir_rel = plan.get("working_directory", ".")
            workdir = root if workdir_rel == "." else (root / workdir_rel).resolve()
            tests: dict[str, dict[str, str]] = {}
            artifacts: list[dict[str, str]] = []
            for phase in PHASES:
                binding, evidence = _run_test(root, cap, phase, plan["tests"][phase], workdir)
                tests[phase] = binding
                artifacts.append(evidence)
            artifacts.append({"path": host_rel, "sha256": host_digest})
            passed = all(t["status"] == "PASS" for t in tests.values())
            now = datetime.now(timezone.utc)
            ttl = plan.get("ttl_seconds", 86400)
            if not isinstance(ttl, int) or ttl < 60 or ttl > 604800:
                ttl = 86400
            bundle = {
                "schema": BUNDLE_SCHEMA,
                "subject_id": cap,
                "status": "PASS" if passed else "FAIL",
                "execution_scope": "CURRENT_HOST",
                "current_host": True,
                "synthetic": False,
                "ci_reference_only": False,
                "global_promotion_claim": False,
                "collected_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
                "host_fingerprint_path": host_rel,
                "host_fingerprint_sha256": host_digest,
                "tests": tests,
                "evidence_artifacts": artifacts,
                "orchestrator": {
                    "id": ORCHESTRATOR_ID,
                    "shell_execution": False,
                    "automatic_promotion": False,
                },
            }
            out = root / f".fa3-current-host/test-bundles/capabilities/{cap}.json"
            _write(out, bundle)
            bundles.append(cap)
            if not passed:
                failed_caps.append(cap)

    registered_ids = sorted(seen & set(expected_ids))
    unregistered = [cap for cap in expected_ids if cap not in seen]
    if blocking or failed_caps:
        integrity = "FAIL"
        status = "BLOCKED_CURRENT_HOST_TEST_PLAN_OR_EXECUTION_FAILURE"
    elif execute and bundles:
        integrity = "PASS"
        status = "EXECUTED_REGISTERED_CURRENT_HOST_TEST_PLANS"
    elif registered_ids:
        integrity = "PASS"
        status = "REGISTERED_TEST_PLANS_NOT_EXECUTED"
    else:
        integrity = "PASS"
        status = "PENDING_CURRENT_HOST_TEST_PLAN_MATERIALIZATION"

    report = {
        "schema": "fa3.current-host-capability-test-orchestrator-report.v1",
        "id": ORCHESTRATOR_ID,
        "orchestrator_integrity": integrity,
        "status": status,
        "execution_requested": execute,
        "capability_count": CAPABILITY_COUNT,
        "registered_plan_count": len(registered_ids),
        "registered_capability_ids": registered_ids,
        "unregistered_capability_count": len(unregistered),
        "unregistered_capability_ids": unregistered,
        "plan_coverage_complete": len(unregistered) == 0,
        "bundles_materialized": len(bundles),
        "bundle_capability_ids": bundles,
        "failed_capability_ids": failed_caps,
        "plans": plan_rows,
        "blocking_findings": blocking,
        "provider_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "automatic_promotion": False,
        "truth_constraints": {
            "explicit_canonical_plan_required": True,
            "shell_execution_allowed": False,
            "exact_registry_test_ids_required": True,
            "missing_plan_is_pending_not_pass": True,
            "test_failure_is_blocking": True,
            "provider_pass_is_capability_pass": False,
            "reference_ci_pass_is_current_host_pass": False,
        },
    }
    _write(root / "reports/current-host-capability-test-orchestrator.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute explicit FA3 current-host capability test plans")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    report = orchestrate(Path(args.root), execute=args.execute)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["orchestrator_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
