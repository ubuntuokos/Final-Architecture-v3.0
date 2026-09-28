"""Regression checks for selective, non-authoritative Pixar donor discovery."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"

EXPECTED = {
    "github:pixaranimationstudios": "FA3-DONOR-PIXAR-GITHUB-ORGANIZATION-001",
    "github:pixaranimationstudios/openusd": "FA3-DONOR-PIXAR-OPENUSD-001",
    "github:pixaranimationstudios/opensubdiv": "FA3-DONOR-PIXAR-OPENSUBDIV-001",
    "github:pixaranimationstudios/openusd-proposals": "FA3-DONOR-PIXAR-OPENUSD-PROPOSALS-001",
    "github:pixaranimationstudios/chook": "FA3-DONOR-PIXAR-CHOOK-001",
    "github:pixaranimationstudios/xolo": "FA3-DONOR-PIXAR-XOLO-001",
}


class PixarDonorRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {row["source"]["normalized_key"]: row for row in cls.entries}

    def test_source_identities_are_unique_and_visible(self):
        self.assertEqual(len(self.by_key), len(self.entries))
        self.assertEqual(len({row["donor_id"] for row in self.entries}), len(self.entries))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        for source, donor_id in EXPECTED.items():
            with self.subTest(source=source):
                self.assertIn(source, self.by_key)
                row = self.by_key[source]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertTrue(row["discoverable_for_planning"])

    def test_candidates_cannot_activate_or_require_accelerators(self):
        self.assertFalse(self.registry["authority"])
        self.assertTrue(self.registry["hardware_audit"]["vendor_neutral"])
        self.assertTrue(self.registry["hardware_audit"]["cpu_only_viable"])
        self.assertEqual(self.registry["hardware_audit"]["accelerator_cardinality"], "0..N")
        for source in EXPECTED:
            row = self.by_key[source]
            with self.subTest(source=source):
                self.assertEqual(row["status"], "CANDIDATE")
                for forbidden in (
                    "authority", "automatic_selection", "automatic_fetch",
                    "automatic_install", "automatic_activation", "automatic_dependency",
                    "automatic_code_import", "automatic_provider_admission",
                    "automatic_model_selection",
                ):
                    self.assertIs(row[forbidden], False)
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")

    def test_license_and_provenance_are_not_implicitly_approved(self):
        for repo in ("openusd", "opensubdiv", "chook", "xolo"):
            row = self.by_key["github:pixaranimationstudios/" + repo]
            with self.subTest(repo=repo):
                self.assertEqual(
                    row["license"]["declared"],
                    "Tomorrow Open Source Technology License 1.0",
                )
                self.assertRegex(row["observed_commit"], r"^[0-9a-f]{40}$")
        proposal = self.by_key["github:pixaranimationstudios/openusd-proposals"]
        self.assertEqual(proposal["license"]["declared"], "UNKNOWN")
        self.assertRegex(proposal["observed_commit"], r"^[0-9a-f]{40}$")

    def test_creative_and_future_applications_are_discoverable(self):
        usd = self.by_key["github:pixaranimationstudios/openusd"]
        self.assertIn("3D Fabric", usd["target_hints"])
        self.assertIn("Asset Graph", usd["target_hints"])
        self.assertIn("FA3 Video Editor", usd["target_hints"])
        self.assertIn("hydra-render-delegates", usd["capability_hints"])
        subdiv = self.by_key["github:pixaranimationstudios/opensubdiv"]
        self.assertIn("cpu-subdivision", subdiv["capability_hints"])
        self.assertIn("Character Studio", subdiv["target_hints"])
        self.assertTrue((ROOT / "docs/pixar-github-donor-curation-2026-09-28.md").is_file())


if __name__ == "__main__":
    unittest.main()
