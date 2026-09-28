import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_cpu_thread_budget import build_thread_plan, make_synthetic_dual_numa_topology
from fa3_openmp_governance import (
    OpenMPAdmissionDenied,
    build_openmp_plan,
    classify_runtime_libraries,
    validate_observed_runtime,
)
from fa3_openmp_governance_gate import evaluate


class OpenMPRuntimeGovernanceTests(unittest.TestCase):
    def setUp(self):
        topology = make_synthetic_dual_numa_topology()
        self.thread_plan = build_thread_plan(
            topology,
            {
                "authority_receipt": "HRB_PLACEMENT_RECEIPT",
                "requested_threads": 8,
            },
        )

    def test_gate_passes_without_current_host_overclaim(self):
        result = evaluate(ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["summary"], {"passed": 24, "total": 24})
        self.assertFalse(result["current_host_runtime_promotion_claim"])

    def test_multiple_openmp_runtime_families_fail_closed(self):
        discovered = classify_runtime_libraries(
            ["/usr/lib/libgomp.so.1", "/opt/intel/lib/libiomp5.so"]
        )
        self.assertEqual(discovered["status"], "MULTIPLE_RUNTIME_CONFLICT")
        with self.assertRaises(OpenMPAdmissionDenied):
            build_openmp_plan(
                self.thread_plan,
                {},
                runtime_libraries=["/usr/lib/libgomp.so.1", "/opt/intel/lib/libiomp5.so"],
            )

    def test_environment_is_sanitized_per_child_process(self):
        plan = build_openmp_plan(
            self.thread_plan,
            {},
            inherited_env={
                "OMP_NUM_THREADS": "64",
                "GOMP_CPU_AFFINITY": "0-63",
                "PATH": "/usr/bin",
            },
            runtime_libraries=["/usr/lib/libgomp.so.1"],
        )
        self.assertEqual(plan["environment"]["OMP_NUM_THREADS"], "8")
        self.assertEqual(plan["effective_child_environment"]["OMP_NUM_THREADS"], "8")
        self.assertEqual(plan["effective_child_environment"]["PATH"], "/usr/bin")
        self.assertNotIn("GOMP_CPU_AFFINITY", plan["effective_child_environment"])

    def test_nested_parallelism_is_bounded_by_hrb_budget(self):
        with self.assertRaises(OpenMPAdmissionDenied):
            build_openmp_plan(self.thread_plan, {"max_active_levels": 2})
        admitted = build_openmp_plan(
            self.thread_plan,
            {
                "max_active_levels": 2,
                "nested_parallelism_admitted": True,
                "benchmark_evidence": True,
                "outer_team_threads": 4,
                "inner_team_threads": 2,
            },
        )
        self.assertTrue(admitted["nested_parallelism"])

    def test_stack_reservation_requires_memory_budget(self):
        with self.assertRaises(OpenMPAdmissionDenied):
            build_openmp_plan(self.thread_plan, {"stack_size": "8M"})
        plan = build_openmp_plan(
            self.thread_plan,
            {
                "stack_size": "8M",
                "hrb_memory_budget_bytes": 64 * 1024 * 1024,
            },
        )
        self.assertEqual(plan["stack_reservation_bytes"], 64 * 1024 * 1024)

    def test_accelerator_offload_has_no_silent_cpu_fallback(self):
        with self.assertRaises(OpenMPAdmissionDenied):
            build_openmp_plan(
                self.thread_plan,
                {
                    "target_offload": {
                        "requested": True,
                        "stable_device_identity": "GPU-UUID",
                        "device_ordinal": 0,
                    }
                },
            )
        plan = build_openmp_plan(
            self.thread_plan,
            {
                "target_offload": {
                    "requested": True,
                    "hrb_accelerator_lease": True,
                    "stable_device_identity": "GPU-UUID",
                    "device_ordinal": 0,
                }
            },
        )
        self.assertEqual(plan["environment"]["OMP_TARGET_OFFLOAD"], "MANDATORY")
        self.assertFalse(plan["target_offload"]["silent_host_fallback_allowed"])

    def test_observed_worker_must_remain_inside_hrb_cpuset(self):
        plan = build_openmp_plan(self.thread_plan, {})
        passed = validate_observed_runtime(
            plan,
            {
                "max_threads": 8,
                "admitted_cpus": list(range(8)),
                "observed_cpus": [0, 1, 2],
                "effective_dynamic": False,
            },
        )
        self.assertEqual(passed["status"], "PASS")
        failed = validate_observed_runtime(
            plan,
            {
                "max_threads": 8,
                "admitted_cpus": list(range(8)),
                "observed_cpus": [0, 8],
                "effective_dynamic": False,
            },
        )
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn("OPENMP_CPUSET_ESCAPE", failed["findings"])


if __name__ == "__main__":
    unittest.main()
