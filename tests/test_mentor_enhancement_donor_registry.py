from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical" / "FA3-DONOR-REFERENCE-REGISTRY-001.json"
TAG = "mentor-enhancement-plan-2026-09-28"
EXPECTED_KEYS = {
    "github:flagrare/llm-tutor",
    "github:h5p/h5p-interactive-book",
    "github:h5p/h5p-interactive-video",
    "github:h5p/h5p-php-library",
    "github:hkuds/deeptutor",
    "github:jupyterlab/jupyterlab",
    "github:kaushal0494/aitutor-evalkit",
    "github:learninglocker/learninglocker",
    "github:learninglocker/xapi-validation",
    "github:ls1intum/artemis",
    "github:ls1intum/pyris",
    "github:open-spaced-repetition/free-spaced-repetition-scheduler",
    "github:oppia/oppia",
    "github:skillcoco/skillcoco",
    "github:tryskilly/skilly",
}


class MentorEnhancementDonorRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.rows = [
            row for row in cls.registry["entries"]
            if TAG in row.get("discovered_from", [])
        ]
        cls.by_key = {row["source"]["normalized_key"]: row for row in cls.rows}

    def test_exact_source_set_and_local_uniqueness(self):
        keys = [row["source"]["normalized_key"] for row in self.rows]
        donor_ids = [row["donor_id"] for row in self.rows]
        self.assertEqual(set(keys), EXPECTED_KEYS)
        self.assertEqual(len(keys), 15)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(donor_ids), len(set(donor_ids)))
        self.assertEqual(
            self.registry["backfill"]["entry_count"],
            len(self.registry["entries"]),
        )

    def test_candidate_only_and_non_authoritative(self):
        for row in self.rows:
            with self.subTest(source=row["source"]["normalized_key"]):
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertTrue(row["discoverable_for_planning"])
                self.assertFalse(row["authority"])
                self.assertFalse(row["upstream_observation"]["source_copy_allowed"])
                self.assertFalse(row["upstream_observation"]["runtime_admitted"])
                for field in (
                    "automatic_selection", "automatic_fetch", "automatic_install",
                    "automatic_activation", "automatic_dependency",
                    "automatic_code_import", "automatic_provider_admission",
                    "automatic_model_selection",
                ):
                    self.assertIs(row[field], False, field)

    def test_fa3_safety_and_capability_invariants(self):
        self.assertEqual(self.registry["capability_count"], 175)
        curation = self.registry["mentor_enhancement_curation"]
        self.assertEqual(curation["source_count"], 15)
        self.assertEqual(curation["capability_count_delta"], 0)
        self.assertEqual(curation["authority_delta"], 0)
        audit = self.registry["hardware_audit"]
        self.assertTrue(audit["vendor_neutral"])
        self.assertTrue(audit["cpu_only_viable"])
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        self.assertEqual(
            audit["live_resource_authority"],
            "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        )


if __name__ == "__main__":
    unittest.main()
