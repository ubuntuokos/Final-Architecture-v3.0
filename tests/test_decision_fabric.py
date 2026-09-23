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
from fa3_local_decision_provider import LocalSemanticDecisionProvider
from fa3_decision_trace import DecisionTraceStore
from fa3_hybrid_retrieval import decision_rerank


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

    def test_local_semantic_provider_uses_logical_router_route(self):
        def transport(payload):
            self.assertEqual(payload["model"], "fa3-text-primary")
            return {
                "choices": [
                    {"message": {"content": '{"selected":"b","confidence":0.88}'}}
                ]
            }

        provider = LocalSemanticDecisionProvider(
            explicitly_enabled=True,
            token="test-only",
            transport=transport,
        )
        fabric = DecisionFabric([provider])
        trace = fabric.decide({
            "contract": "SELECT_ONE",
            "purpose": "choose bounded candidate",
            "candidates": [{"id": "a"}, {"id": "b"}],
            "constraints": {},
            "policy_context": {},
            "evidence_refs": [],
            "failure_policy": "FAIL_CLOSED",
            "rollout": "SHADOW",
            "final_policy_owner": "FA3-AUTH-MODEL-ROUTER-001",
        }, provider.provider_id)
        self.assertEqual(trace["result"]["selected"], "b")
        self.assertEqual(trace["provider_meta"]["logical_route"], "fa3-text-primary")
        self.assertFalse(trace["provider_meta"]["physical_model_pinned"])
        self.assertFalse(trace["provider_meta"]["physical_backend_pinned"])

    def test_trace_store_is_append_only_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DecisionTraceStore(Path(tmp) / "decision-traces.jsonl")
            fabric = DecisionFabric(trace_writer=store.append)
            first = fabric.decide({
                "contract": "BOOLEAN",
                "purpose": "trace-one",
                "candidates": [],
                "constraints": {"value": True},
                "policy_context": {},
                "evidence_refs": [],
                "failure_policy": "NO_DECISION",
                "rollout": "ACTIVE",
                "final_policy_owner": "TEST",
            })
            second = fabric.decide({
                "contract": "BOOLEAN",
                "purpose": "trace-two",
                "candidates": [],
                "constraints": {"value": False},
                "policy_context": {},
                "evidence_refs": [],
                "failure_policy": "NO_DECISION",
                "rollout": "ACTIVE",
                "final_policy_owner": "TEST",
            })
            rows = store.tail(10)
            self.assertEqual([x["decision_id"] for x in rows], [first["decision_id"], second["decision_id"]])

    def test_knowledge_decision_rerank_cannot_add_candidates(self):
        trace = {
            "schema": "fa3.retrieval-trace.v1",
            "trace_id": "trace",
            "plan_id": "plan",
            "stages": [],
            "candidates": [
                {"candidate_id": "low", "source_id": "s", "locator": "1", "score": 0.1, "evidence_refs": []},
                {"candidate_id": "high", "source_id": "s", "locator": "2", "score": 0.9, "evidence_refs": []},
            ],
            "provider_receipts": [],
            "evidence_refs": [],
            "authority_snapshot": {"knowledge_root": "FA3-KNOWLEDGE-001"},
            "derived": True,
        }
        out = decision_rerank(trace, rollout="ACTIVE")
        self.assertTrue(out["decision_rerank_applied"])
        self.assertEqual([x["candidate_id"] for x in out["candidates"]], ["high", "low"])
        self.assertEqual({x["candidate_id"] for x in out["candidates"]}, {"low", "high"})

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
