import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-MICROSOFT-CHAT-COPILOT-2026-10-07.json"
EXPECTED = ["https://github.com/microsoft/chat-copilot"]


def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))


def test_exact_owner_authorized_source_identity():
    d = load_delta()
    assert d["authorization"]["owner_command"] == "donornak"
    assert d["authorization"]["exact_owner_message_marker"] == "a linket donornak"
    assert d["authorization"]["explicit_user_approval"] is True
    assert d["submitted_urls"] == EXPECTED
    assert d["submitted_url_count"] == 1
    assert d["unique_source_count"] == 1
    assert d["new_source_count"] == 1
    assert len(d["canonical_identities"]) == 1

    row = d["canonical_identities"][0]
    assert row["normalized_key"] == "github:microsoft/chat-copilot"
    assert row["donor_id"] == "FA3-DONOR-MICROSOFT-CHAT-COPILOT-001"
    assert row["status"] == "ACCEPTED_REFERENCE"


def test_exact_upstream_archival_provenance():
    d = load_delta()
    review = d["canonical_identities"][0]["upstream_review"]
    assert review["default_branch"] == "main"
    assert review["reviewed_head"] == "23b27821baa11b2a1639070434628e5b151ce706"
    assert review["archived"] is True
    assert d["canonical_identities"][0]["license_observation"] == "MIT_DECLARED_AT_REVIEWED_UPSTREAM_HEAD"


def test_five_level_lineage_is_analysis_only():
    d = load_delta()
    lineage = d["lineage_observations"]
    assert lineage["max_reference_depth_policy"] == 5
    assert lineage["analysis_depth_applied"] == 5
    assert lineage["child_auto_admission"] is False
    assert len(lineage["representative_reference_chains"]) == 5
    for chain in lineage["representative_reference_chains"]:
        assert chain["depth"] == 5
        assert len(chain["nodes"]) == 5


def test_metadata_only_boundaries_and_batch_target():
    d = load_delta()
    assert d["parent_entry_count"] == 1792
    assert d["batch_finalizer_pr"] == 727
    assert all(value is False for value in d["boundaries"].values())
