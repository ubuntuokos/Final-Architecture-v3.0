from __future__ import annotations

import unittest
from pathlib import Path

from src.fa3_current_host_batch_planner import build_plan
from src.fa3_current_host_capability_qualification_constituent_orchestrator import orchestrate as orchestrate_producers
from src.fa3_current_host_capability_test_orchestrator import orchestrate as orchestrate_tests

ROOT = Path(__file__).resolve().parents[1]


class TestCurrentHostBatchOrchestration(unittest.TestCase):
    def test_registered_batch_can_be_selected_without_execution(self):
        plan = build_plan(ROOT, batch_size=5)
        ready = set(plan["execution_ready_capabilities"])
        self.assertTrue(ready)
        producer = orchestrate_producers(ROOT, execute=False, subjects=ready)
        executor = orchestrate_tests(ROOT, execute=False, subjects=ready)
        expected = len(ready) * 3
        self.assertEqual(producer["orchestrator_integrity"], "PASS")
        self.assertEqual(executor["orchestrator_integrity"], "PASS")
        self.assertEqual(producer["selected_producer_count"], expected)
        self.assertEqual(executor["selected_executor_count"], expected)
        self.assertEqual(set(producer["requested_subjects"]), ready)
        self.assertEqual(set(executor["requested_subjects"]), ready)
        self.assertEqual(producer["constituents_materialized"], 0)
        self.assertEqual(executor["results_materialized"], 0)
        self.assertIs(producer["global_promotion_claim"], False)
        self.assertIs(executor["global_promotion_claim"], False)

    def test_unknown_subject_fails_closed_after_full_materialization(self):
        plan = build_plan(ROOT, batch_size=5)
        self.assertEqual(plan["pending_materialization_capability_count"], 0)
        subject = "CAP-999"
        producer = orchestrate_producers(ROOT, execute=False, subjects={subject})
        executor = orchestrate_tests(ROOT, execute=False, subjects={subject})
        self.assertEqual(producer["orchestrator_integrity"], "FAIL")
        self.assertEqual(executor["orchestrator_integrity"], "FAIL")
        self.assertTrue(any(row["code"] == "QCPO-007" for row in producer["blocking_findings"]))
        self.assertTrue(any(row["code"] == "CHOR-007" for row in executor["blocking_findings"]))


if __name__ == "__main__":
    unittest.main()
