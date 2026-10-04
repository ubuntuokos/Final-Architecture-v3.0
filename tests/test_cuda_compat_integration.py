from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_accelerator_backend_probe import enrich_accelerator_backends
from fa3_hardware_discovery import AcceleratorDeviceDescriptor


def device(vendor: str, bdf: str, vendor_id: str) -> AcceleratorDeviceDescriptor:
    return AcceleratorDeviceDescriptor(discovery_id=f"pci:{bdf}", kind="gpu", vendor=vendor, vendor_id=vendor_id, device_id="0x0001", pci_bdf=bdf)


def backend_map(row):
    return {backend.name: backend for backend in row.backends}


NO_BACKEND = {"detected": False, "usable": False, "version": None, "evidence": ()}
AMD_NATIVE = {"detected": True, "usable": True, "version": "7.0", "evidence": ("test:rocm",)}
INTEL_NATIVE = {"detected": True, "usable": True, "version": "1.0", "evidence": ("test:level-zero",)}


class NativeCudaCompatIntegrationTests(unittest.TestCase):
    def base_patches(self, *, rocm=NO_BACKEND, level_zero=NO_BACKEND):
        return (
            mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={}),
            mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value=rocm),
            mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value=level_zero),
            mock.patch("fa3_accelerator_backend_probe._portable_probe", side_effect=[NO_BACKEND, NO_BACKEND]),
            mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value=NO_BACKEND),
        )

    def test_amd_native_rocm_exposes_central_translation_backend(self):
        ps = self.base_patches(rocm=AMD_NATIVE)
        with ps[0], ps[1], ps[2], ps[3], ps[4]:
            row = enrich_accelerator_backends([device("AMD","0000:0a:00.0","0x1002")])[0]
        backend = backend_map(row)["cfa3-cuda-compat"]
        self.assertTrue(backend.available)
        self.assertEqual("translation", backend.backend_class)
        self.assertEqual("DEVICE", backend.binding_scope)
        self.assertIn("cfa3-native", backend.framework_backends)
        self.assertIn("compatibility-classification:FULL_EQUIVALENCE", backend.evidence_sources)
        self.assertIn("external-scale-runtime-dependency:false", backend.evidence_sources)

    def test_intel_level_zero_exposes_same_central_translation_backend_with_sycl(self):
        ps = self.base_patches(level_zero=INTEL_NATIVE)
        with ps[0], ps[1], ps[2], ps[3], ps[4]:
            row = enrich_accelerator_backends([device("INTEL","0000:0b:00.0","0x8086")])[0]
        backend = backend_map(row)["cfa3-cuda-compat"]
        self.assertTrue(backend.available)
        self.assertEqual("translation", backend.backend_class)
        self.assertIn("level-zero", backend.framework_backends)
        self.assertIn("sycl", backend.framework_backends)
        self.assertIn("compatibility-classification:FUNCTIONALLY_REDUCED", backend.evidence_sources)

    def test_multiple_amd_devices_do_not_get_implicit_device_binding(self):
        ps = self.base_patches(rocm=AMD_NATIVE)
        devices = [device("AMD","0000:0a:00.0","0x1002"),device("AMD","0000:0b:00.0","0x1002")]
        with ps[0], ps[1], ps[2], ps[3], ps[4]:
            rows = enrich_accelerator_backends(devices)
        for row in rows:
            backend = backend_map(row)["cfa3-cuda-compat"]
            self.assertFalse(backend.available)
            self.assertEqual("HOST_UNBOUND", backend.binding_scope)


if __name__ == "__main__":
    unittest.main()
