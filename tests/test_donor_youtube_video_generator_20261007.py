"""CFA3 donor intake regression: MohamedElaassal/youtubeVideoGenerator."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-MOHAMEDELAASSAL-YOUTUBE-VIDEO-GENERATOR-2026-10-07.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

KEY = "github:mohamedelaassal/youtubevideogenerator"
DONOR_ID = "FA3-DONOR-MOHAMEDELAASSAL-YOUTUBE-VIDEO-GENERATOR-001"
URL = "https://github.com/MohamedElaassal/youtubeVideoGenerator"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class YoutubeVideoGeneratorDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1920)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1919)
        self.assertEqual(self.delta["proposed_entry_count"], 1920)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edge_delta"], 0)

    def test_exact_source_is_reference_only(self):
        row = self.by_key[KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["locator"], URL)
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
        self.assertEqual(row["license"]["declared"], "MIT")
        self.assertTrue(all(row[flag] is False for flag in FLAGS))
        self.assertTrue(row["discoverable_for_planning"])

    def test_five_level_lineage_is_recorded(self):
        lineage = self.delta["five_level_lineage"]
        self.assertEqual(lineage["max_reference_depth_policy"], 5)
        self.assertEqual(lineage["analysis_depth_applied"], 5)
        self.assertFalse(lineage["child_auto_admission"])
        chain = lineage["deterministic_dependency_chain"]
        self.assertEqual([x["level"] for x in chain], ["L0","L1","L2","L3","L4","L5"])

    def test_no_usage_edge_or_runtime_admission(self):
        self.assertNotIn(DONOR_ID, json.dumps(self.links, sort_keys=True))
        self.assertTrue(all(value is False for value in self.delta["boundaries"].values()))

if __name__ == "__main__":
    unittest.main()
