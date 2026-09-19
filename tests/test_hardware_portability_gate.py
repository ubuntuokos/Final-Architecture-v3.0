import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hardware_portability_gate import (
    CAPABILITY_COUNT,
    CUDA_COMPUTE_CAPABILITY_MIN,
    evaluate,
    portable_hardware_floor_valid,
    scan_repository,
)


class HardwarePortabilityGateTests(unittest.TestCase):
    def test_repository_gate_passes(self):
        result = evaluate(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(CAPABILITY_COUNT, result["capability_count"])
        self.assertEqual(0, result["repository_audit"]["blocking_hardcoded_production_assumptions"])
        self.assertFalse(result["current_host_runtime_promotion_claim"])
        self.assertEqual(8.6, result["gpu_floor"]["cuda_compute_capability_min"])
        self.assertFalse(result["gpu_floor"]["sku_series_authority"])

    def test_minimum_and_larger_hosts_are_admitted(self):
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=1,
            gpu_compute_capability=8.6,
        ))
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=2,
            physical_cores_per_qualifying_cpu=24,
            gpu_count=4,
            gpu_compute_capability=12.0,
        ))

    def test_rtx_a1000_class_cc86_is_admitted_without_sku_exception(self):
        self.assertEqual(8.6, CUDA_COMPUTE_CAPABILITY_MIN)
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=1,
            gpu_compute_capability=8.6,
            gpu_vendor="NVIDIA",
        ))

    def test_marketing_series_is_not_an_admission_input(self):
        profile = json.loads((ROOT / "canonical/profiles/FA3-HARDWARE-BASELINE-001.json").read_text(encoding="utf-8"))
        gpu = profile["portable_minimum"]["gpu"]
        self.assertNotIn("rtx_series_floor", gpu)
        self.assertFalse(gpu["sku_series_admission_authority"])
        self.assertEqual(8.6, gpu["cuda_compute_capability_min"])
        self.assertTrue(gpu["vram_size_pin"].startswith("FORBIDDEN"))

    def test_no_fixed_upper_bound(self):
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=8,
            physical_cores_per_qualifying_cpu=64,
            gpu_count=16,
            gpu_compute_capability=12.0,
        ))

    def test_floor_rejects_under_minimum_hosts(self):
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=7,
            gpu_count=1,
            gpu_compute_capability=8.6,
        ))
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=0,
            gpu_compute_capability=12.0,
        ))
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=1,
            gpu_compute_capability=8.0,
        ))
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=1,
            gpu_compute_capability=12.0,
            gpu_vendor="OTHER",
        ))

    def test_runtime_fixed_cuda_list_is_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "bad.py").write_text(
                'import os\nos.environ["CUDA_VISIBLE_DEVICES"] = "0,1"\n',
                encoding="utf-8",
            )
            audit = scan_repository(root)
            self.assertEqual("FAIL", audit["result"])
            self.assertEqual(1, audit["blocking_hardcoded_production_assumptions"])

    def test_single_fixed_cuda_visible_device_is_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "bad.py").write_text(
                'import os\nos.environ["CUDA_VISIBLE_DEVICES"] = "0"\n',
                encoding="utf-8",
            )
            audit = scan_repository(root)
            self.assertEqual("FAIL", audit["result"])
            self.assertTrue(any(x["kind"] == "FIXED_CUDA_VISIBLE_DEVICES_LIST" for x in audit["blocking_matches"]))

    def test_arbitrary_runtime_sku_and_bdf_are_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "current_host_bad.py").write_text(
                'GPU = "RTX A1000"\nPCI = "0000:65:00.0"\n',
                encoding="utf-8",
            )
            audit = scan_repository(root)
            self.assertEqual("FAIL", audit["result"])
            kinds = {x["kind"] for x in audit["blocking_matches"]}
            self.assertIn("GPU_SKU_RTX", kinds)
            self.assertIn("LITERAL_PCI_BDF", kinds)

    def test_apps_cpp_and_qml_are_runtime_audit_surfaces(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "apps" / "demo").mkdir(parents=True)
            (root / "apps" / "demo" / "bad.cpp").write_text(
                'const char *gpu = "RTX 5090";\n',
                encoding="utf-8",
            )
            audit = scan_repository(root)
            self.assertEqual("FAIL", audit["result"])
            self.assertTrue(any(x["path"].endswith("bad.cpp") for x in audit["blocking_matches"]))

    def test_current_host_tooling_is_not_blanket_exempt_from_literal_machine_pins(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "fa3_demo_current_host.py").write_text(
                'TARGET = "0000:AF:00.0"\n',
                encoding="utf-8",
            )
            audit = scan_repository(root)
            self.assertEqual("FAIL", audit["result"])
            self.assertTrue(any(x["kind"] == "LITERAL_PCI_BDF" for x in audit["blocking_matches"]))

    def test_reference_evidence_hardware_tuple_is_non_normative(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical" / "references"
            p.mkdir(parents=True)
            (p / "fixture.md").write_text(
                "Reference evidence only: E5-2696 v4, RTX 3080, 44C/88T.",
                encoding="utf-8",
            )
            audit = scan_repository(root)
            self.assertEqual("PASS", audit["result"])
            self.assertGreaterEqual(audit["non_normative_hardware_mentions"], 3)

    def test_runtime_reference_fixture_is_allowed_only_when_marked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "src" / "fixture.py").write_text(
                '# reference topology fixture only\nMODEL = "E5-2696 v4"\n',
                encoding="utf-8",
            )
            audit = scan_repository(root)
            self.assertEqual("PASS", audit["result"])
            self.assertGreaterEqual(audit["non_normative_hardware_mentions"], 1)

    def test_reference_evidence_cannot_promote_runtime(self):
        obj = json.loads(
            (ROOT / "evidence/reference/hardware-portability-ci-2026-09-03.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual("PASS", obj["status"])
        self.assertFalse(obj["current_host_runtime_evidence"])
        self.assertFalse(obj["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
