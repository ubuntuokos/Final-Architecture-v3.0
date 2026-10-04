from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_scale_backend_gate import gate


class ScaleBackendGateTests(unittest.TestCase):
    def test_scale_gate_passes_static_materialization(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report["findings"])
        self.assertEqual(175, report["capability_count"])
        self.assertFalse(report["runtime_promotion_claim"])
        self.assertFalse(report["physical_current_host_pass_claimed"])
        self.assertTrue(report["physical_requalification_required"])


if __name__ == "__main__":
    unittest.main()
