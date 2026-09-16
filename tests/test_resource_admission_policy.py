from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_resource_admission_policy import (  # noqa: E402
    classify_requirements,
    metric_resource_class,
    validate_workload_requirements,
)


class ResourceAdmissionPolicyTests(unittest.TestCase):
    def test_cpu_only_workload_does_not_require_accelerator(self) -> None:
        classes, accelerator_required = classify_requirements([
            {"metric": "cpu.physical_cores", "operator": ">=", "value": 8},
            {"metric": "memory.total_gib", "operator": ">=", "value": 16},
        ])
        self.assertEqual(classes, ["cpu", "memory"])
        self.assertFalse(accelerator_required)

    def test_accelerator_metrics_make_accelerator_explicitly_required(self) -> None:
        classes, accelerator_required = classify_requirements([
            {"metric": "cpu.physical_cores", "operator": ">=", "value": 8},
            {"metric": "gpu.vram_gib", "operator": ">=", "value": 8},
        ])
        self.assertEqual(classes, ["accelerator", "cpu"])
        self.assertTrue(accelerator_required)

    def test_npu_and_provider_neutral_accelerator_metrics_are_accelerator_class(self) -> None:
        self.assertEqual(metric_resource_class("npu.memory_gib"), "accelerator")
        self.assertEqual(metric_resource_class("accelerator.memory_gib"), "accelerator")

    def test_cu_tu_remain_forbidden_admission_metrics(self) -> None:
        errors = validate_workload_requirements([
            {"metric": "cu", "operator": ">=", "value": 1},
            {"metric": "cpu.physical_cores", "operator": ">=", "value": 1},
        ])
        self.assertIn("FORBIDDEN_ADMISSION_METRIC:cu", errors)


if __name__ == "__main__":
    unittest.main()
