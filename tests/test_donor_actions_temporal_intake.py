"""Owner-marked Actions/Temporal intake: exact source identity and deny-default checks."""
import json
import unittest
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
EXPECTED = {
    "github:actions/runner": ("FA3-DONOR-ACTIONS-RUNNER-001", "https://github.com/actions/runner", "GITHUB"),
    "github:actions": ("FA3-DONOR-ACTIONS-ORG-001", "https://github.com/actions", "GITHUB_ORGANIZATION"),
    "github:temporalio": ("FA3-DONOR-TEMPORALIO-ORG-001", "https://github.com/temporalio", "GITHUB_ORGANIZATION"),
    "github:temporal-community": ("FA3-DONOR-TEMPORAL-COMMUNITY-ORG-001", "https://github.com/temporal-community", "GITHUB_ORGANIZATION"),
    "github:temporal-sa": ("FA3-DONOR-TEMPORAL-SA-ORG-001", "https://github.com/temporal-sa", "GITHUB_ORGANIZATION"),
}
FLAGS = ("authority", "automatic_selection", "automatic_fetch", "automatic_install",
         "automatic_activation", "automatic_dependency", "automatic_code_import",
         "automatic_provider_admission", "automatic_model_selection")

class ActionsTemporalDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.records = {e["source"]["normalized_key"]: e for e in cls.registry["entries"]}

    def test_registry_count_derived_and_capability_fixed(self):
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.registry["entries"]))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(len(self.records), len(self.registry["entries"]))

    def test_exact_owner_sources_and_no_auto_admission(self):
        for key, (record_id, url, kind) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.records[key]
                self.assertEqual(row["donor_id"], record_id)
                self.assertEqual(row["source"]["locator"], url)
                self.assertEqual(row["source"]["kind"], kind)
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
                self.assertTrue(all(row[flag] is False for flag in FLAGS))
                if kind == "GITHUB_ORGANIZATION":
                    self.assertEqual(row["source"]["discovery_urls"], [url])

    def test_existing_adjacent_projects_remain_independent(self):
        self.assertEqual(self.records["github:actions/runner-images"]["donor_id"],
                         "FA3-DONOR-ACTIONS-RUNNER-IMAGES-001")
        self.assertEqual(self.records["github:temporalio/sdk-python"]["donor_id"],
                         "FA3-DONOR-TEMPORALIO-SDK-PYTHON-001")
        self.assertEqual(self.records["github:actions/runner-images"]["status"], "CANDIDATE")
        self.assertEqual(self.records["github:temporalio/sdk-python"]["status"], "CANDIDATE")

if __name__ == "__main__":
    unittest.main()
