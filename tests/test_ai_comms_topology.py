from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_ai_comms_topology import (
    CommunicationTopologyDenied,
    authorize_message,
    authorize_partner_replacement,
    authorize_wake,
    partner_replacement_required,
    reference_cases,
    reference_topology_policy,
)


class AICommsTopologyTests(unittest.TestCase):
    def test_reference_cases(self) -> None:
        cases = reference_cases()
        self.assertTrue(all(cases.values()), cases)

    def test_unfit_partner_is_replaced_not_augmented(self) -> None:
        required, reasons = partner_replacement_required(
            capability_sufficient=True,
            task_execution_valid=True,
            unauthorized_operation_attempted=False,
            autonomous_scope_expansion_attempted=True,
            unauthorized_model_app_or_resource_attempted=False,
        )
        self.assertTrue(required)
        self.assertEqual(reasons, ("AUTONOMOUS_SCOPE_EXPANSION_ATTEMPT",))
        result = authorize_partner_replacement(
            reference_topology_policy(),
            app_id="editor",
            logical_role="review",
            replacement_reasons=list(reasons),
            via_central_model_router=True,
            candidate_pre_admitted=True,
            participant_count_delta=0,
        )
        self.assertEqual(result["result"], "REPLACE_ALLOWED")
        self.assertEqual(result["participant_count_delta"], 0)

    def test_cross_app_gateway_is_mandatory(self) -> None:
        with self.assertRaises(CommunicationTopologyDenied):
            authorize_message(
                reference_topology_policy(),
                sender_app="editor",
                sender_role="main",
                recipient_app="security-response",
                recipient_role="security-main",
            )

    def test_sleeping_app_requires_user_directive(self) -> None:
        with self.assertRaises(CommunicationTopologyDenied):
            authorize_wake(
                reference_topology_policy(),
                target_app="security-response",
                target_role="security-main",
            )

    def test_security_emergency_is_narrow_and_requires_notification(self) -> None:
        result = authorize_wake(
            reference_topology_policy(),
            target_app="security-response",
            target_role="security-main",
            security_emergency={
                "detector_id": "fa3-security-sensor",
                "trigger": "RANSOMWARE_BEHAVIOR",
                "severity": "CRITICAL",
                "confidence": 0.99,
                "least_privilege": True,
            },
        )
        self.assertTrue(result["notification_required"])
        self.assertFalse(result["gateway_bypass_allowed"])
        self.assertTrue(result["audit_required"])


if __name__ == "__main__":
    unittest.main()
