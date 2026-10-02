"""Exact owner-marked SenteLabsAI organization donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-SENTELABSAI-ORG-2026-10-03.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

DONOR_ID = "FA3-DONOR-SENTELABSAI-ORG-001"
KEY = "github:sentelabsai"
URL = "https://github.com/SenteLabsAI"
CHILD_KEYS = {
    "github:sentelabsai/openexecutive",
    "github:sentelabsai/extensible-mcp",
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class SenteLabsAIOrganizationDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1358)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1357)
        self.assertEqual(self.delta["proposed_entry_count"], 1358)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_sentelabsai_org_is_reference_only_discovery_index(self):
        row = self.by_key[KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["locator"], URL)
        self.assertEqual(row["source"]["kind"], "GITHUB_ORGANIZATION")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
        self.assertFalse(row["submission_review"]["second_registry_approval_required"])
        self.assertIn("DISCOVERY_INDEX", row["donor_modes"])
        self.assertEqual(row["license"], {"declared": "NOT_APPLICABLE", "status": "COLLECTION_INDEX"})
        self.assertTrue(row["discoverable_for_planning"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_child_repositories_are_not_recursively_registered(self):
        self.assertTrue(CHILD_KEYS.isdisjoint(self.by_key))
        self.assertFalse(self.delta["boundaries"]["child_repository_auto_registration"])
        self.assertTrue(all(not item["registered_by_this_intake"] for item in self.delta["observed_child_repositories"]))

    def test_no_usage_edge_created(self):
        self.assertNotIn(DONOR_ID, json.dumps(self.links, sort_keys=True))
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])

if __name__ == "__main__":
    unittest.main()
