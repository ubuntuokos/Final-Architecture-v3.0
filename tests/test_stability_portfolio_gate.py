from __future__ import annotations
import json,shutil,tempfile,unittest
from pathlib import Path
import fa3_stability_portfolio_gate as s
ROOT=Path(__file__).resolve().parents[1]
class StabilityPortfolioGateTests(unittest.TestCase):
    def _copy(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name); shutil.copytree(ROOT/"canonical",root/"canonical"); shutil.copytree(ROOT/"evidence",root/"evidence"); return td,root
    def test_baseline_passes(self):
        r=s.gate(ROOT); self.assertEqual("PASS",r["result"],r); self.assertEqual(143,r["capability_count"]); self.assertFalse(r["current_host_provider_e2e"]); self.assertEqual("PASS",r["stable_audio_3_child_gate_result"]); self.assertEqual("FA3-HARDWARE-BASELINE-001",r["hardware_portability_profile"])
    def test_legacy_machine_tuple_cannot_return_as_normative_contract(self):
        td,root=self._copy()
        try:
            p=root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json"; d=json.loads(p.read_text()); d["hardware_reference"]={"cpu":"2x Intel Xeon E5-2696 v4","gpu":"RTX 3080 12GB"}; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_concrete_gpu_requirement_fails(self):
        td,root=self._copy()
        try:
            p=root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json"; d=json.loads(p.read_text()); d["hardware_admission"]["concrete_gpu_sku_vram_sm_device_count_as_stability_requirement"]=True; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_missing_live_snapshot_requirement_fails(self):
        td,root=self._copy()
        try:
            p=root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json"; d=json.loads(p.read_text()); d["hardware_admission"]["hardware_snapshot_required_before_local_admission"]=False; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_nim_cannot_be_local_default_without_discovery(self):
        td,root=self._copy()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-SD35-NVIDIA-NIM-001.json"; d=json.loads(p.read_text()); d["local_default_without_discovery"]=True; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_license_dimensions_fail_closed(self):
        td,root=self._copy()
        try:
            p=root/"canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json"; d=json.loads(p.read_text()); d["license_admission"]["weight_availability_implies_deployment_entitlement"]=True; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_provider_authority_escalation_fails(self):
        td,root=self._copy()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-SPAR3D-001.json"; d=json.loads(p.read_text()); d["architectural_authority"]=True; p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
    def test_stable_audio_child_gate_is_fail_closed(self):
        td,root=self._copy()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json"; d=json.loads(p.read_text()); d["precision_policy"]["allowed_medium"].append("bf16"); p.write_text(json.dumps(d)); self.assertEqual("FAIL",s.gate(root)["result"])
        finally: td.cleanup()
if __name__=="__main__": unittest.main()
