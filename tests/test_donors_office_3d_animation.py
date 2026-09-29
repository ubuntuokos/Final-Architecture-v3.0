"""Regression guard for the user-requested 2026-09-29 donor capture batch."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
EXPECTED = [
  'github:adrianhajdin',
  'github:apache/openoffice',
  'github:automate-animation/synctoon',
  'github:baotlake',
  'github:ctate',
  'github:danielswolf/rhubarb-lip-sync',
  'github:eferu/motiongenerator',
  'github:gooeyai',
  'github:hoangsonww/docuthinker-ai-app',
  'github:hzxie/awesome-3d-scene-generation',
  'github:libreoffice',
  'github:lightningpixel',
  'github:linuxserver',
  'github:lukerbs/pytoon',
  'github:mengmouxu/scenegen',
  'github:mwasifanwar/3d-scene-generator',
  'github:no6kiko/gorest-2d-animation-spritesheet-generator',
  'github:onlyoffice',
  'github:pantomatrix/pantomatrix',
  'github:pantor/ruckig',
  'github:pascalorg',
  'github:pointergeist/phc-mouse-movement-gen',
  'github:presenton',
  'github:raguilar011095/planet_heightmap_generation',
  'github:sairiteshdomakuntla/2d-generator',
  'github:softmaker-office',
  'github:tmelyralab/musetalk',
  'github:topics/2d-animation',
  'github:topics/3d',
  'github:topics/3d-design',
  'github:topics/3d-generation',
  'github:topics/3d-generation?o=asc&s=forks',
  'github:topics/3d-modeling-software',
  'github:topics/3d-resources',
  'github:topics/3d-scene-generation',
  'github:topics/3d-scene-generation?l=c%2b%2b',
  'github:topics/3d-style',
  'github:topics/3d-visualization',
  'github:topics/ai-3d?l=typescript',
  'github:topics/ai-animation',
  'github:topics/ai-animation-generator?l=typescript',
  'github:topics/ai-art-generator',
  'github:topics/ai-document',
  'github:topics/ai-document-editor',
  'github:topics/ai-document-processing',
  'github:topics/ai-documentation?l=python',
  'github:topics/ai-home-decor',
  'github:topics/ai-photo-generator',
  'github:topics/ai3d',
  'github:topics/animation-editor',
  'github:topics/animation-tool',
  'github:topics/architectural-design',
  'github:topics/document-manager?l=python&o=desc&s=stars',
  'github:topics/document-manager?o=desc&s=stars',
  'github:topics/eco-friendly-projects',
  'github:topics/floorplans',
  'github:topics/generative-motion',
  'github:topics/home-design?l=python',
  'github:topics/house-building',
  'github:topics/human-motion-generation',
  'github:topics/image-generation-ai?l=html',
  'github:topics/image-generation-tool',
  'github:topics/image-generator-desktop',
  'github:topics/image-to-3d',
  'github:topics/interior-design',
  'github:topics/interior-designer',
  'github:topics/interior-designing',
  'github:topics/kitchen-design',
  'github:topics/libreoffice-extension',
  'github:topics/libreoffice-server',
  'github:topics/lip-sync-animation',
  'github:topics/lip-sync?l=typescript',
  'github:topics/lipsync',
  'github:topics/lsystem-plant-generator?o=desc&s=updated',
  'github:topics/microsoft-office',
  'github:topics/microsoft-office?l=html',
  'github:topics/move-generator',
  'github:topics/office',
  'github:topics/office-suite',
  'github:topics/office365',
  'github:topics/poster-generator',
  'github:topics/scenario-generator',
  'github:topics/text-to-3d?l=typescript',
  'github:topics/text-to-image-generation',
  'github:topics/world-generator',
  'github:topics/wps',
  'github:topics/wps-office?l=c%23',
  'github:topics/wps-office?l=powershell',
  'github:yizhouzhao/genmotion'
]
AUTO = ('automatic_selection', 'automatic_fetch', 'automatic_install', 'automatic_activation',
        'automatic_dependency', 'automatic_code_import', 'automatic_provider_admission',
        'automatic_model_selection')

def test_donor_office_3d_animation_batch():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert registry["id"] == "FA3-DONOR-REFERENCE-REGISTRY-001"
    assert registry["capability_count"] == 175
    entries = registry["entries"]
    assert len(entries) == registry["backfill"]["entry_count"]
    by_key = {e["source"]["normalized_key"]: e for e in entries}
    assert len(by_key) == len(entries)
    assert len({e["donor_id"] for e in entries}) == len(entries)
    assert len(EXPECTED) == 89 and len(set(EXPECTED)) == 89
    for key in EXPECTED:
        assert key in by_key, key
        e = by_key[key]
        assert e["authority"] is False
        assert all(e[flag] is False for flag in AUTO)
        assert e["code_reuse_policy"] != "ADMITTED"
    assert by_key["github:danielswolf/rhubarb-lip-sync"]["donor_id"] == "FA3-DONOR-RHUBARB-LIP-SYNC-001"
