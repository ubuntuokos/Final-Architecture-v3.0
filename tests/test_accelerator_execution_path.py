from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_accelerator_execution_path import (
    ExecutionPathError,
    bind_hrb_execution_path,
    compatible_execution_paths,
    execution_path_matches,
    validate_execution_requirement,
)


class AcceleratorExecutionPathTests(unittest.TestCase):
    def setUp(self):
        self.cuda = {
            "accelerator_id": "accel:nvidia:1",
            "backend": "cuda",
            "backend_class": "native",
            "framework_backend": "pytorch-cuda",
            "available": True,
            "health": "READY",
        }
        self.rocm = {
            "accelerator_id": "accel:amd:1",
            "backend": "rocm",
            "backend_class": "native",
            "framework_backend": "pytorch-rocm",
            "available": True,
            "health": "READY",
        }
        self.xpu = {
            "accelerator_id": "accel:intel:1",
            "backend": "level-zero",
            "backend_class": "native",
            "framework_backend": "pytorch-xpu",
            "available": True,
            "health": "READY",
        }
        self.vulkan = {
            "accelerator_id": "accel:portable:1",
            "backend": "vulkan",
            "backend_class": "portable",
            "framework_backend": "vulkan-compute",
            "available": True,
            "health": "READY",
        }
        self.zluda = {
            "accelerator_id": "accel:translation:1",
            "backend": "zluda",
            "backend_class": "translation",
            "framework_backend": "cuda-compat",
            "available": True,
            "health": "READY",
        }

    def test_cuda_only_rejects_rocm(self):
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "cuda", "backend_class": "native", "framework_backend": "pytorch-cuda"}
            ],
            "allow_translation": False,
        }
        self.assertTrue(execution_path_matches(requirement, self.cuda))
        self.assertFalse(execution_path_matches(requirement, self.rocm))

    def test_vendor_neutral_framework_requirement_accepts_multiple_native_paths(self):
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "cuda", "backend_class": "native", "framework_backend": "pytorch-cuda"},
                {"backend": "rocm", "backend_class": "native", "framework_backend": "pytorch-rocm"},
                {"backend": "level-zero", "backend_class": "native", "framework_backend": "pytorch-xpu"},
            ],
            "allow_translation": False,
        }
        matched = compatible_execution_paths(requirement, [self.cuda, self.rocm, self.xpu, self.vulkan])
        self.assertEqual(len(matched), 3)

    def test_portable_vulkan_is_separate_execution_path(self):
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "vulkan", "backend_class": "portable", "framework_backend": "vulkan-compute"}
            ],
            "allow_translation": False,
        }
        self.assertTrue(execution_path_matches(requirement, self.vulkan))
        self.assertFalse(execution_path_matches(requirement, self.cuda))

    def test_canonical_descriptor_name_and_class_aliases_are_accepted(self):
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "vulkan", "backend_class": "portable", "framework_backend": "vulkan-compute"}
            ],
            "allow_translation": False,
        }
        descriptor = {
            "name": "vulkan",
            "class": "portable",
            "detected": True,
            "available": True,
            "binding_scope": "DEVICE",
            "framework_backends": ["vulkan-compute"],
            "health": "READY",
        }
        self.assertTrue(execution_path_matches(requirement, descriptor))

    def test_host_unbound_descriptor_is_never_execution_compatible(self):
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "vulkan", "backend_class": "portable"}
            ],
            "allow_translation": False,
        }
        descriptor = {
            "name": "vulkan",
            "class": "portable",
            "detected": True,
            "available": False,
            "binding_scope": "HOST_UNBOUND",
            "health": "READY",
        }
        self.assertFalse(execution_path_matches(requirement, descriptor))

    def test_translation_is_denied_by_default(self):
        self.assertFalse(execution_path_matches({}, self.zluda))
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "zluda", "backend_class": "translation", "framework_backend": "cuda-compat"}
            ],
            "allow_translation": False,
        }
        self.assertIn("TRANSLATION_PATH_NOT_EXPLICITLY_ALLOWED:0", validate_execution_requirement(requirement))
        self.assertFalse(execution_path_matches(requirement, self.zluda))

    def test_translation_requires_explicit_opt_in(self):
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "zluda", "backend_class": "translation", "framework_backend": "cuda-compat"}
            ],
            "allow_translation": True,
        }
        self.assertEqual(validate_execution_requirement(requirement), [])
        self.assertTrue(execution_path_matches(requirement, self.zluda))

    def test_hrb_binding_requires_authority_and_exact_device(self):
        requirement = {
            "acceptable_execution_paths": [
                {"backend": "cuda", "backend_class": "native", "framework_backend": "pytorch-cuda"}
            ],
            "allow_translation": False,
        }
        with self.assertRaises(ExecutionPathError):
            bind_hrb_execution_path(
                authority_receipt="NOT_HRB",
                accelerator_id=self.cuda["accelerator_id"],
                requirement=requirement,
                candidate=self.cuda,
            )
        with self.assertRaises(ExecutionPathError):
            bind_hrb_execution_path(
                authority_receipt="HRB_PLACEMENT_RECEIPT",
                accelerator_id="different-device",
                requirement=requirement,
                candidate=self.cuda,
            )
        binding = bind_hrb_execution_path(
            authority_receipt="HRB_PLACEMENT_RECEIPT",
            accelerator_id=self.cuda["accelerator_id"],
            requirement=requirement,
            candidate=self.cuda,
        )
        self.assertEqual(binding["backend"], "cuda")
        self.assertEqual(binding["fallback_policy"], "DENY_SILENT_SUBSTITUTION")


if __name__ == "__main__":
    unittest.main()
