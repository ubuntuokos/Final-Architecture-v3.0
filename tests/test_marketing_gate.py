from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_marketing_gate as gate_module
from fa3_marketing_reference import delivery_allowed, native_hungarian_content_valid, run_reference_e2e

class MarketingGateTests(unittest.TestCase):
    def _copy_root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return temp, root

    def test_reference_e2e_passes(self):
        report = run_reference_e2e()
        self.assertEqual("PASS", report["result"], report)
        self.assertFalse(report["current_host_provider_runtime_claim"])

    def test_exact_26_case_matrix_passes(self):
        report = gate_module.run_regressions()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(26, report["total"])
        self.assertEqual(26, report["passed"])
        self.assertTrue(report["case_ids_exact"])

    def test_full_gate_passes(self):
        report = gate_module.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)

    def test_translation_only_hungarian_rejected(self):
        bad = {
            "locale": "hu-HU",
            "generation_mode": "TRANSLATED_FROM_EN",
            "translation_source_locale": "en",
            "text": "Ez egy magyar fordítási tesztszöveg.",
        }
        self.assertFalse(native_hungarian_content_valid(bad))

    def test_suppressed_recipient_rejected(self):
        intent = {
            "via_central_mcp": True,
            "recipient_resolved": True,
            "channel_consent": True,
            "purpose_allowed": True,
            "suppressed": True,
            "unsubscribed": False,
            "human_approved": True,
        }
        self.assertFalse(delivery_allowed(intent))

    def test_provider_authority_drift_fails_closed(self):
        temp, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-MAUTIC-001.json"
            obj = json.loads(path.read_text())
            obj["architectural_authority"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n")
            report = gate_module.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "MKT-CANON-005" for x in report["canonical"]["findings"]))
        finally:
            temp.cleanup()

    def test_hu_hu_policy_drift_fails_closed(self):
        temp, root = self._copy_root()
        try:
            path = root / "canonical/FA3-MARKETING-I18N-001.json"
            obj = json.loads(path.read_text())
            obj["primary_locale"] = "en"
            path.write_text(json.dumps(obj, indent=2) + "\n")
            report = gate_module.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "MKT-CANON-003" for x in report["canonical"]["findings"]))
        finally:
            temp.cleanup()

if __name__ == "__main__":
    unittest.main()
