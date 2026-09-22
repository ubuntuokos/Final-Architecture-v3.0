from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_router_materialize import MaterializationDenied, choose_model, select_bindings


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


if __name__=="__main__":
    unittest.main()
