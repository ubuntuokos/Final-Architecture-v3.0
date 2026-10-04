from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_cuda_compat_native import (
    EXTERNAL_SCALE_RUNTIME_DEPENDENCY,
    NATIVE_BACKEND_NAME,
    analyze_cuda_source,
    translate_cuda_kernel_source,
)

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

    def test_amd_kernel_subset_translates_to_hip(self):
        result = translate_cuda_kernel_source(SIMPLE, target_vendor="AMD")
        self.assertEqual("PASS", result["result"])
        self.assertEqual("hip", result["artifact"]["target_backend"])
        self.assertIn("#include <hip/hip_runtime.h>", result["artifact"]["source"])
        self.assertFalse(result["execution_authorized"])

    def test_intel_kernel_subset_translates_to_opencl(self):
        result = translate_cuda_kernel_source(SIMPLE, target_vendor="INTEL")
        self.assertEqual("PASS", result["result"])
        source = result["artifact"]["source"]
        self.assertIn("__kernel void saxpy(", source)
        self.assertIn("__global float *out", source)
        self.assertIn("get_group_id(0)", source)
        self.assertIn("get_local_size(0)", source)
        self.assertIn("get_local_id(0)", source)
        self.assertEqual("opencl", result["artifact"]["target_backend"])

    def test_host_runtime_and_launch_syntax_fail_closed(self):
        source = SIMPLE + "\nvoid run(float *p) { saxpy<<<1,32>>>(p,p,1.0f,32); cudaFree(p); }"
        report = analyze_cuda_source(source, target_vendor="AMD")
        self.assertFalse(report["supported"])
        self.assertIn("CUDA_HOST_LAUNCH_SYNTAX", report["unsupported_features"])
        self.assertIn("CUDA_RUNTIME_API", report["unsupported_features"])

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


if __name__ == "__main__":
    unittest.main()
