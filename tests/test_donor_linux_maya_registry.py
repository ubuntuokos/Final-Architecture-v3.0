from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical" / "FA3-DONOR-REFERENCE-REGISTRY-001.json"
EXPECTED = {
    "github:autodesk/maya-usd",
    "github:autodesk/maya-hydra",
    "github:autodesk/bifrost-usd",
    "github:mgear-dev/mgear",
    "github:morganloomis/ml_tools",
    "github:autodesk/arnold-usd",
    "github:pixaranimationstudios/openusd",
    "github:academysoftwarefoundation/opencolorio",
}
TAG = "linux-maya-github-donor-curation-2026-09-28"


class LinuxMayaDonorRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.doc["entries"]
        cls.rows = [row for row in cls.entries if TAG in row.get("discovered_from", [])]

    def test_all_eight_verified_sources_registered_once(self):
        keys = [row["source"]["normalized_key"] for row in self.rows]
        self.assertEqual(set(keys), EXPECTED)
        self.assertEqual(len(keys), len(EXPECTED))
        self.assertEqual(len(keys), len(set(keys)))

    def test_registration_is_non_authoritative_and_fail_closed(self):
        for row in self.rows:
            with self.subTest(source=row["source"]["normalized_key"]):
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertTrue(row["discoverable_for_planning"])
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                for field in ("authority", "automatic_selection", "automatic_fetch",
                              "automatic_install", "automatic_activation", "automatic_dependency",
                              "automatic_code_import", "automatic_provider_admission",
                              "automatic_model_selection"):
                    self.assertFalse(row[field], field)
                self.assertTrue(row["target_hints"])
                self.assertTrue(row["capability_hints"])

    def test_no_proprietary_maya_or_arnold_runtime_enrolled(self):
        self.assertFalse(any(row["source"]["normalized_key"] in {
            "github:autodesk/maya", "github:autodesk/arnold"
        } for row in self.rows))
        self.assertFalse(any("Unreal" in target for row in self.rows for target in row["target_hints"]))

    def test_registry_count_and_hardware_audit_stay_valid(self):
        self.assertEqual(self.doc["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len({row["source"]["normalized_key"] for row in self.entries}), len(self.entries))
        self.assertTrue(self.doc["hardware_audit"]["cpu_only_viable"])
        self.assertTrue(self.doc["hardware_audit"]["vendor_neutral"])
        self.assertEqual(self.doc["hardware_audit"]["accelerator_cardinality"], "0..N")
        self.assertEqual(self.doc["hardware_audit"]["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")


if __name__ == "__main__":
    unittest.main()
