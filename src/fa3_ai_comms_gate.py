#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_ai_comms import CONTRACT_ID, GATE_ID, PROFILE_ID, reference_cases
from fa3_ai_comms_topology import reference_cases as topology_reference_cases
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
    "COMM_APP_PARTICIPANT_SET_CLOSED",
    "COMM_APP_PRIMARY_MODEL_REQUIRED",
    "COMM_UNAUTHORIZED_AI_PARTICIPANT_ADDITION_DENIED",
    "COMM_UNFIT_PARTNER_REPLACEMENT_REQUIRED",
    "COMM_REPLACEMENT_PRESERVES_PARTICIPANT_SET",
    "COMM_REPLACEMENT_USES_CENTRAL_MODEL_ROUTER",
    "COMM_CROSS_APP_DEFAULT_DENY",
    "COMM_CROSS_APP_PROTECTED_GATEWAY_REQUIRED",
    "COMM_GATEWAY_BYPASS_DENIED",
    "COMM_ROUTER_DOES_NOT_GRANT_COMMUNICATION_AUTHORITY",
    "COMM_SLEEPING_APP_WAKE_REQUIRES_USER_DIRECTIVE",
    "COMM_SECURITY_EMERGENCY_WAKE_NARROW_EXCEPTION",
    "COMM_SECURITY_EMERGENCY_WAKE_PREAUTHORIZED_SECURITY_TARGET_ONLY",
    "COMM_SECURITY_EMERGENCY_WAKE_LEAST_PRIVILEGE",
    "COMM_SECURITY_EMERGENCY_WAKE_IMMEDIATE_USER_NOTIFICATION",
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
        "topology_schema": root / "canonical/schemas/ai-comms-topology-policy.v1.json",
        "app_lifecycle": root / "canonical/FA3-APP-LIFECYCLE-001.json",
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
    topology_schema = _load(paths["topology_schema"])
    app_lifecycle = _load(paths["app_lifecycle"])
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
        "APPLICATION_MODEL_PARTICIPANT_SET_CLOSED",
        "APPLICATION_PRIMARY_MODEL_REQUIRED",
        "UNAUTHORIZED_AI_PARTICIPANT_ADDITION_FORBIDDEN",
        "UNFIT_PARTNER_REPLACEMENT_REQUIRED",
        "PARTNER_REPLACEMENT_PRESERVES_PARTICIPANT_CARDINALITY",
        "PARTNER_REPLACEMENT_USES_CENTRAL_MODEL_ROUTER",
        "CROSS_APPLICATION_COMMUNICATION_DEFAULT_DENY",
        "CROSS_APPLICATION_PROTECTED_GATEWAY_REQUIRED",
        "CROSS_APPLICATION_GATEWAY_BYPASS_FORBIDDEN",
        "MODEL_ROUTER_DOES_NOT_GRANT_COMMUNICATION_AUTHORITY",
        "SLEEPING_APPLICATION_WAKE_REQUIRES_EXPLICIT_USER_DIRECTIVE",
        "SECURITY_EMERGENCY_WAKE_NARROW_EXCEPTION",
        "SECURITY_EMERGENCY_WAKE_ONLY_PREAUTHORIZED_SECURITY_TARGET",
        "SECURITY_EMERGENCY_WAKE_LEAST_PRIVILEGE",
        "SECURITY_EMERGENCY_WAKE_IMMEDIATE_USER_NOTIFICATION",
    }
    router_semantics = profile.get("model_router_semantics", {})
    hardware = profile.get("hardware_audit_reconciliation", {})
    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("version") == "1.1.0"
        and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P0"
        and profile.get("requirement") == "MUST"
        and profile.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and profile.get("provider_neutral") is True
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("contract_family") == CONTRACT_ID
        and profile.get("topology_policy_schema") == "canonical/schemas/ai-comms-topology-policy.v1.json"
        and required_profile_invariants.issubset(set(profile.get("invariants", [])))
        and router_semantics.get("communication_authority_granted_by_routing") is False
        and router_semantics.get("may_expand_application_participant_set") is False
        and router_semantics.get("may_select_replacement_for_existing_role") is True
        and hardware.get("vendor_neutral") is True
        and hardware.get("accelerator_requirement_created") is False
        and hardware.get("cpu_only_conformance_affected") is False
        and hardware.get("physical_model_or_provider_pin_created") is False
    ):
        findings.append(_finding("AI-COMMS-002", "AI communication profile drift"))

    forbidden = set(contracts.get("forbidden_semantics", []))
    replacement_contract = contracts.get("partner_replacement_contract", {})
    wake_contract = contracts.get("wake_contract", {})
    cross_contract = contracts.get("cross_application_contract", {})
    if not (
        contracts.get("id") == CONTRACT_ID
        and contracts.get("version") == "1.1.0"
        and contracts.get("parent_profile") == PROFILE_ID
        and contracts.get("provider_neutral") is True
        and contracts.get("new_capability") is False
        and contracts.get("new_architectural_authority") is False
        and contracts.get("capability_count") == CAPABILITY_COUNT
        and contracts.get("topology_policy_schema") == "canonical/schemas/ai-comms-topology-policy.v1.json"
        and {
            "PRIVATE_MODEL_LANGUAGE",
            "EMERGENT_AGENT_CODEBOOK",
            "MODEL_ONLY_SLANG",
            "OPAQUE_ENCODING_AS_PRIMARY_SEMANTIC_CHANNEL",
            "UNVERSIONED_STRUCTURED_PROTOCOL",
            "PARALLEL_COMPONENT_OWNED_MODEL_ROUTER",
            "UNDECLARED_APPLICATION_MODEL_PARTICIPANT",
            "PARTICIPANT_SET_EXPANSION_DURING_REPLACEMENT",
            "CROSS_APPLICATION_COMMUNICATION_WITHOUT_PROTECTED_GATEWAY",
            "CROSS_APPLICATION_GATEWAY_BYPASS",
            "MODEL_ROUTER_GRANTED_COMMUNICATION_AUTHORITY",
            "SLEEPING_APPLICATION_WAKE_WITHOUT_USER_DIRECTIVE_OR_SECURITY_EMERGENCY",
            "SECURITY_EMERGENCY_WAKE_TO_NON_SECURITY_TARGET",
        }.issubset(forbidden)
        and replacement_contract.get("unfit_partner_action") == "REPLACE"
        and replacement_contract.get("participant_count_delta_must_equal") == 0
        and replacement_contract.get("central_model_router_required") is True
        and replacement_contract.get("router_does_not_gain_communication_authority") is True
        and cross_contract.get("default") == "DENY"
        and cross_contract.get("protected_gateway_required") is True
        and cross_contract.get("security_emergency_does_not_bypass_gateway") is True
        and wake_contract.get("sleeping_app_requires_explicit_user_directive") is True
        and wake_contract.get("minimum_severity") == "CRITICAL"
        and float(wake_contract.get("minimum_confidence", 0.0)) >= 0.9
        and wake_contract.get("immediate_user_notification_required") is True
    ):
        findings.append(_finding("AI-COMMS-003", "AI communication contract drift"))

    router = decision.get("model_router_reconciliation", {})
    participant = decision.get("application_participant_reconciliation", {})
    replacement = decision.get("partner_replacement_reconciliation", {})
    cross = decision.get("cross_application_reconciliation", {})
    wake = decision.get("wake_reconciliation", {})
    decision_hw = decision.get("hardware_audit_reconciliation", {})
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
        and router.get("communication_authority_granted_to_router") is False
        and router.get("router_may_expand_participant_set") is False
        and participant.get("closed_participant_set") is True
        and participant.get("autonomous_new_ai_party") == "FORBIDDEN"
        and replacement.get("unfit_partner_action") == "REPLACE"
        and replacement.get("participant_count_delta") == 0
        and replacement.get("selection_authority") == "FA3-AUTH-MODEL-ROUTER-001"
        and cross.get("default") == "DENY"
        and cross.get("protected_gateway_required") is True
        and cross.get("gateway_bypass") == "FORBIDDEN"
        and wake.get("sleeping_app_normal_wake") == "EXPLICIT_USER_DIRECTIVE_ONLY"
        and wake.get("exception") == "SECURITY_EMERGENCY_WAKE"
        and wake.get("immediate_user_notification_required") is True
        and wake.get("gateway_bypass_allowed") is False
        and language.get("language_bridge_may_create_private_model_language") is False
        and language.get("language_bridge_may_expand_authority") is False
        and decision_hw.get("vendor_neutral") is True
        and decision_hw.get("cpu_only_conformance_unchanged") is True
        and decision_hw.get("accelerator_floor_created") is False
    ):
        findings.append(_finding("AI-COMMS-004", "Canonical AI communication decision drift"))

    integration = enforcement.get("runtime_integration", {})
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("profile_id") == PROFILE_ID
        and enforcement.get("contract_family") == CONTRACT_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("p0_invariants") == P0_RULES
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and integration.get("topology_module") == "src/fa3_ai_comms_topology.py"
        and integration.get("topology_policy_schema") == "canonical/schemas/ai-comms-topology-policy.v1.json"
        and integration.get("deny_before_persistence_or_dispatch") is True
        and enforcement.get("current_host_production_promotion_claim") is False
    ):
        findings.append(_finding("AI-COMMS-005", "AI communication enforcement drift"))

    if topology_schema.get("$id") != "fa3.ai-comms-topology-policy.v1":
        findings.append(_finding("AI-COMMS-006", "AI communication topology schema drift"))

    lifecycle = app_lifecycle.get("ai_runtime_wake_policy", {})
    if not (
        lifecycle.get("policy_profile") == PROFILE_ID
        and lifecycle.get("sleeping_application_default") == "DENY"
        and lifecycle.get("explicit_user_directive_required") is True
        and lifecycle.get("security_emergency_exception") == "SECURITY_EMERGENCY_WAKE"
        and lifecycle.get("security_exception_immediate_user_notification_required") is True
        and lifecycle.get("protected_cross_app_gateway_remains_required") is True
        and lifecycle.get("model_router_alone_grants_wake_authority") is False
    ):
        findings.append(_finding("AI-COMMS-007", "Application lifecycle wake binding drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("AI-COMMS-008", "AI communication gate missing from global enforcement policy"))
    if policy.get("ai_comms_profile_id") != PROFILE_ID or policy.get("ai_comms_contract_id") != CONTRACT_ID:
        findings.append(_finding("AI-COMMS-009", "Global AI communication binding drift"))
    if policy.get("ai_comms_mandatory_p0_rules") != P0_RULES:
        findings.append(_finding("AI-COMMS-010", "Global AI communication P0 rule binding drift"))

    if dac_contracts.get("communication_policy") != PROFILE_ID:
        findings.append(_finding("AI-COMMS-011", "Developer-agent coordination is not bound to AI communication policy"))
    dac_forbidden = set(dac_contracts.get("forbidden_semantics", []))
    if not {"PRIVATE_MODEL_LANGUAGE", "EMERGENT_AGENT_CODEBOOK", "MODEL_ONLY_SLANG"}.issubset(dac_forbidden):
        findings.append(_finding("AI-COMMS-012", "Developer-agent coordination forbidden communication semantics drift"))
    dac_rules = set(dac_enforcement.get("p0_invariants", []))
    if not {"DAC_HUMAN_AUDITABLE_MODEL_COMMUNICATION", "DAC_PRIVATE_MODEL_LANGUAGE_FORBIDDEN"}.issubset(dac_rules):
        findings.append(_finding("AI-COMMS-013", "Developer-agent coordination runtime enforcement is not bound"))

    semantic_cases = reference_cases()
    topology_cases = topology_reference_cases()
    if not all(semantic_cases.values()):
        findings.append(_finding("AI-COMMS-014", "AI communication semantic positive/negative regressions failed"))
    if not all(topology_cases.values()):
        findings.append(_finding("AI-COMMS-015", "AI communication topology/wake positive/negative regressions failed"))

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
        "regressions": {
            "human_auditable_semantics": semantic_cases,
            "closed_topology_and_wake": topology_cases,
        },
        "current_host_production_claim": False,
        "model_router_reused": True,
        "parallel_model_router_created": False,
        "model_router_grants_communication_authority": False,
        "security_emergency_gateway_bypass_allowed": False,
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
