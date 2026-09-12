import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "canonical/conversation-reconciliation-enforcement.json").read_text())


def load(path: Path):
    return json.loads(path.read_text())


def test_recovered_mandatory_records_exist():
    for ident in CFG["required_profiles"]:
        assert (ROOT / "canonical/profiles" / f"{ident}.json").is_file(), ident
    for ident in CFG["required_providers"]:
        assert (ROOT / "canonical/providers" / f"{ident}.json").is_file(), ident
    for ident in CFG.get("required_contracts", []):
        assert (ROOT / "canonical/contracts" / f"{ident}.json").is_file(), ident
    for ident in CFG.get("required_registries", []):
        assert (ROOT / "canonical/registries" / f"{ident}.json").is_file(), ident


def test_recovered_records_preserve_143_and_zero_authority_delta():
    recovered_profiles = [
        "FA3-STORY-001", "FA3-CONTEXT-MEMORY-SKILL-PROJECTION-001",
        "FA3-RHYTHM-GENERATION-001", "FA3-OPS-AUTO-001", "FA3-LUT-COLOR-001",
        "FA3-DCC-RT3D-001", "FA3-ANIMATION-PRODUCTION-001",
    ]
    recovered_providers = [
        "FA3-PROVIDER-OPENVIKING-001", "FA3-PROVIDER-DRUM-GPT-001",
        "FA3-PROVIDER-XYOPS-001", "FA3-PROVIDER-XYSAT-001", "FA3-PROVIDER-UNREAL-ENGINE-001",
    ]
    for ident in recovered_profiles:
        rec = load(ROOT / "canonical/profiles" / f"{ident}.json")
        assert rec["capability_count"] == 143, ident
        assert rec["new_capability"] is False, ident
        assert rec["new_architectural_authority"] is False, ident
        assert rec["requirement"] == "MUST", ident
    for ident in recovered_providers:
        rec = load(ROOT / "canonical/providers" / f"{ident}.json")
        assert rec["capability_count"] == 143, ident
        assert rec["new_capability"] is False, ident
        assert rec["new_architectural_authority"] is False, ident
        assert rec["architectural_authority"] is False, ident


def test_hardware_portability_no_static_host_pins():
    for ident in ["FA3-DCC-RT3D-001", "FA3-ANIMATION-PRODUCTION-001", "FA3-OPS-AUTO-001"]:
        text = (ROOT / "canonical/profiles" / f"{ident}.json").read_text()
        for forbidden in ["RTX 3090", "RTX3090", "A1000", "T7910", "cuda:0", "GPU 0"]:
            assert forbidden not in text, (ident, forbidden)


def test_recovered_cross_profile_links():
    story = load(ROOT / "canonical/profiles/FA3-STORY-001.json")
    animation = load(ROOT / "canonical/profiles/FA3-ANIMATION-PRODUCTION-001.json")
    knowledge = load(ROOT / "canonical/profiles/FA3-KNOWLEDGE-001.json")
    music = load(ROOT / "canonical/profiles/FA3-MUSIC-001.json")
    assert story["canonical_interchange"]["fountain"].startswith("REQUIRED")
    assert "FA3-STORY-001" in animation["dependencies"]
    assert "FA3-DCC-RT3D-001" in animation["dependencies"]
    assert "FA3-CONTEXT-MEMORY-SKILL-PROJECTION-001" in knowledge["subprofiles"]
    assert "FA3-RHYTHM-GENERATION-001" in music["subprofiles"]
