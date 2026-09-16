#!/usr/bin/env python3
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "canonical" / "FA3-ACCEL-ROCM-001.json"
EXPECTED_PROVIDERS = {
    "FA3-PROVIDER-ROCM-RUNTIME-001",
    "FA3-PROVIDER-ROCM-LIBRARIES-001",
    "FA3-PROVIDER-AMD-AITER-001",
    "FA3-PROVIDER-RCCL-001",
    "FA3-PROVIDER-AMD-SMI-001",
    "FA3-PROVIDER-ROCPROFILER-001",
    "FA3-PROVIDER-ROCM-MEDIA-001",
}


class RocmCanonicalGate(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY_PATH.read_text())

    def test_release_capability_invariants(self):
        self.assertEqual(self.policy["capability_delta"], 0)
        self.assertEqual(self.policy["authority_delta"], 0)
        self.assertEqual(self.policy["capability_count"], 143)
        self.assertFalse(self.policy["new_capability"])
        self.assertFalse(self.policy["new_architectural_authority"])

    def test_provider_family_complete(self):
        self.assertEqual(set(self.policy["provider_family"]), EXPECTED_PROVIDERS)
        for provider_id in EXPECTED_PROVIDERS:
            path = ROOT / "canonical" / "providers" / f"{provider_id}.json"
            self.assertTrue(path.is_file(), path)
            record = json.loads(path.read_text())
            self.assertEqual(record["id"], provider_id)
            self.assertFalse(record["new_capability"])
            self.assertEqual(record["capability_count"], 143)

    def test_non_amd_host_is_not_forced_materialization(self):
        states = self.policy["materialization_state_machine"]
        self.assertEqual(states["amd_gpu_absent"], "AVAILABLE_NOT_MATERIALIZED")
        self.assertIn("NEVER_INSTALL_OR_ACTIVATE_ROCM", states["rule"])
        self.assertFalse(self.policy["evidence"]["current_host_runtime_pass_claimed"])

    def test_evidence_contract_present(self):
        self.assertTrue((ROOT / self.policy["evidence"]["collector"]).is_file())
        self.assertTrue((ROOT / self.policy["evidence"]["reference_receipt"]).is_file())


if __name__ == "__main__":
    unittest.main()
