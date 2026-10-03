"""Owner-marked Maggi-Chen/Inspector donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-MAGGI-CHEN-INSPECTOR-2026-10-03.json"

SOURCE_KEY = "github:maggi-chen/inspector"
DONOR_ID = "FA3-DONOR-MAGGI-CHEN-INSPECTOR-001"
OBSERVED_HEAD = "2d813d96eb38adec9b8fb25388a3f4f1a2c63573"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)


class InspectorDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_delta(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 1422)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1421)
        self.assertEqual(self.delta["proposed_entry_count"], 1422)
        self.assertEqual(self.delta["source_count"], 1)
        self.assertEqual(self.delta["unique_source_key_count"], 1)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_inspector_source_is_owner_marked_reference(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["kind"], "GITHUB_REPOSITORY")
        self.assertEqual(row["source"]["locator"], "https://github.com/Maggi-Chen/Inspector")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
        self.assertFalse(row["submission_review"]["second_registry_approval_required"])
        self.assertTrue(row["discoverable_for_planning"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_license_snapshot_and_reference_only_scope(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["license"]["declared"], "MIT")
        self.assertEqual(row["source_snapshot"]["commit"], OBSERVED_HEAD)
        self.assertFalse(row["selection_scope"]["runtime_adoption"])
        self.assertFalse(row["selection_scope"]["code_copy"])
        self.assertIn("ARCHITECTURE_PATTERN", row["donor_modes"])
        self.assertIn("QUALITY_REFERENCE", row["donor_modes"])
        self.assertIn("TEST_PATTERN", row["donor_modes"])

    def test_no_fork_alias_or_same_intake_usage_edge(self):
        keys = {e["source"]["normalized_key"] for e in self.entries}
        self.assertNotIn("github:chonglab/inspector", keys)
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])
        self.assertFalse(self.delta["boundaries"]["runtime_admission"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])


if __name__ == "__main__":
    unittest.main()
