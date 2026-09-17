#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
from typing import Any

from fa3_os_runtime import default_journal_path, run_reference_conformance
from fa3_os_runtime_gate import gate as reference_gate

CONFORMANCE_ID = "FA3-OS-RUNTIME-CONFORMANCE-001"
EVIDENCE_FILE = Path("evidence/receipts/fa3-os-runtime-current-host.json")


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
    evidence = None
    if evidence_path.is_file():
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except Exception:
            findings.append({"code": "FA3-OS-HOST-003", "severity": "P0", "message": "Current-host evidence is malformed"})
    evidence_pass = bool(
        isinstance(evidence, dict)
        and evidence.get("schema") == "fa3.os-runtime-current-host-evidence.v1"
        and evidence.get("conformance_id") == CONFORMANCE_ID
        and evidence.get("result") == "PASS"
        and evidence.get("actual_journal_append_verified") is True
        and evidence.get("privacy_negative_tests_passed") is True
        and evidence.get("control_center_smoke_passed") is True
        and evidence.get("gateway_authorization_verified") is True
    )
    if require_evidence and not evidence_pass:
        findings.append({"code": "FA3-OS-HOST-004", "severity": "P0", "message": "Fresh target-host admission evidence is absent or incomplete"})
    journal = default_journal_path()
    return {
        "gate_id": "FA3-OS-RUNTIME-CURRENT-HOST-GATESET-001",
        "conformance_id": CONFORMANCE_ID,
        "result": "PASS" if not findings else "FAIL",
        "reference_runtime_result": runtime.get("result"),
        "host": {
            "system": platform.system(), "release": platform.release(), "machine": platform.machine(),
            "journal_path": str(journal), "journal_parent_exists": journal.parent.exists(),
            "journal_parent_writable": os.access(journal.parent, os.W_OK) if journal.parent.exists() else False,
        },
        "evidence_present": evidence is not None,
        "evidence_pass": evidence_pass,
        "production_admitted": evidence_pass and not findings,
        "status": "CURRENT_HOST_PASS" if evidence_pass and not findings else "PENDING_CURRENT_HOST",
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
