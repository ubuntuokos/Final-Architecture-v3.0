import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-VANESSIK-2026-10-03.json"
DONOR_ID = 'FA3-DONOR-VANESSIK-001'


class VanessikDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.by_id = {row["donor_id"]: row for row in cls.registry["entries"]}

    def test_append_only_registry_and_historical_delta(self):
        entries = self.registry["entries"]
        self.assertEqual(self.registry["backfill"]["entry_count"], len(entries))
        self.assertGreaterEqual(len(entries), self.delta["resulting_entry_count"])
        self.assertEqual(self.delta["parent_entry_count"], 1420)
        self.assertEqual(self.delta["new_source_count"], 1)
        self.assertEqual(self.delta["resulting_entry_count"], 1421)
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

    def test_vanessik_is_reference_only(self):
        row = self.by_id[DONOR_ID]
        self.assertEqual(row["source"]["normalized_key"], "github:vanessik")
        self.assertEqual(row["source"]["locator"], "https://github.com/Vanessik")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertFalse(row["authority"])
        for flag in (
            "automatic_selection",
            "automatic_fetch",
            "automatic_install",
            "automatic_activation",
            "automatic_dependency",
            "automatic_code_import",
            "automatic_provider_admission",
            "automatic_model_selection",
        ):
            self.assertFalse(row[flag], (DONOR_ID, flag))
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")

    def test_prior_unresolved_submission_is_resolved_by_new_approval(self):
        resolution = self.delta["resolves_prior_unresolved_submission"]
        self.assertEqual(resolution["delta_id"], "FA3-DONOR-HAIR-GROOM-SOURCES-2026-10-03")
        self.assertEqual(resolution["corrected_candidate"], "https://github.com/Vanessik")
        self.assertEqual(resolution["resolution"], "NEW_EXPLICIT_OWNER_APPROVAL_AS_SEPARATE_INTAKE")


if __name__ == "__main__":
    unittest.main()
