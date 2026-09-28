"""AMD/ROCm official donor candidates remain discovery-only and hardware-neutral."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
REQUIRED_KEYS = {
    "github:amd",
    "github:rocm",
    "github:gpuopen-librariesandsdks",
    "github:amd/skills",
    "github:amd/gaia",
    "github:amd/ryzenai-sw",
    "github:amd/xdna-driver",
    "github:rocm/therock",
    "github:rocm/rocm-systems",
    "github:rocm/rocm-libraries",
    "github:rocm/rocm-examples",
    "github:rocm/amdmigraphx",
    "github:gpuopen-librariesandsdks/orochi",
    "github:gpuopen-librariesandsdks/amf",
}
NO_AUTOMATION = (
    "automatic_selection",
    "automatic_fetch",
    "automatic_install",
    "automatic_activation",
    "automatic_dependency",
    "automatic_code_import",
    "automatic_provider_admission",
    "automatic_model_selection",
)


class AmdRocmDonorRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {entry["source"]["normalized_key"]: entry for entry in cls.entries}

    def test_official_sources_exist_once(self):
        keys = [entry["source"]["normalized_key"] for entry in self.entries]
        for key in REQUIRED_KEYS:
            with self.subTest(source=key):
                self.assertEqual(keys.count(key), 1)

    def test_donors_cannot_autonomously_activate(self):
        for key in REQUIRED_KEYS:
            with self.subTest(source=key):
                entry = self.by_key[key]
                self.assertEqual(entry["status"], "CANDIDATE")
                self.assertTrue(entry["discoverable_for_planning"])
                self.assertFalse(entry["authority"])
                self.assertEqual(entry["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                for field in NO_AUTOMATION:
                    self.assertFalse(entry[field], field)

    def test_vendor_neutral_cpu_only_hardware_contract(self):
        hw = self.registry["hardware_audit"]
        self.assertTrue(hw["vendor_neutral"])
        self.assertTrue(hw["cpu_only_viable"])
        self.assertEqual(hw["accelerator_cardinality"], "0..N")
        self.assertFalse(hw["global_accelerator_requirement"])
        self.assertFalse(hw["runtime_hardware_dependency"])
        self.assertEqual(hw["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))


if __name__ == "__main__":
    unittest.main()
