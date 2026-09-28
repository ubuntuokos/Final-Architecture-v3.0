from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_reuse_catalog import build_catalog

EXPECTED = {
    "github:blender",
    "github:blender/blender",
    "github:blender/cycles",
    "github:blender/blender-addons",
    "github:blender/blender-addons-contrib",
}


def registry():
    return json.loads(
        (ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").read_text(encoding="utf-8")
    )


class BlenderGithubDonorTests(unittest.TestCase):
    def test_exact_five_source_unique_references(self):
        data = registry()
        rows = data["entries"]
        keys = [r["source"]["normalized_key"] for r in rows]
        ids = [r["donor_id"] for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(data["backfill"]["entry_count"], len(rows))
        self.assertTrue(EXPECTED.issubset(set(keys)))
        self.assertEqual(len([k for k in keys if k in EXPECTED]), 5)

    def test_non_authoritative_and_not_implicitly_admitted(self):
        rows = {r["source"]["normalized_key"]: r for r in registry()["entries"]}
        for key in EXPECTED:
            row = rows[key]
            self.assertEqual(row["status"], "CANDIDATE")
            self.assertTrue(row["discoverable_for_planning"])
            self.assertEqual(
                row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW"
            )
            for flag in (
                "authority", "automatic_selection", "automatic_fetch",
                "automatic_install", "automatic_activation", "automatic_dependency",
                "automatic_code_import", "automatic_provider_admission",
                "automatic_model_selection",
            ):
                self.assertFalse(row[flag], (key, flag))
            self.assertTrue(row["target_hints"])

    def test_license_and_archive_boundaries(self):
        rows = {r["source"]["normalized_key"]: r for r in registry()["entries"]}
        self.assertEqual(rows["github:blender/blender"]["license"]["declared"], "GPL-3.0")
        self.assertEqual(rows["github:blender/cycles"]["license"]["declared"], "Apache-2.0")
        for key in ("github:blender/blender-addons", "github:blender/blender-addons-contrib"):
            self.assertIn("archived", rows[key]["tags"])
            self.assertEqual(rows[key]["license"]["status"], "UNKNOWN")

    def test_federation_and_hardware_audit(self):
        data = registry()
        audit = data["hardware_audit"]
        self.assertTrue(audit["vendor_neutral"])
        self.assertTrue(audit["cpu_only_viable"])
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        self.assertFalse(audit["runtime_hardware_dependency"])
        self.assertEqual(
            audit["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        )
        candidate_ids = {
            r["candidate_id"] for r in build_catalog(ROOT)["entries"]
            if r["candidate_class"] == "DONOR_REFERENCE"
        }
        for row in data["entries"]:
            if row["source"]["normalized_key"] in EXPECTED:
                self.assertIn(row["donor_id"], candidate_ids)


if __name__ == "__main__":
    unittest.main()
