import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from fa3_hardware_portability_gate import (
    CAPABILITY_COUNT,
    REFERENCE_PLATFORM_FAMILIES,
    REFERENCE_VENDOR_FAMILIES,
    evaluate,
    portable_hardware_floor_valid,
    scan_repository,
)

class HardwarePortabilityGateTests(unittest.TestCase):
    def test_repository_gate_passes(self):
        result=evaluate(ROOT)
        self.assertEqual("PASS",result["result"],result)
        self.assertEqual(CAPABILITY_COUNT,result["capability_count"])
        self.assertEqual("FORBIDDEN",result["accelerator_floor"]["vendor_pin"])
        self.assertEqual("FORBIDDEN",result["accelerator_floor"]["runtime_api_pin"])
        self.assertFalse(result["current_host_runtime_promotion_claim"])

    def test_vendor_neutral_reference_families(self):
        self.assertTrue({"NVIDIA","AMD","INTEL"} <= REFERENCE_VENDOR_FAMILIES)
        self.assertIn("NVIDIA_DGX",REFERENCE_PLATFORM_FAMILIES)
        for vendor in ("NVIDIA","AMD","INTEL"):
            self.assertTrue(portable_hardware_floor_valid(
                cpu_packages=1, physical_cores_per_qualifying_cpu=8,
                accelerator_count=1, accelerator_vendor=vendor,
            ))

    def test_vendor_specific_capability_is_not_global_floor(self):
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=1, physical_cores_per_qualifying_cpu=8,
            gpu_count=1, gpu_vendor="AMD", gpu_compute_capability=0.0,
        ))
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1, physical_cores_per_qualifying_cpu=8,
            accelerator_count=1, accelerator_vendor="AMD", workload_compatible=False,
        ))

    def test_floor_rejects_only_global_minimum_failures(self):
        self.assertFalse(portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=7,accelerator_count=1))
        self.assertFalse(portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=0))
        self.assertTrue(portable_hardware_floor_valid(cpu_packages=4,physical_cores_per_qualifying_cpu=64,accelerator_count=16,accelerator_vendor="FUTURE_VENDOR"))

    def test_canonical_profile_has_no_vendor_or_runtime_pin(self):
        obj=json.loads((ROOT/"canonical/profiles/FA3-HARDWARE-BASELINE-001.json").read_text(encoding="utf-8"))
        gpu=obj["portable_minimum"]["gpu"]
        self.assertEqual("FORBIDDEN",gpu["vendor_pin"])
        self.assertEqual("FORBIDDEN",gpu["global_runtime_api_pin"])
        self.assertTrue(gpu["global_cuda_compute_capability_floor"].startswith("FORBIDDEN"))
        self.assertTrue({"NVIDIA","AMD","INTEL"} <= set(gpu["supported_reference_vendor_families"]))
        self.assertIn("NVIDIA_DGX",gpu["supported_reference_platform_families"])

    def test_runtime_fixed_vendor_lists_are_blocking(self):
        for line in (
            'CUDA_VISIBLE_DEVICES="0,1"\n',
            'ROCR_VISIBLE_DEVICES="0,1"\n',
            'ZE_AFFINITY_MASK="0.0"\n',
            'DEVICE="0000:05:00.0"\n',
        ):
            with self.subTest(line=line), tempfile.TemporaryDirectory() as td:
                root=Path(td); (root/"apps").mkdir()
                (root/"apps"/"bad.py").write_text(line,encoding="utf-8")
                audit=scan_repository(root)
                self.assertEqual("FAIL",audit["result"],audit)

    def test_apps_qml_cpp_are_audited(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"apps").mkdir()
            (root/"apps"/"bad.qml").write_text('property string gpu: "RTX 3090"\n',encoding="utf-8")
            audit=scan_repository(root)
            self.assertEqual("FAIL",audit["result"],audit)

    def test_reference_evidence_hardware_tuple_is_non_normative(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"canonical"/"references"; p.mkdir(parents=True)
            (p/"fixture.md").write_text("Reference evidence only: Xeon E5-2697 v4, RTX 3090, 0000:05:00.0.",encoding="utf-8")
            audit=scan_repository(root)
            self.assertEqual("PASS",audit["result"])
            self.assertGreaterEqual(audit["non_normative_hardware_mentions"],2)

if __name__=="__main__":
    unittest.main()
