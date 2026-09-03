import json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_gpu_kernel_runtime_gate as g
from fa3_gpu_kernel_dispatch_reference import KernelRequest, KernelCandidate, choose_candidate, deepgemm_arch_eligible, provider_arch_eligible

class GPUKernelRuntimeTests(unittest.TestCase):
    def test_baseline_gate_passes(self):
        r=g.gate(ROOT)
        self.assertEqual("PASS",r["result"],r)
        self.assertEqual((28,28),(r["regressions"]["passed"],r["regressions"]["total"]))
        self.assertFalse(r["current_host_provider_runtime_evidence"])

    def test_framework_native_baseline_is_not_sm86_pinned(self):
        req=KernelRequest("r","l","GPU-x","0000:05:00.0","sm89","linear_silu",64,4096,4096,1,"BF16","NT")
        base=KernelCandidate(g.FRAMEWORK_PROVIDER,("sm89",),("BF16",),("linear_silu",),False,True,1.0)
        self.assertEqual(g.FRAMEWORK_PROVIDER,choose_candidate(req,[base]).provider_id)

    def test_deepgemm_snapshot_support_is_provider_metadata(self):
        self.assertFalse(deepgemm_arch_eligible("sm86",("sm90","sm100")))
        self.assertTrue(deepgemm_arch_eligible("sm90",("sm90","sm100")))
        self.assertTrue(provider_arch_eligible("sm89",("sm89",)))

    def test_custom_without_correctness_is_not_selected(self):
        req=KernelRequest("r","l","GPU-x","0000:05:00.0","sm86","linear_silu",64,4096,4096,1,"BF16","NT")
        base=KernelCandidate(g.FRAMEWORK_PROVIDER,("sm86",),("BF16",),("linear_silu",),False,True,1.0)
        bad=KernelCandidate(g.AMPERE_PROVIDER,("sm86",),("BF16",),("linear_silu",),True,False,0.1)
        self.assertEqual(g.FRAMEWORK_PROVIDER,choose_candidate(req,[base,bad]).provider_id)

    def test_requested_ineligible_provider_fails_no_silent_fallback(self):
        req=KernelRequest("r","l","GPU-x","0000:05:00.0","sm86","linear_silu",64,4096,4096,1,"BF16","NT",g.DEEPGEMM_PROVIDER)
        base=KernelCandidate(g.FRAMEWORK_PROVIDER,("sm86",),("BF16",),("linear_silu",),False,True,1.0)
        with self.assertRaises(ValueError): choose_candidate(req,[base])

    def test_canonical_admission_contains_no_exact_reference_host_tuple(self):
        adm=json.loads((ROOT/g.PATHS["admission"]).read_text())
        self.assertTrue(g.admission_portability_valid(adm))
        text=json.dumps(adm)
        self.assertNotIn("RTX 3080",text)
        self.assertNotIn("E5-2696",text)
        self.assertNotIn("T7910",text)

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
            self.assertFalse(r["current_host_runtime_promotion_claim"])
        finally: td.cleanup()

    def test_provider_authority_escalation_rejected(self):
        p={"canonical_root":False,"architectural_authority":True,"new_capability":False,"new_architectural_authority":False,"capability_count":143}
        self.assertFalse(g.provider_boundary_valid(p))

if __name__=="__main__": unittest.main()
