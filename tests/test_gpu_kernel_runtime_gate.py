import json, shutil, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_gpu_kernel_runtime_gate as g
from fa3_gpu_kernel_dispatch_reference import KernelRequest, KernelCandidate, choose_candidate, deepgemm_arch_eligible

class GPUKernelRuntimeTests(unittest.TestCase):
    def test_baseline_gate_passes(self):
        r=g.gate(ROOT)
        self.assertEqual("PASS",r["result"],r)
        self.assertEqual((28,28),(r["regressions"]["passed"],r["regressions"]["total"]))
        self.assertFalse(r["current_host_provider_runtime_evidence"])
    def test_deepgemm_rejected_on_sm86(self):
        self.assertFalse(deepgemm_arch_eligible("sm86"))
        self.assertTrue(deepgemm_arch_eligible("sm90"))
        self.assertTrue(deepgemm_arch_eligible("sm100"))
    def test_custom_without_correctness_is_not_selected(self):
        req=KernelRequest("r","l","GPU-x","0000:05:00.0","sm86","linear_silu",64,4096,4096,1,"BF16","NT")
        base=KernelCandidate("pytorch",("sm86",),("BF16",),("linear_silu",),False,True,1.0)
        bad=KernelCandidate(g.AMPERE_PROVIDER,("sm86",),("BF16",),("linear_silu",),True,False,0.1)
        self.assertEqual("pytorch",choose_candidate(req,[base,bad]).provider_id)
    def test_requested_ineligible_provider_fails_no_silent_fallback(self):
        req=KernelRequest("r","l","GPU-x","0000:05:00.0","sm86","linear_silu",64,4096,4096,1,"BF16","NT",g.DEEPGEMM_PROVIDER)
        base=KernelCandidate("pytorch",("sm86",),("BF16",),("linear_silu",),False,True,1.0)
        with self.assertRaises(ValueError): choose_candidate(req,[base])
    def test_reference_host_is_corrected_e52696(self):
        adm=json.loads((ROOT/g.PATHS["admission"]).read_text())
        self.assertTrue(g.reference_host_semantics_valid(adm))
        self.assertNotIn("E5-2697",json.dumps(adm))
    def test_deepgemm_pin_is_immutable(self):
        ref=json.loads((ROOT/g.PATHS["reference"]).read_text())
        self.assertEqual("31f4f7276de598d2b59942f6613aa534055b4ab5",ref["primary_snapshot"]["commit"])
        self.assertTrue(g.immutable_pin_valid(ref["primary_snapshot"]["commit"]))
    def test_reference_ci_cannot_satisfy_current_host(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        try:
            (root/"evidence/receipts").mkdir(parents=True)
            r=g.current_host_gate(root)
            self.assertEqual("FAIL",r["result"])
            self.assertFalse(r["current_host_promotion_claim"])
        finally: td.cleanup()
    def test_provider_authority_escalation_rejected(self):
        p={"canonical_root":False,"architectural_authority":True,"new_capability":False,"new_architectural_authority":False,"capability_count":143}
        self.assertFalse(g.provider_boundary_valid(p))

if __name__=="__main__": unittest.main()
