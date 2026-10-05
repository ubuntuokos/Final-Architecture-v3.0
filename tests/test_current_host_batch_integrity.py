from __future__ import annotations

import unittest
from pathlib import Path

from fa3_current_host_batch_integrity import validate_selection
from fa3_current_host_batch_planner import build_plan

ROOT = Path(__file__).resolve().parents[1]


class CurrentHostBatchIntegrityTests(unittest.TestCase):
    def test_full_525_selection_is_digest_bound(self):
        plan = build_plan(ROOT, batch_size=5)
        report = validate_selection(
            ROOT,
            batch_id="FULL-525",
            subjects=plan["execution_ready_capabilities"],
            selection_sha256=plan["execution_ready_selection_sha256"],
        )
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(175, report["subject_count"])
        self.assertEqual(525, report["obligation_count"])
        self.assertFalse(report["global_promotion_claim"])

    def test_tampered_selection_digest_fails_closed(self):
        plan = build_plan(ROOT, batch_size=5)
        report = validate_selection(
            ROOT,
            batch_id="FULL-525",
            subjects=plan["execution_ready_capabilities"],
            selection_sha256="0" * 64,
        )
        self.assertEqual("FAIL", report["result"])
        self.assertTrue(any("SHA-256" in item for item in report["findings"]))

    def test_subject_order_or_membership_cannot_drift(self):
        plan = build_plan(ROOT, batch_size=5)
        subjects = list(plan["execution_ready_capabilities"])
        subjects[0], subjects[1] = subjects[1], subjects[0]
        report = validate_selection(
            ROOT,
            batch_id="FULL-525",
            subjects=subjects,
            selection_sha256=plan["execution_ready_selection_sha256"],
        )
        self.assertEqual("FAIL", report["result"])

    def test_scoped_selection_accepts_exact_execution_ready_subset(self):
        from fa3_current_host_batch_planner import _selection_digest
        plan = build_plan(ROOT, batch_size=5)
        subjects = plan["execution_ready_capabilities"][:2]
        report = validate_selection(
            ROOT,
            batch_id="SCOPED",
            subjects=subjects,
            selection_sha256=_selection_digest(subjects, plan["registry_sha256"]),
            batch_size=5,
        )
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(6, report["obligation_count"])


if __name__ == "__main__":
    unittest.main()
