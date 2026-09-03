from __future__ import annotations
import json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from fa3_ffmpeg_ai_current_host import (
    build_identity_onnx,hrb_receipt_valid,make_reference_receipt,observed_onnx_provider,
    quality_valid,resolved_runtime_index,validate_current_host_receipt
)
from fa3_ffmpeg_ai_current_host_gate import gate

class FFmpegAICurrentHostTests(unittest.TestCase):
    def test_reference_receipt_contract_passes_validator(self):
        r=make_reference_receipt()
        self.assertEqual([],validate_current_host_receipt(r))

    def test_gate_rejects_synthetic_fixture_as_live_evidence(self):
        r=make_reference_receipt()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/"receipt.json";p.write_text(json.dumps(r))
            report=gate(root,p)
        self.assertEqual("FAIL",report["result"])
        self.assertTrue(any(x["code"]=="FFMPEG-AI-HOST-014" for x in report["findings"]))

    def test_silent_cuda_cpu_fallback_is_denied(self):
        self.assertEqual("FALLBACK_CPU",observed_onnx_provider("Failed to enable CUDA. Falling back to CPU"))
        r=make_reference_receipt();r["onnx_cuda_dnn"]["observed_provider"]="FALLBACK_CPU";r["onnx_cuda_dnn"]["silent_cpu_fallback_observed"]=True
        self.assertTrue(any(x["code"]=="FFMPEG-AI-HOST-007" for x in validate_current_host_receipt(r)))

    def test_hrb_uuid_bdf_and_expiry_are_required(self):
        r=make_reference_receipt();hrb=r["hrb_placement"];g=r["live_gpus"]
        self.assertTrue(hrb_receipt_valid(hrb,g));self.assertEqual(1,resolved_runtime_index(hrb,g))
        bad=deepcopy(hrb);bad["device_uuid"]="GPU-other"
        self.assertFalse(hrb_receipt_valid(bad,g))
        bad=deepcopy(hrb);bad["static_runtime_ordinal_as_identity"]=True
        self.assertFalse(hrb_receipt_valid(bad,g))

    def test_quality_gate_is_fail_closed(self):
        r=make_reference_receipt()
        self.assertTrue(quality_valid(r["quality"]))
        bad=deepcopy(r["quality"]);bad["vmaf"]=79.9
        self.assertFalse(quality_valid(bad))
        bad=deepcopy(r["quality"]);bad["timestamps_monotonic"]=False
        self.assertFalse(quality_valid(bad))

    def test_zero_copy_claim_is_forbidden_for_stable_dnn_baseline(self):
        r=make_reference_receipt();r["copy_boundary_evidence"]["zero_copy_claimed"]=True
        self.assertTrue(any(x["code"]=="FFMPEG-AI-HOST-009" for x in validate_current_host_receipt(r)))

    def test_identity_onnx_is_deterministic_and_nonempty(self):
        a=build_identity_onnx();b=build_identity_onnx()
        self.assertEqual(a,b);self.assertGreater(len(a),50)
        self.assertIn(b"Identity",a);self.assertIn(b"fa3_ffmpeg_identity_graph",a)

    def test_capability_and_global_promotion_drift_are_denied(self):
        r=make_reference_receipt();r["capability_count_after"]=144;r["global_promotion_claim"]=True
        self.assertTrue(any(x["code"]=="FFMPEG-AI-HOST-013" for x in validate_current_host_receipt(r)))

if __name__=="__main__":unittest.main()
