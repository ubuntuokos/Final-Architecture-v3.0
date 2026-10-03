import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA=ROOT/"canonical/deltas/FA3-DONOR-DIGITAL-SALON-HAIR-2026-10-03.json"

EXPECTED={
"FA3-DONOR-DIGITAL-SALON-ORG-001",
"FA3-DONOR-ZHOUSHIWEI-PROFILE-001",
"FA3-DONOR-KEYUWU-CS-PROFILE-001",
"FA3-DONOR-TIGERWASH-PROFILE-001",
"FA3-DONOR-DIGITAL-SALON-PROJECT-001",
"FA3-DONOR-JHONVE-PROFILE-001",
"FA3-DONOR-ARXIV-RESEARCH-INDEX-001",
}

def test_digital_salon_hair_intake():
    registry=json.loads(REG.read_text())
    delta=json.loads(DELTA.read_text())
    rows={x["donor_id"]:x for x in registry["entries"]}
    assert EXPECTED <= set(rows)
    assert registry["backfill"]["entry_count"] == len(registry["entries"])
    assert len(registry["entries"]) >= 1428
    assert delta["parent_entry_count"] == 1421
    assert delta["new_source_count"] == 7
    assert delta["resulting_entry_count"] == 1428
    assert delta["usage_edges_created"] == 0
    assert delta["capability_baseline"] == 175
    for donor_id in EXPECTED:
        row=rows[donor_id]
        assert row["status"] == "ACCEPTED_REFERENCE"
        assert row["authority"] is False
        assert row["automatic_activation"] is False
        assert row["automatic_provider_admission"] is False
        assert row["automatic_model_selection"] is False
