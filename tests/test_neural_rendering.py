from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_neural_rendering import NeuralRenderingError,SelectionRequest,select_provider,validate_execution_preflight

def candidate(ident,admitted=True,execution_class="HOST_NATIVE_ACCELERATED",priority=0):
    return {"id":ident,"execution_class":execution_class,"policy_eligible":True,"provider_admitted":admitted,
            "model_artifact_admitted":True,"runtime_compatible":True,"hardware_compatible":True,"supply_chain_valid":True,"priority":priority}

class NeuralRenderingTests(unittest.TestCase):
    def test_deterministic_filter_and_selection(self):
        r=select_provider(SelectionRequest(operation_id="op-1",candidates=(candidate("bad",False,priority=99),candidate("good",priority=1))))
        self.assertEqual(["good"],r["selected_ids"]); self.assertFalse(r["execution_authorized_by_decision"])
    def test_jev_cannot_expand_candidate_set(self):
        with self.assertRaises(NeuralRenderingError) as c:
            select_provider(SelectionRequest(operation_id="op-2",candidates=(candidate("a"),candidate("b"))),advisory=lambda a,s:["a","b","c"])
        self.assertEqual("NR-ADVISORY-EXPANSION",c.exception.code)
    def test_optional_jev_outage_does_not_become_authority(self):
        def broken(_a,_s): raise RuntimeError("offline")
        r=select_provider(SelectionRequest(operation_id="op-3",candidates=(candidate("a",priority=2),candidate("b",priority=1))),advisory=broken)
        self.assertEqual(["a"],r["selected_ids"]); self.assertEqual("deterministic-selection-after-optional-advisory-error",r["implementation"])
    def test_exact_provider_is_not_silently_substituted(self):
        r=select_provider(SelectionRequest(operation_id="op-4",requested_provider_id="wanted",candidates=(candidate("other",priority=100),candidate("wanted",False))))
        self.assertEqual("STOP_BLOCKED",r["outcome"]); self.assertEqual([],r["selected_ids"])
    def test_host_execution_requires_hrb(self):
        with self.assertRaises(NeuralRenderingError) as c:
            validate_execution_preflight(selected_provider_id="p",executed_provider_id="p",execution_class="HOST_NATIVE_ACCELERATED",model_artifact_ref="m",supply_chain_receipt_ref="s",evidence_context_ref="e")
        self.assertEqual("NR-HRB-LEASE-MISSING",c.exception.code)
    def test_browser_execution_requires_web_ai_receipt(self):
        with self.assertRaises(NeuralRenderingError) as c:
            validate_execution_preflight(selected_provider_id="p",executed_provider_id="p",execution_class="BROWSER_WEBGPU",model_artifact_ref="m",supply_chain_receipt_ref="s",evidence_context_ref="e")
        self.assertEqual("NR-WEB-AI-RECEIPT-MISSING",c.exception.code)
if __name__=="__main__": unittest.main()
