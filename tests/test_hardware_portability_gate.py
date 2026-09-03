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

    def test_minimum_and_larger_hosts_are_admitted(self):
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=1,
            gpu_rtx_series=30,
        ))
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=2,
            physical_cores_per_qualifying_cpu=24,
            gpu_count=4,
            gpu_rtx_series=50,
        ))

    def test_no_fixed_upper_bound(self):
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=8,
            physical_cores_per_qualifying_cpu=64,
            gpu_count=16,
            gpu_rtx_series=60,
        ))

    def test_floor_rejects_under_minimum_hosts(self):
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=7,
            gpu_count=1,
            gpu_rtx_series=30,
        ))
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=0,
            gpu_rtx_series=50,
        ))
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1,
            physical_cores_per_qualifying_cpu=8,
            gpu_count=1,
            gpu_rtx_series=20,
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
