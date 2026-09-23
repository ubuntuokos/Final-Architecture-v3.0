from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_marketing_agent_native_gate import ACTION_IDS, gate


class MarketingAgentNativeGateTests(unittest.TestCase):
    def test_static_reference_gate(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"])
        self.assertEqual(15, report["action_count"])
        self.assertEqual(0, report["capability_delta"])
        self.assertEqual(0, report["authority_delta"])
        self.assertFalse(report["current_host_production_e2e_claim"])
        self.assertEqual(15, len(ACTION_IDS))


if __name__ == "__main__":
    unittest.main()
