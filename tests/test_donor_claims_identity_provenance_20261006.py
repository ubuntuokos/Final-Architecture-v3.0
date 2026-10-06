import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-CLAIMS-IDENTITY-PROVENANCE-2026-10-06.json"

EXPECTED = [
    "https://github.com/claimed-framework",
    "https://github.com/topics/claims?l=html&o=desc&s=updated",
    "https://github.com/topics/file-claim",
    "https://github.com/thunlp/CLAIM",
    "https://github.com/marketplace/actions/actions-custom-oidc-claim",
    "https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens/",
    "https://github.com/gitcoinco/claim-tool",
    "https://github.com/decentralized-identity/claim-format-registry",
    "https://github.com/decentralized-identity/claims-credentials",
    "https://github.com/netlify/deploy-and-claim"
]

def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))

def test_exact_owner_authorized_source_set():
    d = load_delta()
    assert d["authorization"]["owner_command"] == "donornak"
    assert d["authorization"]["explicit_user_approval"] is True
    assert d["submitted_urls"] == EXPECTED
    assert d["submitted_url_count"] == 10
    assert d["unique_source_count"] == 10
    assert d["new_source_count"] == 10
    assert len(d["canonical_identities"]) == 10
    keys = [x["normalized_key"] for x in d["canonical_identities"]]
    ids = [x["donor_id"] for x in d["canonical_identities"]]
    assert len(keys) == len(set(keys)) == 10
    assert len(ids) == len(set(ids)) == 10
    assert all(x["status"] == "ACCEPTED_REFERENCE" for x in d["canonical_identities"])

def test_metadata_only_boundaries():
    d = load_delta()
    assert d["batch_finalizer_pr"] == 727
    assert d["lineage_observations"]["max_reference_depth_policy"] == 5
    assert d["lineage_observations"]["child_auto_admission"] is False
    assert all(value is False for value in d["boundaries"].values())
