"""Owner-marked Google Antigravity donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-GOOGLE-ANTIGRAVITY-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

EXPECTED = {
    "github:google-antigravity/antigravity-sdk-python": ("FA3-DONOR-GOOGLE-ANTIGRAVITY-SDK-PYTHON-001", "GITHUB_REPOSITORY"),
    "github:topics/antigravity-tools": ("FA3-DONOR-ANTIGRAVITY-TOOLS-TOPIC-001", "GITHUB_TOPIC"),
    "github:topics/antigravity": ("FA3-DONOR-ANTIGRAVITY-TOPIC-001", "GITHUB_TOPIC"),
    "github:topics/google-antigravity": ("FA3-DONOR-GOOGLE-ANTIGRAVITY-TOPIC-001", "GITHUB_TOPIC"),
    "github:google-antigravity": ("FA3-DONOR-GOOGLE-ANTIGRAVITY-ORG-001", "GITHUB_ORGANIZATION"),
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class GoogleAntigravityDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_delta(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1354)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1349)
        self.assertEqual(self.delta["proposed_entry_count"], 1354)
        self.assertEqual(self.delta["source_count"], 5)
        self.assertEqual(self.delta["unique_source_key_count"], 5)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_sources_are_reference_only(self):
        self.assertEqual(set(EXPECTED), {x["normalized_key"] for x in self.delta["sources"]})
        for key, (donor_id, kind) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["source"]["kind"], kind)
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
                self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
                self.assertFalse(row["submission_review"]["second_registry_approval_required"])
                self.assertTrue(row["discoverable_for_planning"])
                self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_sdk_license_and_index_boundaries(self):
        sdk = self.by_key["github:google-antigravity/antigravity-sdk-python"]
        self.assertEqual(sdk["license"]["declared"], "Apache-2.0")
        for key in (
            "github:topics/antigravity-tools",
            "github:topics/antigravity",
            "github:topics/google-antigravity",
            "github:google-antigravity",
        ):
            self.assertEqual(self.by_key[key]["license"]["status"], "COLLECTION_INDEX")

    def test_historical_intake_remains_reference_only_but_later_explicit_sdk_pattern_use_is_bounded(self):
        self.assertTrue(all(v is False for v in self.delta["boundaries"].values()))
        sdk_id = "FA3-DONOR-GOOGLE-ANTIGRAVITY-SDK-PYTHON-001"
        sdk_usage = [x for x in self.links.get("donor_usage_records", []) if x.get("donor_id") == sdk_id and x.get("status") != "REMOVED"]
        self.assertEqual(1, len(sdk_usage))
        row = sdk_usage[0]
        self.assertEqual("ARCHITECTURE_PATTERN", row["usage_kind"])
        self.assertFalse(row["code_imported"])
        self.assertFalse(row["runtime_dependency"])
        self.assertFalse(row["compiled_runtime_dependency"])
        self.assertFalse(row["provider_admission"])
        self.assertFalse(row["model_admission"])
        self.assertFalse(row["automatic_activation"])
        index_ids = {donor_id for key, (donor_id, _kind) in EXPECTED.items() if key != "github:google-antigravity/antigravity-sdk-python"}
        used_ids = {x.get("donor_id") for x in self.links.get("donor_usage_records", []) if x.get("status") != "REMOVED"}
        self.assertTrue(index_ids.isdisjoint(used_ids))

if __name__ == "__main__":
    unittest.main()
