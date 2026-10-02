import json
import unittest
from pathlib import Path

from fa3_release_baseline import module_active_capability_count
from fa3_h3_replacement_gate import gate

ROOT=Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class H3ReplacementPolicyTests(unittest.TestCase):
    def test_h3_is_retired_and_not_selectable(self):
        p=load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        self.assertEqual(p["status"],"RETIRED_REFERENCE_ONLY")
        self.assertEqual(p["activation_mode"],"DISABLED_FORBIDDEN")
        self.assertTrue(p["runtime_execution_forbidden"])
        self.assertTrue(p["provider_selection_forbidden"])

    def test_h3_removed_from_active_video_provider_sets(self):
        profile=load("canonical/profiles/FA3-VIDEO-001.json")
        video=load("canonical/video-enforcement.json")
        self.assertNotIn("FA3-PROVIDER-MINIMAX-H3-001",profile["providers"])
        self.assertNotIn("FA3-PROVIDER-MINIMAX-H3-001",video["provider_ids"])
        self.assertEqual(video["h3_policy_mode"],"HISTORICAL_REFERENCE_ONLY_NO_EXECUTION")

    def test_replacement_uses_active_175_baseline_and_existing_authorities(self):
        p=load("canonical/h3-replacement-enforcement.json")
        self.assertEqual(module_active_capability_count(__file__),175)
        self.assertEqual(p["capability_count"],175)
        self.assertEqual(p["capability_delta"],0)
        self.assertEqual(p["authority_delta"],0)
        self.assertEqual(set(p["capability_bindings"]),{"CAP-159","CAP-160"})
        chain=p["replacement"]["mandatory_execution_chain"]
        self.assertIn("FA3-AUTH-MODEL-ROUTER-001",chain)
        self.assertIn("provider_admission",chain)
        self.assertIn("FA3-AUTH-HOST-RESOURCE-BROKER-001",chain)
        self.assertIn("ProviderProjectionLossReport",chain)

    def test_hardware_audit_is_vendor_neutral_and_cpu_control_plane_valid(self):
        h=load("canonical/h3-replacement-enforcement.json")["hardware_audit"]
        self.assertTrue(h["vendor_neutral"])
        self.assertTrue(h["accelerator_neutral"])
        self.assertTrue(h["cpu_only_control_plane_supported"])
        self.assertEqual(h["accelerator_cardinality"],"0..N")
        self.assertTrue(h["local_accelerator_execution_requires_hrb"])

    def test_kling_limits_are_dynamic_and_proxy_identity_is_distinct(self):
        k=load("canonical/providers/FA3-PROVIDER-KLING-001.json")
        self.assertTrue(k["capability_discovery"]["canonical_numeric_limits_forbidden"])
        self.assertEqual(k["capability_discovery"]["mode"],"DYNAMIC_AT_ADMISSION_AND_EXECUTION")
        self.assertTrue(k["provider_identity_policy"]["proxy_or_aggregator_must_not_impersonate_native_kling"])
        self.assertTrue({"CAP-159","CAP-160"}.issubset(set(k["capability_projection"])))

    def test_executable_replacement_gate_passes_static_policy(self):
        report=gate(ROOT)
        self.assertEqual(report["result"],"PASS",report["errors"])
        self.assertFalse(report["current_host_runtime_claim"])
        self.assertFalse(report["provider_runtime_promotion_claim"])

if __name__=="__main__":
    unittest.main()
