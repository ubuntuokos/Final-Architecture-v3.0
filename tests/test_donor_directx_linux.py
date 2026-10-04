"""Fail-closed checks for the 2026-09-28 DirectX and Linux D3D donor capture."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
TAG = "directx-linux-curation-2026-09-28"

class DirectXLinuxDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.curated = [x for x in cls.entries if TAG in x.get("tags", [])]
        cls.by_key = {x["source"]["normalized_key"]: x for x in cls.entries}

    def test_all_18_curated_and_normalized_sources_are_unique(self):
        self.assertEqual(len(self.curated), 18)
        self.assertEqual(len(self.entries), len({x["donor_id"] for x in self.entries}))
        self.assertEqual(len(self.entries), len({x["source"]["normalized_key"] for x in self.entries}))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["directx_linux_curation"]["source_unique_records"], 18)
        self.assertIn("github:microsoft/directx-headers", self.by_key)
        self.assertIn("github:doitsujin/dxvk", self.by_key)
        self.assertIn("github:hanskristian-work/vkd3d-proton", self.by_key)
        self.assertIn("codeberg:vkd3d/vkd3d", self.by_key)

    def test_platform_semantics_and_dependencies(self):
        for key in ("github:khronosgroup/vulkan-headers", "github:khronosgroup/vulkan-loader",
                    "github:khronosgroup/spirv-headers", "github:khronosgroup/spirv-tools"):
            self.assertIn(key, self.by_key)
        self.assertIn("wsl2", self.by_key["github:microsoft/directx-headers"]["tags"])
        self.assertIn("d3d12", self.by_key["github:hanskristian-work/vkd3d-proton"]["tags"])
        self.assertIn("d3d11", self.by_key["github:doitsujin/dxvk"]["tags"])
        for row in self.curated:
            self.assertNotIn("Unreal Engine", row["target_hints"])
            self.assertTrue(row["target_hints"])
            self.assertTrue(row["discoverable_for_planning"])

    def test_no_implicit_code_or_runtime_admission(self):
        for row in self.curated:
            if row["status"] == "ACCEPTED_REFERENCE":
                review = row.get("submission_review", {})
                self.assertEqual(review.get("basis"), "OWNER_PRE_REVIEWED_DIRECT_DONOR_LINK")
                self.assertEqual(review.get("scope"), "REFERENCE_REGISTRATION_ONLY")
                self.assertIs(review.get("second_registry_approval_required"), False)
                self.assertTrue(row.get("intake_provenance"))
            else:
                self.assertEqual(row["status"], "CANDIDATE")
            self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
            for field in ("authority", "automatic_selection", "automatic_fetch",
                          "automatic_install", "automatic_activation", "automatic_dependency",
                          "automatic_code_import", "automatic_provider_admission",
                          "automatic_model_selection"):
                self.assertIs(row[field], False, (row["donor_id"], field))
        self.assertTrue(self.registry["directx_linux_curation"]["no_runtime_admission"])

    def test_hardware_audit_remains_vendor_neutral(self):
        audit = self.registry["hardware_audit"]
        self.assertTrue(audit["vendor_neutral"])
        self.assertTrue(audit["cpu_only_viable"])
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        self.assertEqual(audit["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")

if __name__ == "__main__":
    unittest.main()
