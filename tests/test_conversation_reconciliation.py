import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "canonical/conversation-reconciliation-enforcement.json").read_text())
PROFILES = ROOT / "canonical/profiles"
PROVIDERS = ROOT / "canonical/providers"

def load(path):
    return json.loads(path.read_text())

def test_required_records_materialized():
    for ident in CFG["required_profiles"]:
        assert (PROFILES / f"{ident}.json").is_file(), ident
    for ident in CFG["required_providers"]:
        assert (PROVIDERS / f"{ident}.json").is_file(), ident

def test_capability_count_and_no_new_authority():
    for ident in CFG["required_profiles"]:
        rec = load(PROFILES / f"{ident}.json")
        assert rec.get("capability_count") == 143, ident
        assert rec.get("new_architectural_authority") is False, ident
        assert rec.get("new_capability") is False, ident
    for ident in CFG["required_providers"]:
        rec = load(PROVIDERS / f"{ident}.json")
        assert rec.get("capability_count") == 143, ident
        assert rec.get("architectural_authority") is False, ident
        assert rec.get("new_architectural_authority") is False, ident
        assert rec.get("new_capability") is False, ident

def test_geometry_closure():
    root = load(PROFILES / "FA3-3D-GEOM-001.json")
    child = load(PROFILES / "FA3-MESH-GEN-001.json")
    assert root["authority_role"] == "SOLE_CANONICAL_GEOMETRY_SEMANTIC_AUTHORITY"
    assert child["relationship"] == {"type": "SUBPROFILE-OF", "parent": "FA3-3D-GEOM-001"}

def test_hrb_cuda_authority_separation_and_evidence_scope():
    hrb = load(PROFILES / "FA3-HOST-RESOURCE-BROKER-001.json")
    cuda = load(PROFILES / "FA3-CUDA-PY-001.json")
    ev = load(ROOT / "evidence/reference/hrb-cuda-current-host-2026-08-28.json")
    assert set(hrb["authority_scope"]) == {"admission", "placement", "reservation", "lease"}
    assert cuda["provider_role"].endswith("NOT_AUTHORITY")
    assert ev["global_promotion_claim"] is False

def test_conversation_reconciliation_decision_is_non_semantic():
    d = load(ROOT / "canonical/decisions/FA3-DEC-CONVERSATION-RECONCILIATION-2026-08-30.json")
    assert d["new_capabilities"] == 0
    assert d["new_architectural_authorities"] == 0
    assert d["capability_count_after"] == 143
