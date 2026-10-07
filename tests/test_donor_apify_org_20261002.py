"""Exact owner-marked Apify organization donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-APIFY-ORG-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

DONOR_ID = "FA3-DONOR-APIFY-ORG-001"
KEY = "github:apify"
URL = "https://github.com/apify"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class ApifyOrganizationDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1317)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1316)
        self.assertEqual(self.delta["proposed_entry_count"], 1317)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_apify_org_is_reference_only_discovery_index(self):
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
        self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_delta_blocks_automatic_child_or_cloud_admission(self):
        self.assertEqual(self.delta["unique_source_key_count"], 1)
        self.assertEqual(self.delta["sources"][0]["normalized_key"], KEY)
        boundaries = self.delta["boundaries"]
        for field in (
            "child_repository_auto_registration", "automatic_fetch", "automatic_install",
            "automatic_activation", "automatic_code_import", "automatic_dependency",
            "automatic_provider_admission", "automatic_model_selection",
            "apify_cloud_activation", "actor_store_admission", "usage_edge_created",
        ):
            self.assertFalse(boundaries[field])

    def test_org_discovery_record_has_no_usage_edge(self):
        self.assertNotIn(DONOR_ID, json.dumps(self.links, sort_keys=True))

if __name__ == "__main__":
    unittest.main()
