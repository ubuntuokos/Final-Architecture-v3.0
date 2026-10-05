"""Regression coverage for G'MIC donor-family metadata curation (no runtime admission)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
TAG = "gmic-curation-2026-09-28"
EXPECTED = {
    "github:greyclab/gmic",
    "github:c-koi/gmic-qt",
    "github:greyclab/cimg",
    "github:greyclab/gmic-community",
    "github:greyclab/gmic-py",
    "github:greyclab/gmic-blender",
}

class GmicDonorFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}
        cls.curated = [e for e in cls.entries if TAG in e.get("tags", [])]

    def test_verified_family_has_six_unique_sources_and_preserves_prior_gmic(self):
        self.assertEqual({e["source"]["normalized_key"] for e in self.curated}, EXPECTED)
        self.assertEqual(len(self.curated), 6)
        core = self.by_key["github:greyclab/gmic"]
        self.assertEqual(core["donor_id"], "FA3-DONOR-G-MIC-001")
        self.assertEqual(core["status"], "ANALYZED")
        self.assertIn("prior-fa3-research-backfill", core["discovered_from"])
        self.assertIn("project:g'mic", core.get("legacy_source_keys", []))
        self.assertEqual(self.registry["gmic_github_curation"]["new_record_count"], 5)
        self.assertEqual(self.registry["gmic_github_curation"]["repository_count"], 6)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))

    def test_license_provenance_and_historical_boundaries(self):
        self.assertEqual(self.by_key["github:c-koi/gmic-qt"]["license"]["declared"], "GPL-3.0")
        self.assertEqual(self.by_key["github:greyclab/gmic-community"]["license"]["status"], "UNKNOWN")
        for row in self.curated:
            self.assertEqual(row["source"]["kind"], "GITHUB")
            self.assertEqual(len(row["upstream_snapshot"]["head_sha"]), 40)
            self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
        blender = self.by_key["github:greyclab/gmic-blender"]
        self.assertIn("experimental-historical", blender["tags"])
        self.assertEqual(blender["donor_modes"], ["ARCHITECTURE_PATTERN", "WORKFLOW_PATTERN"])

    def test_non_authority_and_optional_cpu_only_hardware(self):
        audit = self.registry["hardware_audit"]
        self.assertTrue(audit["vendor_neutral"])
        self.assertTrue(audit["cpu_only_viable"])
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        self.assertTrue(self.registry["gmic_github_curation"]["non_authoritative"])
        for row in self.curated:
            self.assertTrue(row["discoverable_for_planning"])
            for flag in (
                "authority", "automatic_selection", "automatic_fetch",
                "automatic_install", "automatic_activation", "automatic_dependency",
                "automatic_code_import", "automatic_provider_admission",
                "automatic_model_selection",
            ):
                self.assertIs(row[flag], False, (row["donor_id"], flag))

    def test_global_registry_unique_keys_and_ids(self):
        self.assertEqual(len(self.entries), len({e["donor_id"] for e in self.entries}))
        self.assertEqual(len(self.entries), len({e["source"]["normalized_key"] for e in self.entries}))

if __name__ == "__main__":
    unittest.main()
