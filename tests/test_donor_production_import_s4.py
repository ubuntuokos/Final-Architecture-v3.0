"""S4 source-unique official research candidates, not provider/runtime admissions."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_selective_import_preview import ALL


class S4ResearchCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(
            (ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json")
            .read_text(encoding="utf-8")
        )
        cls.entries = cls.registry["entries"]
        cls.by_source = {
            row["source"]["normalized_key"]: row for row in cls.entries
        }

    def test_two_new_official_meta_sources_are_registered_once(self):
        self.assertEqual(len(self.entries), len(self.by_source))
        self.assertEqual(len(self.entries), len({e["donor_id"] for e in self.entries}))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 656)
        for key in (
            "github:facebookresearch/sam-audio",
            "github:facebookresearch/perception_models",
        ):
            with self.subTest(key=key):
                e = self.by_source[key]
                self.assertEqual(e["status"], "CANDIDATE")
                self.assertIn("Production Import & Migration Fabric", e["target_hints"])
                self.assertTrue(e["discoverable_for_planning"])
                for field in (
                    "authority", "automatic_selection", "automatic_fetch",
                    "automatic_install", "automatic_activation",
                    "automatic_dependency", "automatic_code_import",
                    "automatic_provider_admission", "automatic_model_selection",
                ):
                    self.assertFalse(e[field], (key, field))
                self.assertEqual(
                    e["code_reuse_policy"],
                    "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW"
                )

    def test_custom_sam_license_is_not_silently_marked_open_source(self):
        row = self.by_source["github:facebookresearch/sam-audio"]
        self.assertEqual(row["license"]["declared"], "SAM License")
        self.assertNotEqual(row["license"]["status"], "ADMITTED")
        self.assertTrue(any("gated" in text.lower() for text in row["notes"]))

    def test_existing_17_selector_invariant_and_175_capability_count(self):
        self.assertEqual({key: len(value) for key, value in ALL.items()},
                         {"TEXT": 4, "AUDIO": 6, "VIDEO": 7})
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.registry["new_architectural_authority"])

    def test_parent_plan_links_s4_and_only_candidate_metadata(self):
        parent = (
            ROOT / "docs/production-import-selective-content-plan-2026-09-29.md"
        ).read_text(encoding="utf-8")
        self.assertIn("production-import-s4-stem-strategy-2026-09-29.md", parent)
        s4 = (
            ROOT / "docs/production-import-s4-stem-strategy-2026-09-29.md"
        ).read_text(encoding="utf-8")
        self.assertIn("RESEARCH ONLY", s4)
        self.assertIn("CPU-only", s4)
        self.assertIn("SAM License", s4)


if __name__ == "__main__":
    unittest.main()
