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
    return AcceleratorDeviceDescriptor(
        discovery_id=f"pci:{bdf}",
        kind="gpu",
        vendor=vendor,
        vendor_id=vendor_id,
        device_id="0x0001",
        pci_bdf=bdf,
    )


def backend_map(row):
    return {backend.name: backend for backend in row.backends}


NO_PORTABLE = {
    "detected": False,
    "usable": False,
    "version": None,
    "evidence": (),
}


class ScaleBackendIntegrationTests(unittest.TestCase):
    def patches(self, scale):
        return (
            mock.patch("fa3_accelerator_backend_probe._nvidia_cuda_by_bdf", return_value={}),
            mock.patch("fa3_accelerator_backend_probe._rocm_probe", return_value=NO_PORTABLE),
            mock.patch("fa3_accelerator_backend_probe._level_zero_probe", return_value=NO_PORTABLE),
            mock.patch(
                "fa3_accelerator_backend_probe._portable_probe",
                side_effect=[NO_PORTABLE, NO_PORTABLE],
            ),
            mock.patch("fa3_accelerator_backend_probe._zluda_probe", return_value=NO_PORTABLE),
            mock.patch("fa3_accelerator_backend_probe.probe_scale", return_value=scale),
        )

    def admitted_receipt(self):
        return {
            "schema": "fa3.scale-execution-rights-receipt.v1",
            "authority": "FA3-AUTH-SECURITY-GOV-001",
            "subject_id": "FA3-EXTERNAL-SCALE-TOOLKIT",
            "result": "PASS",
            "execution_allowed": True,
            "commercial_use_allowed": True,
            "entitlement_reference": "secret-broker://license/scale/customer-entitlement",
            "raw_secret_material_present": False,
        }

    def test_exact_amd_bdf_plus_rights_admits_scale_translation_backend(self):
        scale = {
            "detected": True,
            "usable": True,
            "version": "1.2.0",
            "devices": {
                "0000:0a:00.0": {
                    "ordinal": "0",
                    "name": "AMD Radeon",
                    "target": "gfx1100",
                    "vendor": "AMD",
                }
            },
            "evidence": ("scaleinfo:rc=0",),
        }
        ps = self.patches(scale)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5]:
            row = enrich_accelerator_backends(
                [device("AMD", "0000:0a:00.0", "0x1002")],
                scale_rights_receipt=self.admitted_receipt(),
            )[0]
        backend = backend_map(row)["scale-cuda"]
        self.assertTrue(backend.available)
        self.assertEqual("translation", backend.backend_class)
        self.assertEqual("DEVICE", backend.binding_scope)
        self.assertTrue(backend.experimental)
        self.assertIn("cuda-compat", backend.framework_backends)

    def test_scale_detected_but_rights_missing_is_not_available(self):
        scale = {
            "detected": True,
            "usable": True,
            "version": "1.2.0",
            "devices": {
                "0000:0a:00.0": {
                    "ordinal": "0",
                    "name": "AMD Radeon",
                    "target": "gfx1100",
                    "vendor": "AMD",
                }
            },
            "evidence": ("scaleinfo:rc=0",),
        }
        ps = self.patches(scale)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5]:
            row = enrich_accelerator_backends(
                [device("AMD", "0000:0a:00.0", "0x1002")]
            )[0]
        backend = backend_map(row)["scale-cuda"]
        self.assertFalse(backend.available)
        self.assertEqual("DEVICE", backend.binding_scope)
        self.assertIn("scale-rights:FAIL", backend.evidence_sources)

    def test_scale_does_not_claim_intel_support(self):
        scale = {
            "detected": True,
            "usable": True,
            "version": "1.2.0",
            "devices": {
                "0000:0a:00.0": {
                    "ordinal": "0",
                    "name": "AMD Radeon",
                    "target": "gfx1100",
                    "vendor": "AMD",
                }
            },
            "evidence": ("scaleinfo:rc=0",),
        }
        ps = self.patches(scale)
        with ps[0], ps[1], ps[2], ps[3], ps[4], ps[5]:
            row = enrich_accelerator_backends(
                [device("INTEL", "0000:0a:00.0", "0x8086")],
                scale_rights_receipt=self.admitted_receipt(),
            )[0]
        self.assertNotIn("scale-cuda", backend_map(row))


if __name__ == "__main__":
    unittest.main()
