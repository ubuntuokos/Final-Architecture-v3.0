from __future__ import annotations
import json,shutil,tempfile,unittest
from pathlib import Path
import fa3_stability_portfolio_gate as s
ROOT=Path(__file__).resolve().parents[1]
class StabilityPortfolioGateTests(unittest.TestCase):
    def _copy(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name); shutil.copytree(ROOT/"canonical",root/"canonical"); shutil.copytree(ROOT/"evidence",root/"evidence"); return td,root
    def test_baseline_passes(self):
        r=s.gate(ROOT); self.assertEqual("PASS",r["result"],r); self.assertEqual(143,r["capability_count"]); self.assertFalse(r["current_host_provider_e2e"])
    def test_old_cpu_baseline_fails(self):
        td,root=self._copy()
        try:
            p=root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json"; d=json.loads(p.read_text()); d["hardware_reference"]["cpu"]="2x Intel Xeon E5-2697 v4"; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_nim_cannot_be_current_host_default(self):
        td,root=self._copy()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-SD35-NVIDIA-NIM-001.json"; d=json.loads(p.read_text()); d["current_host_local_default"]=True; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_license_dimensions_fail_closed(self):
        td,root=self._copy()
        try:
            p=root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json"; d=json.loads(p.read_text()); d["license_admission"]["code_license_implies_model_license"]=True; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_provider_authority_escalation_fails(self):
        td,root=self._copy()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-SPAR3D-001.json"; d=json.loads(p.read_text()); d["architectural_authority"]=True; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
if __name__=="__main__": unittest.main()
