"""Guard canonical donor identity uniqueness and legacy-key continuity."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


class DonorIdentityUniquenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]

    def test_unique_ids_and_primary_source_keys(self):
        ids = [entry["donor_id"] for entry in self.entries]
        keys = [entry["source"]["normalized_key"] for entry in self.entries]
        self.assertEqual(len(ids), len(set(ids)), "Repeated canonical donor ID")
        self.assertEqual(len(keys), len(set(keys)), "Repeated primary source key")
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))

    def test_project_aliases_resolve_to_single_upstream_identity(self):
        for donor_id, canonical_key, legacy_key, expected_status in (
            ("FA3-DONOR-G-MIC-001", "github:greyclab/gmic", "project:g'mic", "ANALYZED"),
            ("FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001",
             "github:nvidia/model-optimizer", "project:nvidia-model-optimizer",
             "ACCEPTED_REFERENCE"),
        ):
            with self.subTest(donor_id=donor_id):
                records = [e for e in self.entries if e["donor_id"] == donor_id]
                self.assertEqual(len(records), 1)
                record = records[0]
                self.assertEqual(record["source"]["normalized_key"], canonical_key)
                self.assertIn(legacy_key, record["legacy_source_keys"])
                self.assertNotIn(legacy_key, {
                    e["source"]["normalized_key"] for e in self.entries
                })
                self.assertIn("prior-fa3-research-backfill", record["discovered_from"])
                self.assertEqual(record["status"], expected_status)
                for flag in (
                    "authority", "automatic_selection", "automatic_fetch",
                    "automatic_install", "automatic_activation", "automatic_dependency",
                    "automatic_code_import", "automatic_provider_admission",
                    "automatic_model_selection",
                ):
                    self.assertIs(record[flag], False, (donor_id, flag))


if __name__ == "__main__":
    unittest.main()
