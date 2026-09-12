from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_coach import CoachInputError, build_proposal  # noqa: E402
from fa3_coach_gate import validate  # noqa: E402


class CoachGateTests(unittest.TestCase):
    def test_coach_gate_passes_reference_materialization(self) -> None:
        self.assertEqual(validate(), [])

    def test_coach_is_proposal_only_and_user_goal_owned(self) -> None:
        proposal = build_proposal(
            {
                "mode": "PLAN",
                "goal": "Complete a verifiable milestone",
                "actions": ["Define evidence", "Execute through authorized boundary"],
            }
        )
        self.assertEqual(proposal["status"], "PROPOSAL_ONLY")
        self.assertEqual(proposal["goal"]["owner"], "USER")
        self.assertIs(proposal["authority"]["direct_execution_allowed"], False)
        self.assertIs(proposal["authority"]["architectural_authority"], False)
        self.assertIs(proposal["authority"]["canonical_memory_write_allowed"], False)
        self.assertIs(proposal["authority"]["cross_workspace_persistence_allowed"], False)

    def test_knowledge_gap_and_action_request_create_typed_delegations(self) -> None:
        proposal = build_proposal(
            {
                "mode": "BLOCKER_REVIEW",
                "goal": "Resolve a technical blocker",
                "knowledge_gap": True,
                "actionable_request": True,
            }
        )
        delegations = {item["kind"]: item["target"] for item in proposal["delegations"]}
        self.assertEqual(delegations["MENTOR"], "FA3-MENTOR-001")
        self.assertIn("FA3-AUTH-MCP-GATEWAY-001", delegations["ACTION"])

    def test_accountability_requires_explicit_commitment(self) -> None:
        with self.assertRaises(CoachInputError):
            build_proposal({"mode": "ACCOUNTABILITY", "goal": "Finish task"})

        proposal = build_proposal(
            {
                "mode": "ACCOUNTABILITY",
                "goal": "Finish task",
                "user_commitment": True,
            }
        )
        self.assertIs(proposal["plan"]["user_commitment_recorded"], True)

    def test_invalid_or_empty_goal_fails_closed(self) -> None:
        with self.assertRaises(CoachInputError):
            build_proposal({"mode": "PLAN", "goal": ""})


if __name__ == "__main__":
    unittest.main()
