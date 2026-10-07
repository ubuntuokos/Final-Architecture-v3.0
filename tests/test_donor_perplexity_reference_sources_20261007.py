import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-PERPLEXITY-REFERENCE-SOURCES-2026-10-07.json"

EXPECTED = [
    "https://github.com/perplexityai",
    "https://github.com/helallao/perplexity-ai",
    "https://github.com/topics/perplexity-ai-api",
    "https://github.com/topics/perplexity-clone",
    "https://github.com/topics/perplexity?l=rust&o=desc&s=stars",
]


def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))


def test_exact_owner_authorized_source_set():
    d = load_delta()
    assert d["authorization"]["owner_command"] == "donornak"
    assert d["authorization"]["execution_command"] == "végezd el a donor felvételt"
    assert d["authorization"]["explicit_user_approval"] is True
    assert d["submitted_urls"] == EXPECTED
    assert d["submitted_url_count"] == 5
    assert d["unique_source_count"] == 5
    assert d["new_source_count"] == 5
    assert len(d["canonical_identities"]) == 5

    keys = [x["normalized_key"] for x in d["canonical_identities"]]
    ids = [x["donor_id"] for x in d["canonical_identities"]]
    assert len(keys) == len(set(keys)) == 5
    assert len(ids) == len(set(ids)) == 5
    assert all(x["status"] == "ACCEPTED_REFERENCE" for x in d["canonical_identities"])


def test_five_level_lineage_is_analysis_only():
    d = load_delta()
    lineage = d["lineage_observations"]
    assert lineage["max_reference_depth_policy"] == 5
    assert lineage["analysis_depth_applied"] == 5
    assert lineage["child_auto_admission"] is False
    assert lineage["representative_reference_chains"]
    for chain in lineage["representative_reference_chains"]:
        assert chain["depth"] == 5
        assert len(chain["nodes"]) == 5


def test_restricted_bypass_patterns_are_not_admitted():
    d = load_delta()
    observations = " ".join(d["lineage_observations"]["restricted_pattern_observations"]).lower()
    assert "not admitted" in observations or "excluded" in observations
    assert "query-limit bypass" in observations
    assert "cookie/session extraction" in observations
    assert "impersonation" in observations


def test_metadata_only_boundaries():
    d = load_delta()
    assert d["batch_finalizer_pr"] == 727
    assert all(value is False for value in d["boundaries"].values())
