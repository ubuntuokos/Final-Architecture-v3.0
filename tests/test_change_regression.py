from __future__ import annotations
import unittest
from fa3_change_regression import diagnose

class ChangeRegressionTests(unittest.TestCase):
    def test_capability_gate_and_evidence_regressions_are_fail_closed(self):
        out=diagnose(
            previous={"capability_ids":["CAP-001","CAP-002"],"mandatory_gates":["G1","G2"]},
            current={"capability_ids":["CAP-001"],"mandatory_gates":["G1"]},
            evidence_states=[{"current":False}],
        )
        self.assertEqual(out["result"],"FAIL")
        codes={x["code"] for x in out["findings"]}
        self.assertEqual(codes,{"CAPABILITY_REGRESSION","MANDATORY_GATE_REGRESSION","EVIDENCE_STALE_AFTER_CHANGE"})
        self.assertFalse(out["authoritative_promotion_decision"])

if __name__=="__main__": unittest.main()
