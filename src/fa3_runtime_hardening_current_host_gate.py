#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_runtime_hardening_current_host import (
    CAPABILITY_COUNT,
    CONFORMANCE_ID,
    GATE_ID,
    RECEIPT_PATHS,
    VALIDATORS,
    load_json,
)

MATERIALIZATION_PATHS = {
    "conformance": "canonical/FA3-RUNTIME-HARDENING-CURRENT-HOST-CONFORMANCE-001.json",
    "gate_record": "canonical/FA3-GATE-RUNTIME-HARDENING-CURRENT-HOST-001.json",
    "enforcement": "canonical/runtime-hardening-current-host-enforcement.json",
    "decision": "canonical/decisions/FA3-DEC-RUNTIME-HARDENING-CURRENT-HOST-2026-09-19.json",
    "reference": "canonical/references/FA3-RUNTIME-HARDENING-CURRENT-HOST-UPSTREAM-REFERENCE-2026-09-19.json",
    "policy": "canonical/enforcement-policy.json",
    "manifest": "fa3-current-host/manifest.json",
    "workflow": ".github/workflows/fa3-runtime-hardening-current-host.yml",
    "shared": "src/fa3_runtime_hardening_current_host.py",
    "sandbox_collector": "evidence/collect-runtime-isolation-sandbox-current-host.py",
    "media_collector": "evidence/collect-media-gpu-zerocopy-current-host.py",
    "hu_aqc_collector": "evidence/collect-hu-aqc-current-host.py",
    "shadow_collector": "evidence/collect-promotion-shadow-current-host.py",
}


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def _materialization_check(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    data: dict[str, Any] = {}
    for key, rel in MATERIALIZATION_PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(finding("HARDEN-HOST-001", "required current-host materialization missing", path=rel))
            continue
        if path.suffix == ".json":
            try:
                data[key] = load_json(path)
            except Exception as exc:
                findings.append(finding("HARDEN-HOST-002", "current-host JSON unreadable", path=rel, error=repr(exc)))
        else:
            data[key] = path.read_text(encoding="utf-8")

    if findings:
        return findings, data

    conformance = data["conformance"]
    if not (
        conformance.get("id") == CONFORMANCE_ID
        and conformance.get("status") == "EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING"
        and conformance.get("capability_count") == CAPABILITY_COUNT
        and conformance.get("new_capabilities") == 0
        and conformance.get("new_architectural_authorities") == 0
        and conformance.get("architectural_authority") is False
        and conformance.get("global_promotion_claim") is False
        and len(conformance.get("surfaces", [])) == 4
    ):
        findings.append(finding("HARDEN-HOST-003", "current-host conformance invariant drift"))

    gate_record = data["gate_record"]
    if not (
        gate_record.get("gateset_id") == GATE_ID
        and gate_record.get("conformance_id") == CONFORMANCE_ID
        and gate_record.get("fail_closed") is True
        and gate_record.get("current_host_runner_required") is True
        and gate_record.get("global_promotion_claim") is False
        and gate_record.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(finding("HARDEN-HOST-004", "current-host gate-record invariant drift"))

    enforcement = data["enforcement"]
    rules = enforcement.get("rules", {})
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("capability_count") == CAPABILITY_COUNT
        and rules.get("github_hosted_substitution") == "DENY"
        and rules.get("sandbox_compatibility_smoke_as_production_isolation") == "DENY"
        and rules.get("media_full_pipeline_zero_copy_overclaim") == "DENY"
        and rules.get("shadow_promotion_authority") == "DENY"
        and rules.get("global_promotion_effect") == "NONE"
    ):
        findings.append(finding("HARDEN-HOST-005", "current-host enforcement invariant drift"))

    decision = data["decision"]
    if not (
        decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("conformance_id") == CONFORMANCE_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("current_host_runtime_promotion_claim") is False
        and decision.get("global_promotion_claim") is False
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("HARDEN-HOST-006", "current-host decision invariant drift"))

    reference = data["reference"]
    if not (
        reference.get("status") == "REFERENCE_VERIFIED"
        and reference.get("production_admission_effect") == "REFERENCE_ONLY_NOT_CURRENT_HOST_PASS"
        and reference.get("global_promotion_claim") is False
    ):
        findings.append(finding("HARDEN-HOST-007", "upstream reference overclaims runtime admission"))

    policy = data["policy"]
    if (
        policy.get("runtime_hardening_current_host_conformance_id") != CONFORMANCE_ID
        or policy.get("runtime_hardening_current_host_gate_id") != GATE_ID
        or policy.get("runtime_hardening_current_host_status") != "PENDING_REAL_SELF_HOSTED_EXECUTION"
    ):
        findings.append(finding("HARDEN-HOST-008", "global enforcement policy current-host binding missing/drifted"))

    manifest = data["manifest"]
    surfaces = {x.get("name"): x for x in manifest.get("registered_current_host_surfaces", [])}
    expected_surfaces = {
        "runtime-isolation-agent-sandbox",
        "media-gpu-zero-host-round-trip",
        "hu-aqc",
        "promotion-shadow",
    }
    if not expected_surfaces.issubset(set(surfaces)):
        findings.append(finding("HARDEN-HOST-009", "current-host manifest missing hardening surfaces"))
    else:
        for name in expected_surfaces:
            row = surfaces[name]
            if (
                row.get("collection_status") != "EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING"
                or row.get("global_promotion_claim") is not False
            ):
                findings.append(finding("HARDEN-HOST-010", "current-host surface status/promotion drift", surface=name))

    workflow = data["workflow"]
    required_workflow_tokens = [
        "workflow_dispatch:",
        "execute_current_host:",
        "runs-on: [self-hosted, linux, x64, fa3-current-host]",
        "runtime-hardening-current-host",
        "--require-evidence",
    ]
    for token in required_workflow_tokens:
        if token not in workflow:
            findings.append(finding("HARDEN-HOST-011", "current-host workflow contract drift", token=token))
    return findings, data


def gate(
    root: Path,
    *,
    require_evidence: bool = False,
    require_media_claim: bool = False,
    receipt_dir: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    findings, _ = _materialization_check(root)
    surface_reports: dict[str, Any] = {}
    all_evidence_pass = True

    for key, rel in RECEIPT_PATHS.items():
        if key == "media_accelerator_memory_residency" and not require_media_claim:
            surface_reports[key] = {
                "path": str((receipt_dir / Path(rel).name) if receipt_dir else (root / rel)),
                "present": False,
                "pass": False,
                "satisfied": True,
                "status": "NOT_APPLICABLE",
                "reasons": ["no zero-host-round-trip claim requested for this run"],
            }
            continue
        path = (receipt_dir / Path(rel).name) if receipt_dir else (root / rel)
        if not path.is_file():
            ok = False
            reasons = ["receipt missing"]
        else:
            try:
                receipt = load_json(path)
                ok, reasons = VALIDATORS[key](receipt, root=root)
            except Exception as exc:
                ok = False
                reasons = [f"receipt unreadable: {exc!r}"]
        all_evidence_pass = all_evidence_pass and ok
        surface_reports[key] = {
            "path": str(path),
            "present": path.is_file(),
            "pass": ok,
            "satisfied": ok,
            "status": "PASS" if ok else "PENDING_OR_FAIL",
            "reasons": reasons,
        }
        if require_evidence and not ok:
            findings.append(
                finding(
                    "HARDEN-HOST-020",
                    "required current-host hardening surface is not PASS",
                    surface=key,
                    reasons=reasons,
                )
            )

    scoped_status = "CURRENT_HOST_PASS" if all_evidence_pass else "PENDING_CURRENT_HOST"
    report = {
        "schema": "fa3.runtime-hardening-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "conformance_id": CONFORMANCE_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if not findings else "FAIL",
        "status": scoped_status,
        "require_evidence": require_evidence,
        "require_media_claim": require_media_claim,
        "blocking_findings": len(findings),
        "findings": findings,
        "surfaces": surface_reports,
        "surface_pass_count": sum(1 for row in surface_reports.values() if row["pass"]),
        "surface_total": len(surface_reports),
        "current_host_runtime_promotion_claim": False,
        "global_promotion_claim": False,
        "production_promotion_gate_bypassed": False,
    }
    out = root / "reports/runtime-hardening-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="FA3 runtime-hardening current-host gate")
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--require-evidence", action="store_true")
    p.add_argument("--require-media-claim", action="store_true")
    p.add_argument("--receipt-dir")
    a = p.parse_args()
    report = gate(
        Path(a.root),
        require_evidence=a.require_evidence,
        require_media_claim=a.require_media_claim,
        receipt_dir=Path(a.receipt_dir).resolve() if a.receipt_dir else None,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
