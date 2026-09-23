from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_router_materialize import MaterializationDenied, choose_model, render_litellm, select_bindings


class _DecisionFabricStub:
    def __init__(self, ranked):
        self.ranked = ranked
        self.requests = []

    def decide(self, request, provider_id):
        self.requests.append((request, provider_id))
        return {
            "status": "DECIDED",
            "result": {"ranked": list(self.ranked)},
            "authority": False,
            "candidate_set_expanded": False,
        }


class TestModelRouterSelection(unittest.TestCase):
    def test_preferred_model_is_runtime_only(self):
        self.assertEqual(choose_model(["z-chat","a-chat"],["z-chat"]),"z-chat")
        self.assertEqual(choose_model(["z-chat","a-chat"],[]),"a-chat")

    def test_non_chat_catalog_fails_closed(self):
        with self.assertRaises(MaterializationDenied):
            choose_model(["embed-model","whisper-large"],[])

    def test_provider_priority_and_route_scope(self):
        routes=[
            {"route":"fa3-pageindex-index"},
            {"route":"fa3-pageindex-reason"},
        ]
        candidates=[
            {"provider_id":"P1","runtime_id":"r1","api_base":"http://127.0.0.1:1/v1","priority":10,"routes":["fa3-pageindex-index"]},
            {"provider_id":"P2","runtime_id":"r2","api_base":"http://127.0.0.1:2/v1","priority":5,"routes":["*"]},
        ]
        catalogs={"r1":["model-a"],"r2":["model-b"]}
        selected=select_bindings(routes,candidates,catalogs)
        self.assertEqual(selected["fa3-pageindex-index"]["runtime_id"],"r1")
        self.assertEqual(selected["fa3-pageindex-reason"]["runtime_id"],"r2")
        self.assertEqual(selected["fa3-pageindex-index"]["selection"],"RUNTIME_DISCOVERED")

    def test_litellm_provider_options_are_preserved_without_routing_override(self):
        routes=[{"route":"fa3-text-primary"}]
        candidates=[{
            "provider_id":"P1",
            "runtime_id":"r1",
            "api_base":"http://127.0.0.1:11434",
            "priority":10,
            "routes":["*"],
            "litellm_provider":"ollama_chat",
            "litellm_options":{"num_gpu":0,"num_ctx":512},
        }]
        selected=select_bindings(routes,candidates,{"r1":["gemma3:1b"]})
        binding=selected["fa3-text-primary"]
        self.assertEqual(binding["litellm_options"],{"num_gpu":0,"num_ctx":512})
        rendered=render_litellm(selected)
        self.assertIn('model: "ollama_chat/gemma3:1b"',rendered)
        self.assertIn('api_base: "http://127.0.0.1:11434"',rendered)
        self.assertIn("num_gpu: 0",rendered)
        self.assertNotIn("FA3_MODEL_ROUTER_BACKEND_DUMMY_KEY",rendered)

    def test_reserved_litellm_option_fails_closed(self):
        with self.assertRaises(MaterializationDenied):
            select_bindings(
                [{"route":"fa3-text-primary"}],
                [{
                    "provider_id":"P1",
                    "runtime_id":"r1",
                    "api_base":"http://127.0.0.1:11434",
                    "priority":10,
                    "routes":["*"],
                    "litellm_options":{"model":"forbidden"},
                }],
                {"r1":["gemma3:1b"]},
            )

    def test_decision_fabric_active_may_only_choose_pre_admitted_candidate(self):
        routes=[{"route":"fa3-pageindex-index"}]
        candidates=[
            {"provider_id":"P1","runtime_id":"r1","api_base":"http://127.0.0.1:1/v1","priority":10,"routes":["*"]},
            {"provider_id":"P2","runtime_id":"r2","api_base":"http://127.0.0.1:2/v1","priority":5,"routes":["*"]},
        ]
        catalogs={"r1":["model-a"],"r2":["model-b"]}
        fabric=_DecisionFabricStub(["r2::model-b","r1::model-a"])
        selected=select_bindings(
            routes,candidates,catalogs,
            decision_fabric=fabric,
            decision_rollout="ACTIVE",
        )
        self.assertEqual(selected["fa3-pageindex-index"]["runtime_id"],"r2")
        self.assertFalse(selected["fa3-pageindex-index"]["decision_advisory_changes_authority"])
        request,_provider=fabric.requests[0]
        self.assertEqual(
            {row["id"] for row in request["candidates"]},
            {"r1::model-a","r2::model-b"},
        )
        self.assertEqual(request["final_policy_owner"],"FA3-AUTH-MODEL-ROUTER-001")

    def test_decision_fabric_shadow_never_changes_deterministic_binding(self):
        routes=[{"route":"fa3-pageindex-index"}]
        candidates=[
            {"provider_id":"P1","runtime_id":"r1","api_base":"http://127.0.0.1:1/v1","priority":10,"routes":["*"]},
            {"provider_id":"P2","runtime_id":"r2","api_base":"http://127.0.0.1:2/v1","priority":5,"routes":["*"]},
        ]
        catalogs={"r1":["model-a"],"r2":["model-b"]}
        fabric=_DecisionFabricStub(["r2::model-b","r1::model-a"])
        selected=select_bindings(
            routes,candidates,catalogs,
            decision_fabric=fabric,
            decision_rollout="SHADOW",
        )
        self.assertEqual(selected["fa3-pageindex-index"]["runtime_id"],"r1")

    def test_decision_fabric_cannot_escape_model_router_candidate_set(self):
        routes=[{"route":"fa3-pageindex-index"}]
        candidates=[
            {"provider_id":"P1","runtime_id":"r1","api_base":"http://127.0.0.1:1/v1","priority":10,"routes":["*"]},
        ]
        catalogs={"r1":["model-a"]}
        fabric=_DecisionFabricStub(["foreign::model-x"])
        with self.assertRaises(MaterializationDenied):
            select_bindings(
                routes,candidates,catalogs,
                decision_fabric=fabric,
                decision_rollout="ACTIVE",
            )


if __name__=="__main__":
    unittest.main()
