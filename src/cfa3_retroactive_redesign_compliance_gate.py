#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from cfa3_retroactive_redesign_compliance import evaluate_record

GATE_ID = "CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-GATESET-001"
POLICY = "canonical/CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-POLICY-001.json"
DECISION = "canonical/decisions/CFA3-DEC-RETROACTIVE-REDESIGN-COMPLIANCE-2026-10-07.json"
CONTRACT = "canonical/contracts/CFA3-RETROACTIVE-REDESIGN-RECORD-001.schema.json"
GATE_RECORD = "canonical/FA3-GATE-CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-001.json"
DEV_POLICY = "canonical/CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001.json"
APP_LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
GATE_REGISTRY = "canonical/FA3-GATE-REGISTRY-001.json"
ENFORCEMENT = "canonical/enforcement-policy.json"
DONOR_REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
CH_IMPACT = "canonical/current-host-impact/FA3-CH-IMPACT-CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-20261007.json"


def _load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required: " + rel)
    return value


def _fixture(policy: dict[str, Any], root: Path, phase: str) -> dict[str, Any]:
    return {
        "schema": "cfa3.retroactive-redesign-record.v1",
        "component": {
            "id": "fixture.legacy-component",
            "kind": "APPLICATION",
            "designed_before_mandatory_donor_policy": True,
            "trigger_evidence_refs": ["fixture:legacy-design"]
        },
        "phase": phase,
        "legacy_source_discovery_complete": True,
        "legacy_sources": [],
        "current_rule_baseline": {
            "captured_from_canonical_main": True,
            "captured_main_sha": "a" * 40,
            "mandatory_rule_refs": ["canonical:CFA3-current-rule-baseline"]
        },
        "rule_delta": [
            {"category": category, "status": "ALREADY_COMPLIANT", "rationale": "fixture", "evidence_refs": ["fixture:pass"]}
            for category in policy["current_rule_delta_review"]["required_categories"]
        ],
        "finalization_checks": {
            name: "PASS" for name in policy["finalization_gate"]["required_checks"]
        },
        "donor_registry_sha256": hashlib.sha256((root / DONOR_REGISTRY).read_bytes()).hexdigest(),
        "capability_baseline": 175,
        "capability_delta": 0,
        "architectural_authority_delta": 0
    }


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[str] = []
    try:
        policy = _load(root, POLICY)
        decision = _load(root, DECISION)
        contract = _load(root, CONTRACT)
        gate_record = _load(root, GATE_RECORD)
        dev_policy = _load(root, DEV_POLICY)
        app_links = _load(root, APP_LINKS)
        gate_registry = _load(root, GATE_REGISTRY)
        enforcement = _load(root, ENFORCEMENT)
        ch = _load(root, CH_IMPACT)
    except Exception as exc:
        return {
            "schema": "cfa3.retroactive-redesign-compliance-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "findings": ["LOAD_FAILED:" + str(exc)],
            "current_host_runtime_promotion_claim": False,
        }

    if policy.get("id") != "CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-POLICY-001" or policy.get("mandatory") is not True:
        findings.append("POLICY_IDENTITY_OR_MANDATORY_DRIFT")
    if policy.get("capability_baseline") != 175 or policy.get("capability_delta") != 0:
        findings.append("CAPABILITY_BASELINE_DRIFT")
    if policy.get("architectural_authority_delta") != 0:
        findings.append("AUTHORITY_DELTA_DRIFT")
    if decision.get("policy_id") != policy.get("id") or decision.get("status") != "CANONICAL_CLOSED":
        findings.append("DECISION_BINDING_INVALID")
    if contract.get("title") != "CFA3-RETROACTIVE-REDESIGN-RECORD-001":
        findings.append("RECORD_CONTRACT_INVALID")
    if gate_record.get("enforcement_id") != GATE_ID or gate_record.get("fail_closed") is not True:
        findings.append("GATE_RECORD_INVALID")

    composed = dev_policy.get("composed_development_policies", [])
    if policy.get("id") not in composed:
        findings.append("DEVELOPMENT_GOVERNANCE_BINDING_MISSING")
    donor_policy = app_links.get("policy", {})
    for key in (
        "legacy_pre_donor_redesign_source_recovery_required",
        "legacy_source_temporary_planning_use_allowed",
        "legacy_redesign_finalization_requires_canonical_donor_resolution",
        "legacy_redesign_current_rule_delta_required",
    ):
        if donor_policy.get(key) is not True:
            findings.append("APPLICATION_DONOR_POLICY_BINDING_MISSING:" + key)

    ids = gate_registry.get("mandatory_reference_gates", [])
    mirror = enforcement.get("mandatory_reference_gates", [])
    if GATE_ID not in ids or mirror != ids:
        findings.append("GLOBAL_GATE_MEMBERSHIP_INVALID")
    if enforcement.get("retroactive_redesign_compliance_gate_id") != GATE_ID:
        findings.append("ENFORCEMENT_GATE_BINDING_MISSING")

    plan = _fixture(policy, root, "REDESIGN_IN_PROGRESS")
    missing_source = {
        "locator": "https://example.invalid/cfa3-legacy-source",
        "normalized_key": "https://example.invalid/cfa3-legacy-source",
        "origin_refs": ["fixture:historical-plan"],
        "registry_status_at_discovery": "MISSING",
        "temporary_planning_use": True,
        "canonical_donor_id": None,
        "registration_evidence_refs": []
    }
    plan["legacy_sources"] = [missing_source]
    if evaluate_record(root, plan).get("result") != "PASS":
        findings.append("TEMPORARY_PLANNING_USE_REGRESSION")

    final_missing = copy.deepcopy(plan)
    final_missing["phase"] = "REDESIGN_FINAL"
    if evaluate_record(root, final_missing).get("result") != "FAIL":
        findings.append("MISSING_DONOR_FINALIZATION_NOT_BLOCKED")

    final_clean = _fixture(policy, root, "REDESIGN_FINAL")
    if evaluate_record(root, final_clean).get("result") != "PASS":
        findings.append("CLEAN_FINALIZATION_REGRESSION")

    unresolved = copy.deepcopy(final_clean)
    unresolved["rule_delta"][0]["status"] = "REQUIRES_CHANGE"
    if evaluate_record(root, unresolved).get("result") != "FAIL":
        findings.append("UNRESOLVED_RULE_DELTA_NOT_BLOCKED")

    if ch.get("physical_requalification_required") is not False or ch.get("current_host_runtime_promotion_claim") is not False:
        findings.append("CURRENT_HOST_BOUNDARY_INVALID")

    return {
        "schema": "cfa3.retroactive-redesign-compliance-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": 175,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "current_host_runtime_promotion_claim": False,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = gate(root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
