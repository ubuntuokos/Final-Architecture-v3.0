from __future__ import annotations

import unittest
from pathlib import Path

from src.fa3_current_host_capability_qualification_constituent_orchestrator import orchestrate as orchestrate_producers
from src.fa3_current_host_capability_test_orchestrator import orchestrate as orchestrate_tests

ROOT = Path(__file__).resolve().parents[1]
READY = {"CAP-054", "CAP-074", "CAP-075", "CAP-076", "CAP-080"}


class TestCurrentHostBatchOrchestration(unittest.TestCase):
    def test_registered_batch_can_be_selected_without_execution(self):
        producer = orchestrate_producers(ROOT, execute=False, subjects=READY)
        executor = orchestrate_tests(ROOT, execute=False, subjects=READY)
        self.assertEqual(producer["orchestrator_integrity"], "PASS")
        self.assertEqual(executor["orchestrator_integrity"], "PASS")
        self.assertEqual(producer["selected_producer_count"], 15)
        self.assertEqual(executor["selected_executor_count"], 15)
        self.assertEqual(set(producer["requested_subjects"]), READY)
        self.assertEqual(set(executor["requested_subjects"]), READY)
        self.assertEqual(producer["constituents_materialized"], 0)
        self.assertEqual(executor["results_materialized"], 0)
        self.assertIs(producer["global_promotion_claim"], False)
        self.assertIs(executor["global_promotion_claim"], False)

    def test_unregistered_subject_fails_closed(self):
        producer = orchestrate_producers(ROOT, execute=False, subjects={"CAP-001"})
        executor = orchestrate_tests(ROOT, execute=False, subjects={"CAP-001"})
        self.assertEqual(producer["orchestrator_integrity"], "FAIL")
        self.assertEqual(executor["orchestrator_integrity"], "FAIL")
        self.assertTrue(any(row["code"] == "QCPO-007" for row in producer["blocking_findings"]))
        self.assertTrue(any(row["code"] == "CHOR-007" for row in executor["blocking_findings"]))


if __name__ == "__main__":
    unittest.main()
