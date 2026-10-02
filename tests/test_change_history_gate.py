from __future__ import annotations
import unittest
from pathlib import Path
from fa3_change_history_gate import gate

ROOT=Path(__file__).resolve().parents[1]

class ChangeHistoryGateTests(unittest.TestCase):
    def test_static_p0_gate_passes_on_materialization(self):
        report=gate(ROOT)
        self.assertEqual(report["result"],"PASS",report["findings"])
        self.assertEqual(report["capability_count"],175)
        self.assertEqual(report["capability_delta"],0)
        self.assertEqual(report["authority_delta"],0)
        self.assertFalse(report["current_host_runtime_claim"])

if __name__=="__main__": unittest.main()
