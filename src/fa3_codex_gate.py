#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-CODEX-GATESET-001"
PROVIDER_ID = "FA3-PROVIDER-CODEX-001"
REMOVED_SURFACES = [
    ".github/workflows/fa3-codex-current-host.yml",
    "bin/fa3-codex-bootstrap.sh",
    "bin/fa3-codex-current-host.sh",
    "canonical/codex-runtime-admission.json",
    "canonical/contracts/FA3-CODEX-ADAPTER-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-CODEX-ADAPTER-2026-08-31.json",
    "canonical/references/FA3-CODEX-UPSTREAM-REFERENCE-2026-08-31.json",
    "docs/codex-current-host.md",
    "evidence/collect-codex-current-host.py",
    "evidence/reference/codex-adapter-ci-2026-08-31.json",
    "examples/codex-delegated-agent-request.json",
    "src/fa3_codex_adapter.py",
    "tests/test_codex_adapter.py",
]


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    provider_path = root / "canonical/providers/FA3-PROVIDER-CODEX-001.json"
    enforcement_path = root / "canonical/codex-enforcement.json"
    if not provider_path.is_file() or not enforcement_path.is_file():
        return {"gate_id": GATE_ID, "result": "FAIL", "findings": [finding("CODEX-DECOM-001", "Codex tombstone/decommission enforcement record missing")]}
    provider = loadj(provider_path)
    enforcement = loadj(enforcement_path)
    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("status") == "REMOVED_PAID_PROVIDER_TOMBSTONE"
        and provider.get("active") is False
        and provider.get("routing_eligible") is False
        and provider.get("production_admission") == "DENY"
        and provider.get("runtime_surface") == "ABSENT"
        and provider.get("capability_count") == 143
    ):
        findings.append(finding("CODEX-DECOM-002", "Codex provider is not a fail-closed paid-provider tombstone"))
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("status") == "DECOMMISSION_GUARD"
        and enforcement.get("fail_closed") is True
        and enforcement.get("provider_active") is False
        and enforcement.get("routing_eligible") is False
        and enforcement.get("production_admission") == "DENY"
    ):
        findings.append(finding("CODEX-DECOM-003", "Codex decommission guard weakened"))
    present = [rel for rel in REMOVED_SURFACES if (root / rel).exists()]
    if present:
        findings.append(finding("CODEX-DECOM-004", "removed Codex executable/runtime surface returned", paths=present))
    manifest_path = root / "fa3-current-host/manifest.json"
    if manifest_path.is_file():
        manifest = loadj(manifest_path)
        names = {x.get("name") for x in manifest.get("registered_current_host_surfaces", [])}
        if "codex" in names:
            findings.append(finding("CODEX-DECOM-005", "Codex current-host runtime surface returned"))
    report = {
        "schema": "fa3.codex-decommission-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "status": "REMOVED_NOT_APPLICABLE" if not findings else "DECOMMISSION_DRIFT",
        "current_host_production_claim": False,
        "capability_count": 143,
    }
    out = root / "reports/codex-decommission-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def current_host_gate(root: Path) -> dict[str, Any]:
    report = gate(root)
    return {
        "schema": "fa3.codex-current-host-decommission-report.v1",
        "gate_id": GATE_ID,
        "result": report["result"],
        "status": "REMOVED_NOT_APPLICABLE" if report["result"] == "PASS" else "FAIL",
        "current_host_production_claim": False,
        "production_promotion_claim": False,
        "findings": report["findings"],
    }
