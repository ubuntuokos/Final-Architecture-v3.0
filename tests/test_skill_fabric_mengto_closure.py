import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_skill_fabric_is_provider_neutral_and_authority_preserving():
    p = load("canonical/profiles/FA3-SKILL-FABRIC-001.json")
    assert p["status"] == "CANONICAL"
    assert p["priority"] == "P0"
    assert p["requirement"] == "MUST"
    assert p["provider_neutral"] is True
    assert p["new_capability"] is False
    assert p["new_architectural_authority"] is False
    assert p["capability_count"] == 143
    assert all(v is False for v in p["authority_boundaries"].values())


def test_skill_contract_requires_trigger_procedure_guardrails_and_acceptance():
    p = load("canonical/profiles/FA3-SKILL-FABRIC-001.json")
    required = set(p["skill_contract"]["required_sections"])
    assert {"use_when", "procedure", "guardrails", "pitfalls", "acceptance_checks"} <= required
    assert "trigger" in p["skill_contract"]["required_metadata"]
    assert p["selection_and_composition"]["smallest_matching_skill_set_required"] is True
    assert p["selection_and_composition"]["composition_cannot_expand_authority"] is True


def test_mengto_is_reference_only_and_not_installed():
    provider = load("canonical/providers/FA3-PROVIDER-MENGTO-SKILLS-001.json")
    runtime = provider["runtime"]
    assert provider["architectural_authority"] is False
    assert provider["new_capability"] is False
    assert provider["capability_count"] == 143
    assert runtime["install_MengTo_Skills"] is False
    assert runtime["clone_MengTo_Skills"] is False
    assert runtime["import_python_or_node_package"] is False
    assert runtime["network_access_to_upstream_required"] is False
    assert runtime["FA3_operates_when_upstream_is_unavailable"] is True
    assert provider["upstream"]["content_imported"] is False


def test_existing_admission_and_mcp_authority_are_reused():
    profile = load("canonical/profiles/FA3-SKILL-FABRIC-001.json")
    contract = load("canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json")
    assert profile["contract_id"] == contract["id"]
    assert contract["execution_safety"]["package_is_data_until_separately_authorized"] is True
    assert contract["tool_governance"]["central_mcp_gateway_required"] is True
    assert contract["tool_governance"]["discovery_is_not_authorization"] is True
    assert contract["context_governance"]["on_demand_loading_required"] is True


def test_closure_decision_has_no_capability_or_authority_drift():
    d = load("canonical/decisions/FA3-DEC-SKILL-FABRIC-MENGTO-CLOSURE-2026-09-17.json")
    assert d["capability_count_before"] == d["capability_count_after"] == 143
    assert d["new_architectural_authority"] == 0
    assert d["closure_conditions"]["separate_MengTo_installation_required"] is False
    assert d["closure_conditions"]["upstream_runtime_dependency"] is False
    assert d["closure_conditions"]["existing_authority_boundaries_preserved"] is True
