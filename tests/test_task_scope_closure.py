"""CFA3 task-scope / bounded retry / handoff / closure regressions."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_agent_workload import (
    WorkloadContractError,
    compile_execution_plan,
    validate_execution_admission,
)
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


def behavior_context():
    return {
        "action": "READ",
        "current_owner_restriction_allows": True,
        "scope_bound": True,
        "scope_allows_action": True,
        "scope_origin": "REQUIRED_FOR_APPROVED_GOAL",
        "scope_refs": ["implement task-scope policy"],
        "uncertain_state": False,
        "blocker_kind": None,
        "autonomous_workaround": False,
        "silent_redesign_or_repair": False,
    }


def execution_fixture(binding):
    task = {
        "schema": "fa3.agent-workload-task.v1",
        "task_id": "task-1",
        "root_task_id": "goal-scope-1",
        "scope_origin": "REQUIRED_FOR_APPROVED_GOAL",
        "scope_refs": ["implement task-scope policy"],
        "goal_scope_binding": binding,
        "action_ref": "orchestration.execute",
        "agent_definition_ref": "agent:a",
        "workspace_refs": [],
        "resource_requirements": {},
        "network_envelope_ref": "net:1",
        "model_intent": {"required_capabilities": ["tools"]},
        "authorized_ai_participants": ["agent:a"],
        "fanout_limits": {
            "max_children": 1,
            "max_depth": 1,
            "max_concurrent_children": 1,
            "max_runtime_seconds": 60,
            "max_retries": 1,
            "max_tool_calls": 2,
            "max_model_requests": 2,
        },
        "provenance_refs": [],
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
            "tools": True,
            "structured_output": False,
            "media_input": False,
            "media_output": False,
            "streaming": True,
        },
    }
    return task, graph, model


class TaskScopeClosureTests(unittest.TestCase):
    def control(self):
        binding = goal_scope_binding(goal())
        return binding, start_task_control(
            binding, task_id="task-1", root_task_id="goal-scope-1"
        )

    def evidence_receipt(self, control):
        return {
            "authority": "FA3-AUTH-OBS-EVIDENCE-001",
            "result": "VERIFIED",
            "task_id": control["task_id"],
            "control_revision": control["control_revision"],
            "receipt_ref": "evidence:task-scope-verification",
            "evidence_refs": ["evidence:criterion-1"],
        }

    def test_binding_is_revision_scope_and_root_locked(self):
        binding = goal_scope_binding(goal())
        self.assertEqual(binding["policy_id"], POLICY_ID)
        self.assertEqual(binding["max_same_blocker_attempts"], 3)
        self.assertFalse(binding["automatic_scope_expansion"])
        changed = goal()
        changed["revision"] = 8
        self.assertNotEqual(goal_scope_binding(changed)["goal_digest"], binding["goal_digest"])
        with self.assertRaises(TaskScopeClosureError):
            validate_goal_scope_binding(binding, expected_root_task_id="other-goal")

    def test_scope_overlap_is_rejected(self):
        g = goal()
        g["scope"]["out_of_scope"].append("implement task-scope policy")
        with self.assertRaises(TaskScopeClosureError):
            goal_scope_binding(g)

    def test_undeclared_work_is_followup_not_scope_expansion(self):
        result = classify_scope_item(goal()["scope"], "new unrelated task")
        self.assertEqual(result["classification"], "OUT_OF_SCOPE_FOLLOWUP")
        self.assertTrue(result["requires_new_task"])
        self.assertFalse(result["automatic_execution_allowed_by_scope"])

    def test_three_same_blocker_failures_freeze_and_fourth_is_impossible(self):
        _, control = self.control()
        fp = blocker_fingerprint("CI_BLOCKER", ["run:1"])
        for n in range(3):
            control = record_blocker_failure(control, fp, f"failure {n + 1}")
        self.assertEqual(control["blocker_attempts"][fp], MAX_SAME_BLOCKER_ATTEMPTS)
        self.assertEqual(control["state"], HUMAN_INTERVENTION_REQUIRED)
        self.assertTrue(control["execution_frozen"])
        self.assertFalse(control["automatic_retry_allowed"])
        self.assertFalse(control["automatic_replan_allowed"])
        self.assertFalse(control["alternative_route_allowed"])
        with self.assertRaises(TaskScopeClosureError):
            record_blocker_failure(control, fp, "fourth")
        with self.assertRaises(TaskScopeClosureError):
            assert_execution_allowed(control)

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

    def test_followup_is_persisted_bound_and_tamper_evident(self):
        binding, control = self.control()
        control = register_followup_handoff(
            control,
            binding,
            goal()["scope"],
            scope_item="unrelated provider upgrade",
            discovered_issue="A provider upgrade is available.",
            why_out_of_scope="The current task only implements task-scope policy.",
            current_state="Original task remains active.",
            evidence_refs=["evidence:provider-note"],
            suggested_new_task_objective="Evaluate the provider upgrade separately.",
            suggested_new_conversation_start="Start a new CFA3 provider-upgrade task.",
        )
        handoff = control["followup_handoffs"][0]
        self.assertTrue(handoff["requires_new_task_id"])
        self.assertTrue(handoff["requires_user_start"])
        self.assertFalse(handoff["automatic_start"])
        forged = copy.deepcopy(control)
        forged["followup_handoffs"][0]["current_state"] = "forged"
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(forged)

    def test_verified_close_requires_evidence_authority_receipt(self):
        _, control = self.control()
        with self.assertRaises(TaskScopeClosureError):
            close_task_control(control, "VERIFIED")
        bad = self.evidence_receipt(control)
        bad["authority"] = "agent-self"
        with self.assertRaises(TaskScopeClosureError):
            close_task_control(control, "VERIFIED", verification_evidence=bad)
        closed = close_task_control(
            control, "VERIFIED", verification_evidence=self.evidence_receipt(control)
        )
        self.assertEqual(closed["state"], CLOSED)
        self.assertEqual(closed["user_closure_state"], DONE)
        with self.assertRaises(TaskScopeClosureError):
            assert_execution_allowed(closed)

    def test_verified_close_with_followup_projects_new_task_discovered(self):
        binding, control = self.control()
        control = register_followup_handoff(
            control,
            binding,
            goal()["scope"],
            scope_item="another followup",
            discovered_issue="Separate work was discovered.",
            why_out_of_scope="It is not part of this task.",
            current_state="Original task is otherwise complete.",
            evidence_refs=[],
            suggested_new_task_objective="Handle separate work.",
            suggested_new_conversation_start="Start a separate CFA3 task.",
        )
        closed = close_task_control(
            control, "VERIFIED", verification_evidence=self.evidence_receipt(control)
        )
        self.assertEqual(closed["user_closure_state"], NEW_TASK_DISCOVERED)

    def test_nonverified_terminal_freezes_for_human_intervention(self):
        _, control = self.control()
        blocked = close_task_control(control, "FAILED")
        self.assertEqual(blocked["state"], HUMAN_INTERVENTION_REQUIRED)
        self.assertTrue(blocked["execution_frozen"])
        with self.assertRaises(TaskScopeClosureError):
            assert_execution_allowed(blocked)

    def test_goal_bound_execution_requires_active_control_and_fresh_admission(self):
        binding, control = self.control()
        task, graph, model = execution_fixture(binding)
        with self.assertRaises(WorkloadContractError):
            compile_execution_plan(
                task, graph, model,
                task_spec_digest="sha256:task",
                max_transfer_hops=1,
                behavior_context=behavior_context(),
            )
        plan = compile_execution_plan(
            task, graph, model,
            task_spec_digest="sha256:task",
            max_transfer_hops=1,
            behavior_context=behavior_context(),
            task_control=control,
        )
        admission = validate_execution_admission(plan, task_control=control)
        self.assertTrue(admission["fresh_revalidation"])
        self.assertEqual(admission["decision"], "ALLOW")

        fp = blocker_fingerprint("TRANSIENT_BLOCKER", ["run:1"])
        newer = record_blocker_failure(control, fp, "failed once")
        with self.assertRaises(WorkloadContractError):
            validate_execution_admission(plan, task_control=newer)

    def test_frozen_control_cannot_compile_or_resume_cached_plan(self):
        binding, control = self.control()
        task, graph, model = execution_fixture(binding)
        plan = compile_execution_plan(
            task, graph, model,
            task_spec_digest="sha256:task",
            max_transfer_hops=1,
            behavior_context=behavior_context(),
            task_control=control,
        )
        fp = blocker_fingerprint("BLOCKER", ["run"])
        frozen = control
        for _ in range(3):
            frozen = record_blocker_failure(frozen, fp, "fail")
        with self.assertRaises(WorkloadContractError):
            compile_execution_plan(
                task, graph, model,
                task_spec_digest="sha256:task",
                max_transfer_hops=1,
                behavior_context=behavior_context(),
                task_control=frozen,
            )
        with self.assertRaises(WorkloadContractError):
            validate_execution_admission(plan, task_control=frozen)


if __name__ == "__main__":
    unittest.main()
