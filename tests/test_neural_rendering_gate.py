from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_neural_rendering_gate import gate
class NeuralRenderingGateTests(unittest.TestCase):
    def test_static_reference_gate(self):
        r=gate(ROOT); self.assertEqual("PASS",r["result"],r["findings"]); self.assertEqual(0,r["capability_delta"]); self.assertEqual(0,r["authority_delta"]); self.assertFalse(r["current_host_provider_e2e_claim"])
    def test_active_conformance_reconciled_without_runtime_promotion(self):
        import json
        from fa3_release_baseline import load_active_release_baseline
        count=load_active_release_baseline(ROOT).capability_count
        def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
        profile=load("canonical/profiles/FA3-NEURAL-RENDERING-001.json")
        runtime=load("canonical/FA3-NEURAL-RENDERING-RUNTIME-CONFORMANCE-001.json")
        contract=load("canonical/contracts/FA3-NEURAL-RENDERING-CONTRACTS-001.json")
        gate_record=load("canonical/FA3-GATE-NEURAL-RENDERING-001.json")
        for record in (profile,runtime,contract,gate_record): self.assertEqual(count,record["capability_count"])
        self.assertEqual("FA3-DEC-CAPABILITY-MODEL-175-2026-09-26",runtime["capability_model_reconciliation"])
        self.assertEqual("FA3-DEC-HARDWARE-SAFETY-2026-09-26",runtime["hardware_safety_envelope"]["decision_id"])
        self.assertEqual("CAP-175",runtime["software_coexistence"]["capability"])
        self.assertFalse(runtime["current_host_production_provider_admission"])
        self.assertFalse(runtime["global_promotion_claim"])
if __name__=="__main__": unittest.main()
