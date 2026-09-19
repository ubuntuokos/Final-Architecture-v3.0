from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from fa3_asset_egress_policy import evaluate,validate_decision
from fa3_knowledge_compilation import compile_projection,derive_from_journal_event
from fa3_multimodal_knowledge import normalize_projection
from fa3_openkb_provider import OpenKBProvider
from fa3_condb_provider import ConDBProvider
from fa3_pageindex_knowledge_closure_gate import gate
ROOT=Path(__file__).resolve().parents[1]
class FakeDB:
    def __init__(self,path): self.path=path
    def store(self,tree,format="document"): return "tree-1"
    def close(self): pass
class ClosureTests(unittest.TestCase):
    def test_gate(self): self.assertEqual("PASS",gate(ROOT)["result"])
    def test_compilation_provenance(self):
        sha="a"*64
        r=compile_projection({"source_ref":"artifact:A","source_sha256":sha,"locator":"page:1"},{"claims":[{"statement":"x","confidence":1.0}]},"FA3-NATIVE-KNOWLEDGE-COMPILER")
        self.assertTrue(r["derived"]); self.assertEqual(1,len(r["provenance_edges"]))
        b=derive_from_journal_event({"event_id":"E1"},{"artifact_ref":"artifact:A","artifact_sha256":sha,"locator":"page:1"})
        self.assertEqual("DENY",b["writeback_to_source"])
    def test_multimodal_binary_rejected(self):
        with self.assertRaises(ValueError): normalize_projection({"artifact_ref":"a","artifact_sha256":"b"*64,"media_type":"image","derived_descriptors":[],"bytes":"x"})
    def test_multimodal_temporal(self):
        r=normalize_projection({"artifact_ref":"a","artifact_sha256":"b"*64,"media_type":"video","derived_descriptors":[{"locator":"time:0-1000","start_ms":0,"end_ms":1000,"text":"scene"}]})
        self.assertFalse(r["binary_payload_stored"])
    def test_egress_default_deny_and_explicit_allow(self):
        req={"request_id":"R","source_ref":"file:A","source_sha256":"c"*64,"data_class":"INTERNAL","destination_provider":"FA3-PROVIDER-PAGEINDEX-MCP-001","destination_uri":"https://app.pageindex.ai/mcp","purpose":"index"}
        self.assertEqual("DENY",evaluate(req)["status"])
        req["approval"]={"status":"APPROVED","approval_id":"A1"}
        d=evaluate(req); self.assertEqual("ALLOW",d["status"]); validate_decision(d,source_sha256="c"*64,provider_id="FA3-PROVIDER-PAGEINDEX-MCP-001")
    def test_openkb_is_derived_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"x.md"; src.write_text("hello")
            p=OpenKBProvider((root,),root/"derived",runner=lambda **kw:{"ok":True})
            r=p.compile({"source":str(src),"workspace_id":"w"}); self.assertTrue(r["derived"]); self.assertFalse(r["source_authority"])
    def test_condb_cache_rebuildable(self):
        with tempfile.TemporaryDirectory() as td:
            p=ConDBProvider(Path(td),db_factory=FakeDB)
            r=p.ingest_tree({"tree":{"type":"object"},"cache_id":"c"}); self.assertTrue(r["rebuildable"]); self.assertFalse(r["durable_authority"])
if __name__=="__main__": unittest.main()
