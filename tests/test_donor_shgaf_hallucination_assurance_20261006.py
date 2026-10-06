import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-SHGAF-HALLUCINATION-ASSURANCE-2026-10-06.json"

EXPECTED_KEYS = {
    "github:topics/ai-hallucination",
    "github:topics/hallucination-detection",
    "github:topics/anti-hallucination",
    "github:topics/hallucination-reduced-ai",
    "github:topics/hallucination",
    "github:topics/hallucination-prevention",
    "github:topics/hallucination-research",
    "github:topics/hallucination-benchmark",
    "github:topics/no-hallucination",
    "github:topics/anti-hallucination-",
    "github:topics/prompt-injection",
    "github:microsoft/conli_hallucination",
    "github-file:salvatorera/artificial-intelligence-articles/articles/llm_hallucinations.md",
    "github:salvatorera/artificial-intelligence-articles",
    "https://arxiv.org/html/2601.19106v1",
    "github:idiap/hallucination-detection",
    "github:thedataletter/ai-hallucination-detector",
    "https://typesafe.ai/blog/introducing-system-one-models-and-jev",
}

def load_delta():
    return json.loads(DELTA.read_text(encoding="utf-8"))

def test_exact_submitted_and_normalized_source_counts():
    data = load_delta()
    assert data["schema"] == "fa3.donor-intake-delta.v1"
    assert data["submitted_url_count"] == 20
    assert len(data["submitted_urls"]) == 20
    assert data["canonical_identity_count"] == 18
    assert data["query_or_sort_view_alias_count"] == 2
    assert data["new_source_count"] == 18
    assert data["projected_entry_count_if_applied_alone"] == 1810
    assert data["projected_entry_count_with_agentscope_embabel_batch"] == 1824
    assert {x["normalized_key"] for x in data["canonical_identities"]} == EXPECTED_KEYS

def test_owner_approved_reference_only_boundary():
    data = load_delta()
    assert data["approval_mode"] == "OWNER_APPROVED_ANALYSIS_AND_SHGAF_PLAN"
    assert data["capability_baseline"] == 175
    assert data["capability_delta"] == 0
    assert data["authority_delta"] == 0
    assert data["usage_edges_created"] == 0
    assert data["canonical_registry_materialized"] is False
    assert data["waiting_queue_only"] is True
    for key, value in data["boundaries"].items():
        assert value is False, (key, value)

def test_existing_fact_verification_rule_is_not_recreated():
    data = load_delta()
    joined = "\n".join(data["requirements"])
    assert "already-existing CFA3 authoritative/deterministic fact-verification rule" in joined
    assert data["boundaries"]["new_fact_verification_rule_created"] is False
