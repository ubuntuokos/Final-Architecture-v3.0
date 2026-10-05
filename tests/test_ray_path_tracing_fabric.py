from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_ray_path_tracing_fabric import RayTracingBackendDescriptor, cpu_software_reference_descriptor, resolve_ray_path_tracing


class RayPathTracingFabricTests(unittest.TestCase):
    def test_cpu_software_path_exists_but_requires_runtime_admission(self):
        result = resolve_ray_path_tracing(
            [cpu_software_reference_descriptor()],
            application_id="fa3.test", workload_id="cpu", trace_mode="RAY_TRACING",
        )
        self.assertEqual("UNAVAILABLE", result["result"])
        self.assertIn("RUNTIME_NOT_ADMITTED", result["blocked_candidates"][0]["blocking_reasons"])
        self.assertFalse(result["execution_authorized"])

    def test_cpu_only_path_can_be_candidate_without_hardware_traversal(self):
        result = resolve_ray_path_tracing(
            [cpu_software_reference_descriptor(provider_admitted=True, runtime_admitted=True)],
            application_id="fa3.test", workload_id="cpu", trace_mode="PATH_TRACING", hardware_traversal="DISABLED",
        )
        self.assertEqual("CANDIDATE_AVAILABLE", result["result"])
        self.assertEqual("SOFTWARE_CPU", result["candidates"][0]["compatibility_class"])
        self.assertTrue(result["path_tracing_progressive_accumulation_required"])
        self.assertFalse(result["automatic_backend_selection"])

    def test_exact_device_binding_is_required_for_gpu(self):
        gpu = RayTracingBackendDescriptor(
            backend_id="amd0", vendor="AMD", api="VULKAN_RT", available=True, device_bound=False,
            supported_modes=("RAY_TRACING",), hardware_traversal=True, compatibility_class="PORTABLE",
            provider_admitted=True, runtime_admitted=True,
        )
        result = resolve_ray_path_tracing([gpu], application_id="fa3.test", workload_id="gpu", trace_mode="RAY_TRACING")
        self.assertEqual("UNAVAILABLE", result["result"])
        self.assertIn("EXACT_DEVICE_OR_CPU_HOST_BINDING_REQUIRED", result["blocked_candidates"][0]["blocking_reasons"])

    def test_no_silent_fallback_from_explicit_backend(self):
        gpu = RayTracingBackendDescriptor(
            backend_id="amd0", vendor="AMD", api="VULKAN_RT", available=True, device_bound=True,
            supported_modes=("RAY_TRACING",), hardware_traversal=True, compatibility_class="PORTABLE",
            provider_admitted=True, runtime_admitted=True,
        )
        result = resolve_ray_path_tracing(
            [gpu], application_id="fa3.test", workload_id="gpu", trace_mode="RAY_TRACING", requested_backend_id="intel0",
        )
        self.assertEqual("UNAVAILABLE", result["result"])
        self.assertEqual("EXPLICIT_BACKEND_NOT_FOUND", result["reason"])
        self.assertFalse(result["silent_fallback"])

    def test_hardware_traversal_requirement_blocks_cpu(self):
        result = resolve_ray_path_tracing(
            [cpu_software_reference_descriptor(provider_admitted=True, runtime_admitted=True)],
            application_id="fa3.test", workload_id="cpu", trace_mode="RAY_TRACING", hardware_traversal="REQUIRED",
        )
        self.assertEqual("UNAVAILABLE", result["result"])
        self.assertIn("HARDWARE_TRAVERSAL_REQUIRED", result["blocked_candidates"][0]["blocking_reasons"])

    def test_neural_denoise_is_model_router_handoff_not_backend_authority(self):
        gpu = RayTracingBackendDescriptor(
            backend_id="nvidia0", vendor="NVIDIA", api="VULKAN_RT", available=True, device_bound=True,
            supported_modes=("PATH_TRACING",), hardware_traversal=True, compatibility_class="NATIVE",
            provider_admitted=True, runtime_admitted=True,
        )
        result = resolve_ray_path_tracing(
            [gpu], application_id="fa3.test", workload_id="pt", trace_mode="PATH_TRACING", neural_denoise=True,
        )
        self.assertTrue(result["model_router_required_for_neural_denoise"])
        self.assertTrue(result["candidates"][0]["neural_denoise_handoff_required"])
        self.assertFalse(result["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
