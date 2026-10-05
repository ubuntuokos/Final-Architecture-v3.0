import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-TILE-AI-CORE-2026-10-05.json"


def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))


def test_tile_ai_core_delta_identity_and_counts():
    data = load_delta()
    assert data["schema"] == "fa3.donor-intake-delta.v1"
    assert data["delta_id"] == "CFA3-DONOR-TILE-AI-CORE-2026-10-05"
    assert data["parent_entry_count"] == 1548
    assert data["submitted_url_count"] == 3
    assert data["unique_source_count"] == 3
    assert data["new_source_count"] == 3
    assert data["proposed_entry_count"] == 1551
    assert data["capability_baseline"] == 175
    assert data["capability_delta"] == 0
    assert data["authority_delta"] == 0
    assert data["usage_edges_created"] == 0


def test_tile_ai_core_exact_sources_and_normalized_keys():
    data = load_delta()
    assert data["submitted_urls"] == [
        "https://github.com/tile-ai/tilelang",
        "https://github.com/tile-ai/TileRT",
        "https://github.com/tile-ai/TileOPs",
    ]
    identities = {item["donor_id"]: item for item in data["canonical_identities"]}
    assert identities["FA3-DONOR-TILE-AI-TILELANG-001"]["normalized_key"] == "github:tile-ai/tilelang"
    assert identities["FA3-DONOR-TILE-AI-TILERT-001"]["normalized_key"] == "github:tile-ai/tilert"
    assert identities["FA3-DONOR-TILE-AI-TILEOPS-001"]["normalized_key"] == "github:tile-ai/tileops"
    assert {item["status"] for item in identities.values()} == {"ACCEPTED_REFERENCE"}


def test_tile_ai_core_is_queue_only_and_non_authoritative():
    data = load_delta()
    assert data["canonical_registry_materialized"] is False
    assert data["waiting_queue_only"] is True
    boundaries = data["boundaries"]
    for key in (
        "automatic_fetch",
        "automatic_install",
        "automatic_activation",
        "automatic_code_import",
        "automatic_dependency",
        "automatic_provider_admission",
        "automatic_model_selection",
        "usage_edge_created",
        "capability_count_change",
        "authority_change",
        "runtime_change",
        "current_host_pass_claimed",
        "canonical_planning_visibility",
    ):
        assert boundaries[key] is False
