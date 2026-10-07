from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_neural_rendering import NeuralRenderingError,SelectionRequest,select_provider,validate_execution_preflight,validate_frame_surface,validate_output_policy
from fa3_neural_rendering_jev_adapter import JevAdvisoryError,JevRequest,advise

def candidate(ident,admitted=True,execution_class="HOST_NATIVE_ACCELERATED",priority=0,feature_classes=None):
    row={"id":ident,"execution_class":execution_class,"policy_eligible":True,"provider_admitted":admitted,
         "model_artifact_admitted":True,"runtime_compatible":True,"hardware_compatible":True,"supply_chain_valid":True,"priority":priority}
    if feature_classes is not None: row["feature_classes"]=feature_classes
    return row

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
    def test_jev_model_backed_advisory_stays_bounded(self):
        req=JevRequest(operation_id="op-jev",eligible_candidate_ids=("a","b"),context_refs=("ctx:1",),provenance_refs=("prov:1",))
        r=advise(req,invoke_via_fa3_model_router=lambda payload:{"ranked_candidate_ids":["b","a"],"human_readable_reason":"b has the requested execution class"})
        self.assertEqual("JEV_VIA_FA3_MODEL_ROUTER",r["implementation"]); self.assertEqual(["b","a"],r["ranked_candidate_ids"]); self.assertFalse(r["authority"])

    def test_jev_router_result_cannot_expand_candidates(self):
        req=JevRequest(operation_id="op-jev-2",eligible_candidate_ids=("a","b"))
        with self.assertRaises(JevAdvisoryError) as c:
            advise(req,invoke_via_fa3_model_router=lambda payload:{"ranked_candidate_ids":["a","b","c"]})
        self.assertEqual("JEV-NR-CANDIDATE-EXPANSION",c.exception.code)

    def test_browser_execution_requires_web_ai_receipt(self):
        with self.assertRaises(NeuralRenderingError) as c:
            validate_execution_preflight(selected_provider_id="p",executed_provider_id="p",execution_class="BROWSER_WEBGPU",model_artifact_ref="m",supply_chain_receipt_ref="s",evidence_context_ref="e")
        self.assertEqual("NR-WEB-AI-RECEIPT-MISSING",c.exception.code)
    def test_cpu_execution_is_explicit_and_model_router_bound(self):
        with self.assertRaises(NeuralRenderingError) as c:
            validate_execution_preflight(selected_provider_id="cpu",executed_provider_id="cpu",execution_class="CPU_SOFTWARE",model_artifact_ref="m",supply_chain_receipt_ref="s",evidence_context_ref="e",hrb_lease_ref="lease")
        self.assertEqual("NR-MODEL-ROUTER-RECEIPT-MISSING",c.exception.code)
        r=validate_execution_preflight(selected_provider_id="cpu",executed_provider_id="cpu",execution_class="CPU_SOFTWARE",model_artifact_ref="m",supply_chain_receipt_ref="s",evidence_context_ref="e",hrb_lease_ref="lease",model_router_receipt_ref="router")
        self.assertEqual("CPU_SOFTWARE",r["execution_class"]); self.assertFalse(r["silent_fallback_allowed"])

    def test_feature_class_filters_provider_candidates(self):
        r=select_provider(SelectionRequest(operation_id="op-feature",feature_class="SUPER_RESOLUTION",candidates=(candidate("nr",feature_classes=["NEURAL_RENDER"]),candidate("sr",feature_classes=["SUPER_RESOLUTION"]))))
        self.assertEqual(["sr"],r["selected_ids"]); self.assertEqual("SUPER_RESOLUTION",r["feature_class"])

    def test_temporal_frame_surface_contract(self):
        surface={"frame_id":"f1","width":1920,"height":1080,"color_space":"scene-linear","timecode":"00:00:00:00","source_artifact_ref":"asset:1","provenance_ref":"prov:1","motion_vectors_ref":"mv:1","depth_ref":"depth:1","temporal_history_ref":"hist:1","camera_ref":"cam:1","jitter":[0.0,0.0]}
        r=validate_frame_surface(surface,feature_class="NEURAL_RENDER")
        self.assertEqual("VALIDATED",r["status"]); self.assertFalse(r["canonical_timeline_mutated"])

    def test_frame_generation_is_forbidden_for_final_master(self):
        with self.assertRaises(NeuralRenderingError) as c:
            validate_output_policy(feature_class="FRAME_GENERATION",output_class="FINAL_MASTER")
        self.assertEqual("NR-FRAME-GENERATION-FINAL-FORBIDDEN",c.exception.code)

    def test_super_resolution_requires_target_dimensions(self):
        surface={"frame_id":"f1","width":960,"height":540,"color_space":"scene-linear","timecode":"00:00:00:00","source_artifact_ref":"asset:1","provenance_ref":"prov:1","motion_vectors_ref":"mv:1","depth_ref":"depth:1","temporal_history_ref":"hist:1","camera_ref":"cam:1","jitter":[0.0,0.0]}
        with self.assertRaises(NeuralRenderingError) as c:
            validate_frame_surface(surface,feature_class="SUPER_RESOLUTION")
        self.assertEqual("NR-TARGET-DIMENSION-MISSING",c.exception.code)

if __name__=="__main__": unittest.main()
