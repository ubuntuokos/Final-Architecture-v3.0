from __future__ import annotations
import unittest
from pathlib import Path

from fa3_browser_session_gate import gate


class BrowserSessionGateTests(unittest.TestCase):
    def test_repository_static_gate_passes_without_runtime_promotion_claim(self):
        root=Path(__file__).resolve().parents[1]
        report=gate(root)
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual(143,report["capability_count"])
        self.assertEqual(0,report["capability_delta"])
        self.assertEqual(0,report["authority_delta"])
        self.assertFalse(report["current_host_runtime_claim"])
        self.assertFalse(report["human_completion_claim"])
        self.assertFalse(report["global_promotion_claim"])


if __name__=="__main__":
    unittest.main()
