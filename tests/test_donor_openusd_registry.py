"""Guard scoped OpenUSD donor capture and planning federation."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_reuse_catalog import build_catalog

DONOR_ID = "FA3-DONOR-PIXAR-OPENUSD-001"
SOURCE_KEY = "github:pixaranimationstudios/openusd"
REFERENCE_SHA = "ee47c679abde5b467a7b6a41f3b2285564a4222e"


class OpenUsdDonorRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(
            (ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").read_text(
                encoding="utf-8"
            )
        )
        cls.matches = [
            item
            for item in cls.registry["entries"]
            if item["source"]["normalized_key"] == SOURCE_KEY
        ]

    def test_exactly_one_upstream_identity_and_consistent_backfill(self):
        self.assertEqual(len(self.matches), 1)
        ids = [row["donor_id"] for row in self.registry["entries"]]
        keys = [row["source"]["normalized_key"] for row in self.registry["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(ids.count(DONOR_ID), 1)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(ids))

    def test_only_reference_candidate_no_implicit_admission(self):
        row = self.matches[0]
        self.assertEqual(row["status"], "CANDIDATE")
        self.assertEqual(row["source"]["locator"], "https://github.com/PixarAnimationStudios/OpenUSD")
        self.assertTrue(row["discoverable_for_planning"])
        self.assertFalse(row["authority"])
        self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
        self.assertEqual(row["license"]["declared"], "TOST-1.0")
        self.assertEqual(row["license"]["status"], "KNOWN_DECLARATION")
        for field in (
            "automatic_selection", "automatic_fetch", "automatic_install",
            "automatic_activation", "automatic_dependency", "automatic_code_import",
            "automatic_provider_admission", "automatic_model_selection",
        ):
            with self.subTest(field=field):
                self.assertIs(row[field], False)

    def test_snapshot_consumer_hints_and_exclusions(self):
        row = self.matches[0]
        self.assertTrue(any(REFERENCE_SHA in note for note in row["notes"]))
        for target in ("3D Fabric", "Asset Graph", "Bforartists",
                       "FA3 Video Editor", "Realtime / Virtual Production Interchange"):
            self.assertIn(target, row["target_hints"])
        self.assertIn("usd-scene-composition", row["capability_hints"])
        self.assertIn("hydra-render-delegation", row["capability_hints"])
        self.assertFalse(any("no unreal engine target" in note.casefold() for note in row["notes"]))
        self.assertTrue(any("OPTIONAL" in note.upper() and "PR #523" in note for note in row["notes"]))
        self.assertIn("usd-asset-interchange", row["capability_hints"])
        self.assertIn("Character Studio", row["target_hints"])
        policy = self.registry["hardware_audit"]
        self.assertTrue(policy["vendor_neutral"])
        self.assertTrue(policy["cpu_only_viable"])
        self.assertEqual(policy["accelerator_cardinality"], "0..N")
        self.assertEqual(policy["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")

    def test_future_planning_catalog_has_reference_not_dependency(self):
        catalog = build_catalog(ROOT)
        rows = [x for x in catalog["entries"] if x["candidate_id"] == DONOR_ID]
        self.assertEqual(len(rows), 1)
        item = rows[0]
        self.assertEqual(item["candidate_class"], "DONOR_REFERENCE")
        self.assertEqual(item["distribution_class"], "REFERENCE_ONLY")
        self.assertEqual(item["release_bundle_status"], "EXCLUDED")
        self.assertIs(item["authority"], False)
        self.assertIs(item["automatic_dependency"], False)
        self.assertIs(item["automatic_code_import"], False)


if __name__ == "__main__":
    unittest.main()
