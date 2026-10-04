import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical" / "FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical" / "deltas" / "FA3-DONOR-TRIPO-UNITY-DCC-POSE-SOURCES-2026-10-04.json"
PORTABILITY = ROOT / "canonical" / "assessments" / "FA3-DONOR-TRIPO-CUDA-PORTABILITY-ASSESSMENT-2026-10-04.json"

KEYS = {
    "github:vast-ai-research/tripo-3d-for-blender",
    "github:topics/tripo3d",
    "github:m4rio/trellis-tripo-3d",
    "github:topics/tripo",
    "github:tianyilt/fastapi-triposr",
    "github:vast-ai-research",
    "github:topics/unity-3d-game",
    "github:topics/unity-3d",
    "github:topics/unity3d-game",
    "github:topics/unity-3d-urp",
    "github:topics/unity3d",
    "github:topics/unity3d-games",
    "github:topics/unity-framework",
    "github:topics/unity",
    "github:topics/unity3d-script",
    "github:topics/unity-example",
    "github:topics/zbrush-pc",
    "github:zbrush-tool",
    "github:maxon-computer/zbrush-python-api-examples",
    "github:topics/hard-surface-modeling",
    "github:topics/3d-asset-management",
    "github:topics/character-design",
    "github:packtpublishing/zbrush-cookbook",
    "github:maxon-computer",
    "github:topics/cinema-4d",
    "github:topics/c4d",
    "github:topics/cinema-4d-plugin",
    "github:topics/cinema-4d-free",
    "github:topics/c4d-plugin",
    "github:topics/poser-latest-version",
    "github:pnm4sfix/poser",
    "github:sevdeawesome/poser",
    "github:topics/pose-estimation",
    "github:pnm4sfix",
    "github:topics/pose-tracking",
    "github:flack",
}

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_batch_cardinality_and_invariants():
    registry = load(REGISTRY)
    delta = load(DELTA)
    assert len(registry["entries"]) == 1463
    assert registry["backfill"]["entry_count"] == 1463
    assert delta["parent_entry_count"] == 1427
    assert delta["resulting_entry_count"] == 1463
    assert delta["submitted_url_count"] == 48
    assert delta["unique_submitted_url_count"] == 46
    assert delta["canonical_identity_count"] == 36
    assert delta["new_registry_entries"] == 36
    assert delta["capability_baseline"] == 175
    assert delta["capability_delta"] == 0
    assert delta["authority_delta"] == 0
    assert delta["usage_edges_created"] == 0

def test_all_sources_are_reference_only_and_fail_closed():
    registry = load(REGISTRY)
    by_key = {row["source"]["normalized_key"]: row for row in registry["entries"]}
    assert KEYS <= by_key.keys()
    for key in KEYS:
        row = by_key[key]
        assert row["status"] == "ACCEPTED_REFERENCE"
        assert row["discoverable_for_planning"] is True
        assert row["authority"] is False
        for flag in (
            "automatic_selection",
            "automatic_fetch",
            "automatic_install",
            "automatic_activation",
            "automatic_dependency",
            "automatic_code_import",
            "automatic_provider_admission",
            "automatic_model_selection",
        ):
            assert row[flag] is False

def test_filtered_topic_views_are_preserved():
    registry = load(REGISTRY)
    by_key = {row["source"]["normalized_key"]: row for row in registry["entries"]}
    assert len(by_key["github:topics/tripo"]["source"]["discovery_urls"]) == 3
    assert len(by_key["github:topics/unity-3d"]["source"]["discovery_urls"]) == 3
    assert len(by_key["github:topics/unity3d-games"]["source"]["discovery_urls"]) == 4
    assert len(by_key["github:topics/c4d"]["source"]["discovery_urls"]) == 2
    assert len(by_key["github:topics/cinema-4d-free"]["source"]["discovery_urls"]) == 3

def test_pose_name_collisions_are_disambiguated():
    registry = load(REGISTRY)
    by_key = {row["source"]["normalized_key"]: row for row in registry["entries"]}
    poser = by_key["github:pnm4sfix/poser"]
    alignment = by_key["github:sevdeawesome/poser"]
    assert any("not the Poser DCC" in note for note in poser["notes"])
    assert any("not a 3D Poser" in note for note in alignment["notes"])

def test_rights_sensitive_sources_remain_copy_blocked():
    registry = load(REGISTRY)
    by_key = {row["source"]["normalized_key"]: row for row in registry["entries"]}
    maxon = by_key["github:maxon-computer/zbrush-python-api-examples"]
    fastapi = by_key["github:tianyilt/fastapi-triposr"]
    alignment = by_key["github:sevdeawesome/poser"]
    assert maxon["license"]["declared"] == "CC-BY-ND-4.0"
    assert "NO_DERIVATIVE" in maxon["code_reuse_policy"]
    assert fastapi["license"]["status"] == "NO_ROOT_LICENSE_OBSERVED"
    assert alignment["license"]["status"] == "NO_ROOT_LICENSE_OBSERVED"


def test_cuda_portability_classification_and_shared_placement():
    registry = load(REGISTRY)
    assessment = load(PORTABILITY)
    by_key = {row["source"]["normalized_key"]: row for row in registry["entries"]}

    trellis = by_key["github:m4rio/trellis-tripo-3d"]["hardware_portability"]
    fastapi = by_key["github:tianyilt/fastapi-triposr"]["hardware_portability"]
    blender = by_key["github:vast-ai-research/tripo-3d-for-blender"]["hardware_portability"]
    poser = by_key["github:pnm4sfix/poser"]["hardware_portability"]

    assert trellis["strongly_cuda_oriented"] is True
    assert trellis["shared_function_core"] == "FA3-GENERATIVE-MEDIA-MESH-001"
    assert trellis["target_summary"]["AMD_ROCM"].startswith("UNAVAILABLE")
    assert trellis["target_summary"]["INTEL_GPU"].startswith("UNAVAILABLE")
    assert fastapi["strongly_cuda_oriented"] is True
    assert fastapi["target_summary"]["AMD_ROCM"].startswith("FUNCTIONALLY_REDUCED")
    assert fastapi["target_summary"]["INTEL_GPU"].startswith("FUNCTIONALLY_REDUCED")
    assert blender["strongly_cuda_oriented"] is False
    assert poser["strongly_cuda_oriented"] is False

    assert assessment["policy_id"] == "FA3-CUDA-PORTABILITY-SHARED-FUNCTION-POLICY-001"
    assert assessment["shared_placement"]["functional_core"] == "SHARED_LAYER_ONLY"
    assert assessment["pending_reference_boundary"]["cross_vendor_donor_pr"] == 699
    assert assessment["pending_reference_boundary"]["consumed"] is False
    assert assessment["usage_edges_created"] == 0
    assert assessment["runtime_admission"] is False
