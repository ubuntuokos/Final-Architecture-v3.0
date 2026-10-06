import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-OPTISCALER-NEURAL-RENDERING-2026-10-06.json"

EXPECTED = [
    "https://github.com/optiscaler/OptiScaler",
    "https://github.com/optiscaler",
    "https://github.com/topics/framegeneration?l=c%23",
    "https://github.com/ind4skylivey",
    "https://github.com/wilsjo2/OptiScaler-DLSSNR-PreSR-Multipass",
    "https://github.com/Dagherbou",
]

def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))

def test_exact_owner_authorized_source_set():
    d = load_delta()
    assert d["authorization"]["owner_command"] == "donornak"
    assert d["authorization"]["explicit_user_approval"] is True
    assert d["submitted_urls"] == EXPECTED
    assert d["unique_source_count"] == 6
    assert d["new_source_count"] == 6
    assert len(d["canonical_identities"]) == 6
    keys = [x["normalized_key"] for x in d["canonical_identities"]]
    assert len(keys) == len(set(keys)) == 6
    assert all(x["status"] == "ACCEPTED_REFERENCE" for x in d["canonical_identities"])

def test_metadata_only_boundaries():
    d = load_delta()
    assert d["batch_finalizer_pr"] == 727
    assert d["lineage_observations"]["max_reference_depth_policy"] == 5
    assert d["lineage_observations"]["child_auto_admission"] is False
    assert all(value is False for value in d["boundaries"].values())
