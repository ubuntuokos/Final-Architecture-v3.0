from __future__ import annotations
import json, tempfile, time, unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from fa3_ffmpeg_ai_current_host import (
    EVIDENCE_LEVEL, PRODUCTION_EVIDENCE_LEVEL, build_identity_onnx, build_trust_receipt_valid,
    hardware_snapshot_valid, hrb_lease_valid, make_reference_receipt, normalize_bdf,
    observed_onnx_provider, quality_valid, resolved_runtime_index, validate_current_host_receipt,
)
from fa3_ffmpeg_ai_current_host_gate import gate

class FFmpegAICurrentHostTests(unittest.TestCase):
    def test_reference_receipt_contract_passes_validator(self):
        r = make_reference_receipt()
        self.assertEqual([], validate_current_host_receipt(r))
        self.assertEqual(EVIDENCE_LEVEL, r["evidence_level"])
        self.assertEqual(PRODUCTION_EVIDENCE_LEVEL, r["production_evidence_level_required"])
        self.assertFalse(r["production_e2e_claim"])

    def test_gate_rejects_synthetic_fixture_as_live_evidence(self):
        r = make_reference_receipt()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = root / "receipt.json"; p.write_text(json.dumps(r))
            report = gate(root, p)
        self.assertEqual("FAIL", report["result"])
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-015" for x in report["findings"]))
        self.assertFalse(report["production_e2e_satisfied"])

    def test_hardware_gate_is_portable_not_t7910_pinned(self):
        r = make_reference_receipt(); hw = r["hardware"]
        self.assertTrue(hardware_snapshot_valid(hw))
        hw["observed_machine_identity_non_normative"] = {"vendor": "Any", "product": "Any qualifying host"}
        hw["host_package_count"] = 4; hw["host_physical_core_count"] = 128
        self.assertTrue(hardware_snapshot_valid(hw))
        hw["host_physical_core_count"] = 7
        self.assertFalse(hardware_snapshot_valid(hw))

    def test_canonical_hrb_lease_and_broker_validation_are_required(self):
        r = make_reference_receipt(); lease = r["hrb_accelerator_lease"]; gpus = r["live_gpus"]; broker = r["hrb_broker_validation"]
        self.assertTrue(hrb_lease_valid(lease, gpus, broker))
        self.assertEqual(1, resolved_runtime_index(lease, gpus, broker))
        bad = deepcopy(lease); bad["issuer"] = "OTHER"
        self.assertFalse(hrb_lease_valid(bad, gpus, broker))
        bad = deepcopy(lease); bad["expires_epoch"] = 1
        self.assertFalse(hrb_lease_valid(bad, gpus, broker))
        bad_broker = deepcopy(broker); bad_broker["status"] = "INVALID"
        self.assertFalse(hrb_lease_valid(lease, gpus, bad_broker))

    def test_static_ordinal_is_not_an_identity(self):
        r = make_reference_receipt()
        self.assertIsNone(resolved_runtime_index({}, r["live_gpus"], r["hrb_broker_validation"]))

    def test_extended_nvidia_pci_domain_normalizes_to_canonical_bdf(self):
        self.assertEqual("0000:05:00.0", normalize_bdf("00000000:05:00.0"))
        self.assertEqual("0000:a5:00.0", normalize_bdf("A5:00.0"))

    def test_silent_cuda_cpu_fallback_is_denied(self):
        self.assertEqual("FALLBACK_CPU", observed_onnx_provider("Failed to enable CUDA. Falling back to CPU"))
        r = make_reference_receipt(); r["onnx_cuda_dnn"]["observed_provider"] = "FALLBACK_CPU"; r["onnx_cuda_dnn"]["silent_cpu_fallback_observed"] = True
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-007" for x in validate_current_host_receipt(r)))

    def test_requested_gpu_execution_is_not_enough(self):
        r = make_reference_receipt(); r["gpu_media_e2e"]["hardware_decode_observed"] = False
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-008" for x in validate_current_host_receipt(r)))
        r = make_reference_receipt(); r["gpu_media_e2e"]["cuda_filter_observed"] = False
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-008" for x in validate_current_host_receipt(r)))
        r = make_reference_receipt(); r["gpu_media_e2e"]["nvenc_encode_observed"] = False
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-008" for x in validate_current_host_receipt(r)))

    def test_build_trust_v1_self_assertion_is_denied(self):
        r = make_reference_receipt(); weak = deepcopy(r["ffmpeg_build_trust"]); weak["schema"] = "fa3.ffmpeg-build-trust-receipt.v1"
        self.assertFalse(build_trust_receipt_valid(weak, r["ffmpeg_feature_manifest"]))
        weak = deepcopy(r["ffmpeg_build_trust"]); weak["sbom_sha256"] = None
        self.assertFalse(build_trust_receipt_valid(weak, r["ffmpeg_feature_manifest"]))
        weak = deepcopy(r["ffmpeg_build_trust"]); weak["observed_ffmpeg_version"] = "wrong"
        self.assertFalse(build_trust_receipt_valid(weak, r["ffmpeg_feature_manifest"]))

    def test_smoke_quality_thresholds_are_explicitly_non_production(self):
        r = make_reference_receipt(); self.assertTrue(quality_valid(r["quality"]))
        bad = deepcopy(r["quality"]); bad["threshold_policy"] = "PRODUCTION_POLICY"
        self.assertFalse(quality_valid(bad))
        bad = deepcopy(r["quality"]); bad["vmaf"] = 79.9
        self.assertFalse(quality_valid(bad))

    def test_zero_copy_claim_is_denied_for_stable_dnn_baseline(self):
        r = make_reference_receipt(); r["copy_boundary_evidence"]["zero_copy_claimed"] = True
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-009" for x in validate_current_host_receipt(r)))

    def test_identity_onnx_is_deterministic_and_nonempty(self):
        a = build_identity_onnx(); b = build_identity_onnx()
        self.assertEqual(a, b); self.assertGreater(len(a), 50); self.assertIn(b"Identity", a)

    def test_provenance_chain_is_tamper_evident(self):
        r = make_reference_receipt(); r["provenance"]["chain_material"]["output_sha256"] = "1" * 64
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-013" for x in validate_current_host_receipt(r)))

    def test_capability_and_global_promotion_drift_are_denied(self):
        r = make_reference_receipt(); r["capability_count_after"] = 144; r["global_promotion_claim"] = True
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-014" for x in validate_current_host_receipt(r)))

if __name__ == "__main__":
    unittest.main()
