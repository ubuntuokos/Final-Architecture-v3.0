from __future__ import annotations
import unittest
from pathlib import Path

from fa3_browser_session_gate import gate
from fa3_browser_session_current_host_gate import cli_unpacked_extension_supported
from fa3_release_baseline import module_active_capability_count


class BrowserSessionGateTests(unittest.TestCase):
    def test_extension_test_browser_rejects_branded_chrome_cli_loading(self):
        self.assertFalse(cli_unpacked_extension_supported("Google Chrome 154.0.0.0"))
        self.assertTrue(cli_unpacked_extension_supported("Google Chrome for Testing 154.0.0.0"))
        self.assertTrue(cli_unpacked_extension_supported("Chromium 154.0.0.0"))

    def test_repository_static_gate_passes_without_runtime_promotion_claim(self):
        root=Path(__file__).resolve().parents[1]
        report=gate(root)
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual(module_active_capability_count(__file__),report["capability_count"])
        self.assertEqual(0,report["capability_delta"])
        self.assertEqual(0,report["authority_delta"])
        self.assertFalse(report["current_host_runtime_claim"])
        self.assertFalse(report["human_completion_claim"])
        self.assertFalse(report["global_promotion_claim"])


if __name__=="__main__":
    unittest.main()
