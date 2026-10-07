#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from fa3_os_runtime import default_journal_path, run_reference_conformance
from fa3_os_runtime_gate import gate as reference_gate

CONFORMANCE_ID = "FA3-OS-RUNTIME-CONFORMANCE-001"
EVIDENCE_FILE = Path("evidence/receipts/fa3-os-runtime-current-host.json")
EVIDENCE_SCHEMA = "fa3.os-runtime-current-host-evidence.v1"
REQUIRED_EVIDENCE_FLAGS = (
    "reference_runtime_gate_pass",
    "actual_journal_append_verified",
    "privacy_negative_tests_passed",
    "deterministic_projection_verified",
    "control_center_smoke_passed",
    "selective_erasure_retention_verified",
    "gateway_authorization_verified",
    "retrieval_audit_verified",
)


def _repo_head(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def _fresh_timestamp(value: Any, *, max_age_hours: int = 24) -> bool:
    try:
        captured = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=dt.timezone.utc)
        now = dt.datetime.now(dt.timezone.utc)
        age = now - captured.astimezone(dt.timezone.utc)
        return dt.timedelta(0) <= age <= dt.timedelta(hours=max_age_hours)
    except Exception:
        return False


def _evidence_valid(evidence: Any, *, root: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not isinstance(evidence, dict):
        return False, ["evidence is not an object"]
    if evidence.get("schema") != EVIDENCE_SCHEMA:
        reasons.append("evidence schema mismatch")
    if evidence.get("conformance_id") != CONFORMANCE_ID:
        reasons.append("conformance identity mismatch")
    if evidence.get("result") != "PASS":
        reasons.append("collector result is not PASS")
    if evidence.get("repository_head") != _repo_head(root):
        reasons.append("evidence is not bound to the checked repository HEAD")
    if not _fresh_timestamp(evidence.get("captured_at")):
        reasons.append("evidence is stale or has invalid timestamp")
    if evidence.get("journal_is_actual_default_path") is not True:
        reasons.append("actual default FA3 Journal path was not verified")
    for flag in REQUIRED_EVIDENCE_FLAGS:
        if evidence.get(flag) is not True:
            reasons.append(f"required evidence flag is not true: {flag}")
    if evidence.get("production_admitted") is not True or evidence.get("status") != "CURRENT_HOST_PASS":
        reasons.append("collector did not claim scoped current-host PASS")
    return not reasons, reasons


def gate(root: Path, *, require_evidence: bool = False) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_gate(root)
    findings: list[dict[str, str]] = []
    if reference.get("result") != "PASS":
        findings.append({"code": "FA3-OS-HOST-001", "severity": "P0", "message": "Reference runtime gate is not PASS"})
    runtime = run_reference_conformance()
    if runtime.get("result") != "PASS":
        findings.append({"code": "FA3-OS-HOST-002", "severity": "P0", "message": "Safe host-local reference self-test failed"})

    evidence_path = root / EVIDENCE_FILE
    evidence: Any = None
    if evidence_path.is_file():
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except Exception:
            findings.append({"code": "FA3-OS-HOST-003", "severity": "P0", "message": "Current-host evidence is malformed"})
    evidence_pass, evidence_reasons = _evidence_valid(evidence, root=root)
    if require_evidence and not evidence_pass:
        findings.append({
            "code": "FA3-OS-HOST-004",
            "severity": "P0",
            "message": "Fresh target-host admission evidence is absent or incomplete: " + "; ".join(evidence_reasons),
        })

    journal = default_journal_path()
    admitted = evidence_pass and not findings
    return {
        "gate_id": "FA3-OS-RUNTIME-CURRENT-HOST-GATESET-001",
        "conformance_id": CONFORMANCE_ID,
        "result": "PASS" if not findings else "FAIL",
        "reference_runtime_result": runtime.get("result"),
        "repository_head": _repo_head(root),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "journal_path": str(journal),
            "journal_parent_exists": journal.parent.exists(),
            "journal_parent_writable": os.access(journal.parent, os.W_OK) if journal.parent.exists() else False,
        },
        "required_evidence_flags": list(REQUIRED_EVIDENCE_FLAGS),
        "evidence_present": evidence is not None,
        "evidence_pass": evidence_pass,
        "evidence_reasons": evidence_reasons,
        "production_admitted": admitted,
        "status": "CURRENT_HOST_PASS" if admitted else "PENDING_CURRENT_HOST",
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 OS current-host admission gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--require-evidence", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = gate(Path(args.repo_root), require_evidence=args.require_evidence)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
