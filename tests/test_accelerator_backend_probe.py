from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_accelerator_backend_probe import enrich_accelerator_backends
from fa3_hardware_discovery import (
    AcceleratorBackendDescriptor,
    AcceleratorDeviceDescriptor,
)


def device(vendor, bdf, *, kind="gpu", vendor_id="0xffff", device_id="0x0001"):
    return AcceleratorDeviceDescriptor(
        discovery_id=f"pci:{bdf}",
        kind=kind,
        vendor=vendor,
        vendor_id=vendor_id,
        device_id=device_id,
        pci_bdf=bdf,
    )


def backend_map(row):
    return {backend.name: backend for backend in row.backends}


class AcceleratorBackendProbeTests(unittest.TestCase):
    def common_patches(self):
        return (
            mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={}),
            mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()}),
            mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()}),
            mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[
                {"detected": False, "usable": False, "version": None, "evidence": ()},
                {"detected": False, "usable": False, "version": None, "evidence": ()},
            ]),
            mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()}),
        )

    def test_available_backend_requires_device_binding(self):
        with self.assertRaises(ValueError):
            AcceleratorBackendDescriptor(
                name="vulkan",
                backend_class="portable",
                detected=True,
                available=True,
                binding_scope="HOST_UNBOUND",
            )

    @mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[
        {"detected": False, "usable": False, "version": None, "evidence": ()},
        {"detected": False, "usable": False, "version": None, "evidence": ()},
    ])
    @mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf")
    def test_nvidia_cuda_requires_exact_bdf_binding(self, nvidia, *_):
        nvidia.return_value = {
            "0000:3b:00.0": {
                "uuid": "GPU-test-uuid",
                "driver_version": "610.43.02",
                "runtime_version": "13.2",
            }
        }
        rows = enrich_accelerator_backends([
            device("NVIDIA", "0000:3b:00.0", vendor_id="0x10de"),
            device("NVIDIA", "0000:4b:00.0", vendor_id="0x10de"),
        ])
        first = backend_map(rows[0])
        second = backend_map(rows[1])
        self.assertTrue(first["cuda"].available)
        self.assertEqual(first["cuda"].binding_scope, "DEVICE")
        self.assertEqual(rows[0].stable_device_id, "GPU-test-uuid")
        self.assertNotIn("cuda", second)

    @mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[
        {"detected": False, "usable": False, "version": None, "evidence": ()},
        {"detected": False, "usable": False, "version": None, "evidence": ()},
    ])
    @mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value={"detected": True, "usable": True, "version": "7.0", "evidence": ("rocminfo",)})
    @mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={})
    def test_single_amd_device_can_bind_rocm(self, *_):
        row = enrich_accelerator_backends([
            device("AMD", "0000:0a:00.0", vendor_id="0x1002")
        ])[0]
        rocm = backend_map(row)["rocm"]
        self.assertTrue(rocm.detected)
        self.assertTrue(rocm.available)
        self.assertEqual(rocm.binding_scope, "DEVICE")

    @mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[
        {"detected": False, "usable": False, "version": None, "evidence": ()},
        {"detected": False, "usable": False, "version": None, "evidence": ()},
    ])
    @mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value={"detected": True, "usable": True, "version": "7.0", "evidence": ("rocminfo",)})
    @mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={})
    def test_ambiguous_multi_amd_rocm_is_host_unbound(self, *_):
        rows = enrich_accelerator_backends([
            device("AMD", "0000:0a:00.0", vendor_id="0x1002"),
            device("AMD", "0000:0b:00.0", vendor_id="0x1002"),
        ])
        for row in rows:
            rocm = backend_map(row)["rocm"]
            self.assertTrue(rocm.detected)
            self.assertFalse(rocm.available)
            self.assertEqual(rocm.binding_scope, "HOST_UNBOUND")

    @mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[
        {"detected": True, "usable": True, "version": "1.4", "evidence": ("vulkaninfo",)},
        {"detected": False, "usable": False, "version": None, "evidence": ()},
    ])
    @mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={})
    def test_portable_backend_on_multi_gpu_is_not_device_authority(self, *_):
        rows = enrich_accelerator_backends([
            device("UNKNOWN", "0000:0a:00.0"),
            device("UNKNOWN", "0000:0b:00.0"),
        ])
        for row in rows:
            vulkan = backend_map(row)["vulkan"]
            self.assertFalse(vulkan.available)
            self.assertEqual(vulkan.binding_scope, "HOST_UNBOUND")

    @mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value={"detected": True, "usable": True, "version": None, "evidence": ("explicit-zluda",)})
    @mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[
        {"detected": False, "usable": False, "version": None, "evidence": ()},
        {"detected": False, "usable": False, "version": None, "evidence": ()},
    ])
    @mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value={"detected": True, "usable": True, "version": "7.0", "evidence": ("rocminfo",)})
    @mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={})
    def test_zluda_is_explicit_translation_path_after_rocm_binding(self, *_):
        row = enrich_accelerator_backends([
            device("AMD", "0000:0a:00.0", vendor_id="0x1002")
        ])[0]
        backends = backend_map(row)
        self.assertTrue(backends["rocm"].available)
        self.assertTrue(backends["zluda"].available)
        self.assertEqual(backends["zluda"].backend_class, "translation")
        self.assertTrue(backends["zluda"].experimental)

    @mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value={"detected": True, "usable": True, "version": None, "evidence": ("explicit-zluda",)})
    @mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[
        {"detected": False, "usable": False, "version": None, "evidence": ()},
        {"detected": False, "usable": False, "version": None, "evidence": ()},
    ])
    @mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value={"detected": False, "usable": False, "version": None, "evidence": ()})
    @mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value={"detected": True, "usable": False, "version": "7.0", "evidence": ("rocminfo",)})
    @mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={})
    def test_zluda_cannot_be_available_without_device_bound_rocm(self, *_):
        row = enrich_accelerator_backends([
            device("AMD", "0000:0a:00.0", vendor_id="0x1002")
        ])[0]
        backends = backend_map(row)
        self.assertFalse(backends["rocm"].available)
        self.assertFalse(backends["zluda"].available)
        self.assertEqual(backends["zluda"].binding_scope, "HOST_UNBOUND")


if __name__ == "__main__":
    unittest.main()
