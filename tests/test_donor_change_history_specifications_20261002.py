"""Owner-marked Change-History specification donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-CHANGE-HISTORY-SPECIFICATIONS-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

EXPECTED = {
    "https://slsa.dev/spec/v1.2/build-provenance":
        ("FA3-DONOR-SLSA-BUILD-PROVENANCE-001", "https://slsa.dev/spec/v1.2/build-provenance"),
    "https://in-toto.io/docs/specs/":
        ("FA3-DONOR-IN-TOTO-SPECIFICATIONS-001", "https://in-toto.io/docs/specs/"),
    "https://opentelemetry.io/docs/specs/semconv/general/events/":
        ("FA3-DONOR-OPENTELEMETRY-EVENT-CONVENTIONS-001", "https://opentelemetry.io/docs/specs/semconv/general/events/"),
    "https://openlineage.io/docs/spec/facets/job-facets/lineage/":
        ("FA3-DONOR-OPENLINEAGE-LINEAGE-FACET-001", "https://openlineage.io/docs/spec/facets/job-facets/lineage/"),
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class ChangeHistorySpecificationDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_intake_delta(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1344)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1340)
        self.assertEqual(self.delta["proposed_entry_count"], 1344)
        self.assertEqual(self.delta["source_count"], 4)
        self.assertEqual(self.delta["unique_source_key_count"], 4)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_sources_are_reference_only(self):
        self.assertEqual(set(EXPECTED), {x["normalized_key"] for x in self.delta["sources"]})
        for key, (donor_id, url) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["source"]["locator"], url)
                self.assertEqual(row["source"]["kind"], "SPECIFICATION")
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
                self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
                self.assertFalse(row["submission_review"]["second_registry_approval_required"])
                self.assertEqual(row["license"]["declared"], "UNKNOWN")
                self.assertTrue(row["discoverable_for_planning"])
                self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_intake_does_not_create_usage_edges_or_runtime_admission(self):
        serialized = json.dumps(self.links, sort_keys=True)
        for donor_id, _url in EXPECTED.values():
            self.assertNotIn(donor_id, serialized)
        for value in self.delta["boundaries"].values():
            self.assertFalse(value)

if __name__ == "__main__":
    unittest.main()
