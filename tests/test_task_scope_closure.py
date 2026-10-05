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
    MAIN_TASK_CONTINUITY_ID,
    MAX_SAME_BLOCKER_ATTEMPTS,
    NEW_TASK_DISCOVERED,
    POLICY_ID,
    REQUESTED_RESULT_SCOPE_GUARD_ID,
    TaskScopeClosureError,
    assert_execution_allowed,
    blocker_fingerprint,
    classify_scope_item,
    close_task_control,
    goal_scope_binding,
    record_blocker_failure,
    record_main_task_event,
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


def behavior_context(scope_origin="REQUIRED_FOR_APPROVED_GOAL"):
    return {
        "action": "READ",
        "current_owner_restriction_allows": True,
        "scope_bound": True,
        "scope_allows_action": True,
        "scope_origin": scope_origin,
        "scope_refs": ["implement task-scope policy"],
        "uncertain_state": False,
        "blocker_kind": None,
        "autonomous_workaround": False,
        "silent_redesign_or_repair": False,
    }


def execution_fixture(binding, scope_origin="REQUIRED_FOR_APPROVED_GOAL"):
    task = {
        "schema": "fa3.agent-workload-task.v1",
        "task_id": "task-1",
        "root_task_id": "goal-scope-1",
        "scope_origin": scope_origin,
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
        self.assertEqual(binding["requested_result_scope_guard_id"], REQUESTED_RESULT_SCOPE_GUARD_ID)
        self.assertTrue(binding["requested_result_is_exclusive_execution_target"])
        self.assertEqual(
            binding["action_admission"],
            "DIRECTLY_REQUIRED_FOR_REQUESTED_RESULT_OR_MINIMUM_NECESSARY_BLOCKER_RESOLUTION",
        )
        self.assertEqual(binding["self_generated_subtask"], "FORBIDDEN")
        self.assertEqual(
            binding["blocker_resolution_scope"],
            "MINIMUM_NECESSARY_FOR_REQUESTED_RESULT_ONLY",
        )
        self.assertFalse(binding["blocker_resolution_may_expand_scope"])
        self.assertEqual(binding["completion_after_requested_result"], "STOP")
        self.assertFalse(binding["automatic_post_completion_work"])
        changed = goal()
        changed["revision"] = 8
        self.assertNotEqual(goal_scope_binding(changed)["goal_digest"], binding["goal_digest"])
        with self.assertRaises(TaskScopeClosureError):
            validate_goal_scope_binding(binding, expected_root_task_id="other-goal")

    def test_requested_result_scope_guard_is_immutable_in_task_control(self):
        binding, control = self.control()
        self.assertEqual(control["requested_result_scope_guard_id"], REQUESTED_RESULT_SCOPE_GUARD_ID)
        self.assertTrue(control["requested_result_is_exclusive_execution_target"])
        self.assertEqual(control["self_generated_subtask"], "FORBIDDEN")
        tampered = copy.deepcopy(control)
        tampered["automatic_post_completion_work"] = True
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(tampered, expected_binding=binding)
        tampered = copy.deepcopy(control)
        tampered["blocker_resolution_may_expand_scope"] = True
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(tampered, expected_binding=binding)

    def test_main_task_binding_is_immutable_and_owner_only(self):
        binding, control = self.control()
        self.assertEqual(binding["main_task_continuity_id"], MAIN_TASK_CONTINUITY_ID)
        self.assertEqual(binding["main_task_id"], "goal-scope-1")
        self.assertEqual(binding["main_task_switch_authority"], "EXPLICIT_OWNER_ONLY")
        self.assertFalse(binding["main_task_automatic_reassignment"])
        self.assertEqual(control["main_task_id"], "goal-scope-1")
        tampered = copy.deepcopy(control)
        tampered["main_task_id"] = "parallel-pr-718"
        with self.assertRaises(TaskScopeClosureError):
            validate_task_control(tampered)

    def test_rules_parallel_work_and_blockers_do_not_replace_main_task(self):
        binding, control = self.control()
        original = control["main_task_id"]
        for kind, summary in (
            ("CONSTRAINT_UPDATE", "A new runtime rule was introduced."),
            ("PARALLEL_OBSERVATION", "Parallel PR status changed."),
            ("MONITORING_OBLIGATION", "A related PR must be watched."),
            ("PARALLEL_TASK_REFERENCE", "Another task is running in parallel."),
        ):
            control = record_main_task_event(control, kind, summary, refs=["ref:test"])
            self.assertEqual(control["main_task_id"], original)
            self.assertFalse(control["main_task_events"][-1]["replaces_main_task"])
        fp = blocker_fingerprint("TEST_BLOCKER", ["run:1"])
        control = record_main_task_event(control, "BLOCKER", "Execution is blocked.", refs=["run:1"])
        control = record_blocker_failure(control, fp, "blocked once")
        self.assertEqual(control["main_task_id"], original)
        self.assertEqual(control["goal_id"], original)
        validate_task_control(control, expected_binding=binding)

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
        self.assertEqual(plan["main_task_continuity_id"], MAIN_TASK_CONTINUITY_ID)
        self.assertEqual(plan["main_task_id"], "goal-scope-1")
        self.assertEqual(plan["main_task_binding_revision"], 1)
        self.assertEqual(plan["main_task_binding_digest"], plan["goal_scope_binding_digest"])
        self.assertEqual(admission["main_task_id"], "goal-scope-1")

        fp = blocker_fingerprint("TRANSIENT_BLOCKER", ["run:1"])
        newer = record_blocker_failure(control, fp, "failed once")
        with self.assertRaises(WorkloadContractError):
            validate_execution_admission(plan, task_control=newer)

    def test_explicit_user_scope_also_requires_active_control(self):
        binding, control = self.control()
        task, graph, model = execution_fixture(binding, "EXPLICIT_USER_SCOPE")
        with self.assertRaises(WorkloadContractError):
            compile_execution_plan(
                task, graph, model,
                task_spec_digest="sha256:task",
                max_transfer_hops=1,
                behavior_context=behavior_context("EXPLICIT_USER_SCOPE"),
            )
        plan = compile_execution_plan(
            task, graph, model,
            task_spec_digest="sha256:task",
            max_transfer_hops=1,
            behavior_context=behavior_context("EXPLICIT_USER_SCOPE"),
            task_control=control,
        )
        self.assertTrue(plan["task_scope_control_required"])
        self.assertEqual(plan["scope_origin"], "EXPLICIT_USER_SCOPE")
        self.assertEqual(
            validate_execution_admission(plan, task_control=control)["decision"],
            "ALLOW",
        )

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
