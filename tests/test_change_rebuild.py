from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from fa3_change_graph import make_edge
from fa3_change_history import DerivedChangeIndex, build_record

class ChangeRebuildTests(unittest.TestCase):
    def test_atomic_rebuild_is_deterministic_and_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"idx.sqlite3"
            records=[build_record(record_id="r1",timestamp="2026-10-02T00:00:00Z",
                source_kind="TEST",source_ref="test:r1",object_type="PROFILE",object_id="P1",
                operation="UPDATED",payload={"value":1})]
            edges=[make_edge(edge_id="e1",source_id="r1",target_id="P1",relation="AFFECTS",
                             provenance={"source":"test"})]
            idx=DerivedChangeIndex(path)
            first=idx.rebuild(records,edges)
            second=idx.rebuild(records,edges)
            self.assertEqual(first,second)
            self.assertEqual(idx.history("PROFILE","P1")[0]["id"],"r1")
            self.assertFalse(idx.rollback_projection()["source_mutation"])

if __name__=="__main__": unittest.main()
