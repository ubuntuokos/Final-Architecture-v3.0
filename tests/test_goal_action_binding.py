import copy
import unittest

from fa3_decision_fabric import DecisionFabric
from fa3_goal_action_binding import (
    ActionBindingDenied, prepare_action_request, bind_advisory_selection,
    choose_advisory_action,
)
from fa3_goal_execution import compile_plan
from test_goal_execution_foundation import ROOT, fixture, task, preflight

def prepared():
    goal = fixture()
    plan = compile_plan(ROOT, goal, [task()], preflight())
    kw = dict(registered_action_ids=["orchestration.inspect"],
              gateway_action_ids=["orchestration.inspect"],
              security_action_ids=["orchestration.inspect"],
              eligible_agent_refs=["agent-existing-01"])
    return goal, plan, kw

class GoalActionBindingTests(unittest.TestCase):
    def test_reuses_decision_fabric_without_granting_effects(self):
        goal, plan, kw = prepared()
        got = choose_advisory_action(goal, plan, **kw)
        self.assertEqual(got["selected_task_id"], "task-01")
        self.assertFalse(got["authority"])
        self.assertFalse(got["effect_authorization"])
        self.assertFalse(got["execution_performed"])

    def test_candidate_mask_is_intersection_not_untrusted_plan_only(self):
        goal, plan, kw = prepared()
        for name in ("registered_action_ids", "gateway_action_ids", "security_action_ids"):
            with self.subTest(name=name):
                invalid = {**kw, name: ["another.action"]}
                with self.assertRaises(ActionBindingDenied):
                    prepare_action_request(goal, plan, **invalid)

    def test_unauthorized_agent_is_hidden_before_decision(self):
        goal, plan, kw = prepared()
        with self.assertRaises(ActionBindingDenied):
            prepare_action_request(goal, plan, **{**kw, "eligible_agent_refs": ["other-agent"]})

    def test_old_revision_and_foreign_plan_rejected(self):
        goal, plan, kw = prepared()
        goal["revision"] += 1
        with self.assertRaises(ActionBindingDenied):
            prepare_action_request(goal, plan, **kw)

    def test_tampered_trace_and_candidate_expansion_denied(self):
        goal, plan, kw = prepared()
        p = prepare_action_request(goal, plan, **kw)
        trace = DecisionFabric().decide(p["request"])
        for key, value in (("candidate_set_expanded", True), ("authority", True),
                           ("candidate_digest_sha256", "0"*64), ("status", "NO_DECISION")):
            with self.subTest(key=key):
                changed = {**trace, key: value}
                with self.assertRaises(ActionBindingDenied):
                    bind_advisory_selection(p, changed)
        wrong = copy.deepcopy(trace)
        wrong["result"]["selected"] = "direct.shell"
        with self.assertRaises(ActionBindingDenied):
            bind_advisory_selection(p, wrong)

    def test_provider_failure_cannot_select_action(self):
        goal, plan, kw = prepared()
        p = prepare_action_request(goal, plan, **kw)
        trace = DecisionFabric().decide(p["request"], provider_id="missing")
        with self.assertRaises(ActionBindingDenied):
            bind_advisory_selection(p, trace)

if __name__ == "__main__":
    unittest.main()
