from __future__ import annotations

import unittest
from pathlib import Path

from fa3_orchestration_guard_chain import evaluate_guard_chain, load_guard_contract

ROOT = Path(__file__).resolve().parents[1]


class GuardChainTests(unittest.TestCase):
    def task(self):
        return {
            "task_id": "research",
            "task_group_id": "F15",
            "objective_ancestry": ["goal", "blueprint", "research"],
            "required_capabilities": ["retrieval"],
            "metadata": {
                "agent_application_blueprint": {
                    "task_group_id": "F15",
                    "role_kind": "WORKER"
                }
            }
        }

    def test_guard_order(self):
        c = load_guard_contract(ROOT)
        self.assertEqual([x["guard_id"] for x in c["guard_chain"]], [f"G{i}" for i in range(11)])
        self.assertFalse(c["authority"])

    def test_planning_pass_with_explicit_authority_inputs(self):
        result = evaluate_guard_chain(
            ROOT,
            self.task(),
            phase="PLANNING",
            context={
                "goal_valid": True,
                "scope_monotonic": True,
                "dependency_graph_valid": True,
                "security_decision": "PASS",
                "specialist_eligible": True,
            },
        )
        self.assertEqual(result["overall_result"], "PASS")
        self.assertEqual(result["task_group"]["task_group_id"], "F15")

    def test_unknown_task_group_blocks(self):
        task = self.task()
        task["task_group_id"] = "F99"
        task["metadata"]["agent_application_blueprint"]["task_group_id"] = "F99"
        result = evaluate_guard_chain(
            ROOT,
            task,
            phase="PLANNING",
            context={
                "goal_valid": True,
                "scope_monotonic": True,
                "dependency_graph_valid": True,
                "security_decision": "PASS",
                "specialist_eligible": True,
            },
        )
        self.assertEqual(next(x for x in result["guards"] if x["guard_id"] == "G1")["state"], "BLOCK")
        self.assertEqual(result["overall_result"], "BLOCK")

    def test_runtime_resource_wait_is_not_pass(self):
        result = evaluate_guard_chain(
            ROOT,
            self.task(),
            phase="RUNTIME",
            context={
                "runtime_admitted": True,
                "workload_mode_compatible": True,
                "hrb_admitted": False,
                "model_route_valid": True,
                "uaf_effect_authorized": True,
            },
        )
        self.assertEqual(result["overall_result"], "WAITING_RESOURCE")
        self.assertEqual(next(x for x in result["guards"] if x["guard_id"] == "G7")["state"], "WAITING_RESOURCE")

    def test_post_execution_requires_independent_evidence(self):
        pending = evaluate_guard_chain(ROOT, self.task(), phase="POST_EXECUTION", context={})
        self.assertEqual(pending["overall_result"], "WAITING_AUTHORITY")
        passed = evaluate_guard_chain(ROOT, self.task(), phase="POST_EXECUTION", context={"evidence_verified": True})
        self.assertEqual(passed["overall_result"], "PASS")


if __name__ == "__main__":
    unittest.main()
