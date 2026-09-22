#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_ai_comms import CONTRACT_ID, GATE_ID, PROFILE_ID, reference_cases
from fa3_release_baseline import module_active_capability_count

DECISION_ID = "FA3-DEC-AI-COMMS-2026-09-22"
CAPABILITY_COUNT = module_active_capability_count(__file__)

P0_RULES = [
    "COMM_HUMAN_AUDITABLE_SEMANTICS_REQUIRED",
    "COMM_PRIVATE_MODEL_LANGUAGE_FORBIDDEN",
    "COMM_EMERGENT_CODEBOOK_FORBIDDEN",
    "COMM_MODEL_ONLY_SLANG_FORBIDDEN",
    "COMM_OPAQUE_SEMANTIC_CHANNEL_FORBIDDEN",
    "COMM_HUMAN_READABLE_TEXT_REQUIRED",
    "COMM_DECLARED_HUMAN_LANGUAGE_REQUIRED",
    "COMM_STRUCTURED_SCHEMA_VERSIONED_REQUIRED",
    "COMM_STRUCTURED_PAYLOAD_SUPPLEMENTAL_ONLY",
    "COMM_NEW_SHORTHAND_MUST_BE_DEFINED",
    "COMM_PROVENANCE_REQUIRED",
    "COMM_UNKNOWN_MODE_FAIL_CLOSED",
    "COMM_PROVIDER_CANNOT_CREATE_PROTOCOL_AUTHORITY",
    "COMM_LANGUAGE_BRIDGE_NON_AUTHORITY",
    "COMM_MODEL_ROUTER_REUSED_NO_PARALLEL_ROUTER",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-AI-COMMS-001.json",
        "contracts": root / "canonical/contracts/FA3-AI-COMMS-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-AI-COMMS-2026-09-22.json",
        "enforcement": root / "canonical/ai-comms-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
        "dac_contracts": root / "canonical/contracts/FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001.json",
        "dac_enforcement": root / "canonical/developer-agent-coordination-enforcement.json",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("AI-COMMS-001", f"missing {name} artifact"))
    if findings:
        report = {"schema": "fa3.ai-comms-gate-report.v1", "gate_id": GATE_ID, "result": "FAIL", "findings": findings}
        _write(root / "reports/ai-comms-gate-report.json", report)
        return report

    profile = _load(paths["profile"])
    contracts = _load(paths["contracts"])
    decision = _load(paths["decision"])
    enforcement = _load(paths["enforcement"])
    policy = _load(paths["policy"])
    dac_contracts = _load(paths["dac_contracts"])
    dac_enforcement = _load(paths["dac_enforcement"])

    required_profile_invariants = {
        "HUMAN_AUDITABLE_SEMANTICS_REQUIRED",
        "PRIVATE_MODEL_LANGUAGE_FORBIDDEN",
        "EMERGENT_CODEBOOK_FORBIDDEN",
        "MODEL_ONLY_SLANG_OR_UNDEFINED_SHORTHAND_FORBIDDEN",
        "OPAQUE_ENCODING_AS_SEMANTIC_CHANNEL_FORBIDDEN",
        "HUMAN_READABLE_TEXT_IS_AUTHORITATIVE",
        "UNKNOWN_COMMUNICATION_MODE_FAILS_CLOSED",
        "CENTRAL_MODEL_ROUTER_REUSED_NO_PARALLEL_ROUTER",
    }
    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P0"
        and profile.get("requirement") == "MUST"
        and profile.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and profile.get("provider_neutral") is True
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("contract_family") == CONTRACT_ID
        and required_profile_invariants.issubset(set(profile.get("invariants", [])))
    ):
        findings.append(_finding("AI-COMMS-002", "AI communication profile drift"))

    forbidden = set(contracts.get("forbidden_semantics", []))
    if not (
        contracts.get("id") == CONTRACT_ID
        and contracts.get("parent_profile") == PROFILE_ID
        and contracts.get("provider_neutral") is True
        and contracts.get("new_capability") is False
        and contracts.get("new_architectural_authority") is False
        and contracts.get("capability_count") == CAPABILITY_COUNT
        and {
            "PRIVATE_MODEL_LANGUAGE",
            "EMERGENT_AGENT_CODEBOOK",
            "MODEL_ONLY_SLANG",
            "OPAQUE_ENCODING_AS_PRIMARY_SEMANTIC_CHANNEL",
            "UNVERSIONED_STRUCTURED_PROTOCOL",
            "PARALLEL_COMPONENT_OWNED_MODEL_ROUTER",
        }.issubset(forbidden)
    ):
        findings.append(_finding("AI-COMMS-003", "AI communication contract drift"))

    router = decision.get("model_router_reconciliation", {})
    language = decision.get("language_fabric_reconciliation", {})
    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("profile_id") == PROFILE_ID
        and decision.get("contract_family") == CONTRACT_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and router.get("authority_reused") is True
        and router.get("parallel_router_created") is False
        and router.get("semantic_policy_authority_granted_to_router") is False
        and language.get("language_bridge_may_create_private_model_language") is False
        and language.get("language_bridge_may_expand_authority") is False
    ):
        findings.append(_finding("AI-COMMS-004", "Canonical AI communication decision drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("profile_id") == PROFILE_ID
        and enforcement.get("contract_family") == CONTRACT_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("p0_invariants") == P0_RULES
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and enforcement.get("current_host_production_promotion_claim") is False
    ):
        findings.append(_finding("AI-COMMS-005", "AI communication enforcement drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("AI-COMMS-006", "AI communication gate missing from global enforcement policy"))
    if policy.get("ai_comms_profile_id") != PROFILE_ID or policy.get("ai_comms_contract_id") != CONTRACT_ID:
        findings.append(_finding("AI-COMMS-007", "Global AI communication binding drift"))
    if policy.get("ai_comms_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("AI-COMMS-008", "Global AI communication P0 rule binding drift"))

    if dac_contracts.get("communication_policy") != PROFILE_ID:
        findings.append(_finding("AI-COMMS-009", "Developer-agent coordination is not bound to AI communication policy"))
    dac_forbidden = set(dac_contracts.get("forbidden_semantics", []))
    if not {"PRIVATE_MODEL_LANGUAGE", "EMERGENT_AGENT_CODEBOOK", "MODEL_ONLY_SLANG"}.issubset(dac_forbidden):
        findings.append(_finding("AI-COMMS-010", "Developer-agent coordination forbidden communication semantics drift"))
    dac_rules = set(dac_enforcement.get("p0_invariants", []))
    if not {"DAC_HUMAN_AUDITABLE_MODEL_COMMUNICATION", "DAC_PRIVATE_MODEL_LANGUAGE_FORBIDDEN"}.issubset(dac_rules):
        findings.append(_finding("AI-COMMS-011", "Developer-agent coordination runtime enforcement is not bound"))

    cases = reference_cases()
    if not all(cases.values()):
        findings.append(_finding("AI-COMMS-012", "AI communication positive/negative regressions failed"))

    report = {
        "schema": "fa3.ai-comms-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "capability_count": CAPABILITY_COUNT,
        "capability_delta": 0,
        "authority_delta": 0,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "regressions": cases,
        "current_host_production_claim": False,
        "model_router_reused": True,
        "parallel_model_router_created": False,
    }
    _write(root / "reports/ai-comms-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
