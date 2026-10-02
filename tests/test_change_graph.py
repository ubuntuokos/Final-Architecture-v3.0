from __future__ import annotations
import unittest
from fa3_change_graph import explicit_pairs, make_edge, reachable
from fa3_change_history import ChangeHistoryError

class ChangeGraphTests(unittest.TestCase):
    def test_explicit_lineage_and_impact(self):
        self.assertEqual(explicit_pairs(["a","b"],["x","y"],[("a","x"),("b","y")]),
                         [("a","x"),("b","y")])
        edges=[make_edge(edge_id="e1",source_id="a",target_id="x",relation="AFFECTS",
                         provenance={"source":"test"}),
               make_edge(edge_id="e2",source_id="x",target_id="y",relation="REQUALIFIES",
                         provenance={"source":"test"})]
        self.assertEqual(reachable(edges,["a"]),["x","y"])

    def test_cartesian_inference_is_forbidden(self):
        with self.assertRaises(ChangeHistoryError):
            explicit_pairs(["a","b"],["x","y"],None)

if __name__=="__main__": unittest.main()
