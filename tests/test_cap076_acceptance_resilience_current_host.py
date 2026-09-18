import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.fa3_cap076_acceptance_resilience_current_host import (
    _run_negative,
    _run_rollback,
    validate_acceptance_promotion,
)


class Cap076AcceptanceResilienceCurrentHostTests(unittest.TestCase):
    def test_consistent_accept_and_deny_states_are_valid(self):
        pass_acceptance = {
            "schema": "fa3.acceptance-report.v1",
            "status": "PASS",
            "decision": "ACCEPT",
            "fail_closed": True,
            "criteria_total": 19,
        }
        pass_state = {
            "schema": "fa3.runtime-status.v1",
            "target_state": "PROMOTED",
            "actual_state": "PROMOTED",
            "promotion_allowed": True,
            "acceptance": "PASS",
            "reason": None,
        }
        self.assertEqual(
            validate_acceptance_promotion(pass_acceptance, pass_state, 0), []
        )

        deny_acceptance = {
            "schema": "fa3.acceptance-report.v1",
            "status": "DENIED",
            "decision": "DENY",
            "fail_closed": True,
            "criteria_total": 19,
        }
        deny_state = {
            "schema": "fa3.runtime-status.v1",
            "target_state": "PROMOTED",
            "actual_state": "PROMOTION_BLOCKED",
            "promotion_allowed": False,
            "acceptance": "DENIED",
            "reason": "fail-closed",
        }
        self.assertEqual(
            validate_acceptance_promotion(deny_acceptance, deny_state, 2), []
        )

    def test_inconsistent_promotion_state_is_rejected(self):
        acceptance = {
            "schema": "fa3.acceptance-report.v1",
            "status": "DENIED",
            "decision": "DENY",
            "fail_closed": True,
            "criteria_total": 19,
        }
        state = {
            "schema": "fa3.runtime-status.v1",
            "target_state": "PROMOTED",
            "actual_state": "PROMOTED",
            "promotion_allowed": True,
            "acceptance": "DENIED",
            "reason": None,
        }
        findings = validate_acceptance_promotion(acceptance, state, 0)
        self.assertTrue(findings)
        self.assertTrue(
            any("promotion_allowed" in item or "actual_state" in item for item in findings)
        )

    def test_negative_receipt_faults_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scope = root / ".fa3-current-host/qualification-source-artifacts/cap076-neg"
            scope.mkdir(parents=True)
            result = _run_negative(root, scope)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["fail_status_rejected"])
            self.assertTrue(result["unsigned_rejected"])
            self.assertTrue(result["unreadable_rejected"])

    def test_rollback_restores_exact_valid_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scope = root / ".fa3-current-host/qualification-source-artifacts/cap076-rollback"
            scope.mkdir(parents=True)
            result = _run_rollback(root, scope)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["fault_rejected"])
            self.assertTrue(result["rollback_hash_equal"])
            self.assertTrue(result["restored_receipt_valid"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
