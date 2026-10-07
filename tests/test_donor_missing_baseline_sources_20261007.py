import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-MISSING-BASELINE-SOURCES-2026-10-07.json"

EXPECTED = [
    "https://github.com/deepseek-ai",
    "https://github.com/topics/deepseek",
    "https://github.com/topics/deepseek-v3",
    "https://github.com/topics/deepseek-harness",
    "https://github.com/esengine",
    "https://github.com/topics/deepseek-tui",
    "https://deepseekcoder.github.io/",
    "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash",
    "https://github.com/dazeb/openclaw-deepseek-integration",
    "https://github.com/huggingface/open-r1",
    "https://github.com/doxdk/deepseek-desktop",
    "https://github.com/starryrbs/awesome-ai-tools",
    "https://github.com/topics/tileset-generator",
    "https://github.com/meetpateltech/ai-infinity",
    "https://github.com/tile-ai",
    "https://github.com/tesslio/spec-driven-development-tile",
    "https://github.com/topics/tilemap-editor",
    "https://atlas.design/",
    "https://github.com/TheOrcDev/videorc",
    "https://vivago.ai/agent/home",
]


def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))


def test_exact_owner_authorized_missing_source_set():
    d = load_delta()
    assert d["authorization"]["owner_command"] == "donornak"
    assert d["authorization"]["explicit_user_approval"] is True
    assert d["submitted_urls"] == EXPECTED
    assert d["submitted_url_count"] == 20
    assert d["unique_source_count"] == 20
    assert d["new_source_count"] == 20
    assert len(d["canonical_identities"]) == 20

    keys = [x["normalized_key"] for x in d["canonical_identities"]]
    ids = [x["donor_id"] for x in d["canonical_identities"]]
    assert len(keys) == len(set(keys)) == 20
    assert len(ids) == len(set(ids)) == 20
    assert all(x["status"] == "ACCEPTED_REFERENCE" for x in d["canonical_identities"])


def test_every_source_has_five_level_lineage_coverage():
    d = load_delta()
    lineage = d["lineage_observations"]
    assert lineage["max_reference_depth_policy"] == 5
    assert lineage["analysis_depth_applied"] == 5
    assert lineage["child_auto_admission"] is False

    chains = lineage["source_lineage_coverage"]
    assert len(chains) == 20
    assert {x["source"] for x in chains} == set(EXPECTED)
    for chain in chains:
        assert chain["depth"] == 5
        assert len(chain["nodes"]) == 5


def test_high_risk_reference_boundaries_are_fail_closed():
    d = load_delta()
    text = " ".join(d["lineage_observations"]["special_risk_observations"]).lower()
    assert "no longer maintained" in text
    assert "conflicting license" in text
    assert "agpl-3.0-only" in text
    assert "do not recursively admit" in text


def test_metadata_only_and_current_finalizer_binding():
    d = load_delta()
    assert d["status"] == "STAGED_PENDING_ROLLING_BATCH_APPEND"
    assert d["batch_finalizer_pr"] == 727
    assert d["serialization_scope"] == "SINGLE_WRITER_ROLLING_DONOR_FINALIZER"
    assert d["parent_entry_count"] == 1792
    assert d["parent_registry_blob_sha"] == "2bb6a74dd415b6374e4a6d5adce1bc9265229b63"
    assert all(value is False for value in d["boundaries"].values())


def test_capability_and_authority_invariants_are_explicit():
    d = load_delta()
    req = " ".join(d["requirements"])
    assert "175" in req
    assert "capability delta is 0" in req
    assert "architectural authority delta is 0" in req
    assert "FA3-AUTH-MODEL-ROUTER-001" in req
    assert "CPU-only" in req
