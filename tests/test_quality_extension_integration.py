import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_quality_extension_decision_is_capability_neutral():
    decision = load("canonical/decisions/FA3-DEC-QUALITY-EXTENSIONS-PINNING-VALIDATION-2026-09-14.json")
    assert decision["new_capabilities"] == 0
    assert decision["new_architectural_authorities"] == 0
    assert decision["capability_count_change"] == 0


def test_marketing_production_denies_piper_without_removing_piper():
    policy = load("canonical/FA3-VOICE-QUALITY-ROUTING-001.json")
    assert "FA3-PROVIDER-PIPER-001" in policy["provider_quality_eligibility"]
    assert "PRODUCTION" not in policy["provider_quality_eligibility"]["FA3-PROVIDER-PIPER-001"]
    assert "FA3-PROVIDER-PIPER-001" in policy["workflow_overrides"]["MARKETING_PRODUCTION"]["forbidden_provider_ids"]


def test_layered_preflight_does_not_replace_provider_specific_gate():
    contract = load("canonical/contracts/FA3-AUDIO-PREFLIGHT-CONTRACTS-001.json")
    assert contract["policy"]["provider_specific_gate_still_required"] is True
    assert contract["policy"]["pydantic_or_api_schema_validation_is_not_sufficient"] is True


def test_lock_registry_forbids_floating_promotion_refs():
    registry = load("canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json")
    assert registry["policy"]["floating_main_allowed_for_runtime"] is False
    assert registry["policy"]["floating_main_allowed_for_promotion_evidence"] is False
