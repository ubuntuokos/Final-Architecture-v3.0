"""Exact owner-marked browser source discovery donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-BROWSER-SOURCE-INDEXES-2026-10-02.json"

EXPECTED = {
    "github:mozilla": ("FA3-DONOR-MOZILLA-ORG-001", "https://github.com/mozilla", "GITHUB_ORGANIZATION"),
    "github:topics/firefox-based": ("FA3-DONOR-FIREFOX-BASED-TOPIC-001", "https://github.com/topics/firefox-based", "GITHUB_TOPIC"),
    "github:googlechrome": ("FA3-DONOR-GOOGLECHROME-ORG-001", "https://github.com/googlechrome", "GITHUB_ORGANIZATION"),
    "github:operasoftware": ("FA3-DONOR-OPERASOFTWARE-ORG-001", "https://github.com/operasoftware", "GITHUB_ORGANIZATION"),
    "github:topics/opera?o=asc&s=stars": ("FA3-DONOR-OPERA-STARS-ASC-TOPIC-001", "https://github.com/topics/opera?o=asc&s=stars", "GITHUB_TOPIC"),
    "github:topics/opera?l=c%2b%2b&o=asc&s=forks": ("FA3-DONOR-OPERA-CPP-FORKS-ASC-TOPIC-001", "https://github.com/topics/opera?l=c%2B%2B&o=asc&s=forks", "GITHUB_TOPIC"),
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class BrowserSourceIndexDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.entries), 1316)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["previous_registry_count"], 1310)
        self.assertEqual(self.delta["expected_registry_count"], 1316)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertFalse(self.delta["authority"])

    def test_all_exact_owner_marked_urls_are_reference_only(self):
        self.assertEqual(set(EXPECTED), {x["normalized_source_key"] for x in self.delta["sources"]})
        for key, (donor_id, url, kind) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["source"]["locator"], url)
                self.assertEqual(row["source"]["kind"], kind)
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
                self.assertFalse(row["submission_review"]["second_registry_approval_required"])
                self.assertIn("DISCOVERY_INDEX", row["donor_modes"])
                self.assertEqual(row["license"], {"declared": "NOT_APPLICABLE", "status": "COLLECTION_INDEX"})
                self.assertTrue(all(row[flag] is False for flag in FLAGS))
                self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_filtered_opera_views_are_distinct(self):
        low_star = self.by_key["github:topics/opera?o=asc&s=stars"]
        cpp = self.by_key["github:topics/opera?l=c%2b%2b&o=asc&s=forks"]
        self.assertEqual(low_star["discovery_filter"]["sort"], "stars")
        self.assertEqual(low_star["discovery_filter"]["order"], "asc")
        self.assertEqual(cpp["discovery_filter"]["language"], "c++")
        self.assertEqual(cpp["discovery_filter"]["sort"], "forks")
        self.assertEqual(cpp["discovery_filter"]["order"], "asc")

if __name__ == "__main__":
    unittest.main()
