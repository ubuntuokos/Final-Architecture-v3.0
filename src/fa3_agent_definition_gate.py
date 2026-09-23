#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

CONTRACT_ID = "FA3-AGENT-DEFINITION-CONTRACTS-001"
REGISTRY_ID = "FA3-AGENT-DEFINITION-REGISTRY-001"
GATE_ID = "FA3-GATE-AGENT-DEFINITION-001"
GATESET_ID = "FA3-AGENT-DEFINITION-GATESET-001"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def loadj(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"object required: {path}")
    return obj


def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def definition_valid(row: dict[str, Any]) -> bool:
    source = row.get("source", {})
    return (
        bool(row.get("definition_id"))
        and row.get("status") == "CANONICAL_ROLE_DEFINITION"
        and SHA40.fullmatch(str(source.get("commit", ""))) is not None
        and SHA40.fullmatch(str(source.get("blob_sha", ""))) is not None
        and source.get("body_status") == "REFERENCE_ONLY_NOT_IMPORTED"
        and str(source.get("normalization", "")).startswith("FA3_NATIVE_DERIVED")
        and bool(row.get("summary"))
        and bool(row.get("competency_intents"))
        and bool(row.get("anti_capabilities"))
        and bool(row.get("risk_class"))
        and bool(row.get("human_gate_policy"))
        and row.get("communication_contract") == "FA3-AI-COMMS-001"
        and row.get("action_fabric") == "FA3-UNIFIED-ACTION-FABRIC-001"
        and row.get("runtime_provider_binding") is None
        and row.get("activation_mode") == "EXPLICIT_TASK_SCOPED_ROLE_PROJECTION_ONLY"
        and row.get("authority_grants") == []
        and row.get("capability_grants") == []
        and row.get("tool_grants") == []
        and row.get("model_provider_grants") == []
        and row.get("direct_provider_execution") is False
        and row.get("candidate_set_expansion") is False
        and row.get("private_model_language") is False
        and row.get("execution_runtime_claim") is False
    )


def template_valid(row: dict[str, Any]) -> bool:
    source = row.get("source", {})
    return (
        bool(row.get("template_id"))
        and row.get("status") == "CANONICAL_TEMPLATE_DEFINITION"
        and SHA40.fullmatch(str(source.get("commit", ""))) is not None
        and SHA40.fullmatch(str(source.get("blob_sha", ""))) is not None
        and source.get("body_status") == "REFERENCE_ONLY_NOT_IMPORTED"
        and str(source.get("normalization", "")).startswith("FA3_NATIVE_DERIVED")
        and bool(row.get("summary"))
        and row.get("automatic_execution") is False
        and row.get("durable_workflow_authority") is False
        and row.get("provider_selection_authority") is False
        and row.get("mutation_requires_authorization_or_approval") is True
        and row.get("coordination_contract") == "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
        and row.get("communication_contract") == "FA3-AI-COMMS-001"
        and row.get("authority_grants") == []
    )


def _good_definition() -> dict[str, Any]:
    return {
        "definition_id": "FA3-AGENT-ROLE-TEST-001",
        "status": "CANONICAL_ROLE_DEFINITION",
        "source": {
            "commit": "1" * 40,
            "blob_sha": "2" * 40,
            "body_status": "REFERENCE_ONLY_NOT_IMPORTED",
            "normalization": "FA3_NATIVE_DERIVED_SUMMARY_NO_UPSTREAM_BODY_VENDORED",
        },
        "summary": "Human-readable bounded role definition.",
        "competency_intents": ["review"],
        "anti_capabilities": ["authorization"],
        "risk_class": "LOW_ADVISORY",
        "human_gate_policy": "REQUIRED_FOR_MUTATION_CONSEQUENTIAL_ACTION_OR_AUTHORITY_ESCALATION",
        "communication_contract": "FA3-AI-COMMS-001",
        "action_fabric": "FA3-UNIFIED-ACTION-FABRIC-001",
        "runtime_provider_binding": None,
        "activation_mode": "EXPLICIT_TASK_SCOPED_ROLE_PROJECTION_ONLY",
        "authority_grants": [],
        "capability_grants": [],
        "tool_grants": [],
        "model_provider_grants": [],
        "direct_provider_execution": False,
        "candidate_set_expansion": False,
        "private_model_language": False,
        "execution_runtime_claim": False,
    }


def _good_template() -> dict[str, Any]:
    return {
        "template_id": "FA3-AGENT-TEMPLATE-TEST-001",
        "status": "CANONICAL_TEMPLATE_DEFINITION",
        "source": {
            "commit": "1" * 40,
            "blob_sha": "2" * 40,
            "body_status": "REFERENCE_ONLY_NOT_IMPORTED",
            "normalization": "FA3_NATIVE_DERIVED_STRUCTURE_NO_UPSTREAM_BODY_VENDORED",
        },
        "summary": "Bounded coordination template.",
        "automatic_execution": False,
        "durable_workflow_authority": False,
        "provider_selection_authority": False,
        "mutation_requires_authorization_or_approval": True,
        "coordination_contract": "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001",
        "communication_contract": "FA3-AI-COMMS-001",
        "authority_grants": [],
    }


def regressions() -> dict[str, Any]:
    d = _good_definition()
    t = _good_template()

    def mut(x: dict[str, Any], fn) -> dict[str, Any]:
        y = copy.deepcopy(x)
        fn(y)
        return y

    checks = [
        ("DEF-001", definition_valid(d)),
        ("DEF-002", not definition_valid(mut(d, lambda x: x["authority_grants"].append("FA3-AUTH-SECURITY-GOV-001")))),
        ("DEF-003", not definition_valid(mut(d, lambda x: x["capability_grants"].append("CAP-028")))),
        ("DEF-004", not definition_valid(mut(d, lambda x: x.update(runtime_provider_binding="FA3-PROVIDER-CREWAI-001")))),
        ("DEF-005", not definition_valid(mut(d, lambda x: x.update(direct_provider_execution=True)))),
        ("DEF-006", not definition_valid(mut(d, lambda x: x.update(candidate_set_expansion=True)))),
        ("DEF-007", not definition_valid(mut(d, lambda x: x.update(private_model_language=True)))),
        ("DEF-008", not definition_valid(mut(d, lambda x: x["source"].update(body_status="VENDORED_UNREVIEWED")))),
        ("DEF-009", template_valid(t)),
        ("DEF-010", not template_valid(mut(t, lambda x: x.update(automatic_execution=True)))),
        ("DEF-011", not template_valid(mut(t, lambda x: x.update(durable_workflow_authority=True)))),
        ("DEF-012", not template_valid(mut(t, lambda x: x["authority_grants"].append("TEMPORAL")))),
    ]
    return {
        "result": "PASS" if all(ok for _, ok in checks) else "FAIL",
        "cases": [{"case_id": cid, "status": "PASS" if ok else "FAIL"} for cid, ok in checks],
        "total": len(checks),
        "passed": sum(ok for _, ok in checks),
    }


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    count = load_active_release_baseline(root).capability_count

    profile = loadj(root / "canonical/profiles/FA3-AGENT-DEFINITION-001.json")
    contract = loadj(root / "canonical/contracts/FA3-AGENT-DEFINITION-CONTRACTS-001.json")
    registry = loadj(root / "canonical/FA3-AGENT-DEFINITION-REGISTRY-001.json")
    agent_exec = loadj(root / "canonical/profiles/FA3-AGENT-EXEC-001.json")
    instructions = loadj(root / "canonical/profiles/FA3-AGENT-INSTRUCTIONS-001.json")
    ai_comms = loadj(root / "canonical/profiles/FA3-AI-COMMS-001.json")
    uaf = loadj(root / "canonical/contracts/FA3-UNIFIED-ACTION-FABRIC-CONTRACTS-001.json")
    workforce = loadj(root / "canonical/FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001.json")
    distribution = loadj(root / "canonical/distribution-registry.json")

    if not (
        profile.get("id") == "FA3-AGENT-DEFINITION-001"
        and profile.get("status") == "CANONICAL"
        and profile.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and profile.get("relationship") == "SUBPROFILE-OF"
        and profile.get("provider_neutral") is True
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == count
        and profile.get("contract_family") == CONTRACT_ID
        and profile.get("registry") == REGISTRY_ID
        and profile.get("gate_id") == GATESET_ID
    ):
        findings.append(finding("DEF-CANON-000", "agent definition profile governance drift"))

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("status") == "CANONICAL"
        and contract.get("parent_profile") == "FA3-AGENT-DEFINITION-001"
        and contract.get("parent_execution_profile") == "FA3-AGENT-EXEC-001"
        and contract.get("provider_neutral") is True
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == count
        and contract.get("registry") == REGISTRY_ID
    ):
        findings.append(finding("DEF-CANON-001", "agent definition contract governance drift"))

    sem = contract.get("definition_semantics", {})
    if any(sem.get(k) is not False for k in (
        "security_identity_authority",
        "authorization_authority",
        "capability_grant_authority",
        "tool_permission_authority",
        "model_or_provider_routing_authority",
        "host_resource_authority",
        "durable_workflow_authority",
        "evidence_authority",
        "workforce_specialist_authority",
    )):
        findings.append(finding("DEF-CANON-002", "agent definition contract gained authority"))

    if not (
        registry.get("id") == REGISTRY_ID
        and registry.get("status") == "CANONICAL"
        and registry.get("canonical_registry_authority") == "FA3-REGISTRY-001"
        and registry.get("contract_family") == CONTRACT_ID
        and registry.get("profile_id") == "FA3-AGENT-DEFINITION-001"
        and registry.get("parent_profile") == "FA3-AGENT-DEFINITION-001"
        and registry.get("parent_execution_profile") == "FA3-AGENT-EXEC-001"
        and registry.get("provider_neutral") is True
        and registry.get("new_capability") is False
        and registry.get("new_architectural_authority") is False
        and registry.get("capability_count") == count
    ):
        findings.append(finding("DEF-CANON-003", "agent definition registry governance drift"))

    definitions = registry.get("definitions", [])
    templates = registry.get("templates", [])
    dids = [row.get("definition_id") for row in definitions]
    tids = [row.get("template_id") for row in templates]
    if len(dids) != len(set(dids)) or not all(definition_valid(row) for row in definitions):
        findings.append(finding("DEF-CANON-004", "invalid or duplicate canonical role definition"))
    if len(tids) != len(set(tids)) or not all(template_valid(row) for row in templates):
        findings.append(finding("DEF-CANON-005", "invalid or duplicate canonical template definition"))

    summary = registry.get("admission_summary", {})
    if not (
        summary.get("definition_count") == len(definitions)
        and summary.get("template_count") == len(templates)
        and summary.get("upstream_persona_bodies_vendored") is False
        and summary.get("runtime_providers_admitted_by_this_registry") is False
        and summary.get("current_host_runtime_claim") is False
        and summary.get("global_promotion_claim") is False
    ):
        findings.append(finding("DEF-CANON-006", "registry admission summary drift"))

    if not (
        agent_exec.get("id") == "FA3-AGENT-EXEC-001"
        and instructions.get("authority_model", {}).get("project_instructions_are_untrusted_scoped_context") is True
        and ai_comms.get("id") == "FA3-AI-COMMS-001"
        and uaf.get("id") == "FA3-UNIFIED-ACTION-FABRIC-CONTRACTS-001"
    ):
        findings.append(finding("DEF-CANON-007", "required FA3 execution/instruction/communication/action boundary drift"))

    role_projection = workforce.get("role_definition_projection", {})
    if not (
        role_projection.get("profile_id") == "FA3-AGENT-DEFINITION-001"
        and role_projection.get("registry_id") == REGISTRY_ID
        and role_projection.get("contract_id") == CONTRACT_ID
        and role_projection.get("may_decorate_selected_specialist") is True
        and role_projection.get("may_expand_specialist_set") is False
        and role_projection.get("may_select_provider") is False
        and role_projection.get("may_override_hard_filters") is False
        and role_projection.get("may_expand_authorized_ai_participant_set") is False
        and role_projection.get("may_grant_capability_tool_model_secret_or_resource_access") is False
        and role_projection.get("runtime_provider_selection_remains_workforce_and_existing_admission") is True
    ):
        findings.append(finding("DEF-CANON-008", "workforce role-definition boundary missing or invalid"))

    specialist_ids = {row.get("id") for row in workforce.get("specialists", [])}
    if specialist_ids.intersection(set(dids)):
        findings.append(finding("DEF-CANON-009", "role definition incorrectly materialized as workforce specialist"))

    dist = {row.get("subject_id"): row for row in distribution.get("records", [])}
    for row in definitions:
        source_provider = row.get("source_provider_id")
        if source_provider and source_provider not in dist:
            findings.append(finding("DEF-CANON-010", "external source provider missing distribution classification", source_provider_id=source_provider))
    if any(dist[row.get("source_provider_id")].get("release_bundle_status") != "EXCLUDED" for row in definitions if row.get("source_provider_id") in dist):
        findings.append(finding("DEF-CANON-011", "source provider unexpectedly included in release bundle"))

    reg = regressions()
    result = "PASS" if not findings and reg["result"] == "PASS" else "FAIL"
    report = {
        "schema": "fa3.agent-definition-gate-report.v1",
        "gate_id": GATE_ID,
        "gateset_id": GATESET_ID,
        "contract_id": CONTRACT_ID,
        "registry_id": REGISTRY_ID,
        "result": result,
        "findings": findings,
        "regressions": reg,
        "definition_count": len(definitions),
        "template_count": len(templates),
        "runtime_provider_promotion_claimed": False,
        "current_host_runtime_claim": False,
        "global_promotion_claim": False,
    }
    out = root / "reports/agent-definition-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 provider-neutral Agent Definition admission gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
