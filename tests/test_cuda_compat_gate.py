from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_cuda_compat_gate import gate


class NativeCudaCompatGateTests(unittest.TestCase):
    def test_native_cuda_compat_gate_passes_static_materialization(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report["findings"])
        self.assertFalse(report["external_scale_runtime_dependency"])
        self.assertFalse(report["physical_current_host_pass_claimed"])


if __name__ == "__main__":
    unittest.main()
