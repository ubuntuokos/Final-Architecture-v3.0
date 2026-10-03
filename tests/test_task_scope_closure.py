"""FA3 task-scope / closure policy regressions."""
from __future__ import annotations

import copy
import unittest

from fa3_task_scope_closure import (
    CLOSED,
    DONE,
    HUMAN_INTERVENTION_REQUIRED,
    MAX_SAME_BLOCKER_ATTEMPTS,
    NEW_TASK_DISCOVERED,
    POLICY_ID,
    TaskScopeClosureError,
    assert_execution_allowed,
    blocker_fingerprint,
    classify_scope_item,
    close_task_control,
    goal_scope_binding,
    record_blocker_failure,
    register_followup_handoff,
    start_task_control,
    validate_goal_scope_binding,
    validate_task_control,
)


def goal():
    return {
        "schema": "fa3.goal-contract.v1",
        "goal_id": "goal-scope-1",
        "revision": 7,
        "owner_ref": "owner",
        "objective": "Complete one explicitly scoped task",
        "workspace_ref": "ws",
        "scope": {
            "in_scope": ["implement task-scope policy"],
            "out_of_scope": ["unrelated provider upgrade"],
        },
        "acceptance_criteria": [{"criterion_id": "C1"}],
        "execution_policy": {"mode": "HYBRID"},
    }


class TaskScopeClosureTests(unittest.TestCase):
    def control(self):
        binding = goal_scope_binding(goal())
        return binding, start_task_control(binding, task_id="task-1", root_task_id="goal-scope-1")

    def test_binding_is_revision_and_scope_locked(self):
        binding = goal_scope_binding(goal())
        self.assertEqual(binding["policy_id"], POLICY_ID)
        self.assertEqual(binding["max_same_blocker_attempts"], 3)
        self.assertFalse(binding["automatic_scope_expansion"])
        self.assertFalse(binding["automatic_followup_execution"])
        changed = goal()
        changed["revision"] = 8
        self.assertNotEqual(goal_scope_binding(changed)["goal_digest"], binding["goal_digest"])
        bad = copy.deepcopy(binding)
        bad["max_same_blocker_attempts"] = 4
        with self.assertRaises(TaskScopeClosureError):
            validate_goal_scope_binding(bad)

    def test_undeclared_work_cannot_expand_current_scope(self):
        x = classify_scope_item(goal()["scope"], "new unrelated task")
        self.assertEqual(x["classification"], "OUT_OF_SCOPE_FOLLOWUP")
        self.assertTrue(x["requires_new_task"])
        self.assertFalse(x["automatic_execution_allowed_by_scope"])
        self.assertEqual(x["reason"], "UNDECLARED_SCOPE_NOT_AUTO_EXPANDED")

    def test_three_same_blocker_failures_freeze_execution(self):
        _, control = self.control()
        fp = blocker_fingerprint("CI_BLOCKER", ["run:1"])
        control = record_blocker_failure(control, fp, "first failure")
        control = record_blocker_failure(control, fp, "second failure")
        control = record_blocker_failure(
            control, fp, "third failure", human_action="Inspect the external blocker and explicitly resume or revise the task."
        )
        self.assertEqual(control["blocker_attempts"][fp], MAX_SAME_BLOCKER_ATTEMPTS)
        self.assertEqual(control["state"], HUMAN_INTERVENTION_REQUIRED)
        self.assertTrue(control["execution_frozen"])
        self.assertFalse(control["automatic_retry_allowed"])
        self.assertFalse(control["automatic_replan_allowed"])
        self.assertFalse(control["alternative_route_allowed"])
        with self.assertRaises(TaskScopeClosureError):
            record_blocker_failure(control, fp, "fourth failure")
        with self.assertRaises(TaskScopeClosureError):
            assert_execution_allowed(control)

    def test_third_failure_requires_explicit_human_action(self):
        _, control = self.control()
        fp = blocker_fingerprint("HUMAN_BLOCKER", [])
        control = record_blocker_failure(control, fp, "one")
        control = record_blocker_failure(control, fp, "two")
        with self.assertRaises(TaskScopeClosureError):
            record_blocker_failure(control, fp, "three")

    def test_followup_is_draft_only_and_requires_new_task(self):
        binding, control = self.control()
        control = register_followup_handoff(
            control, binding, goal()["scope"],
            scope_item="unrelated provider upgrade",
            discovered_issue="A provider upgrade is available.",
            why_out_of_scope="The current task only implements task-scope policy.",
            current_state="Original task still active.",
            evidence_refs=["evidence:provider-note"],
            suggested_new_task_objective="Evaluate the provider upgrade separately.",
            suggested_new_conversation_start="FA3 provider upgrade evaluation — treat this as a new task.",
        )
        handoff = control["followup_handoffs"][0]
        self.assertTrue(handoff["requires_new_task_id"])
        self.assertTrue(handoff["requires_user_start"])
        self.assertFalse(handoff["automatic_start"])
        self.assertFalse(handoff["execution_performed"])

    def test_verified_task_with_no_followup_is_done_and_cannot_execute(self):
        _, control = self.control()
        closed = close_task_control(control, "VERIFIED")
        self.assertEqual(closed["state"], CLOSED)
        self.assertEqual(closed["user_closure_state"], DONE)
        with self.assertRaises(TaskScopeClosureError):
            assert_execution_allowed(closed)

    def test_verified_task_with_followup_projects_new_task_state(self):
        binding, control = self.control()
        control = register_followup_handoff(
            control, binding, goal()["scope"],
            scope_item="another undeclared followup",
            discovered_issue="Another task was discovered.",
            why_out_of_scope="It is not part of the explicit scope.",
            current_state="Original task can still complete.",
            evidence_refs=[],
            suggested_new_task_objective="Handle the separate follow-up.",
            suggested_new_conversation_start="Start a new FA3 task for the discovered follow-up.",
        )
        closed = close_task_control(control, "VERIFIED")
        self.assertEqual(closed["user_closure_state"], NEW_TASK_DISCOVERED)
        self.assertEqual(closed["internal_terminal_state"], "VERIFIED")

    def test_nonverified_terminal_requires_human_action(self):
        _, control = self.control()
        with self.assertRaises(TaskScopeClosureError):
            close_task_control(control, "FAILED")
        blocked = close_task_control(
            control, "FAILED", human_action="Review the failure and explicitly decide how to continue."
        )
        self.assertEqual(blocked["state"], HUMAN_INTERVENTION_REQUIRED)

    def test_tampered_active_control_with_three_attempts_is_rejected(self):
        _, control = self.control()
        fp = blocker_fingerprint("X", [])
        control["blocker_attempts"][fp] = 3
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(control)


if __name__ == "__main__":
    unittest.main()
