from __future__ import annotations
import unittest
from fa3_change_graph import make_edge
from fa3_change_rollback import rollback_impact

class RollbackImpactTests(unittest.TestCase):
    def test_rollback_analysis_never_executes_source_mutation(self):
        edges=[make_edge(edge_id="e1",source_id="r1",target_id="artifact",relation="AFFECTS",
                         provenance={"source":"test"})]
        out=rollback_impact("cs1",["r1"],edges)
        self.assertIn("artifact",out["affected_ids"])
        self.assertFalse(out["source_mutation"])
        self.assertFalse(out["rollback_executed"])
        self.assertTrue(out["requires_explicit_external_rollback_authority"])

if __name__=="__main__": unittest.main()
