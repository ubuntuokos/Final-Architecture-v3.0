#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline
from fa3_uaf import ActionRegistry

GATE_ID = "FA3-MARKETING-AGENT-NATIVE-GATESET-001"
DECISION_ID = "FA3-DEC-MARKETING-AGENT-NATIVE-JEV-2026-09-23"
CONTRACT_ID = "FA3-MARKETING-DECISION-FABRIC-CONTRACTS-001"
ACTION_IDS = {
    "marketing.contact.project", "marketing.contact.reconcile",
    "marketing.consent.record", "marketing.suppression.apply",
    "marketing.segment.preview", "marketing.campaign.draft",
    "marketing.campaign.validate", "marketing.campaign.approve",
    "marketing.campaign.schedule", "marketing.campaign.pause",
    "marketing.newsletter.prepare", "marketing.newsletter.dispatch",
    "marketing.delivery.reconcile", "marketing.experiment.record",
    "marketing.analytics.project",
}
EXPLICIT_APPROVAL = {
    "marketing.consent.record", "marketing.suppression.apply",
    "marketing.campaign.approve", "marketing.campaign.schedule",
    "marketing.campaign.pause", "marketing.newsletter.dispatch",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def validate(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-MARKETING-001.json",
        "marketing_contract": root / "canonical/contracts/FA3-MARKETING-CONTRACTS-001.json",
        "decision_contract": root / f"canonical/contracts/{CONTRACT_ID}.json",
        "decision": root / f"canonical/decisions/{DECISION_ID}.json",
        "gate": root / "canonical/FA3-GATE-MARKETING-AGENT-NATIVE-001.json",
        "runtime": root / "canonical/FA3-MARKETING-RUNTIME-CONFORMANCE-001.json",
        "reference": root / "evidence/reference/marketing-agent-native-ci-2026-09-23.json",
        "implementation": root / "src/fa3_marketing_decision_fabric.py",
        "adapter": root / "src/fa3_marketing_uaf.py",
    }
    for name, path in paths.items():
        if not path.is_file():
            findings.append(_finding("MKT-AN-001", "required file missing", name=name, path=path.as_posix()))
    if findings:
        return findings
    count = load_active_release_baseline(root).capability_count
    profile = _load(paths["profile"])
    marketing_contract = _load(paths["marketing_contract"])
    contract = _load(paths["decision_contract"])
    decision = _load(paths["decision"])
    gate_record = _load(paths["gate"])
    runtime = _load(paths["runtime"])
    reference = _load(paths["reference"])

    checks = [
        (CONTRACT_ID in profile.get("contracts", []), "MKT-AN-002", "decision contract is not bound to marketing profile"),
        (profile.get("agent_native", {}).get("fabric") == "FA3-UNIFIED-ACTION-FABRIC-001", "MKT-AN-003", "UAF binding missing"),
        (profile.get("agent_native", {}).get("direct_surface_or_agent_provider_bypass") is False, "MKT-AN-004", "direct provider bypass is not forbidden"),
        (contract.get("id") == CONTRACT_ID and contract.get("upstream_runtime_dependency") is False, "MKT-AN-005", "decision fabric identity/runtime boundary invalid"),
        (contract.get("jev_role") == "OPTIONAL_ADVISORY_PROVIDER_NOT_AUTHORITY", "MKT-AN-006", "Jev role is not advisory-only"),
        (contract.get("new_capability") is False and contract.get("new_architectural_authority") is False, "MKT-AN-007", "decision fabric changes baseline"),
        (contract.get("capability_count") == count, "MKT-AN-008", "capability count drift"),
        (decision.get("id") == DECISION_ID and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0, "MKT-AN-009", "decision changes baseline"),
        (gate_record.get("gateset_id") == GATE_ID and gate_record.get("fail_closed") is True, "MKT-AN-010", "gate record invalid"),
        (runtime.get("required_evidence_level") == "CURRENT_HOST_PRODUCTION_E2E_PASS", "MKT-AN-011", "current-host boundary weakened"),
        (runtime.get("status") == "PENDING_CURRENT_HOST_PRODUCTION_E2E" and runtime.get("promotion_claim") is False, "MKT-AN-012", "provider runtime incorrectly promoted"),
        (reference.get("status") == "PASS" and reference.get("evidence_level") == "STATIC_AND_REFERENCE_PASS_NOT_RUNTIME", "MKT-AN-013", "reference evidence semantics invalid"),
        (reference.get("current_host_production_e2e_claim") is False, "MKT-AN-014", "reference evidence impersonates current host"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append(_finding(code, message))

    declared = set(marketing_contract.get("agent_native_action_fabric", {}).get("actions", []))
    if declared != ACTION_IDS:
        findings.append(_finding("MKT-AN-015", "marketing contract action inventory drift", missing=sorted(ACTION_IDS - declared), extra=sorted(declared - ACTION_IDS)))
    registry = ActionRegistry.from_directory(root / "canonical/actions")
    actions = {item.action_id: item for item in registry.list() if item.action_id.startswith("marketing.")}
    if set(actions) != ACTION_IDS:
        findings.append(_finding("MKT-AN-016", "canonical marketing action inventory drift", missing=sorted(ACTION_IDS - set(actions)), extra=sorted(set(actions) - ACTION_IDS)))
    for action_id, action in actions.items():
        if action.security.get("authentication") != "required" or action.security.get("authorization") != "required" or action.evidence.get("required") is not True or action.evidence.get("decision_receipt_required") is not True:
            findings.append(_finding("MKT-AN-017", "action security/evidence requirement invalid", action=action_id))
        if action.provider.get("selection") != "policy-bounded-capability-match":
            findings.append(_finding("MKT-AN-018", "action provider selection is not policy bounded", action=action_id))
        if action_id in EXPLICIT_APPROVAL and action.security.get("approval") != "explicit":
            findings.append(_finding("MKT-AN-019", "high-impact action lacks explicit approval", action=action_id))
        accelerator = action.resources.get("accelerator", {})
        if accelerator.get("cardinality") != "0..N":
            findings.append(_finding("MKT-AN-020", "hardware cardinality is not portable", action=action_id))
    required_invariants = {
        "APPLICATION_OR_POLICY_SUPPLIES_A_NON_EMPTY_BOUNDED_CANDIDATE_SET",
        "ADVISORY_PROVIDER_CANNOT_ADD_OR_AUTHORIZE_CANDIDATES",
        "DETERMINISTIC_POLICY_FILTERS_RUN_BEFORE_OPTIONAL_ADVISORY_RANKING",
        "NO_DIRECT_PROVIDER_MUTATION_OUTSIDE_UAF",
    }
    if not required_invariants.issubset(set(contract.get("mandatory_invariants", []))):
        findings.append(_finding("MKT-AN-021", "mandatory decision invariants missing"))
    return findings


def gate(root: Path) -> dict[str, Any]:
    findings = validate(root)
    report = {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "schema_version": "1.0.0",
        "gate": {"id": GATE_ID, "mode": "STATIC_CANONICAL_AND_REFERENCE"},
        "result": "PASS" if not findings else "BLOCKED",
        "decision": {
            "reason_code": "MARKETING_AGENT_NATIVE_STATIC_PASS" if not findings else "MARKETING_AGENT_NATIVE_BLOCKED",
            "promotion_effect": "STATIC_REFERENCE_ONLY_CURRENT_HOST_PROVIDER_ADMISSION_UNCHANGED",
            "exit_code": 0 if not findings else 2,
        },
        "findings": findings,
        "action_count": len(ACTION_IDS),
        "capability_delta": 0,
        "authority_delta": 0,
        "current_host_production_e2e_claim": False,
        "global_promotion_claim": False,
    }
    out = root.resolve() / "reports/marketing-agent-native-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
