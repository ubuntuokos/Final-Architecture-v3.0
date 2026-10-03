"""FA3 task-scope / closure policy regressions."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fa3_agent_workload import WorkloadContractError, compile_execution_plan

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

    def test_third_failure_freezes_even_without_human_action_text(self):
        _, control = self.control()
        fp = blocker_fingerprint("HUMAN_BLOCKER", [])
        control = record_blocker_failure(control, fp, "one")
        control = record_blocker_failure(control, fp, "two")
        control = record_blocker_failure(control, fp, "three")
        self.assertEqual(control["state"], HUMAN_INTERVENTION_REQUIRED)
        self.assertTrue(control["execution_frozen"])
        self.assertTrue(control["human_action_required"])
        with self.assertRaises(TaskScopeClosureError):
            assert_execution_allowed(control)

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

    def test_attempt_counter_must_match_append_only_ledger(self):
        _, control = self.control()
        fp = blocker_fingerprint("LEDGER", [])
        control = record_blocker_failure(control, fp, "one")
        tampered = copy.deepcopy(control)
        tampered["blocker_attempts"] = {}
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(tampered)
        tampered = copy.deepcopy(control)
        tampered["attempt_ledger"][0]["attempt"] = 2
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(tampered)

    def test_active_control_cannot_carry_terminal_state(self):
        _, control = self.control()
        control["internal_terminal_state"] = "VERIFIED"
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(control)
        with self.assertRaises(TaskScopeClosureError):
            assert_execution_allowed(control)

    def test_followup_scope_must_match_bound_scope_digest(self):
        binding, control = self.control()
        forged_scope = {
            "in_scope": ["different task"],
            "out_of_scope": ["implement task-scope policy"],
        }
        with self.assertRaises(TaskScopeClosureError):
            register_followup_handoff(
                control, binding, forged_scope,
                scope_item="implement task-scope policy",
                discovered_issue="Forged classification.",
                why_out_of_scope="Caller supplied unrelated scope.",
                current_state="Active.",
                evidence_refs=[],
                suggested_new_task_objective="Should never be created.",
                suggested_new_conversation_start="Should never be created.",
            )

    def test_canonical_schemas_include_emitted_scope_fields(self):
        root = Path(__file__).resolve().parents[1]
        task_schema = json.loads((root / "canonical/contracts/FA3-AGENT-WORKLOAD-TASK-001.schema.json").read_text())
        plan_schema = json.loads((root / "canonical/contracts/FA3-AGENT-EXECUTION-PLAN-001.schema.json").read_text())
        self.assertIn("goal_scope_binding", task_schema["properties"])
        self.assertIn("task_scope_policy_id", plan_schema["properties"])
        self.assertIn("task_scope_control_required", plan_schema["properties"])

    def test_goal_bound_execution_plan_requires_active_control(self):
        binding, control = self.control()
        task = {
            "schema": "fa3.agent-workload-task.v1",
            "task_id": "task-1",
            "root_task_id": "goal-scope-1",
            "action_ref": "orchestration.execute",
            "agent_definition_ref": "agent:a",
            "workspace_refs": [],
            "resource_requirements": {},
            "network_envelope_ref": "net:1",
            "model_intent": {"required_capabilities": ["tools"]},
            "authorized_ai_participants": ["agent:a"],
            "fanout_limits": {
                "max_children": 1, "max_depth": 1, "max_concurrent_children": 1,
                "max_runtime_seconds": 60, "max_retries": 1,
                "max_tool_calls": 2, "max_model_requests": 2,
            },
            "goal_scope_binding": binding,
        }
        graph = {
            "schema": "fa3.agent-workflow-graph.v1",
            "graph_id": "g",
            "entry_node": "n1",
            "yaml_is_canonical": False,
            "nodes": [{"node_id": "n1", "kind": "AGENT", "side_effecting": False}],
            "edges": [],
        }
        model = {
            "schema": "fa3.model-capability-descriptor.v1",
            "logical_model_id": "default",
            "source": "PROVIDER_DECLARED",
            "router_authority": "FA3-AUTH-MODEL-ROUTER-001",
            "model_id_heuristic": False,
            "capabilities": {
                "tools": True, "structured_output": False, "media_input": False,
                "media_output": False, "streaming": True,
            },
        }
        with self.assertRaises(WorkloadContractError):
            compile_execution_plan(
                task, graph, model, task_spec_digest="sha256:task", max_transfer_hops=1
            )
        stripped = copy.deepcopy(task)
        del stripped["goal_scope_binding"]
        with self.assertRaises(WorkloadContractError):
            compile_execution_plan(
                stripped, graph, model, task_spec_digest="sha256:task", max_transfer_hops=1
            )
        plan = compile_execution_plan(
            task, graph, model, task_spec_digest="sha256:task", max_transfer_hops=1,
            task_control=control,
        )
        self.assertTrue(plan["task_scope_control_required"])
        closed = close_task_control(control, "VERIFIED")
        with self.assertRaises(WorkloadContractError):
            compile_execution_plan(
                task, graph, model, task_spec_digest="sha256:task", max_transfer_hops=1,
                task_control=closed,
            )


if __name__ == "__main__":
    unittest.main()
