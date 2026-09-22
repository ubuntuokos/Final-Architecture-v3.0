import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

import fa3_gpu_kernel_runtime_gate as g
from fa3_gpu_kernel_dispatch_reference import (
    KernelRequest,
    KernelCandidate,
    choose_candidate,
    deepgemm_arch_eligible,
    provider_arch_eligible,
)


def request(
    request_id,
    arch,
    backend="cuda",
    backend_class="native",
    framework="pytorch-cuda",
    requested_provider=None,
):
    return KernelRequest(
        request_id=request_id,
        hrb_lease_id="lease-"+request_id,
        accelerator_id="accel-"+request_id,
        topology_binding="pci:dynamic",
        accelerator_arch=arch,
        compute_backend=backend,
        backend_class=backend_class,
        framework_backend=framework,
        operation="linear_silu",
        m=64,
        n=4096,
        k=4096,
        batch=1,
        dtype="BF16",
        layout="NT",
        requested_provider=requested_provider,
    )


def candidate(
    provider_id,
    backend,
    backend_class,
    arch,
    framework,
    *,
    custom=False,
    correctness=True,
    benchmark=1.0,
    compatibility=True,
):
    return KernelCandidate(
        provider_id=provider_id,
        supported_backends=(backend,),
        supported_backend_classes=(backend_class,),
        supported_arches=(arch,),
        supported_dtypes=("BF16",),
        supported_ops=("linear_silu",),
        custom_kernel=custom,
        correctness_pass=correctness,
        benchmark_ms=benchmark,
        compatibility_pass=compatibility,
        supported_framework_backends=(framework,),
    )


class GPUKernelRuntimeTests(unittest.TestCase):
    def test_baseline_gate_passes(self):
        r=g.gate(ROOT)
        self.assertEqual("PASS",r["result"],r)
        self.assertEqual((28,28),(r["regressions"]["passed"],r["regressions"]["total"]))
        self.assertFalse(r["current_host_provider_runtime_evidence"])

    def test_framework_native_cuda_baseline_is_not_sm86_pinned(self):
        req=request("r","sm89")
        base=candidate(g.FRAMEWORK_PROVIDER,"cuda","native","sm89","pytorch-cuda")
        self.assertEqual(g.FRAMEWORK_PROVIDER,choose_candidate(req,[base]).provider_id)

    def test_backend_neutral_dispatch_accepts_rocm_xpu_and_vulkan(self):
        cases=[
            (
                request("rocm","gfx1100","rocm","native","pytorch-rocm"),
                candidate("SYNTH-ROCM","rocm","native","gfx1100","pytorch-rocm"),
            ),
            (
                request("xpu","xe2","level-zero","native","pytorch-xpu"),
                candidate("SYNTH-XPU","level-zero","native","xe2","pytorch-xpu"),
            ),
            (
                request("vk","generic-vulkan","vulkan","portable","vulkan-compute"),
                candidate("SYNTH-VULKAN","vulkan","portable","generic-vulkan","vulkan-compute"),
            ),
        ]
        for req, cand in cases:
            with self.subTest(backend=req.compute_backend):
                self.assertEqual(cand.provider_id,choose_candidate(req,[cand]).provider_id)

    def test_backend_mismatch_fails_closed(self):
        req=request("cuda","sm89","cuda","native","pytorch-cuda")
        rocm=candidate("SYNTH-ROCM","rocm","native","gfx1100","pytorch-rocm")
        with self.assertRaises(ValueError):
            choose_candidate(req,[rocm])

    def test_translation_kernel_candidate_is_not_implicitly_admitted(self):
        req=request("zluda","compat","zluda","translation","cuda-compat")
        cand=candidate("SYNTH-ZLUDA","zluda","translation","compat","cuda-compat")
        with self.assertRaises(ValueError):
            choose_candidate(req,[cand])

    def test_deepgemm_snapshot_support_is_provider_metadata(self):
        self.assertFalse(deepgemm_arch_eligible("sm86",("sm90","sm100")))
        self.assertTrue(deepgemm_arch_eligible("sm90",("sm90","sm100")))
        self.assertTrue(provider_arch_eligible("sm89",("sm89",)))

    def test_custom_without_correctness_is_not_selected(self):
        req=request("r","sm86")
        base=candidate(g.FRAMEWORK_PROVIDER,"cuda","native","sm86","pytorch-cuda")
        bad=candidate(g.AMPERE_PROVIDER,"cuda","native","sm86","pytorch-cuda",custom=True,correctness=False,benchmark=0.1)
        self.assertEqual(g.FRAMEWORK_PROVIDER,choose_candidate(req,[base,bad]).provider_id)

    def test_requested_ineligible_provider_fails_no_silent_fallback(self):
        req=request("r","sm86",requested_provider=g.DEEPGEMM_PROVIDER)
        base=candidate(g.FRAMEWORK_PROVIDER,"cuda","native","sm86","pytorch-cuda")
        with self.assertRaises(ValueError):
            choose_candidate(req,[base])

    def test_canonical_admission_contains_no_exact_reference_host_tuple(self):
        adm=json.loads((ROOT/g.PATHS["admission"]).read_text())
        self.assertTrue(g.admission_portability_valid(adm))
        text=json.dumps(adm)
        self.assertNotIn("LEGACY_ACCELERATOR_SKU",text)
        self.assertNotIn("LEGACY_CPU_SKU",text)
        self.assertNotIn("LEGACY_HOST_MODEL",text)
        self.assertEqual("NONE",adm["generic_execution_path_policy"]["backend_floor"])

    def test_contract_has_no_global_cuda_requirement(self):
        contract=json.loads((ROOT/g.PATHS["contract"]).read_text())
        self.assertFalse(contract["backend_semantics"]["generic_contract_requires_cuda"])
        self.assertIn("compute_backend",contract["autotune_key_fields"])
        self.assertNotIn("cuda_version",contract["autotune_key_fields"])
        self.assertNotIn("gpu_arch",contract["required_kernel_capability_fields"])

    def test_deepgemm_pin_is_immutable(self):
        ref=json.loads((ROOT/g.PATHS["reference"]).read_text())
        self.assertEqual("31f4f7276de598d2b59942f6613aa534055b4ab5",ref["primary_snapshot"]["commit"])
        self.assertTrue(g.immutable_pin_valid(ref["primary_snapshot"]["commit"]))

    def test_reference_ci_cannot_satisfy_current_host(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        try:
            (root/"evidence/receipts").mkdir(parents=True)
            r=g.current_host_gate(root)
            self.assertEqual("FAIL",r["result"])
            self.assertFalse(r["current_host_runtime_promotion_claim"])
        finally:
            td.cleanup()

    def test_provider_authority_escalation_rejected(self):
        p={"canonical_root":False,"architectural_authority":True,"new_capability":False,"new_architectural_authority":False,"capability_count":143}
        self.assertFalse(g.provider_boundary_valid(p))


if __name__=="__main__":
    unittest.main()
