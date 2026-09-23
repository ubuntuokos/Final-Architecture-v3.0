#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

PROVIDER_ID = "FA3-PROVIDER-AGENCY-AGENTS-001"
CONTRACT_ID = "FA3-AGENCY-AGENTS-PROJECTION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-AGENCY-AGENTS-INTEGRATION-2026-09-23"
REFERENCE_ID = "FA3-AGENCY-AGENTS-UPSTREAM-REFERENCE-2026-09-23"
CATALOG_ID = "FA3-AGENCY-AGENTS-CURATED-CANDIDATES-001"
AGENT_DEFINITION_CONTRACT_ID = "FA3-AGENT-DEFINITION-CONTRACTS-001"
AGENT_DEFINITION_REGISTRY_ID = "FA3-AGENT-DEFINITION-REGISTRY-001"
GATE_ID = "FA3-GATE-AGENCY-AGENTS-001"
GATESET_ID = "FA3-AGENCY-AGENTS-GATESET-001"
UPSTREAM_PIN = "053ddbbf392a1688fc7043d81529f47ef2cf86c8"
CASE_IDS = [f"AGA-{i:03d}" for i in range(1, 25)]
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _mutate(value: dict[str, Any], fn) -> dict[str, Any]:
    cloned = copy.deepcopy(value)
    fn(cloned)
    return cloned


def agent_source_allowed(item: dict[str, Any]) -> bool:
    try:
        return (
            item.get("provider_id") == PROVIDER_ID
            and SHA40.fullmatch(item.get("source_commit", "")) is not None
            and item.get("source_commit") == UPSTREAM_PIN
            and item.get("trust_class") == "UNTRUSTED_SCOPED_CONTEXT"
            and bool(item.get("task_scope"))
            and item.get("global_auto_injection") is False
            and item.get("persona_is_security_identity") is False
            and item.get("persona_grants_capability") is False
            and item.get("persona_grants_tool_permission") is False
            and item.get("persona_grants_secret_or_resource_access") is False
            and item.get("direct_tool_execution") is False
            and item.get("direct_provider_execution") is False
            and item.get("converted_output_auto_install") is False
        )
    except TypeError:
        return False


def coordination_projection_allowed(item: dict[str, Any]) -> bool:
    try:
        return (
            item.get("contract") == "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
            and item.get("runbook_is_orchestrator_authority") is False
            and item.get("task_contract") == "AgentTask"
            and item.get("delegation_contract") == "AgentDelegation"
            and item.get("handoff_contract") == "AgentMessage"
            and item.get("result_contract") == "AgentResult"
            and item.get("escalation_contract") == "HumanEscalation"
            and item.get("evidence_contract") == "ExecutionEvidence"
            and item.get("human_auditable") is True
            and isinstance(item.get("max_hops"), int)
            and item.get("max_hops") > 0
        )
    except TypeError:
        return False


def decision_input_allowed(item: dict[str, Any]) -> bool:
    try:
        return (
            item.get("decision_profile") == "FA3-DECISION-FABRIC-001"
            and item.get("candidate_set_from_calling_fa3_authority") is True
            and item.get("candidate_set_expansion") is False
            and item.get("imported_rank_is_authorization") is False
            and item.get("direct_tool_execution") is False
        )
    except TypeError:
        return False


def communication_allowed(item: dict[str, Any]) -> bool:
    try:
        return (
            item.get("contract") == "FA3-AI-COMMS-CONTRACTS-001"
            and item.get("human_readable_authoritative") is True
            and bool(item.get("human_readable_text"))
            and item.get("private_model_language") is False
            and item.get("emergent_codebook") is False
            and item.get("model_only_slang") is False
        )
    except TypeError:
        return False


def converted_output_activation_allowed(item: dict[str, Any]) -> bool:
    try:
        return (
            item.get("source_provider") == PROVIDER_ID
            and item.get("separate_admission_pass") is True
            and item.get("fa3_authority_preserved") is True
            and item.get("direct_runtime_install") is False
            and item.get("direct_agents_md_override") is False
            and item.get("direct_secret_access") is False
            and item.get("direct_tool_bypass") is False
        )
    except TypeError:
        return False


def candidate_catalog_valid(catalog: dict[str, Any]) -> bool:
    agents = catalog.get("agents", [])
    templates = catalog.get("templates", [])
    if not (
        catalog.get("id") == CATALOG_ID
        and catalog.get("provider_id") == PROVIDER_ID
        and catalog.get("status") == "CURATED_REFERENCE_SOURCES_NORMALIZED"
        and catalog.get("upstream_commit") == UPSTREAM_PIN
        and catalog.get("new_capability") is False
        and catalog.get("new_architectural_authority") is False
        and catalog.get("persona_body_vendored") is False
        and catalog.get("activation_default") == "INERT_REFERENCE_ONLY"
        and catalog.get("selection_policy", {}).get("full_upstream_auto_import") is False
        and catalog.get("selection_policy", {}).get("distribution_and_content_admission_required_before_materialization") is False
        and catalog.get("selection_policy", {}).get("verbatim_or_substantial_source_body_import_requires_separate_distribution_and_content_admission") is True
        and catalog.get("selection_policy", {}).get("fa3_native_derived_normalization_without_source_body_vendoring_allowed") is True
        and catalog.get("selection_policy", {}).get("activation_requires_separate_fa3_admission") is True
        and isinstance(agents, list) and len(agents) == 12
        and isinstance(templates, list) and len(templates) == 5
    ):
        return False

    ids: list[str] = []
    normalized_ids: list[str] = []
    for item in agents:
        ids.append(str(item.get("candidate_id", "")))
        normalized_ids.append(str(item.get("normalized_definition_id", "")))
        source = item.get("source", {})
        if not (
            item.get("upstream_commit") == UPSTREAM_PIN
            and item.get("trust_class") == "UNTRUSTED_SCOPED_CONTEXT"
            and item.get("persona_body_vendored") is False
            and item.get("activation_status") == "INERT_REFERENCE_ONLY"
            and item.get("authority_grants") == []
            and item.get("tool_grants") == []
            and item.get("model_provider_grants") == []
            and item.get("distribution_gate_required") is True
            and item.get("content_admission_required") is False
            and item.get("content_admission_required_if_source_body_imported") is True
            and item.get("normalization_status") == "CANONICAL_FA3_NATIVE_DEFINITION_MATERIALIZED"
            and bool(item.get("normalized_definition_id"))
            and bool(item.get("fa3_target_role"))
            and bool(source.get("path"))
            and SHA40.fullmatch(str(source.get("blob_sha", ""))) is not None
        ):
            return False
    for item in templates:
        ids.append(str(item.get("candidate_id", "")))
        normalized_ids.append(str(item.get("normalized_template_id", "")))
        source = item.get("source", {})
        if not (
            item.get("upstream_commit") == UPSTREAM_PIN
            and item.get("trust_class") == "UNTRUSTED_SCOPED_CONTEXT"
            and item.get("body_vendored") is False
            and item.get("activation_status") == "INERT_REFERENCE_ONLY"
            and item.get("authority_grants") == []
            and item.get("distribution_gate_required") is True
            and item.get("content_admission_required") is False
            and item.get("content_admission_required_if_source_body_imported") is True
            and item.get("normalization_status") == "CANONICAL_FA3_NATIVE_DEFINITION_MATERIALIZED"
            and bool(item.get("normalized_template_id"))
            and bool(item.get("fa3_target_role"))
            and bool(source.get("path"))
            and SHA40.fullmatch(str(source.get("blob_sha", ""))) is not None
        ):
            return False
    state = catalog.get("admission_state", {})
    return (
        len(ids) == len(set(ids))
        and len(normalized_ids) == len(set(normalized_ids))
        and all(ids)
        and all(normalized_ids)
        and state.get("candidate_selection") == "MATERIALIZED"
        and state.get("source_bodies_imported") is False
        and state.get("source_body_admission_receipts_issued") is False
        and state.get("normalized_definition_materialization") is True
        and state.get("definition_contract_id") == AGENT_DEFINITION_CONTRACT_ID
        and state.get("definition_registry_id") == AGENT_DEFINITION_REGISTRY_ID
        and state.get("canonical_role_definition_count") == 12
        and state.get("canonical_template_definition_count") == 5
        and state.get("runtime_provider_materialization") is False
        and state.get("current_host_claim") is False
    )


def normalized_definition_mapping_valid(catalog: dict[str, Any], registry: dict[str, Any]) -> bool:
    definitions = registry.get("definitions", [])
    templates = registry.get("templates", [])
    if not (
        registry.get("id") == AGENT_DEFINITION_REGISTRY_ID
        and registry.get("contract_family") == AGENT_DEFINITION_CONTRACT_ID
        and registry.get("status") == "CANONICAL"
        and registry.get("provider_neutral") is True
        and registry.get("new_capability") is False
        and registry.get("new_architectural_authority") is False
        and len(definitions) == 12
        and len(templates) == 5
        and registry.get("admission_summary", {}).get("upstream_persona_bodies_vendored") is False
        and registry.get("admission_summary", {}).get("runtime_providers_admitted_by_this_registry") is False
    ):
        return False

    role_sources = {
        item.get("candidate_id"): (
            item.get("normalized_definition_id"),
            item.get("source", {}).get("path"),
            item.get("source", {}).get("blob_sha"),
            item.get("upstream_commit"),
        )
        for item in catalog.get("agents", [])
    }
    template_sources = {
        item.get("candidate_id"): (
            item.get("normalized_template_id"),
            item.get("source", {}).get("path"),
            item.get("source", {}).get("blob_sha"),
            item.get("upstream_commit"),
        )
        for item in catalog.get("templates", [])
    }

    for row in definitions:
        candidate_id = row.get("source_candidate_id")
        expected = role_sources.get(candidate_id)
        source = row.get("source", {})
        if not expected or not (
            row.get("definition_id") == expected[0]
            and row.get("source_provider_id") == PROVIDER_ID
            and source.get("path") == expected[1]
            and source.get("blob_sha") == expected[2]
            and source.get("commit") == expected[3] == UPSTREAM_PIN
            and source.get("body_status") == "REFERENCE_ONLY_NOT_IMPORTED"
            and str(source.get("normalization", "")).startswith("FA3_NATIVE_DERIVED")
            and row.get("authority_grants") == []
            and row.get("capability_grants") == []
            and row.get("tool_grants") == []
            and row.get("model_provider_grants") == []
            and row.get("runtime_provider_binding") is None
            and row.get("direct_provider_execution") is False
            and row.get("candidate_set_expansion") is False
            and row.get("private_model_language") is False
            and row.get("execution_runtime_claim") is False
        ):
            return False

    for row in templates:
        candidate_id = row.get("source_candidate_id")
        expected = template_sources.get(candidate_id)
        source = row.get("source", {})
        if not expected or not (
            row.get("template_id") == expected[0]
            and row.get("source_provider_id") == PROVIDER_ID
            and source.get("path") == expected[1]
            and source.get("blob_sha") == expected[2]
            and source.get("commit") == expected[3] == UPSTREAM_PIN
            and source.get("body_status") == "REFERENCE_ONLY_NOT_IMPORTED"
            and str(source.get("normalization", "")).startswith("FA3_NATIVE_DERIVED")
            and row.get("automatic_execution") is False
            and row.get("durable_workflow_authority") is False
            and row.get("provider_selection_authority") is False
            and row.get("authority_grants") == []
        ):
            return False

    return set(role_sources) == {row.get("source_candidate_id") for row in definitions} and set(template_sources) == {row.get("source_candidate_id") for row in templates}

def _good_source() -> dict[str, Any]:
    return {
        "provider_id": PROVIDER_ID,
        "source_commit": UPSTREAM_PIN,
        "trust_class": "UNTRUSTED_SCOPED_CONTEXT",
        "task_scope": "agent.reference.engineering",
        "global_auto_injection": False,
        "persona_is_security_identity": False,
        "persona_grants_capability": False,
        "persona_grants_tool_permission": False,
        "persona_grants_secret_or_resource_access": False,
        "direct_tool_execution": False,
        "direct_provider_execution": False,
        "converted_output_auto_install": False,
    }


def _good_coordination() -> dict[str, Any]:
    return {
        "contract": "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001",
        "runbook_is_orchestrator_authority": False,
        "task_contract": "AgentTask",
        "delegation_contract": "AgentDelegation",
        "handoff_contract": "AgentMessage",
        "result_contract": "AgentResult",
        "escalation_contract": "HumanEscalation",
        "evidence_contract": "ExecutionEvidence",
        "human_auditable": True,
        "max_hops": 4,
    }


def _good_decision() -> dict[str, Any]:
    return {
        "decision_profile": "FA3-DECISION-FABRIC-001",
        "candidate_set_from_calling_fa3_authority": True,
        "candidate_set_expansion": False,
        "imported_rank_is_authorization": False,
        "direct_tool_execution": False,
    }


def _good_communication() -> dict[str, Any]:
    return {
        "contract": "FA3-AI-COMMS-CONTRACTS-001",
        "human_readable_authoritative": True,
        "human_readable_text": "A feladat átadása ember által olvasható és auditálható.",
        "private_model_language": False,
        "emergent_codebook": False,
        "model_only_slang": False,
    }


def _good_activation() -> dict[str, Any]:
    return {
        "source_provider": PROVIDER_ID,
        "separate_admission_pass": True,
        "fa3_authority_preserved": True,
        "direct_runtime_install": False,
        "direct_agents_md_override": False,
        "direct_secret_access": False,
        "direct_tool_bypass": False,
    }


def run_regressions() -> dict[str, Any]:
    source = _good_source()
    coord = _good_coordination()
    decision = _good_decision()
    comm = _good_communication()
    activation = _good_activation()
    checks = [
        agent_source_allowed(source),
        not agent_source_allowed(_mutate(source, lambda x: x.update(source_commit="main"))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(trust_class="TRUSTED_POLICY"))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(global_auto_injection=True))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(persona_is_security_identity=True))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(persona_grants_capability=True))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(persona_grants_tool_permission=True))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(persona_grants_secret_or_resource_access=True))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(direct_tool_execution=True))),
        not agent_source_allowed(_mutate(source, lambda x: x.update(converted_output_auto_install=True))),
        coordination_projection_allowed(coord),
        not coordination_projection_allowed(_mutate(coord, lambda x: x.update(runbook_is_orchestrator_authority=True))),
        not coordination_projection_allowed(_mutate(coord, lambda x: x.update(handoff_contract="NEXUS_PRIVATE_HANDOFF"))),
        not coordination_projection_allowed(_mutate(coord, lambda x: x.update(human_auditable=False))),
        decision_input_allowed(decision),
        not decision_input_allowed(_mutate(decision, lambda x: x.update(candidate_set_expansion=True))),
        not decision_input_allowed(_mutate(decision, lambda x: x.update(imported_rank_is_authorization=True))),
        communication_allowed(comm),
        not communication_allowed(_mutate(comm, lambda x: x.update(human_readable_authoritative=False))),
        not communication_allowed(_mutate(comm, lambda x: x.update(private_model_language=True))),
        converted_output_activation_allowed(activation),
        not converted_output_activation_allowed(_mutate(activation, lambda x: x.update(separate_admission_pass=False))),
        not converted_output_activation_allowed(_mutate(activation, lambda x: x.update(direct_agents_md_override=True))),
        not converted_output_activation_allowed(_mutate(activation, lambda x: x.update(direct_tool_bypass=True))),
    ]
    cases = [{"case_id": cid, "status": "PASS" if ok else "FAIL"} for cid, ok in zip(CASE_IDS, checks)]
    return {
        "result": "PASS" if len(cases) == len(CASE_IDS) and all(c["status"] == "PASS" for c in cases) else "FAIL",
        "total": len(cases),
        "passed": sum(c["status"] == "PASS" for c in cases),
        "case_ids_exact": [c["case_id"] for c in cases] == CASE_IDS,
        "cases": cases,
    }


def canonical_check(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    count = load_active_release_baseline(root).capability_count

    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-AGENCY-AGENTS-001.json",
        "contract": root / "canonical/contracts/FA3-AGENCY-AGENTS-PROJECTION-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-AGENCY-AGENTS-INTEGRATION-2026-09-23.json",
        "reference": root / "canonical/references/FA3-AGENCY-AGENTS-UPSTREAM-REFERENCE-2026-09-23.json",
        "catalog": root / "canonical/registries/FA3-AGENCY-AGENTS-CURATED-CANDIDATES-001.json",
        "agent_definition_contract": root / "canonical/contracts/FA3-AGENT-DEFINITION-CONTRACTS-001.json",
        "agent_definition_registry": root / "canonical/FA3-AGENT-DEFINITION-REGISTRY-001.json",
        "gui_surface_registry": root / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
        "enforcement": root / "canonical/agency-agents-enforcement.json",
        "gate": root / "canonical/FA3-GATE-AGENCY-AGENTS-001.json",
        "policy": root / "canonical/enforcement-policy.json",
        "agent_profile": root / "canonical/profiles/FA3-AGENT-EXEC-001.json",
        "agent_instructions": root / "canonical/profiles/FA3-AGENT-INSTRUCTIONS-001.json",
        "dac": root / "canonical/contracts/FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001.json",
        "ai_comms": root / "canonical/contracts/FA3-AI-COMMS-CONTRACTS-001.json",
        "skill_fabric": root / "canonical/profiles/FA3-SKILL-FABRIC-001.json",
        "skill_admission": root / "canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json",
        "uaf": root / "canonical/contracts/FA3-UNIFIED-ACTION-FABRIC-CONTRACTS-001.json",
        "decision_fabric": root / "canonical/profiles/FA3-DECISION-FABRIC-001.json",
        "distribution_profile": root / "canonical/profiles/FA3-DISTRIBUTION-COMPLIANCE-001.json",
        "distribution_contract": root / "canonical/contracts/FA3-DISTRIBUTION-COMPLIANCE-CONTRACTS-001.json",
        "distribution_registry": root / "canonical/distribution-registry.json",
        "distribution_manifest": root / "canonical/distribution-manifest.json",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        return {"result": "FAIL", "findings": [_finding("AGA-CANON-000", "required canonical input missing", missing=missing)]}

    provider = _load(paths["provider"])
    contract = _load(paths["contract"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    catalog = _load(paths["catalog"])
    agent_definition_contract = _load(paths["agent_definition_contract"])
    agent_definition_registry = _load(paths["agent_definition_registry"])
    gui_surface_registry = _load(paths["gui_surface_registry"])
    enforcement = _load(paths["enforcement"])
    gate = _load(paths["gate"])
    policy = _load(paths["policy"])
    agent_profile = _load(paths["agent_profile"])
    agent_instructions = _load(paths["agent_instructions"])
    dac = _load(paths["dac"])
    ai_comms = _load(paths["ai_comms"])
    skill_fabric = _load(paths["skill_fabric"])
    skill_admission = _load(paths["skill_admission"])
    uaf = _load(paths["uaf"])
    decision_fabric = _load(paths["decision_fabric"])
    distribution_profile = _load(paths["distribution_profile"])
    distribution_contract = _load(paths["distribution_contract"])
    distribution_registry = _load(paths["distribution_registry"])
    distribution_manifest = _load(paths["distribution_manifest"])

    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == count
        and provider.get("upstream", {}).get("immutable_commit") == UPSTREAM_PIN
        and provider.get("ingestion", {}).get("entire_upstream_repo_is_not_implicitly_admitted") is True
        and provider.get("ingestion", {}).get("upstream_converter_auto_execution") is False
        and provider.get("runtime", {}).get("runtime_activation_status") == "REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY"
        and provider.get("runtime", {}).get("current_host_runtime_claim") is False
        and provider.get("curated_candidate_catalog") == CATALOG_ID
        and provider.get("ingestion", {}).get("curated_candidate_selection_materialized") is True
        and provider.get("ingestion", {}).get("curated_candidate_selection_is_admission") is False
    ):
        findings.append(_finding("AGA-CANON-001", "provider identity, trust or runtime boundary drift"))

    boundaries = provider.get("authority_boundaries", {})
    if not boundaries or any(value is not False for value in boundaries.values()):
        findings.append(_finding("AGA-CANON-002", "provider crossed an architectural authority boundary"))

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == count
        and contract.get("normalization_targets", {}).get("coordination") == "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
        and contract.get("agent_mapping", {}).get("persona_implies_capability_grant") is False
        and contract.get("runbook_mapping", {}).get("upstream_runbook_is_durable_workflow_authority") is False
        and contract.get("conversion_mapping", {}).get("direct_converter_execution_on_production_path") is False
        and contract.get("decision_boundary", {}).get("candidate_set_expansion") == "DENY"
        and contract.get("curated_candidate_catalog") == CATALOG_ID
        and contract.get("agent_mapping", {}).get("candidate_catalog_is_activation_authority") is False
        and contract.get("agent_mapping", {}).get("candidate_selection_requires_separate_content_admission") is False
        and contract.get("agent_mapping", {}).get("fa3_native_definition_registry") == AGENT_DEFINITION_REGISTRY_ID
        and contract.get("agent_mapping", {}).get("upstream_body_vendoring_required") is False
        and contract.get("agent_mapping", {}).get("verbatim_future_import_requires_separate_distribution_and_content_admission") is True
        and contract.get("normalization_targets", {}).get("agent_definition") == AGENT_DEFINITION_CONTRACT_ID
    ):
        findings.append(_finding("AGA-CANON-003", "normalization contract drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("upstream_pin") == UPSTREAM_PIN
        and decision.get("status") == "CANONICAL_IMPLEMENTED_STATIC_GATES_OPEN_RUNTIME_AND_RELEASE_VALIDATION"
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == count
        and decision.get("current_host_runtime_claim") is False
        and set(decision.get("open_reconciliations", [])) == {
            "LATEST_UNIFIED_RELEASE_PROJECTION_REGENERATION_PENDING",
            "FRESH_PERMANENT_CI_AFTER_AGENT_DEFINITION_AND_GUI_BINDING_PENDING",
        }
        and decision.get("parallel_change_reconciliation", {}).get("skill_distribution", {}).get("provider_target_class") == "EXTERNAL_REDISTRIBUTABLE"
        and decision.get("parallel_change_reconciliation", {}).get("skill_distribution", {}).get("status") == "RECONCILED_CANONICAL_MAIN"
        and decision.get("parallel_change_reconciliation", {}).get("gui", {}).get("target_surface_route") == "agents.workflows"
        and decision.get("parallel_change_reconciliation", {}).get("gui", {}).get("status") == "RECONCILED_CANONICAL_MAIN"
        and decision.get("parallel_change_reconciliation", {}).get("gui", {}).get("child_surface_id") == "agency-agents.imported-pack"
        and decision.get("parallel_change_reconciliation", {}).get("gui", {}).get("agent_definition_registry_id") == AGENT_DEFINITION_REGISTRY_ID
        and decision.get("curated_candidate_selection", {}).get("catalog_id") == CATALOG_ID
        and decision.get("curated_candidate_selection", {}).get("status") == "SOURCE_CANDIDATES_NORMALIZED_TO_FA3_NATIVE_DEFINITIONS"
        and decision.get("curated_candidate_selection", {}).get("agent_candidates") == 12
        and decision.get("curated_candidate_selection", {}).get("template_candidates") == 5
        and decision.get("curated_candidate_selection", {}).get("persona_bodies_vendored") is False
        and decision.get("curated_candidate_selection", {}).get("source_candidate_activation_enabled") is False
        and decision.get("curated_candidate_selection", {}).get("definition_contract_id") == AGENT_DEFINITION_CONTRACT_ID
        and decision.get("curated_candidate_selection", {}).get("definition_registry_id") == AGENT_DEFINITION_REGISTRY_ID
        and decision.get("curated_candidate_selection", {}).get("canonical_role_definitions") == 12
        and decision.get("curated_candidate_selection", {}).get("canonical_template_definitions") == 5
        and decision.get("curated_candidate_selection", {}).get("runtime_provider_admission_performed") is False
    ):
        findings.append(_finding("AGA-CANON-004", "decision or deliberately-open reconciliation state drift"))

    artifacts = reference.get("observed_artifacts", {})
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("immutable_commit") == UPSTREAM_PIN
        and reference.get("license", {}).get("name") == "MIT"
        and reference.get("license", {}).get("blob_sha") == "523078c01624b9b1b1c551e75054b9d3a9f953ab"
        and artifacts.get("divisions", {}).get("division_count") == 18
        and artifacts.get("runbooks", {}).get("runbook_count") == 4
        and artifacts.get("converter", {}).get("executable_source") is True
        and reference.get("interpretation", {}).get("full_upstream_content_admission_performed") is False
        and reference.get("interpretation", {}).get("current_host_runtime_evidence_claimed") is False
        and reference.get("distribution", {}).get("class") == "REFERENCE_ONLY"
        and reference.get("distribution", {}).get("release_bundle_status") == "EXCLUDED"
    ):
        findings.append(_finding("AGA-CANON-005", "immutable upstream reference observation drift"))

    if not candidate_catalog_valid(catalog):
        findings.append(_finding("AGA-CANON-011", "curated source catalog drift or unsafe source activation"))
    if not (
        agent_definition_contract.get("id") == AGENT_DEFINITION_CONTRACT_ID
        and agent_definition_contract.get("status") == "CANONICAL"
        and agent_definition_contract.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and agent_definition_contract.get("provider_neutral") is True
        and agent_definition_contract.get("new_capability") is False
        and agent_definition_contract.get("new_architectural_authority") is False
        and agent_definition_contract.get("capability_count") == count
        and agent_definition_contract.get("registry") == AGENT_DEFINITION_REGISTRY_ID
        and normalized_definition_mapping_valid(catalog, agent_definition_registry)
    ):
        findings.append(_finding("AGA-CANON-013", "Agency source-to-Agent-Definition normalization drift"))

    rules = enforcement.get("rules", [])
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("gateset_id") == GATESET_ID
        and enforcement.get("upstream_pin") == UPSTREAM_PIN
        and enforcement.get("fail_closed") is True
        and enforcement.get("capability_count") == count
        and enforcement.get("current_host_runtime_claim_forbidden") is True
        and len(rules) >= 20
    ):
        findings.append(_finding("AGA-CANON-006", "enforcement matrix drift"))

    if not (
        gate.get("id") == GATE_ID
        and gate.get("gateset_id") == GATESET_ID
        and gate.get("case_ids") == CASE_IDS
        and gate.get("mandatory_rules") == rules
        and gate.get("regression_case_count") == len(CASE_IDS)
        and gate.get("current_host_provider_runtime_evidence") is False
        and gate.get("candidate_catalog_id") == CATALOG_ID
        and gate.get("candidate_catalog_status_required") == "CURATED_REFERENCE_SOURCES_NORMALIZED"
        and gate.get("agent_definition_contract_id") == AGENT_DEFINITION_CONTRACT_ID
        and gate.get("agent_definition_registry_id") == AGENT_DEFINITION_REGISTRY_ID
    ):
        findings.append(_finding("AGA-CANON-007", "gate record drift"))

    if not (
        GATESET_ID in policy.get("mandatory_reference_gates", [])
        and policy.get("agency_agents_provider_id") == PROVIDER_ID
        and policy.get("agency_agents_contract_id") == CONTRACT_ID
        and policy.get("agency_agents_gate_id") == GATESET_ID
        and policy.get("agency_agents_upstream_pin") == UPSTREAM_PIN
        and policy.get("agency_agents_runtime_status") == "REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY"
        and policy.get("agency_agents_mandatory_p0_rules") == rules
    ):
        findings.append(_finding("AGA-CANON-008", "global enforcement binding drift"))

    dac_contracts = set(dac.get("contracts", []))
    required_dac = {"AgentTask", "AgentDelegation", "AgentMessage", "AgentResult", "HumanEscalation", "ExecutionEvidence"}
    if not (
        agent_profile.get("id") == "FA3-AGENT-EXEC-001"
        and agent_instructions.get("id") == "FA3-AGENT-INSTRUCTIONS-001"
        and required_dac.issubset(dac_contracts)
        and ai_comms.get("id") == "FA3-AI-COMMS-CONTRACTS-001"
        and skill_fabric.get("id") == "FA3-SKILL-FABRIC-001"
        and skill_admission.get("id") == "FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001"
        and uaf.get("id") == "FA3-UNIFIED-ACTION-FABRIC-CONTRACTS-001"
        and decision_fabric.get("id") == "FA3-DECISION-FABRIC-001"
    ):
        findings.append(_finding("AGA-CANON-009", "required existing FA3 target contracts are unavailable or drifted"))

    agent_native = provider.get("agent_native", {})
    decision_boundary = provider.get("decision_fabric", {})
    comms = provider.get("ai_communication", {})
    skill = provider.get("skill_fabric", {})
    distribution = provider.get("distribution", {})
    surface = provider.get("surface_reconciliation", {})
    if not (
        agent_native.get("fabric") == "FA3-UNIFIED-ACTION-FABRIC-001"
        and agent_native.get("imported_persona_is_canonical_instruction_projection") is False
        and agent_native.get("direct_agent_provider_bypass") is False
        and decision_boundary.get("candidate_set_expansion_forbidden") is True
        and decision_boundary.get("imported_agent_rank_is_not_authorization") is True
        and comms.get("human_auditable_required") is True
        and comms.get("private_model_language_forbidden") is True
        and skill.get("persona_is_not_skill") is True
        and skill.get("extracted_procedure_requires_separate_skill_admission") is True
        and distribution.get("class") == "EXTERNAL_REDISTRIBUTABLE"
        and distribution.get("release_bundle_status") == "EXCLUDED"
        and distribution.get("inclusion_requires_distribution_decision_receipt") is True
        and distribution.get("profile_id") == "FA3-DISTRIBUTION-COMPLIANCE-001"
        and distribution.get("contract_id") == "FA3-DISTRIBUTION-COMPLIANCE-CONTRACTS-001"
        and distribution.get("binding_status") == "CANONICAL_RECONCILED"
        and surface.get("canonical_target_route") == "agents.workflows"
        and surface.get("view_kind") == "IMPORTED_PACK_CHILD_VIEW"
        and surface.get("execution_intent_route") == "agents.action-center"
        and surface.get("new_top_level_navigation_route_required") is False
        and surface.get("status") == "RECONCILED_CANONICAL_GUI"
        and surface.get("child_surface_id") == "agency-agents.imported-pack"
        and surface.get("agent_definition_registry_id") == AGENT_DEFINITION_REGISTRY_ID
        and surface.get("mode") == "READ_ONLY_CANONICAL_DEFINITIONS"
        and surface.get("direct_provider_execution") is False
        and provider.get("agent_definition_projection", {}).get("contract_id") == AGENT_DEFINITION_CONTRACT_ID
        and provider.get("agent_definition_projection", {}).get("registry_id") == AGENT_DEFINITION_REGISTRY_ID
        and provider.get("agent_definition_projection", {}).get("status") == "CANONICAL_FA3_NATIVE_NORMALIZATION_MATERIALIZED"
        and provider.get("agent_definition_projection", {}).get("upstream_bodies_vendored") is False
        and provider.get("agent_definition_projection", {}).get("definition_is_runtime_provider") is False
        and contract.get("supply_chain", {}).get("distribution_profile_binding") == "FA3-DISTRIBUTION-COMPLIANCE-001"
        and contract.get("supply_chain", {}).get("distribution_contract_binding") == "FA3-DISTRIBUTION-COMPLIANCE-CONTRACTS-001"
        and contract.get("supply_chain", {}).get("distribution_compliance_status") == "CANONICAL_RECONCILED"
    ):
        findings.append(_finding("AGA-CANON-010", "Agent Native, Decision Fabric, AI-Comms, Skill Fabric, distribution or GUI reconciliation drift"))

    agent_surface = next((row for row in gui_surface_registry.get("surfaces", []) if row.get("route_id") == "agents.workflows"), {})
    child = next((row for row in agent_surface.get("children", []) if row.get("surface_id") == "agency-agents.imported-pack"), {})
    if not (
        child.get("provider_id") == PROVIDER_ID
        and child.get("candidate_catalog_id") == CATALOG_ID
        and child.get("agent_definition_registry_id") == AGENT_DEFINITION_REGISTRY_ID
        and child.get("projection") == "CANONICAL_AGENT_DEFINITION_REFERENCE"
        and child.get("mode") == "READ_ONLY_CANONICAL_DEFINITIONS"
        and child.get("activation_status") == "DEFINITION_AVAILABLE_RUNTIME_PROVIDER_SEPARATE"
        and child.get("execution_intent_route") == "agents.action-center"
        and child.get("direct_provider_execution") is False
        and child.get("authority") is False
    ):
        findings.append(_finding("AGA-CANON-014", "Agency GUI imported-pack projection drift"))

    records = {row.get("subject_id"): row for row in distribution_registry.get("records", [])}
    provider_dist = records.get(PROVIDER_ID, {})
    reference_dist = records.get(REFERENCE_ID, {})
    manifest_excluded = {
        row.get("subject_id"): row
        for row in distribution_manifest.get("excluded", [])
    }
    if not (
        distribution_profile.get("id") == "FA3-DISTRIBUTION-COMPLIANCE-001"
        and distribution_profile.get("status") == "CANONICAL"
        and distribution_contract.get("id") == "FA3-DISTRIBUTION-COMPLIANCE-CONTRACTS-001"
        and distribution_contract.get("status") == "CANONICAL"
        and provider_dist.get("class") == "EXTERNAL_REDISTRIBUTABLE"
        and provider_dist.get("release_bundle_status") == "EXCLUDED"
        and provider_dist.get("inclusion_requires_distribution_decision_receipt") is True
        and reference_dist.get("class") == "REFERENCE_ONLY"
        and reference_dist.get("release_bundle_status") == "EXCLUDED"
        and manifest_excluded.get(PROVIDER_ID, {}).get("class") == "EXTERNAL_REDISTRIBUTABLE"
        and manifest_excluded.get(REFERENCE_ID, {}).get("class") == "REFERENCE_ONLY"
        and distribution_manifest.get("included_external_count") == 0
    ):
        findings.append(_finding("AGA-CANON-012", "canonical Distribution Compliance registry/manifest binding drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    canonical = canonical_check(root)
    regressions = run_regressions()
    result = "PASS" if canonical["result"] == "PASS" and regressions["result"] == "PASS" else "FAIL"
    report = {
        "schema": "fa3.agency-agents-gate-report.v1",
        "gate_id": GATE_ID,
        "gateset_id": GATESET_ID,
        "provider_id": PROVIDER_ID,
        "contract_id": CONTRACT_ID,
        "upstream_pin": UPSTREAM_PIN,
        "result": result,
        "canonical": canonical,
        "regressions": regressions,
        "upstream_source_body_import": "NOT_PERFORMED_BY_DESIGN",
        "curated_source_selection": "MATERIALIZED_INERT_REFERENCE_ONLY",
        "agent_definition_normalization": "CANONICAL_12_ROLE_5_TEMPLATE_NO_UPSTREAM_BODY_VENDORED",
        "gui_surface_reconciliation": "RECONCILED_CANONICAL_GUI_READ_ONLY_DEFINITIONS",
        "runtime_provider_admission": "SEPARATE_NOT_CLAIMED_BY_REFERENCE_PROVIDER",
        "external_redistributable_binding": "CANONICAL_RECONCILED_EXTERNAL_REDISTRIBUTABLE_BUNDLE_EXCLUDED",
        "current_host_runtime_claim": False,
        "global_promotion_claim": False,
    }
    _write(root.resolve() / "reports/agency-agents-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Agency Agents reference-provider normalization gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
