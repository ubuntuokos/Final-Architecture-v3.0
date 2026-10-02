"""Owner-marked Paperclip donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-PAPERCLIP-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

SOURCE_KEY = "github:paperclipai/paperclip"
DONOR_ID = "FA3-DONOR-PAPERCLIPAI-PAPERCLIP-001"
OBSERVED_HEAD = "144083fd481464f4a328f0d184a82263de63228d"
PRIOR_HEAD = "b54b2dc35c1f41d367ff4d94615ebfd38bbbdad0"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)


class PaperclipDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_delta(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 1355)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1354)
        self.assertEqual(self.delta["proposed_entry_count"], 1355)
        self.assertEqual(self.delta["source_count"], 1)
        self.assertEqual(self.delta["unique_source_key_count"], 1)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_paperclip_source_is_owner_marked_reference(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["kind"], "GITHUB_REPOSITORY")
        self.assertEqual(row["source"]["locator"], "https://github.com/paperclipai/paperclip")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
        self.assertFalse(row["submission_review"]["second_registry_approval_required"])
        self.assertTrue(row["discoverable_for_planning"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_license_and_analysis_provenance(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["license"]["declared"], "MIT")
        self.assertEqual(row["source_snapshot"]["commit"], OBSERVED_HEAD)
        self.assertEqual(row["source_snapshot"]["prior_fa3_analysis_commit"], PRIOR_HEAD)
        self.assertFalse(row["selection_scope"]["runtime_adoption"])
        self.assertFalse(row["selection_scope"]["control_plane_adoption"])
        self.assertFalse(row["selection_scope"]["code_copy"])

    def test_no_same_intake_usage_edge_or_runtime_admission(self):
        serialized = json.dumps(self.links, sort_keys=True)
        self.assertNotIn(DONOR_ID, serialized)
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])
        self.assertTrue(all(value is False for value in self.delta["boundaries"].values()))


if __name__ == "__main__":
    unittest.main()
