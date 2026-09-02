import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_cpu_numa_threading_gate import evaluate
from fa3_cpu_thread_budget import AdmissionDenied, build_thread_plan, make_reference_t7910_topology


class CpuNumaThreadingGateTests(unittest.TestCase):
    def test_reference_gate_passes(self):
        result = evaluate(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["summary"], {"passed": 24, "total": 24})
        self.assertFalse(result["current_host_runtime_promotion_claim"])

    def test_physical_core_first_and_numa_local(self):
        topology = make_reference_t7910_topology()
        plan = build_thread_plan(topology, {"authority_receipt": "HRB_PLACEMENT_RECEIPT"})
        self.assertEqual(plan["thread_budget"], 44)
        node0 = [entry["cpu_id"] for entry in topology["logical_cpus"] if entry["numa_node"] == 0]
        local = build_thread_plan(topology, {"authority_receipt": "HRB_PLACEMENT_RECEIPT", "allowed_cpus": node0, "numa_node": 0})
        self.assertEqual(local["thread_budget"], 22)

    def test_oversubscription_fails_closed(self):
        topology = make_reference_t7910_topology()
        with self.assertRaises(AdmissionDenied):
            build_thread_plan(topology, {"authority_receipt": "HRB_PLACEMENT_RECEIPT", "requested_threads": 88})

    def test_smt_requires_all_admission_evidence(self):
        topology = make_reference_t7910_topology()
        plan = build_thread_plan(topology, {
            "authority_receipt": "HRB_PLACEMENT_RECEIPT",
            "requested_threads": 88,
            "allow_smt": True,
            "benchmark_evidence": True,
            "explicit_smt_admission": True,
        })
        self.assertTrue(plan["uses_smt_above_physical_budget"])

    def test_kmp_is_not_global(self):
        topology = make_reference_t7910_topology()
        generic = build_thread_plan(topology, {"authority_receipt": "HRB_PLACEMENT_RECEIPT", "requested_threads": 8})
        intel = build_thread_plan(topology, {"authority_receipt": "HRB_PLACEMENT_RECEIPT", "requested_threads": 8, "openmp_provider": "INTEL_LIBIOMP"})
        self.assertNotIn("KMP_AFFINITY", generic["provider_settings"])
        self.assertIn("KMP_AFFINITY", intel["provider_settings"])


if __name__ == "__main__":
    unittest.main()
