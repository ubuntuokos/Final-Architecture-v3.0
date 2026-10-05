from __future__ import annotations
import unittest
from fa3_orchestration_governance import (
    OrchestrationGovernanceError, approval_allows, bind_approval,
    build_monitor_projection, build_task_governance, issue_execution_claim,
    validate_claim_takeover, validate_dependency_graph, validate_responsibility_chain,
)

class Tests(unittest.TestCase):
    def test_structural_parent_is_not_execution_dependency(self):
        edges = validate_dependency_graph(["a", "b"], [
            {"from_task_id": "b", "to_task_id": "a", "type": "STRUCTURAL_PARENT"}
        ])
        self.assertEqual(edges[0]["type"], "STRUCTURAL_PARENT")

    def test_hard_dependency_cycle_fails_closed(self):
        with self.assertRaises(OrchestrationGovernanceError):
            validate_dependency_graph(["a", "b"], [
                {"from_task_id": "a", "to_task_id": "b", "type": "BLOCKED_BY"},
                {"from_task_id": "b", "to_task_id": "a", "type": "DATA_REQUIRES"},
            ])

    def test_subtask_requires_real_boundary(self):
        with self.assertRaises(OrchestrationGovernanceError):
            build_task_governance({"task_id": "b", "parent_task_id": "a"})
        g = build_task_governance({
            "task_id": "b", "parent_task_id": "a",
            "split_reasons": ["INDEPENDENT_REVIEW_OR_APPROVAL"],
        })
        self.assertEqual(g["liveness_state"], "READY")

    def test_delegation_scope_cannot_expand(self):
        with self.assertRaises(OrchestrationGovernanceError):
            validate_responsibility_chain([
                {"principal_id": "owner", "role": "OWNER", "authority_scope": ["read"]},
                {"principal_id": "child", "role": "WORKER", "authority_scope": ["read", "write"]},
            ])

    def test_live_claim_cannot_be_stolen(self):
        current = issue_execution_claim("t", "a", 1, "idem-1", ["read"], "2026-10-01T00:00:00+00:00")
        successor = issue_execution_claim("t", "b", 2, "idem-2", ["read"], "2026-10-01T01:00:00+00:00")
        with self.assertRaises(OrchestrationGovernanceError):
            validate_claim_takeover(current, successor, "2026-09-30T20:00:00+00:00")
        current["state"] = "RELEASED"
        self.assertTrue(validate_claim_takeover(current, successor, "2026-09-30T20:00:00+00:00"))

    def test_approval_is_revision_and_digest_bound(self):
        digest = "a" * 64
        a = bind_approval("plan", 3, digest, "IMPLEMENT", ["orchestration.execute"], "AUTH-HUMAN")
        self.assertTrue(approval_allows(a, "plan", 3, digest, "orchestration.execute"))
        self.assertFalse(approval_allows(a, "plan", 4, digest, "orchestration.execute"))
        self.assertFalse(approval_allows(a, "plan", 3, "b" * 64, "orchestration.execute"))

    def test_budget_and_liveness_are_projected_not_authority(self):
        g = build_task_governance({
            "task_id": "x",
            "budget_envelope": {"retry_count": 2, "parallelism": 4},
            "liveness_state": "WAITING_RESOURCE",
        }, "goal")
        self.assertFalse(g["monitoring_authority"])
        self.assertEqual(g["budget_envelope"]["parallelism"], 4)

    def test_monitor_projection_is_non_authoritative(self):
        p = build_monitor_projection([
            {"status": "ROUTED", "governance_projection": {"liveness_state": "RUNNING"}},
            {"status": "HUMAN_ESCALATION", "governance_projection": {"liveness_state": "BLOCKED"}},
        ])
        self.assertFalse(p["authority"])
        self.assertEqual(p["attention_required"], 1)
        self.assertEqual(p["liveness_counts"]["RUNNING"], 1)

if __name__ == "__main__":
    unittest.main()
