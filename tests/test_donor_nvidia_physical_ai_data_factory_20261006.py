import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-NVIDIA-PHYSICAL-AI-DATA-FACTORY-2026-10-06.json"

def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))

def test_exact_owner_source_and_identity():
    data = load_delta()
    assert data["schema"] == "fa3.donor-intake-delta.v1"
    assert data["submitted_urls"] == ["https://github.com/NVIDIA/physical-ai-data-factory"]
    assert data["owner_donor_command"] == "donornak"
    assert data["unique_source_count"] == 1
    assert data["new_source_count"] == 1
    assert data["canonical_identities"] == [{
        "source": "https://github.com/NVIDIA/physical-ai-data-factory",
        "normalized_key": "github:nvidia/physical-ai-data-factory",
        "donor_id": "FA3-DONOR-NVIDIA-PHYSICAL-AI-DATA-FACTORY-001",
        "kind": "GITHUB",
        "status": "ACCEPTED_REFERENCE",
        "mode": "PHYSICAL_AI_SYNTHETIC_DATA_WORKFLOW_ORCHESTRATION_SIMULATION_LABELING_VALIDATION_REFERENCE",
        "observed_revision": "e4c663cbbdcf159ad952751274c883c81d3ab4be",
        "license_observation": "ROOT_REPOSITORY_DECLARES_APACHE-2.0_CODE_AND_CC-BY-4.0_DOCUMENTATION_SKILLS",
    }]

def test_non_authoritative_staged_intake():
    data = load_delta()
    assert data["parent_entry_count"] == 1792
    assert data["proposed_entry_count"] == 1793
    assert data["canonical_registry_materialized"] is False
    assert data["waiting_queue_only"] is True
    assert data["capability_baseline"] == 175
    assert data["capability_delta"] == 0
    assert data["authority_delta"] == 0
    assert data["usage_edges_created"] == 0
    for value in data["boundaries"].values():
        assert value is False
