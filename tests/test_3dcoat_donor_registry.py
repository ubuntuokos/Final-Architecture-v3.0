"""Metadata-only regression checks for 3DCoat donor candidates."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DOC = ROOT / "docs/3dcoat-donor-curation-2026-09-28.md"
EXPECTED = {
    "github:andrewshpagin/io-coat3d": "FA3-DONOR-ANDREWSHPAGIN-IO-COAT3D-001",
    "github:liamsmyth/lks_3dctools": "FA3-DONOR-LIAMSMYTH-LKS-3DCTOOLS-001",
}


class Coat3DDonorRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_unique_candidates_have_discoverable_targets(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(len(self.entries), len({e["donor_id"] for e in self.entries}))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        for key, donor_id in EXPECTED.items():
            with self.subTest(source=key):
                self.assertIn(key, self.by_key)
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertTrue(row["discoverable_for_planning"])
                self.assertIn("3D Fabric", row["target_hints"])
                self.assertRegex(row["observed_commit"], r"^[0-9a-f]{40}$")
        self.assertTrue(DOC.is_file())

    def test_license_review_blocks_source_copy(self):
        for key in EXPECTED:
            row = self.by_key[key]
            self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
        self.assertIn("GPL-2.0-or-later", self.by_key["github:andrewshpagin/io-coat3d"]["license"]["declared"])
        self.assertEqual(
            self.by_key["github:liamsmyth/lks_3dctools"]["license"]["status"],
            "UNVERIFIED_FOR_SOURCE_COPY",
        )

    def test_no_candidate_can_admit_code_hardware_or_models(self):
        audit = self.registry["hardware_audit"]
        self.assertTrue(audit["vendor_neutral"])
        self.assertTrue(audit["cpu_only_viable"])
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        for key in EXPECTED:
            row = self.by_key[key]
            for flag in (
                "authority", "automatic_selection", "automatic_fetch", "automatic_install",
                "automatic_activation", "automatic_dependency", "automatic_code_import",
                "automatic_provider_admission", "automatic_model_selection",
            ):
                with self.subTest(source=key, flag=flag):
                    self.assertIs(row[flag], False)


if __name__ == "__main__":
    unittest.main()
