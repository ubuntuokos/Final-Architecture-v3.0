from __future__ import annotations
import importlib.util, json, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("fa3_open_science_desktop_gate",ROOT/"src/fa3_open_science_desktop_gate.py")
gate=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(gate)
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))

class OpenScienceDesktopGateTests(unittest.TestCase):
    def test_static_materialization_passes(self):
        r=gate.run(ROOT); self.assertEqual("PASS",r["result"]); self.assertEqual(0,r["blocking_findings"]); self.assertFalse(r["current_host_production_claim"])
    def test_provider_is_optional_and_non_authoritative(self):
        p=load("canonical/providers/FA3-PROVIDER-OPEN-SCIENCE-DESKTOP-001.json"); self.assertEqual("ACCEPTED_REFERENCE",p["status"]); self.assertFalse(p["canonical_root"]); self.assertFalse(p["architectural_authority"]); self.assertFalse(p["new_capability"]); self.assertEqual(143,p["capability_count"]); self.assertEqual("OPTIONAL_DISABLED_BY_DEFAULT",p["activation_mode"]); self.assertEqual("NOT_ADMITTED_PENDING_CURRENT_HOST",p["runtime_activation_status"])
    def test_approval_skill_and_provenance_boundaries(self):
        p=load("canonical/providers/FA3-PROVIDER-OPEN-SCIENCE-DESKTOP-001.json"); c=load("canonical/contracts/FA3-SCIENTIFIC-RESEARCH-WORKBENCH-CONTRACTS-001.json"); self.assertEqual("FORBIDDEN",p["approval_policy"]["production_full_approval_mode"]); self.assertTrue(p["skill_policy"]["third_party_skill_license_must_be_independently_admitted"]); self.assertEqual("NON_AUTHORITATIVE_PROJECTION_ONLY",p["provenance_policy"]["upstream_local_run_log_role"]); self.assertFalse(c["runtime_safety"]["production_full_approval_mode_allowed"]); self.assertTrue(c["skills"]["third_party_skill_inert_until_admitted"])
    def test_portable_canonical_is_role_based(self):
        paths=["canonical/providers/FA3-PROVIDER-OPEN-SCIENCE-DESKTOP-001.json","canonical/contracts/FA3-SCIENTIFIC-RESEARCH-WORKBENCH-CONTRACTS-001.json","canonical/decisions/FA3-DEC-OPEN-SCIENCE-DESKTOP-2026-09-12.json","canonical/FA3-OPEN-SCIENCE-DESKTOP-CURRENT-HOST-CONFORMANCE-001.json","canonical/FA3-GATE-OPEN-SCIENCE-DESKTOP-001.json","canonical/open-science-desktop-enforcement.json"]
        text="\n".join((ROOT/p).read_text(encoding="utf-8") for p in paths).lower(); self.assertNotIn("rtx 3090",text); self.assertNotIn("rtx3090",text); self.assertNotIn("a1000",text); c=load("canonical/FA3-OPEN-SCIENCE-DESKTOP-CURRENT-HOST-CONFORMANCE-001.json"); self.assertEqual("EVIDENCE_ONLY",c["portable_hardware_policy"]["current_host_hardware_tuple"]); self.assertEqual("FORBIDDEN",c["portable_hardware_policy"]["exact_gpu_sku_pin"])
    def test_current_host_binding_is_3090_compute_a1000_ui(self):
        b=load("fa3-current-host/open-science-desktop-hardware-binding.json"); self.assertEqual("NVIDIA RTX A1000",b["roles"]["display_ui"]["model"]); self.assertEqual("DISPLAY",b["roles"]["display_ui"]["role"]); self.assertEqual("NVIDIA GeForce RTX 3090",b["roles"]["compute_ai"]["model"]); self.assertEqual("COMPUTE",b["roles"]["compute_ai"]["role"]); self.assertFalse(b["role_swap_allowed"]); self.assertFalse(b["automatic_fallback_allowed"])
    def _receipt(self,swap=False):
        ui_model="NVIDIA GeForce RTX 3090" if swap else "NVIDIA RTX A1000"; ai_model="NVIDIA RTX A1000" if swap else "NVIDIA GeForce RTX 3090"; ui_uuid="GPU-AI" if swap else "GPU-UI"; ai_uuid="GPU-UI" if swap else "GPU-AI"; ui_bdf="0000:05:00.0" if swap else "0000:a5:00.0"; ai_bdf="0000:a5:00.0" if swap else "0000:05:00.0"
        return {"schema":"fa3.open-science-desktop-current-host-receipt.v1","conformance_id":"FA3-OPEN-SCIENCE-DESKTOP-CURRENT-HOST-CONFORMANCE-001","status":"PASS","real_current_host_execution":True,"capability_count_after":143,"new_architectural_authorities":0,"global_promotion_claim":False,"policy":{"full_approval_mode":False,"unadmitted_skills_active":False,"provenance_projection_only":True},"hrb":{"authority_id":"FA3-AUTH-HOST-RESOURCE-BROKER-001","display_binding":{"role":"DISPLAY","model":ui_model,"display_active":True,"device_uuid":ui_uuid,"pci_bdf":ui_bdf},"compute_lease":{"role":"COMPUTE","model":ai_model,"display_active":False,"compute_eligible":True,"lease_valid":True,"device_uuid":ai_uuid,"pci_bdf":ai_bdf}},"hardware_conformance":{"uuid_bdf_live_identity":True,"topology_revalidated_at_admission":True,"numa_locality_evidence":True,"cuda_execution":True,"no_fallback":True},"execution":{"ui_gpu_uuid":ui_uuid,"compute_gpu_uuid":ai_uuid,"ui_claimed_compute_gpu":False,"compute_used_display_gpu":False,"observed_cuda":True,"silent_cpu_fallback_observed":False,"cross_accelerator_fallback_observed":False}}
    def test_valid_current_host_receipt_matches_binding(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"receipt.json"; p.write_text(json.dumps(self._receipt()),encoding="utf-8"); r=gate.run(ROOT,p)
        self.assertEqual("PASS",r["result"]); self.assertTrue(r["current_host_production_claim"])
    def test_role_swap_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"receipt.json"; p.write_text(json.dumps(self._receipt(True)),encoding="utf-8"); r=gate.run(ROOT,p)
        self.assertEqual("FAIL",r["result"]); self.assertGreater(r["blocking_findings"],0)

if __name__=="__main__": unittest.main()
