from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_cuda_compat_shared import (
    SHARED_APPLICATION_SCOPE,
    inspect_cuda_runtime_compatibility,
    prepare_cuda_compat_build,
    prepare_cuda_compat_translation,
    resolve_cuda_compatibility,
)
from fa3_hardware_discovery import AcceleratorBackendDescriptor, AcceleratorDeviceDescriptor


def amd_with_native_compat():
    return AcceleratorDeviceDescriptor(
        discovery_id="pci:0000:0a:00.0", kind="gpu", vendor="AMD",
        vendor_id="0x1002", device_id="0x0001", pci_bdf="0000:0a:00.0",
        backends=(AcceleratorBackendDescriptor(
            name="cfa3-cuda-compat", backend_class="translation",
            available=True, detected=True, binding_scope="DEVICE",
            runtime_version="2.0", framework_backends=("cuda-compat","cfa3-native","rocm"),
            experimental=True, evidence_sources=("test:cfa3-native",),
        ),),
    )


SIMPLE = """
__global__ void k(float *x) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    x[i] = x[i] + 1.0f;
}
"""


class SharedCudaCompatTests(unittest.TestCase):
    def test_all_applications_use_same_native_entrypoint_without_allowlist(self):
        with mock.patch("fa3_cuda_compat_shared.enrich_accelerator_backends", return_value=[amd_with_native_compat()]):
            story = resolve_cuda_compatibility([], application_id="fa3.story-screenplay", workload_id="story-job-1", requested_backend="cfa3-cuda-compat", allow_translation=True, cuda_source=SIMPLE)
            video = resolve_cuda_compatibility([], application_id="fa3.video-editor", workload_id="video-job-1", requested_backend="cfa3-cuda-compat", allow_translation=True, cuda_source=SIMPLE)
        for result in (story, video):
            self.assertEqual(SHARED_APPLICATION_SCOPE, result["application_scope"])
            self.assertFalse(result["application_allowlist"])
            self.assertEqual("cfa3-cuda-compat", result["candidates"][0]["backend"])
            self.assertEqual("FULL_EQUIVALENCE", result["candidates"][0]["compatibility_result"])
            self.assertFalse(result["execution_authorized"])
            self.assertFalse(result["external_scale_runtime_dependency"])

    def test_translation_backend_is_blocked_without_explicit_opt_in(self):
        with mock.patch("fa3_cuda_compat_shared.enrich_accelerator_backends", return_value=[amd_with_native_compat()]):
            result = resolve_cuda_compatibility([], application_id="fa3.any-application", workload_id="job-1", requested_backend="cfa3-cuda-compat", allow_translation=False, cuda_source=SIMPLE)
        self.assertEqual("UNAVAILABLE", result["result"])
        self.assertIn("TRANSLATION_NOT_EXPLICITLY_ALLOWED", result["blocked_candidates"][0]["blocking_reasons"])

    def test_unsupported_source_is_user_visible_and_fail_closed(self):
        bad = SIMPLE + "\nvoid host(float *x){ k<<<1,32>>>(x); }"
        with mock.patch("fa3_cuda_compat_shared.enrich_accelerator_backends", return_value=[amd_with_native_compat()]):
            result = resolve_cuda_compatibility([], application_id="fa3.any-application", workload_id="job-2", requested_backend="cfa3-cuda-compat", allow_translation=True, cuda_source=bad)
        self.assertEqual("UNAVAILABLE", result["result"])
        self.assertIn("CUDA_SOURCE_SUBSET_UNSUPPORTED", result["blocked_candidates"][0]["blocking_reasons"])
        self.assertIn("CUDA_HOST_LAUNCH_SYNTAX", result["blocked_candidates"][0]["source_analysis"]["unsupported_features"])

    def test_shared_translation_api_returns_artifact_not_execution_authority(self):
        result = prepare_cuda_compat_translation(application_id="fa3.any-application", workload_id="job-3", cuda_source=SIMPLE, target_vendor="AMD")
        self.assertEqual("PASS", result["result"])
        self.assertEqual("FULL_EQUIVALENCE", result["compatibility_result"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["application_allowlist"])
        self.assertIn("#include <hip/hip_runtime.h>", result["translation"]["artifact"]["source"])

    def test_shared_intel_sycl_translation_discloses_reduction(self):
        result = prepare_cuda_compat_translation(application_id="fa3.any-application", workload_id="job-intel", cuda_source=SIMPLE, target_vendor="INTEL")
        self.assertEqual("PASS", result["result"])
        self.assertEqual("FUNCTIONALLY_REDUCED", result["compatibility_result"])
        self.assertIn("SYCL_HOST_QUEUE_LAUNCH_WRAPPER_REQUIRED", result["translation"]["artifact"]["limitations"])

    def test_shared_build_plan_fails_closed_on_unknown_nvcc_option(self):
        result = prepare_cuda_compat_build(application_id="fa3.any-application", workload_id="job-build", sources=["kernel.cu"], nvcc_args=["-O3","--unknown"], target_vendor="AMD", target_backend="hip")
        self.assertEqual("DENY", result["result"])
        self.assertIn("UNSUPPORTED_NVCC_OPTION:--unknown", result["build_plan"]["findings"])
        self.assertFalse(result["compiler_execution_authorized"])

    def test_shared_runtime_inspection_is_not_execution_authority(self):
        result = inspect_cuda_runtime_compatibility(application_id="fa3.any-application", workload_id="job-runtime", symbols=["cudaMalloc","cudaFree"], target_vendor="INTEL", target_backend="sycl")
        self.assertEqual("PASS", result["result"])
        self.assertEqual("FUNCTIONALLY_REDUCED", result["runtime_map"]["classification"])
        self.assertFalse(result["execution_authorized"])

    def test_unknown_explicit_backend_fails_without_fallback(self):
        result = resolve_cuda_compatibility([], application_id="fa3.any-application", workload_id="job-4", requested_backend="invented-backend", allow_translation=True)
        self.assertEqual("DENY", result["result"])
        self.assertEqual("UNSUPPORTED_EXPLICIT_BACKEND", result["reason"])
        self.assertEqual([], result["candidates"])


if __name__ == "__main__":
    unittest.main()
