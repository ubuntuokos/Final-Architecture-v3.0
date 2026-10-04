from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_cuda_compat_build import make_build_plan
from fa3_cuda_compat_frontend import parse_cuda_translation_unit
from fa3_cuda_compat_native import (
    EXTERNAL_SCALE_RUNTIME_DEPENDENCY,
    NATIVE_BACKEND_NAME,
    analyze_cuda_source,
    translate_cuda_kernel_source,
)
from fa3_cuda_compat_runtime import runtime_api_support

SIMPLE = """
__global__ void saxpy(float *out, const float *x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) out[i] = a * x[i] + out[i];
}
"""


class NativeCudaCompatTests(unittest.TestCase):
    def test_external_scale_is_not_a_runtime_dependency(self):
        self.assertFalse(EXTERNAL_SCALE_RUNTIME_DEPENDENCY)
        self.assertEqual("cfa3-cuda-compat", NATIVE_BACKEND_NAME)

    def test_structured_frontend_emits_kernel_ir(self):
        ir = parse_cuda_translation_unit(SIMPLE)
        self.assertEqual(1, len(ir.kernels))
        self.assertEqual("saxpy", ir.kernels[0].name)
        self.assertEqual(["out", "x", "a", "n"], [p.name for p in ir.kernels[0].parameters])
        self.assertIn("THREAD_INDEX", ir.detected_features)
        self.assertEqual((), ir.unsupported_features)

    def test_comments_do_not_create_fake_runtime_or_launch_findings(self):
        source = SIMPLE + '\n// cudaFree(x); fake<<<1,1>>>(x);\n'
        report = analyze_cuda_source(source, target_vendor="AMD")
        self.assertTrue(report["supported"], report["unsupported_features"])

    def test_amd_supported_subset_translates_to_hip_full_equivalence(self):
        result = translate_cuda_kernel_source(SIMPLE, target_vendor="AMD")
        self.assertEqual("PASS", result["result"])
        self.assertEqual("FULL_EQUIVALENCE", result["compatibility_result"])
        self.assertEqual("hip", result["artifact"]["target_backend"])
        self.assertIn("#include <hip/hip_runtime.h>", result["artifact"]["source"])
        self.assertFalse(result["execution_authorized"])

    def test_amd_supported_runtime_calls_map_to_hip(self):
        source = SIMPLE + "\nvoid cleanup(float *p) { cudaFree(p); }"
        result = translate_cuda_kernel_source(source, target_vendor="AMD")
        self.assertEqual("PASS", result["result"], result)
        self.assertIn("hipFree(p)", result["artifact"]["source"])
        self.assertEqual("FULL_EQUIVALENCE", result["compatibility_result"])

    def test_amd_runtime_types_and_copy_kind_are_mapped_before_full_equivalence(self):
        source = SIMPLE + "\nvoid copy(float *dst, float *src) { cudaError_t e = cudaMemcpy(dst, src, 16, cudaMemcpyHostToDevice); if (e != cudaSuccess) {} }"
        result = translate_cuda_kernel_source(source, target_vendor="AMD")
        self.assertEqual("PASS", result["result"], result)
        translated = result["artifact"]["source"]
        self.assertIn("hipError_t", translated)
        self.assertIn("hipMemcpyHostToDevice", translated)
        self.assertIn("hipSuccess", translated)
        self.assertNotIn("cudaMemcpyHostToDevice", translated)

    def test_unknown_cuda_runtime_identifier_blocks_amd_full_equivalence(self):
        source = SIMPLE + "\nvoid x() { cudaInventedType thing; }"
        report = analyze_cuda_source(source, target_vendor="AMD")
        self.assertFalse(report["supported"])
        self.assertIn("UNSUPPORTED_CUDA_IDENTIFIER:cudaInventedType", report["unsupported_features"])

    def test_intel_sycl_is_primary_and_functionally_reduced(self):
        result = translate_cuda_kernel_source(SIMPLE, target_vendor="INTEL")
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual("sycl", result["artifact"]["target_backend"])
        self.assertEqual("SYCL_CPP", result["artifact"]["target_language"])
        self.assertEqual("FUNCTIONALLY_REDUCED", result["compatibility_result"])
        self.assertIn("#include <sycl/sycl.hpp>", result["artifact"]["source"])
        self.assertIn("item.get_local_id(2)", result["artifact"]["source"])
        self.assertIn("SYCL_HOST_QUEUE_LAUNCH_WRAPPER_REQUIRED", result["artifact"]["limitations"])

    def test_intel_launch_bounds_is_removed_by_structured_lowerer(self):
        source = "__global__ __launch_bounds__(256) void k(float *x) { int i = threadIdx.x; x[i] = 1.0f; }"
        result = translate_cuda_kernel_source(source, target_vendor="INTEL")
        self.assertEqual("PASS", result["result"], result)
        self.assertNotIn("__launch_bounds__", result["artifact"]["source"])
        self.assertIn("inline void k(", result["artifact"]["source"])

    def test_intel_opencl_remains_explicit_secondary_target(self):
        result = translate_cuda_kernel_source(SIMPLE, target_vendor="INTEL", target_backend="opencl")
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual("opencl", result["artifact"]["target_backend"])
        self.assertEqual("FUNCTIONALLY_REDUCED", result["compatibility_result"])
        self.assertIn("__kernel void saxpy(", result["artifact"]["source"])

    def test_host_launch_syntax_fails_closed(self):
        source = SIMPLE + "\nvoid run(float *p) { saxpy<<<1,32>>>(p,p,1.0f,32); }"
        report = analyze_cuda_source(source, target_vendor="AMD")
        self.assertFalse(report["supported"])
        self.assertEqual("UNAVAILABLE", report["compatibility_result"])
        self.assertIn("CUDA_HOST_LAUNCH_SYNTAX", report["unsupported_features"])

    def test_unknown_amd_runtime_symbol_fails_closed(self):
        source = SIMPLE + "\nvoid run() { cudaGraphLaunchX(); }"
        report = analyze_cuda_source(source, target_vendor="AMD")
        self.assertFalse(report["supported"])
        self.assertTrue(any(x.startswith("UNSUPPORTED_RUNTIME_SYMBOL:") for x in report["unsupported_features"]))

    def test_intel_runtime_api_requires_explicit_host_adapter(self):
        source = SIMPLE + "\nvoid cleanup(float *p) { cudaFree(p); }"
        report = analyze_cuda_source(source, target_vendor="INTEL")
        self.assertFalse(report["supported"])
        self.assertIn("CUDA_RUNTIME_API_REQUIRES_HOST_ADAPTER", report["unsupported_features"])

    def test_intel_unsupported_atomic_is_reported(self):
        source = "__global__ void k(int *x) { atomicAdd(x, 1); }"
        report = analyze_cuda_source(source, target_vendor="INTEL")
        self.assertFalse(report["supported"])
        self.assertIn("CUDA_ATOMICS", report["unsupported_features"])

    def test_closed_binary_is_not_claimed(self):
        report = analyze_cuda_source("binary", target_vendor="AMD", source_kind="CUBIN")
        self.assertFalse(report["supported"])
        self.assertIn("SOURCE_KIND_UNSUPPORTED", report["unsupported_features"])
        self.assertFalse(report["closed_binary_compatibility_claimed"])

    def test_runtime_map_classification_is_explicit(self):
        amd = runtime_api_support(["cudaMalloc", "cudaFree"], target_vendor="AMD", target_backend="hip")
        intel = runtime_api_support(["cudaMalloc", "cudaFree"], target_vendor="INTEL", target_backend="sycl")
        missing = runtime_api_support(["cudaGraphLaunchX"], target_vendor="AMD", target_backend="hip")
        self.assertEqual("FULL_EQUIVALENCE", amd["classification"])
        self.assertEqual("FUNCTIONALLY_REDUCED", intel["classification"])
        self.assertEqual("UNAVAILABLE", missing["classification"])
        self.assertFalse(amd["runtime_execution_authorized"])

    def test_two_token_nvcc_architecture_option_is_preserved(self):
        plan = make_build_plan(
            sources=["kernel.cu"],
            nvcc_args=["-gencode", "arch=compute_90,code=sm_90"],
            target_vendor="AMD",
            target_backend="hip",
        )
        self.assertEqual("PASS", plan["result"], plan)
        self.assertEqual(["-gencode", "arch=compute_90,code=sm_90"], plan["normalized_nvcc_options"])

    def test_unknown_nvcc_option_is_denied_not_dropped(self):
        plan = make_build_plan(
            sources=["kernel.cu"],
            nvcc_args=["-O3", "--std=c++20", "--invented-cuda-option"],
            target_vendor="AMD",
            target_backend="hip",
        )
        self.assertEqual("DENY", plan["result"])
        self.assertIn("UNSUPPORTED_NVCC_OPTION:--invented-cuda-option", plan["findings"])
        self.assertFalse(plan["silent_option_drop"])
        self.assertFalse(plan["compiler_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
