import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "FA3-DONOR-AGENTSCOPE-EMBABEL-PLAN-2026-10-06.json"

EXPECTED_KEYS = {
    "github:agentscope-ai",
    "github:agentscope-ai/agentscope",
    "github:agentscope-ai/agentscope-samples",
    "github:agentscope-ai/agentscope-runtime",
    "github:agentscope-ai/agentteams",
    "github:agentscope-ai/reme",
    "github:agentscope-ai/openjudge",
    "github:agentscope-ai/trinity-rft",
    "github:agentscope-ai/tuft",
    "https://agentscope.io/",
    "github:embabel",
    "github:embabel/embabel-agent",
    "github:embabel/embabel-agent-examples",
    "github:embabel/tripper",
}

def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))

def test_exact_approved_source_set_and_baseline():
    data = load_delta()
    assert data["schema"] == "fa3.donor-intake-delta.v1"
    assert data["parent_entry_count"] == 1792
    assert data["submitted_url_count"] == 14
    assert data["unique_source_count"] == 14
    assert data["new_source_count"] == 14
    assert data["proposed_entry_count"] == 1806
    assert data["capability_baseline"] == 175
    assert data["capability_delta"] == 0
    assert data["authority_delta"] == 0
    assert data["usage_edges_created"] == 0
    keys = {row["normalized_key"] for row in data["canonical_identities"]}
    assert keys == EXPECTED_KEYS

def test_plan_approval_binding_is_exact():
    data = load_delta()
    assert data["approval_mode"] == "APPROVED_PLAN_PROCESSED_DONORS_ONLY"
    assert data["approval_ref"] == "canonical/decisions/CFA3-DEC-AGENTSCOPE-EMBABEL-PLAN-APPROVAL-2026-10-06.json"
    assert data["assessment_ref"] == "canonical/assessments/CFA3-AGENTSCOPE-EMBABEL-DONOR-REUSE-ASSESSMENT-2026-10-06.json"
    assert data["plan_ref"] == "docs/CFA3-AGENTSCOPE-EMBABEL-INTEGRATION-PLAN-2026-10-06.md"

def test_intake_is_non_authoritative_and_non_executing():
    data = load_delta()
    assert data["canonical_registry_materialized"] is False
    assert data["waiting_queue_only"] is True
    for value in data["boundaries"].values():
        assert value is False
