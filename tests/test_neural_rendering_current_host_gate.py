from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_neural_rendering_current_host_gate import gate
class NeuralRenderingCurrentHostGateTests(unittest.TestCase):
    def test_optional_provider_not_requested(self):
        r=gate(ROOT,""); self.assertEqual("PASS",r["result"]); self.assertFalse(r["provider_e2e_claim"]); self.assertFalse(r["production_provider_admission"])
    def test_unknown_provider_fails_closed(self):
        r=gate(ROOT,"unknown"); self.assertEqual("BLOCKED",r["result"]); self.assertEqual(2,r["decision"]["exit_code"])
if __name__=="__main__": unittest.main()
