from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fa3_context_selection import ContextSelector, verify_projection
from fa3_decision_fabric import (
    DecisionError,
    DecisionFabric,
    ProviderResult,
    RuleDecisionProvider,
)
from fa3_jev_decision_provider import JevDecisionProvider


class ExpandingProvider:
    provider_id = "TEST-EXPANDING"
    semantic = True

    def decide(self, request):
        return ProviderResult("DECIDED", {"selected": "UNAUTHORIZED-CANDIDATE"}, 0.9)


class FailingProvider:
    provider_id = "TEST-FAILING"
    semantic = True

    def decide(self, request):
        raise RuntimeError("test provider failure")


class DecisionFabricTests(unittest.TestCase):
    def test_rule_provider_selects_only_candidate(self):
        fabric = DecisionFabric([RuleDecisionProvider()])
        trace = fabric.decide({
            "contract": "SELECT_ONE",
            "purpose": "test",
            "candidates": [
                {"id": "a", "metadata": {"priority": 1}},
                {"id": "b", "metadata": {"priority": 2}},
            ],
            "constraints": {},
            "policy_context": {},
            "evidence_refs": [],
            "failure_policy": "NO_DECISION",
            "rollout": "ACTIVE",
            "final_policy_owner": "TEST",
        })
        self.assertEqual(trace["result"]["selected"], "b")
        self.assertFalse(trace["authority"])
        self.assertFalse(trace["candidate_set_expanded"])

    def test_candidate_expansion_is_denied(self):
        fabric = DecisionFabric([ExpandingProvider()])
        with self.assertRaises(DecisionError):
            fabric.decide({
                "contract": "SELECT_ONE",
                "purpose": "test",
                "candidates": [{"id": "a"}],
                "constraints": {},
                "policy_context": {},
                "evidence_refs": [],
                "failure_policy": "FAIL_CLOSED",
                "rollout": "SHADOW",
                "final_policy_owner": "TEST",
            }, "TEST-EXPANDING")

    def test_high_risk_provider_failure_fails_closed(self):
        fabric = DecisionFabric([FailingProvider()])
        trace = fabric.decide({
            "contract": "BOOLEAN",
            "purpose": "risk",
            "candidates": [],
            "constraints": {},
            "policy_context": {},
            "evidence_refs": [],
            "failure_policy": "FAIL_CLOSED",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-SCS-001",
        }, "TEST-FAILING")
        self.assertEqual(trace["status"], "DENIED")
        self.assertFalse(trace["authority"])

    def test_context_hidden_is_reversible_and_source_preserved(self):
        selector = ContextSelector()
        projection = selector.project([
            {"id": "decision", "kind": "canonical_decision", "text": "must remain"},
            {"id": "a", "kind": "note", "text": "alpha", "metadata": {"priority": 10}},
            {"id": "b", "kind": "note", "text": "beta", "metadata": {"priority": 1}},
        ], target_active=1, rollout="ACTIVE")
        verify_projection(projection)
        by_id = {row["id"]: row for row in projection["items"]}
        self.assertEqual(by_id["decision"]["state"], "PROTECTED")
        self.assertEqual(by_id["a"]["state"], "ACTIVE")
        self.assertEqual(by_id["b"]["state"], "HIDDEN")
        restored = selector.restore(projection, "b")
        verify_projection(restored)
        self.assertEqual({row["id"]: row for row in restored["items"]}["b"]["state"], "ACTIVE")

    def test_jev_requires_explicit_admission_and_runtime_model(self):
        provider = JevDecisionProvider(
            explicitly_enabled=False,
            api_key="test",
            model="jev-test-not-called",
        )
        fabric = DecisionFabric([provider])
        trace = fabric.decide({
            "contract": "BOOLEAN",
            "purpose": "test",
            "candidates": [],
            "constraints": {},
            "policy_context": {},
            "evidence_refs": [],
            "failure_policy": "NO_DECISION",
            "rollout": "SHADOW",
            "final_policy_owner": "TEST",
        }, provider.provider_id)
        self.assertEqual(trace["status"], "NO_DECISION")

    def test_no_accelerator_environment_is_required(self):
        old = {k: os.environ.get(k) for k in ("CUDA_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "ZE_AFFINITY_MASK")}
        try:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            os.environ["ROCR_VISIBLE_DEVICES"] = ""
            os.environ["ZE_AFFINITY_MASK"] = ""
            fabric = DecisionFabric()
            trace = fabric.decide({
                "contract": "BOOLEAN",
                "purpose": "cpu-only",
                "candidates": [],
                "constraints": {"value": True},
                "policy_context": {},
                "evidence_refs": [],
                "failure_policy": "FAIL_CLOSED",
                "rollout": "ACTIVE",
                "final_policy_owner": "TEST",
            })
            self.assertEqual(trace["status"], "DECIDED")
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
