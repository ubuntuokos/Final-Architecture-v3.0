"""Owner-marked 2D/3D character-animation donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-CHARACTER-ANIMATION-2D3D-2026-10-02.json"

EXPECTED_KEYS = {
    "github:tahoma2d/tahoma2d",
    "github:inochi2d/inochi2d",
    "github:inochi2d/inochi-creator",
    "github:mangolion/stretchystudio",
    "github:shitagaki-lab/see-through",
    "github:rive-app/rive-runtime",
    "github:guillaumeblanc/ozz-animation",
    "github:nfrechette/acl",
    "github:o3de/o3de",
    "github:vrm-c/vrm-specification",
    "github:vrm-c/univrm",
    "github:emilianavt/openseeface",
    "github:google-ai-edge/mediapipe",
    "github:open-mmlab/mmpose",
    "github:perfanalytics/pose2sim",
    "github:phongdaot/mocapanything",
    "github:zzysteve/sata",
    "github:facebookresearch/animateddrawings",
    "github:ubisoft/ubisoft-laforge-zeroeggs",
    "github:zju3dv/easymocap",
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class CharacterAnimationDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_fixed_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1333)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1317)
        self.assertEqual(self.delta["proposed_entry_count"], 1333)
        self.assertEqual(self.delta["new_record_count"], 16)
        self.assertEqual(self.delta["matched_existing_count"], 4)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_all_twenty_approved_sources_are_registered_reference_only(self):
        self.assertEqual(set(self.delta["sources"][i]["normalized_key"] for i in range(20)), EXPECTED_KEYS)
        for key in EXPECTED_KEYS:
            row = self.by_key[key]
            self.assertEqual(row["status"], "ACCEPTED_REFERENCE", key)
            self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER", key)
            self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY", key)
            self.assertFalse(row["submission_review"]["second_registry_approval_required"], key)
            self.assertTrue(row["discoverable_for_planning"], key)
            self.assertTrue(all(row[flag] is False for flag in FLAGS), key)

    def test_existing_ids_are_preserved(self):
        self.assertEqual(self.by_key["github:mangolion/stretchystudio"]["donor_id"], "FA3-DONOR-STRETCHY-STUDIO-001")
        self.assertEqual(self.by_key["github:guillaumeblanc/ozz-animation"]["donor_id"], "FA3-DONOR-OZZ-ANIMATION-001")
        self.assertEqual(self.by_key["github:nfrechette/acl"]["donor_id"], "FA3-DONOR-ANIMATION-COMPRESSION-LIBRARY-ACL-001")
        osf = self.by_key["github:emilianavt/openseeface"]
        self.assertEqual(osf["donor_id"], "FA3-DONOR-OPENSEEFACE-001")
        self.assertIn("project:openseeface", osf["legacy_source_keys"])
        self.assertNotIn("project:openseeface", self.by_key)

    def test_restricted_sources_remain_reference_only(self):
        zeroeggs = self.by_key["github:ubisoft/ubisoft-laforge-zeroeggs"]
        easymocap = self.by_key["github:zju3dv/easymocap"]
        vrm_spec = self.by_key["github:vrm-c/vrm-specification"]
        animated = self.by_key["github:facebookresearch/animateddrawings"]
        self.assertIn("REFERENCE_ONLY", zeroeggs["code_reuse_policy"])
        self.assertIn("REFERENCE_ONLY", easymocap["code_reuse_policy"])
        self.assertIn("REFERENCE_ONLY", vrm_spec["code_reuse_policy"])
        self.assertIn("REFERENCE_ONLY", animated["code_reuse_policy"])
        self.assertEqual(zeroeggs["license"]["declared"], "CC-BY-NC-ND-4.0")
        self.assertEqual(easymocap["license"]["declared"], "Project Registration License v1.0")

    def test_delta_creates_no_runtime_or_usage_authority(self):
        self.assertEqual(self.delta["source_count"], 20)
        self.assertEqual(self.delta["unique_source_key_count"], 20)
        for value in self.delta["boundaries"].values():
            self.assertFalse(value)

if __name__ == "__main__":
    unittest.main()
