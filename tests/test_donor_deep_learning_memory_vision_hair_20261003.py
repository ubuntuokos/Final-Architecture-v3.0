import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-DEEP-LEARNING-MEMORY-VISION-HAIR-2026-10-03.json"

EXPECTED_IDS = [
  "FA3-DONOR-GITHUB-TOPIC-DEEP-LEARNING-PROJECTS-001",
  "FA3-DONOR-GITHUB-TOPIC-AI-DEEP-LEARNING-001",
  "FA3-DONOR-GITHUB-TOPIC-ANDREW-NG-DEEP-LEARNING-001",
  "FA3-DONOR-GITHUB-TOPIC-DEEP-LEARNING-THEORY-001",
  "FA3-DONOR-GITHUB-TOPIC-DEEP-LEARNING-TUTORIAL-001",
  "FA3-DONOR-GITHUB-TOPIC-MACHINE-LEARNING-PROJECTS-001",
  "FA3-DONOR-HTTPS-DEEPLEARNING-AI-PROFILE-001",
  "FA3-DONOR-GITHUB-TOPIC-AI-MEMORY-SYSTEM-001",
  "FA3-DONOR-GITHUB-TOPIC-AI-MEMORIES-001",
  "FA3-DONOR-GITHUB-TOPIC-AI-MEMORY-001",
  "FA3-DONOR-GITHUB-TOPIC-AI-MEMORY-SYSTEMS-001",
  "FA3-DONOR-GITHUB-TOPIC-MEMORY-ENGINE-001",
  "FA3-DONOR-GITHUB-TOPIC-LIP-SYNC-001",
  "FA3-DONOR-CL0UD-9-LIP-SYNC-VIDEO-GENERATOR-001",
  "FA3-DONOR-GITHUB-TOPIC-EYE-TRACKING-001",
  "FA3-DONOR-PYMOVEMENTS-PYMOVEMENTS-001",
  "FA3-DONOR-DEEPTI-96-EYE-MOVEMENT-DETECTION-001",
  "FA3-DONOR-MESHCAPADE-DIFFLOCKS-001",
  "FA3-DONOR-MESHCAPADE-ORG-001",
  "FA3-DONOR-GITHUB-TOPIC-HAIR-SEGMENTATION-001",
  "FA3-DONOR-FIGHTING-ZHANG-STRANDDESIGNER-001"
]

def test_deep_learning_memory_vision_hair_donor_intake():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    entries = registry["entries"]
    by_id = {row["donor_id"]: row for row in entries}

    assert registry["capability_count"] == 175
    # Later serialized donor intakes are append-only; this test owns only the\n    # #644 snapshot floor while the delta below remains fixed at 1405.\n    assert registry["backfill"]["entry_count"] == len(entries)\n    assert len(entries) >= 1405\n    assert delta["parent_entry_count"] == 1384
    assert delta["submitted_url_count"] == 23
    assert delta["unique_source_count"] == 21
    assert delta["resulting_entry_count"] == 1405
    assert delta["usage_edges_created"] == 0

    for donor_id in EXPECTED_IDS:
        row = by_id[donor_id]
        assert row["status"] == "ACCEPTED_REFERENCE"
        assert row["authority"] is False
        assert row["automatic_fetch"] is False
        assert row["automatic_install"] is False
        assert row["automatic_activation"] is False
        assert row["automatic_dependency"] is False
        assert row["automatic_code_import"] is False
        assert row["automatic_provider_admission"] is False
        assert row["automatic_model_selection"] is False

    memory = by_id["FA3-DONOR-GITHUB-TOPIC-AI-MEMORY-001"]
    assert len(memory["source"]["discovery_urls"]) == 2
    memory_system = by_id["FA3-DONOR-GITHUB-TOPIC-AI-MEMORY-SYSTEM-001"]
    assert len(memory_system["source"]["discovery_urls"]) == 2

    lip = by_id["FA3-DONOR-CL0UD-9-LIP-SYNC-VIDEO-GENERATOR-001"]
    assert lip["license"]["status"] == "REVIEW_REQUIRED"
    assert "BLOCKED" in lip["code_reuse_policy"]

    difflocks = by_id["FA3-DONOR-MESHCAPADE-DIFFLOCKS-001"]
    assert "REVIEW_REQUIRED" == difflocks["license"]["status"]

    strand = by_id["FA3-DONOR-FIGHTING-ZHANG-STRANDDESIGNER-001"]
    assert strand["license"]["status"] == "PENDING_SOURCE_RELEASE_AND_REVIEW"
