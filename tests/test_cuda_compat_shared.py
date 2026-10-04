from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_cuda_compat_shared import SHARED_APPLICATION_SCOPE, resolve_cuda_compatibility
from fa3_hardware_discovery import AcceleratorBackendDescriptor, AcceleratorDeviceDescriptor


def amd_with_scale():
    return AcceleratorDeviceDescriptor(
        discovery_id="pci:0000:0a:00.0",
        kind="gpu",
        vendor="AMD",
        vendor_id="0x1002",
        device_id="0x0001",
        pci_bdf="0000:0a:00.0",
        backends=(
            AcceleratorBackendDescriptor(
                name="scale-cuda",
                backend_class="translation",
                available=True,
                detected=True,
                binding_scope="DEVICE",
                runtime_version="1.2.0",
                framework_backends=("cuda-compat", "scale"),
                experimental=True,
                evidence_sources=("test:scale",),
            ),
        ),
    )


class SharedCudaCompatTests(unittest.TestCase):
    def test_all_applications_use_the_same_central_entrypoint_without_allowlist(self):
        with mock.patch("fa3_cuda_compat_shared.enrich_accelerator_backends", return_value=[amd_with_scale()]):
            story = resolve_cuda_compatibility(
                [],
                application_id="fa3.story-screenplay",
                workload_id="story-job-1",
                requested_backend="scale-cuda",
                allow_translation=True,
            )
            video = resolve_cuda_compatibility(
                [],
                application_id="fa3.video-editor",
                workload_id="video-job-1",
                requested_backend="scale-cuda",
                allow_translation=True,
            )
        self.assertEqual(story["application_scope"], SHARED_APPLICATION_SCOPE)
        self.assertEqual(video["application_scope"], SHARED_APPLICATION_SCOPE)
        self.assertFalse(story["application_allowlist"])
        self.assertFalse(video["application_allowlist"])
        self.assertEqual(story["candidates"][0]["backend"], "scale-cuda")
        self.assertEqual(video["candidates"][0]["backend"], "scale-cuda")
        self.assertFalse(story["execution_authorized"])
        self.assertFalse(video["execution_authorized"])

    def test_translation_backend_is_blocked_without_explicit_opt_in(self):
        with mock.patch("fa3_cuda_compat_shared.enrich_accelerator_backends", return_value=[amd_with_scale()]):
            result = resolve_cuda_compatibility(
                [],
                application_id="fa3.any-application",
                workload_id="job-1",
                requested_backend="scale-cuda",
                allow_translation=False,
            )
        self.assertEqual(result["result"], "UNAVAILABLE")
        self.assertEqual(result["candidates"], [])
        self.assertIn(
            "TRANSLATION_NOT_EXPLICITLY_ALLOWED",
            result["blocked_candidates"][0]["blocking_reasons"],
        )

    def test_unknown_explicit_backend_fails_closed_without_fallback(self):
        result = resolve_cuda_compatibility(
            [],
            application_id="fa3.any-application",
            workload_id="job-2",
            requested_backend="invented-backend",
            allow_translation=True,
        )
        self.assertEqual(result["result"], "DENY")
        self.assertEqual(result["reason"], "UNSUPPORTED_EXPLICIT_BACKEND")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["candidates"], [])

    def test_application_identity_is_required_but_not_allowlisted(self):
        result = resolve_cuda_compatibility(
            [],
            application_id="",
            workload_id="job-3",
        )
        self.assertEqual(result["result"], "DENY")
        self.assertEqual(result["reason"], "APPLICATION_AND_WORKLOAD_ID_REQUIRED")
        self.assertFalse(result["application_allowlist"])


if __name__ == "__main__":
    unittest.main()
