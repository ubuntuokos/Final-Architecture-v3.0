"""FA3 source-bound design preflight: existing source and permission boundaries."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_goal_preflight import (
    GoalPreflightError, _topological_steps, _intent_rel,
    _tracked_source, design_preflight, compile_source_bound_plan,
)
from test_goal_execution_foundation import fixture as base_fixture, task as base_task

INTENT = "canonical/intents/FA3-GOAL-EXECUTION-APPLICATION-INTENT-2026-09-28.json"


def case():
    goal = base_fixture()
    defs = json.loads(
        (ROOT / "canonical/FA3-AGENT-DEFINITION-REGISTRY-001.json").read_text()
    )["definitions"]
    role = defs[0]["definition_id"]
    goal["execution_policy"]["authorized_ai_participants"] = [role]
    step = base_task()
    step["agent_definition_ref"] = role
    step["depends_on"] = []
    return goal, [step]


class GoalSourcePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Unit-test source-bound goal semantics without live GitHub. The donor
        # readiness module has separate fail-closed tests and live CI enforcement.
        cls._donor_mock = patch("fa3_goal_preflight.donor_readiness_gate", return_value={
            "result":"READY_FOR_SEPARATE_FA3_ADMISSION_GATES","findings":[]})
        cls._donor_mock.start()

    @classmethod
    def tearDownClass(cls):
        cls._donor_mock.stop()

    def test_design_preflight_queries_actual_reuse_donor_action_agent_and_hardware(self):
        goal, steps = case()
        receipt = design_preflight(ROOT, goal, INTENT, steps)
        self.assertEqual(receipt["schema"], "fa3.goal-source-preflight.v1")
        self.assertEqual(receipt["reuse"]["result"], "PASS")
        self.assertGreaterEqual(receipt["application_donor_index"]["donor_records"], 306)
        self.assertTrue(receipt["source_sha256"][INTENT])
        self.assertTrue(receipt["source_sha256"]["canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"])
        self.assertIn("canonical/actions/orchestration.inspect.json", receipt["source_sha256"])
        self.assertEqual(receipt["hardware_audit"]["accelerator_cardinality"], "0..N")
        self.assertEqual(receipt["hardware_audit"]["runtime_host_observation"], "PENDING_CURRENT_HOST")
        self.assertFalse(receipt["authority"])
        self.assertFalse(receipt["runtime_admission"])
        self.assertFalse(receipt["execution_performed"])

    def test_real_existing_workforce_and_workload_bridge_remains_design_only(self):
        goal, steps = case()
        output = compile_source_bound_plan(ROOT, goal, INTENT, steps)
        self.assertEqual(output["schema"], "fa3.goal-source-bound-plan.v1")
        self.assertEqual(output["goal_plan"]["steps"][0]["design_route"]["status"], "ROUTED")
        self.assertEqual(output["goal_plan"]["steps"][0]["runtime_admission"],
                         "PENDING_EXISTING_AUTHORITIES")
        self.assertEqual(output["preflight"]["external_admission"]["hrb_lease"],
                         "REQUIRES_FRESH_HRB_ADMISSION")
        self.assertTrue(output["requires_real_external_authority_admission"])
        self.assertFalse(output["authority"])
        self.assertFalse(output["runtime_admitted"])
        self.assertFalse(output["execution_performed"])

    def test_canonical_sources_are_exact_committed_bytes(self):
        data, sha = _tracked_source(ROOT, INTENT)
        self.assertTrue(data.startswith(b"{"))
        self.assertEqual(len(sha), 64)

    def test_path_escape_and_untracked_intent_rejected(self):
        for candidate in ("../AGENTS.md",
                          "canonical/intents/../FA3-DONOR-REFERENCE-REGISTRY-001.json",
                          "canonical/intents/FA3-NONEXISTENT.json",
                          "canonical/intents/anything.yaml"):
            with self.subTest(candidate=candidate):
                with self.assertRaises(GoalPreflightError):
                    design_preflight(ROOT, case()[0], candidate, case()[1])

    def test_action_effect_must_match_real_uaf_contract(self):
        goal, steps = case()
        steps[0]["effect"] = "WRITE"  # actual orchestration.inspect is nonmutating
        with self.assertRaises(GoalPreflightError):
            design_preflight(ROOT, goal, INTENT, steps)

    def test_unknown_action_cannot_just_be_added_to_prompt_allowlist(self):
        goal, steps = case()
        goal["execution_policy"]["allowed_action_ids"] = ["shell.direct"]
        steps[0]["action_id"] = "shell.direct"
        with self.assertRaises(GoalPreflightError):
            design_preflight(ROOT, goal, INTENT, steps)

    def test_unknown_agent_role_not_admitted_by_user_allowlist(self):
        goal, steps = case()
        goal["execution_policy"]["authorized_ai_participants"] = ["invented-agent"]
        steps[0]["agent_definition_ref"] = "invented-agent"
        with self.assertRaises(GoalPreflightError):
            design_preflight(ROOT, goal, INTENT, steps)

    def test_action_not_in_user_scope_rejected(self):
        goal, steps = case()
        goal["execution_policy"]["allowed_action_ids"] = ["orchestration.plan"]
        with self.assertRaises(GoalPreflightError):
            design_preflight(ROOT, goal, INTENT, steps)

    def test_duplicate_or_cyclic_graph_fails_before_runtime(self):
        goal, steps = case()
        twin = copy.deepcopy(steps[0])
        twin["task_id"] = "task-02"
        steps[0]["depends_on"] = ["task-02"]
        twin["depends_on"] = ["task-01"]
        with self.assertRaises(GoalPreflightError):
            design_preflight(ROOT, goal, INTENT, [*steps, twin])

    def test_missing_dependency_and_excessive_depth_fail(self):
        with self.assertRaises(GoalPreflightError):
            _topological_steps([{"task_id": "A", "depends_on": ["MISSING"]}], 2)
        seq = [{"task_id": "A", "depends_on": []},
               {"task_id": "B", "depends_on": ["A"]},
               {"task_id": "C", "depends_on": ["B"]}]
        with self.assertRaises(GoalPreflightError):
            _topological_steps(seq, 2)

    def test_valid_dag_topologically_orders_without_execution(self):
        graph = _topological_steps([{"task_id": "A", "depends_on": []},
                                    {"task_id": "B", "depends_on": ["A"]}], 2)
        self.assertEqual(graph["order"], ["A", "B"])
        self.assertEqual(graph["max_depth"], 2)
        self.assertFalse(graph["executed"])
        self.assertFalse(graph["candidate_set_expanded"])

    def test_reuse_intent_scope_and_non_mutation(self):
        goal, steps = case()
        original = copy.deepcopy((goal, steps))
        result = design_preflight(ROOT, goal, INTENT, steps)
        self.assertEqual((goal, steps), original)
        self.assertEqual(result["application_project_id"], "FA3-GOAL-EXECUTION-CONTRACTS-001")
        self.assertEqual(result["external_admission"]["security_approval"],
                         "REQUIRES_EXISTING_AUTHORITY")
        self.assertFalse(result["application_donor_index"]["automatic_selection"])


    def test_committed_khronos_assessment_matches_live_reuse_discovery(self):
        from fa3_reuse_assessment import assess_intent
        assessment_path = (
            "canonical/assessments/FA3-GOAL-EXECUTION-REUSE-ASSESSMENT-2026-09-28.json"
        )
        canonical, _ = _tracked_source(ROOT, assessment_path)
        assessment = json.loads(canonical)
        intent = json.loads(_tracked_source(ROOT, INTENT)[0])
        actual = assess_intent(ROOT, intent)
        self.assertEqual(assessment["result"], "PASS")
        self.assertEqual(assessment["intent_id"], actual["intent_id"])
        self.assertEqual(actual["result"], "PASS")
        self.assertEqual(assessment["implementation_readiness"],
                         actual["implementation_readiness"])
        self.assertEqual(assessment["gaps"], actual["gaps"])
        expected = {
            row["source_family_id"]: row
            for row in actual["mandatory_source_reviews"]
        }
        for review in assessment["mandatory_source_reviews"]:
            matching = expected[review["source_family_id"]]
            self.assertEqual(review["review_status"], matching["review_status"])
            self.assertEqual(review["matched_candidate_ids"], matching["matched_candidate_ids"])
            self.assertEqual(review["available_candidate_ids"], matching["available_candidate_ids"])
            self.assertFalse(review["authority"])
            self.assertFalse(review["automatic_selection"])
            self.assertFalse(review["automatic_activation"])
        self.assertFalse(assessment["current_host_runtime_promotion_claim"])
        self.assertFalse(assessment["global_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
