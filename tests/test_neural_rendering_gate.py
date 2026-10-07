from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_neural_rendering_gate import gate,_donor_snapshot_matches_published_commit
class NeuralRenderingGateTests(unittest.TestCase):
    def test_static_reference_gate(self):
        r=gate(ROOT); self.assertEqual("PASS",r["result"],r["findings"]); self.assertEqual(0,r["capability_delta"]); self.assertEqual(0,r["authority_delta"]); self.assertFalse(r["current_host_provider_e2e_claim"])
    def test_donor_snapshot_is_verified_against_recorded_published_commit(self):
        import json
        assessment=json.loads((ROOT/"canonical/assessments/FA3-NEURAL-RENDERING-REUSE-ASSESSMENT-001.json").read_text(encoding="utf-8"))
        self.assertTrue(_donor_snapshot_matches_published_commit(ROOT,assessment["donor_planning_snapshot"]))
        bad=dict(assessment["donor_planning_snapshot"]); bad["donor_registry_entry_count"]+=1
        self.assertFalse(_donor_snapshot_matches_published_commit(ROOT,bad))
    def test_active_records_are_on_175_baseline(self):
        import json
        from fa3_release_baseline import load_active_release_baseline
        count=load_active_release_baseline(ROOT).capability_count
        def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
        for path in (
            "canonical/profiles/FA3-NEURAL-RENDERING-001.json",
            "canonical/contracts/FA3-NEURAL-RENDERING-CONTRACTS-001.json",
            "canonical/providers/FA3-PROVIDER-OPENDLSS-NR-001.json",
            "canonical/FA3-GATE-NEURAL-RENDERING-001.json",
            "canonical/FA3-NEURAL-RENDERING-RUNTIME-CONFORMANCE-001.json",
        ):
            self.assertEqual(count,load(path)["capability_count"],path)
        runtime=load("canonical/FA3-NEURAL-RENDERING-RUNTIME-CONFORMANCE-001.json")
        self.assertEqual("FA3-DEC-HARDWARE-SAFETY-2026-09-26",runtime["hardware_safety_envelope"]["decision_id"])
        self.assertFalse(runtime["current_host_production_provider_admission"])

if __name__=="__main__": unittest.main()
