import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class H3ReplacementPolicyTests(unittest.TestCase):
    def test_h3_is_retired_and_not_selectable(self):
        p = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        self.assertEqual(p["status"], "RETIRED_REFERENCE_ONLY")
        self.assertEqual(p["activation_mode"], "DISABLED_FORBIDDEN")
        self.assertTrue(p["runtime_execution_forbidden"])
        self.assertTrue(p["provider_selection_forbidden"])

    def test_h3_removed_from_active_video_provider_sets(self):
        profile = load("canonical/profiles/FA3-VIDEO-001.json")
        gate = load("canonical/video-enforcement.json")
        self.assertNotIn("FA3-PROVIDER-MINIMAX-H3-001", profile["providers"])
        self.assertNotIn("FA3-PROVIDER-MINIMAX-H3-001", gate["provider_ids"])

    def test_replacement_preserves_geometry_and_authorities(self):
        p = load("canonical/h3-replacement-enforcement.json")
        self.assertEqual(p["capability_delta"], 0)
        self.assertEqual(p["authority_delta"], 0)
        self.assertEqual(p["capability_count"], 143)
        self.assertIn("FA3-AUTH-MODEL-ROUTER-001", p["replacement"]["mandatory_execution_chain"])
        self.assertIn("FA3-AUTH-HOST-RESOURCE-BROKER-001", p["replacement"]["mandatory_execution_chain"])
        self.assertTrue(p["replacement"]["silent_fallback_forbidden"])

    def test_hardware_audit_is_vendor_neutral_and_cpu_only_valid(self):
        h = load("canonical/h3-replacement-enforcement.json")["hardware_audit"]
        self.assertTrue(h["vendor_neutral"])
        self.assertTrue(h["accelerator_neutral"])
        self.assertTrue(h["cpu_only_architecture_supported"])
        self.assertEqual(h["accelerator_cardinality"], "0..N")

if __name__ == "__main__":
    unittest.main()
