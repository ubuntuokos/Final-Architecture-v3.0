import tempfile
import unittest
from pathlib import Path

from fa3_minimax_h3_runtime_admission_gate import current_host_gate, static_gate

ROOT = Path(__file__).resolve().parents[1]


class MiniMaxH3RuntimeGateTests(unittest.TestCase):
    def test_static_runtime_admission_gate_passes(self):
        report = static_gate(ROOT)
        self.assertEqual(report["result"], "PASS", report.get("findings"))
        self.assertFalse(report["runtime_promotion_claim"])

    def test_current_host_gate_fails_closed_without_real_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            report = current_host_gate(Path(td))
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(f["code"] == "H3-HOST-001" for f in report["findings"]))


if __name__ == "__main__":
    unittest.main()
