from __future__ import annotations
import unittest
from fa3_change_explain import explain
from fa3_change_history import ChangeHistoryError, build_record

class ChangeAIBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.records=[build_record(record_id="r",timestamp="t",source_kind="T",source_ref="s",
            object_type="O",object_id="i",operation="U",payload={"x":1})]
        self.impact={"affected_ids":[],"invalidated_ids":[],"requalification_ids":[],"risk_context":{}}

    def test_off_never_calls_router(self):
        calls=[]
        out=explain(self.records,self.impact,ai_mode="OFF",router=lambda x:calls.append(x) or "x")
        self.assertEqual(calls,[])
        self.assertFalse(out["ai_invoked"])

    def test_shadow_and_advisory_are_ai_inference_only(self):
        shadow=explain(self.records,self.impact,ai_mode="SHADOW",router=lambda x:"shadow")
        advisory=explain(self.records,self.impact,ai_mode="ADVISORY",router=lambda x:"advisory")
        for out in (shadow,advisory):
            self.assertEqual(out["ai_output"]["truth_class"],"AI_INFERENCE")
            self.assertFalse(out["ai_output"]["promotable_to_fact"])
            self.assertFalse(out["ai_output"]["authoritative"])

    def test_advisory_requires_router(self):
        with self.assertRaises(ChangeHistoryError):
            explain(self.records,self.impact,ai_mode="ADVISORY",router=None)

if __name__=="__main__": unittest.main()
