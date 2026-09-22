from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fa3_hybrid_retrieval import build_plan, context_passport, fuse_candidates, make_trace
from fa3_knowledge_hybrid_retrieval_gate import gate
from fa3_mcp_gateway import GatewayDenied
from fa3_pageindex_local_provider import PageIndexLocalConfig, build_adapters

ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, **kwargs):
        self.kwargs=kwargs
    def submit_document(self, path, mode=None):
        return {"doc_id":"doc-local","mode":mode}
    def get_tree(self, doc_id, include_text=False):
        return {"result":[{"node_id":"1","title":"Root"}]}
    def get_document(self, doc_id):
        return {"id":doc_id,"name":"fixture.pdf"}
    def get_document_structure(self, doc_id):
        return [{"node_id":"1","title":"Root"}]
    def get_page_content(self, doc_id, pages):
        return [{"page_index":1,"text":"fixture","pages":pages}]
    def chat(self, query, doc_id=None):
        return "answer:"+query


class KnowledgeHybridRetrievalTests(unittest.TestCase):
    def test_static_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual("PASS",report["result"],json.dumps(report,indent=2))

    def test_plan_is_provider_neutral_and_traceable(self):
        plan=build_plan({"query":"revenue","source_scope":{"project_id":"P"}})
        self.assertTrue(plan["provider_neutral"])
        self.assertIn("hierarchical",plan["strategy_order"])
        self.assertIn("tree_reasoning",plan["strategy_order"])
        trace=make_trace(plan,[
            {"source_id":"doc","locator":"page:2","score":0.7,"strategy":"lexical","evidence_refs":["e1"]},
            {"source_id":"doc","locator":"page:2","score":0.9,"strategy":"hierarchical","evidence_refs":["e2"]},
        ],[{"provider_id":"p","adapter_id":"a","receipt_id":"r","status":"PASS"}])
        self.assertEqual(1,len(trace["candidates"]))
        self.assertEqual(["e1","e2"],trace["evidence_refs"])
        passport=context_passport(trace)
        self.assertTrue(passport["derived"])
        self.assertTrue(passport["rebuildable"])

    def test_fusion_is_deterministic(self):
        rows=fuse_candidates([
            {"source_id":"b","locator":"page:1","score":0.2,"strategy":"lexical","evidence_refs":[]},
            {"source_id":"a","locator":"page:1","score":0.8,"strategy":"hierarchical","evidence_refs":[]},
        ])
        self.assertEqual("a",rows[0]["source_id"])

    def test_local_provider_rejects_non_loopback_model_router(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises(GatewayDenied) as ctx:
                PageIndexLocalConfig(root/"store",(root,),"https://api.example.com/v1","index","chat").validate()
            self.assertEqual("PAGEINDEX_LOCAL_MODEL_ROUTER_EGRESS",ctx.exception.code)

    def test_local_provider_indexes_and_retrieves_without_cloud_key(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            pdf=root/"fixture.pdf"
            pdf.write_bytes(b"%PDF-1.4\nfixture")
            config=PageIndexLocalConfig(
                storage_path=root/"store",
                allowed_roots=(root,),
                model_router_base_url="http://127.0.0.1:18791/v1",
                index_route="fa3-pageindex-index",
                reason_route="fa3-pageindex-reason",
            )
            index_adapter,retrieve_adapter=build_adapters(config,client_factory=FakeClient)
            indexed=index_adapter.handler({"source":str(pdf)})
            self.assertEqual("doc-local",indexed["doc_id"])
            reason=retrieve_adapter.handler({"operation":"reason","doc_id":"doc-local","query":"why"})
            self.assertEqual("answer:why",reason["result"])
            self.assertEqual("CENTRAL_MODEL_ROUTER_ONLY",reason["network_egress"])
            self.assertEqual("fa3-pageindex-reason",reason["model_route"])

    def test_local_provider_path_escape_denied(self):
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside:
            root=Path(allowed)
            pdf=Path(outside)/"outside.pdf"
            pdf.write_bytes(b"%PDF-1.4\nfixture")
            config=PageIndexLocalConfig(root/"store",(root,),"http://localhost:18791/v1","i","c")
            index_adapter,_=build_adapters(config,client_factory=FakeClient)
            with self.assertRaises(GatewayDenied) as ctx:
                index_adapter.handler({"source":str(pdf)})
            self.assertEqual("PAGEINDEX_LOCAL_SCOPE_DENIED",ctx.exception.code)


if __name__=="__main__":
    unittest.main()
