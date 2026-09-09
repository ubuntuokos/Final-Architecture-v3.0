#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from fa3_mmg_context_ir import run_reference_conformance

REFERENCE_ID = "FA3-MMG-CONTEXT-IR-REFERENCE-001"
CONTEXT_ID = "FA3-MMG-CONTEXT-IR-001"
CONTRACT_ID = "FA3-MMG-CONTEXT-IR-CONTRACTS-001"
DECISION_ID = "FA3-DEC-MMG-CONTEXT-IR-REFERENCE-2026-09-09"
GATE_SET_ID = "FA3-MMG-CONTEXT-IR-GATESET-001"
GATE_ID = "FA3-GATE-MMG-CONTEXT-IR-001"
EVIDENCE_ID = "FA3-EVIDENCE-MMG-CONTEXT-IR-CI-2026-09-09"
RECON_EVIDENCE_ID = "FA3-EVIDENCE-MMG-CONTEXT-IR-GLOBAL-RECONCILIATION-2026-09-09"
RELEASE_PROJECTION_ID = "FA3-RELEASE-PROJECTION-MMG-CONTEXT-IR-REFERENCE-2026-09-09"
CAPABILITY_BINDINGS = ["CAP-016", "CAP-123", "CAP-126"]
CAPABILITY_COUNT = 143
EXPECTED_CASES = 18


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def reference_check(root: Path) -> dict[str, Any]:
    paths = {
        "profile": root / "canonical/profiles/FA3-VIDEO-001.json",
        "contract": root / "canonical/contracts/FA3-MMG-CONTEXT-IR-CONTRACTS-001.json",
        "enforcement": root / "canonical/mmg-context-ir-enforcement.json",
        "reference": root / "canonical/references/FA3-MMG-CONTEXT-IR-REFERENCE-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-MMG-CONTEXT-IR-REFERENCE-2026-09-09.json",
        "evidence": root / "evidence/reference/mmg-context-ir-ci-2026-09-09.json",
        "reconciliation": root / "evidence/reference/mmg-context-ir-global-reconciliation-ci-2026-09-09.json",
        "release_projection": root / "canonical/releases/FA3-RELEASE-PROJECTION-MMG-CONTEXT-IR-REFERENCE-2026-09-09.json",
        "implementation": root / "src/fa3_mmg_context_ir.py",
        "tests": root / "tests/test_mmg_context_ir_reference.py",
        "cli": root / "bin/fa3-enforce",
    }
    findings: list[dict[str, Any]] = []
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("MMG-GATE-001", f"missing mandatory MMG reference artifact: {name}", path=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings, "blocking_findings": len(findings)}

    profile = _load(paths["profile"])
    contract = _load(paths["contract"])
    enforcement = _load(paths["enforcement"])
    reference = _load(paths["reference"])
    decision = _load(paths["decision"])
    evidence = _load(paths["evidence"])
    reconciliation = _load(paths["reconciliation"])
    release_projection = _load(paths["release_projection"])

    if not (reference.get("id") == REFERENCE_ID and reference.get("context_ir_id") == CONTEXT_ID and reference.get("contract_id") == CONTRACT_ID and reference.get("gate_set_id") == GATE_SET_ID and reference.get("gate_id") == GATE_ID):
        findings.append(_finding("MMG-GATE-002", "reference implementation identity drift"))
    if not (reference.get("provider_neutral") is True and reference.get("canonical_root") is False and reference.get("architectural_authority") is False and reference.get("provider_selection_authority") is False and reference.get("execution_authority") is False and reference.get("evidence_authority") is False):
        findings.append(_finding("MMG-GATE-003", "reference implementation authority boundary drift"))
    if not (reference.get("new_capability") is False and reference.get("new_architectural_authority") is False and reference.get("capability_count") == CAPABILITY_COUNT and reference.get("capability_bindings") == CAPABILITY_BINDINGS):
        findings.append(_finding("MMG-GATE-004", "reference implementation baseline geometry drift"))

    src = reference.get("source", {})
    if _sha256(paths["implementation"]) != src.get("implementation_sha256"):
        findings.append(_finding("MMG-GATE-005", "reference implementation digest mismatch"))
    if _sha256(paths["tests"]) != src.get("test_sha256"):
        findings.append(_finding("MMG-GATE-006", "reference test digest mismatch"))
    if src.get("stdlib_only") is not True:
        findings.append(_finding("MMG-GATE-007", "reference implementation must remain stdlib-only"))

    mmg = profile.get("multimodal_generation_context_ir", {})
    ref_binding = mmg.get("reference_implementation", {})
    if not (profile.get("capability_count") == CAPABILITY_COUNT and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and ref_binding.get("id") == REFERENCE_ID and ref_binding.get("gate_id") == GATE_ID and ref_binding.get("architectural_authority") is False and ref_binding.get("provider_runtime_promotion_claim") is False):
        findings.append(_finding("MMG-GATE-008", "FA3-VIDEO-001 reference implementation binding drift"))
    if not (contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("canonical_root") is False and contract.get("capability_count") == CAPABILITY_COUNT):
        findings.append(_finding("MMG-GATE-009", "MMG canonical contract drift"))

    executable = enforcement.get("executable_reference", {})
    if not (enforcement.get("gate_id") == GATE_SET_ID and enforcement.get("fail_closed") is True and executable.get("reference_id") == REFERENCE_ID and executable.get("gate_id") == GATE_ID and executable.get("mandatory_case_count") == EXPECTED_CASES and executable.get("fail_closed") is True and executable.get("provider_runtime_claim") is False and executable.get("current_host_runtime_claim") is False):
        findings.append(_finding("MMG-GATE-010", "MMG executable enforcement binding drift"))

    if not (decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED" and decision.get("decision") == "NO_BASELINE_SEMANTIC_CHANGE_IMPLEMENTATION_PROJECTION_UPDATE" and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0 and decision.get("capability_count_after") == CAPABILITY_COUNT and decision.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("MMG-GATE-011", "MMG executable reference decision drift"))

    cases = evidence.get("regression_cases", {})
    expected_ids = [f"MMG-REF-{i:03d}" for i in range(1, EXPECTED_CASES + 1)]
    if not (evidence.get("id") == EVIDENCE_ID and evidence.get("status") == "PASS" and cases.get("passed") == EXPECTED_CASES and cases.get("total") == EXPECTED_CASES and cases.get("case_ids") == expected_ids and evidence.get("implementation_sha256") == src.get("implementation_sha256") and evidence.get("test_sha256") == src.get("test_sha256") and evidence.get("current_host_runtime_claim") is False and evidence.get("provider_runtime_execution_claim") is False):
        findings.append(_finding("MMG-GATE-012", "MMG executable PASS evidence drift"))

    if not (reconciliation.get("id") == RECON_EVIDENCE_ID and reconciliation.get("status") == "PASS" and reconciliation.get("reference_id") == REFERENCE_ID and reconciliation.get("gate_id") == GATE_ID and reconciliation.get("capability_bindings") == CAPABILITY_BINDINGS and reconciliation.get("conclusion") == "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILIATION_PASS" and reconciliation.get("capability_count_after") == CAPABILITY_COUNT):
        findings.append(_finding("MMG-GATE-013", "MMG global reconciliation evidence drift"))

    if not (release_projection.get("id") == RELEASE_PROJECTION_ID and release_projection.get("status") == "CANONICAL_RECONCILED" and release_projection.get("reference_id") == REFERENCE_ID and release_projection.get("gate_id") == GATE_ID and release_projection.get("capability_bindings") == CAPABILITY_BINDINGS and release_projection.get("baseline", {}).get("capability_count_after") == CAPABILITY_COUNT):
        findings.append(_finding("MMG-GATE-014", "MMG dedicated release projection drift"))

    cli_text = paths["cli"].read_text(encoding="utf-8")
    if "mmg-context-ir" not in cli_text or "fa3_mmg_context_ir_gate.py" not in cli_text:
        findings.append(_finding("MMG-GATE-015", "./bin/fa3-enforce mmg-context-ir dispatch missing"))

    executable_result = run_reference_conformance()
    if not (executable_result.get("result") == "PASS" and executable_result.get("passed") == EXPECTED_CASES and executable_result.get("total") == EXPECTED_CASES and executable_result.get("current_host_runtime_claim") is False and executable_result.get("provider_runtime_execution_claim") is False):
        findings.append(_finding("MMG-GATE-016", "executable 18-case reference conformance failed", executable_result=executable_result))

    return {
        "schema": "fa3.mmg-context-ir-gate-report.v1",
        "gate_id": GATE_ID,
        "gate_set_id": GATE_SET_ID,
        "reference_id": REFERENCE_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "executable_conformance": executable_result,
        "capability_bindings": CAPABILITY_BINDINGS,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "current_host_runtime_claim": False,
        "provider_runtime_execution_claim": False,
    }


def gate(root: Path) -> dict[str, Any]:
    report = reference_check(root)
    _write(root / "reports/mmg-context-ir-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 MMG Context IR executable reference gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
