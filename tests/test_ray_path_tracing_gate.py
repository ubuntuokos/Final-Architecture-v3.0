from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_ray_path_tracing_gate import gate


class RayPathTracingGateTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report["findings"])
        self.assertEqual(175, report["capability_count"])
        self.assertEqual(0, report["new_capabilities"])
        self.assertFalse(report["runtime_promotion_claim"])
        self.assertFalse(report["physical_current_host_pass_claimed"])


if __name__ == "__main__":
    unittest.main()
