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
    validate_accelerator_execution_requirement,
    validate_workload_envelope,
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

    def test_execution_requirement_requires_accelerator_resource_class(self) -> None:
        errors = validate_workload_envelope({
            "requirements": [
                {"metric": "cpu.physical_cores", "operator": ">=", "value": 8},
            ],
            "accelerator_execution": {
                "acceptable_execution_paths": [
                    {"backend": "cuda", "backend_class": "native", "framework_backend": "pytorch-cuda"},
                ],
                "allow_translation": False,
            },
        })
        self.assertIn("ACCELERATOR_EXECUTION_WITHOUT_ACCELERATOR_RESOURCE_CLASS", errors)

    def test_translation_requirement_is_explicit_opt_in(self) -> None:
        denied = validate_accelerator_execution_requirement({
            "acceptable_execution_paths": [
                {"backend": "zluda", "backend_class": "translation", "framework_backend": "cuda-compat"},
            ],
            "allow_translation": False,
        })
        self.assertIn("TRANSLATION_PATH_NOT_EXPLICITLY_ALLOWED:0", denied)
        admitted = validate_accelerator_execution_requirement({
            "acceptable_execution_paths": [
                {"backend": "zluda", "backend_class": "translation", "framework_backend": "cuda-compat"},
            ],
            "allow_translation": True,
        })
        self.assertEqual(admitted, [])

    def test_cu_tu_remain_forbidden_admission_metrics(self) -> None:
        errors = validate_workload_requirements([
            {"metric": "cu", "operator": ">=", "value": 1},
            {"metric": "cpu.physical_cores", "operator": ">=", "value": 1},
        ])
        self.assertIn("FORBIDDEN_ADMISSION_METRIC:cu", errors)


if __name__ == "__main__":
    unittest.main()
