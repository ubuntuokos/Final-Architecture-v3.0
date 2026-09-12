from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_manager import ManagerInputError, build_management_projection  # noqa: E402
from fa3_manager_gate import validate  # noqa: E402


class ManagerGateTests(unittest.TestCase):
    def test_canonical_gate_passes(self) -> None:
        self.assertEqual([], validate())

    def test_action_is_delegated_not_executed(self) -> None:
        result = build_management_projection({
            "objective": "Do managed work",
            "work_items": [{"id": "w1", "title": "Run task", "state": "READY"}],
            "actionable_request": True,
        })
        self.assertFalse(result["authority"]["direct_execution_allowed"])
        self.assertEqual({"ACTION"}, {item["kind"] for item in result["delegations"]})

    def test_cross_role_delegation_boundaries(self) -> None:
        result = build_management_projection({
            "objective": "Coordinate a mixed case",
            "knowledge_gap": True,
            "coaching_needed": True,
            "actionable_request": True,
        })
        self.assertEqual({"MENTOR", "COACH", "ACTION"}, {item["kind"] for item in result["delegations"]})

    def test_dependency_cycle_fails_closed(self) -> None:
        with self.assertRaises(ManagerInputError):
            build_management_projection({
                "objective": "Cycle",
                "work_items": [
                    {"id": "a", "title": "A", "depends_on": ["b"]},
                    {"id": "b", "title": "B", "depends_on": ["a"]},
                ],
            })

    def test_verified_without_evidence_fails_closed(self) -> None:
        with self.assertRaises(ManagerInputError):
            build_management_projection({
                "objective": "False closure",
                "work_items": [{"id": "a", "title": "A", "state": "VERIFIED", "acceptance_criteria": ["accepted"], "acceptance_met": True}],
            })

    def test_verified_with_acceptance_and_evidence_is_valid(self) -> None:
        result = build_management_projection({
            "mode": "VERIFY_CLOSURE",
            "objective": "Evidence-backed closure",
            "work_items": [{"id": "a", "title": "A", "state": "VERIFIED", "acceptance_criteria": ["accepted"], "acceptance_met": True, "evidence_refs": ["evidence://a"]}],
        })
        self.assertEqual(["a"], result["summary"]["verified"])

    def test_blocked_requires_provenance(self) -> None:
        with self.assertRaises(ManagerInputError):
            build_management_projection({
                "objective": "Blocked",
                "work_items": [{"id": "a", "title": "A", "state": "BLOCKED"}],
            })


if __name__ == "__main__":
    unittest.main()
