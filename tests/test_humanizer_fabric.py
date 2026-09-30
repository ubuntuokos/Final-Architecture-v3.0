import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_humanizer_gate import gate


class HumanizerFabricTests(unittest.TestCase):
    def load(self, rel):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_static_gate(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)

    def test_shared_settings_and_capability(self):
        p = self.load("canonical/profiles/FA3-HUMANIZATION-FABRIC-001.json")
        self.assertEqual(["CAP-125"], p["capability_bindings"])
        self.assertEqual(175, p["capability_count"])
        self.assertFalse(p["architectural_authority"])
        self.assertTrue(p["shared_settings"]["duplicate_local_settings_implementation"] == "DENY")

    def test_ai_off_and_no_direct_provider(self):
        code = (ROOT / "apps/shared/humanizer/HumanizerSettingsService.cpp").read_text(encoding="utf-8")
        self.assertIn('"ai_enabled", false', code)
        self.assertIn("DENIED_AI_DISABLED", code)
        self.assertNotIn("QNetwork", code)
        self.assertNotIn("api.openai.com", code)

    def test_current_host_remains_pending(self):
        row = self.load("canonical/FA3-HUMANIZER-CURRENT-HOST-001.json")
        self.assertTrue(row["host_requalification_required_now"])
        self.assertFalse(row["physical_current_host_pass_claim"])
        self.assertFalse(row["current_host_runtime_promotion_claim"])

    def test_reuse_snapshot_and_no_adoption(self):
        row = self.load("canonical/assessments/FA3-HUMANIZATION-REUSE-ASSESSMENT-001.json")
        self.assertEqual(1233, row["donor_count"])
        self.assertEqual("7e900cac93936d2f319e132def4c172b2a415d4d", row["donor_registry_blob_sha"])
        self.assertEqual([], row["adopted_donors"])
        self.assertEqual("PASS", row["result"])


if __name__ == "__main__":
    unittest.main()
