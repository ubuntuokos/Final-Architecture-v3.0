"""Owner-marked simonsobs/SOOPERCOOL donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-SIMONSOBS-SOOPERCOOL-2026-10-03.json"

SOURCE_KEY = "github:simonsobs/soopercool"
DONOR_ID = "FA3-DONOR-SIMONSOBS-SOOPERCOOL-001"
OBSERVED_HEAD = "6191a79688392e1d57982c7697c54e110b32f49f"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class SoopercoolDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_delta(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 1424)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1423)
        self.assertEqual(self.delta["proposed_entry_count"], 1424)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_source_and_reference_boundary(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["kind"], "GITHUB_REPOSITORY")
        self.assertEqual(row["source"]["locator"], "https://github.com/simonsobs/SOOPERCOOL")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
        self.assertTrue(row["discoverable_for_planning"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_license_and_selective_scope(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["license"]["declared"], "UNKNOWN")
        self.assertEqual(row["source_snapshot"]["commit"], OBSERVED_HEAD)
        self.assertFalse(row["selection_scope"]["runtime_adoption"])
        self.assertFalse(row["selection_scope"]["code_copy"])
        self.assertIn("SCIENTIFIC_COMPUTING_REFERENCE", row["donor_modes"])
        self.assertIn("HPC_REFERENCE", row["donor_modes"])
        self.assertIn("analytic-covariance-estimation", row["capability_hints"])

    def test_no_runtime_or_usage_edge_claim(self):
        self.assertFalse(self.delta["boundaries"]["runtime_admission"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])

if __name__ == "__main__":
    unittest.main()
