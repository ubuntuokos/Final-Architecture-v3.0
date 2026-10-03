"""Owner-marked HiDream-ai GitHub organization donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-HIDREAM-AI-ORG-2026-10-03.json"

KEY = "github:hidream-ai"
URL = "https://github.com/HiDream-ai"
DONOR_ID = "FA3-DONOR-HIDREAM-AI-ORG-001"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class HiDreamAiOrgDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_fixed_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1425)
        self.assertEqual(self.delta["proposed_entry_count"], 1426)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_hidream_org_is_reference_only(self):
        row = self.by_key[KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["locator"], URL)
        self.assertEqual(row["source"]["kind"], "GITHUB_ORGANIZATION")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["license"]["status"], "COLLECTION_INDEX")
        self.assertIn("DISCOVERY_INDEX", row["donor_modes"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_children_models_and_datasets_are_not_recursively_admitted(self):
        self.assertEqual(self.delta["source_count"], 1)
        self.assertEqual(self.delta["observed_child_repository_count"], 27)
        self.assertFalse(self.delta["boundaries"]["child_repository_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["child_model_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["child_dataset_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])

    def test_intake_has_no_runtime_or_capability_effect(self):
        self.assertFalse(self.delta["boundaries"]["runtime_change"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])
        self.assertFalse(self.delta["boundaries"]["authority_change"])
        self.assertFalse(self.delta["boundaries"]["capability_count_change"])

if __name__ == "__main__":
    unittest.main()
