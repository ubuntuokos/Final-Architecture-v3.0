from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_neural_rendering_gate import gate
class NeuralRenderingGateTests(unittest.TestCase):
    def test_static_reference_gate(self):
        r=gate(ROOT); self.assertEqual("PASS",r["result"],r["findings"]); self.assertEqual(0,r["capability_delta"]); self.assertEqual(0,r["authority_delta"]); self.assertFalse(r["current_host_provider_e2e_claim"])
if __name__=="__main__": unittest.main()
