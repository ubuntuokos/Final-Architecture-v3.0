from __future__ import annotations
import unittest
from fa3_change_graph import make_edge
from fa3_change_impact import change_risk_context

class ChangeImpactTests(unittest.TestCase):
    def test_impact_tracks_invalidation_requalification_and_scope(self):
        edges=[
            make_edge(edge_id="e1",source_id="r1",target_id="cap",relation="AFFECTS",provenance={"s":"t"}),
            make_edge(edge_id="e2",source_id="cap",target_id="evid",relation="INVALIDATES",provenance={"s":"t"}),
            make_edge(edge_id="e3",source_id="cap",target_id="host",relation="REQUALIFIES",provenance={"s":"t"}),
        ]
        out=change_risk_context(["r1"],edges,[{"current":False}],["OUT_OF_SCOPE"])
        self.assertIn("evid",out["invalidated_ids"])
        self.assertIn("host",out["requalification_ids"])
        self.assertGreater(out["risk_context"]["deterministic_score"],0)
        self.assertFalse(out["risk_context"]["authoritative_decision"])

if __name__=="__main__": unittest.main()
