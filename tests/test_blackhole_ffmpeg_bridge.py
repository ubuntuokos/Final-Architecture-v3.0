from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_blackhole_ffmpeg_bridge import (
    BridgePolicyDenied,
    evaluate_current_host_evidence,
    reference_lease,
    reference_payload,
    reference_zero_copy,
    run_bridge_regressions,
    validate_payload,
    validate_runtime_lease,
    validate_zero_copy_evidence,
)


class BlackholeFFmpegBridgeTests(unittest.TestCase):
    def setUp(self):
        self.payload = reference_payload()
        self.lease = reference_lease()
        self.zero_copy = reference_zero_copy(self.lease)
        self.now = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)

    def test_corrected_payload_is_valid(self):
        validate_payload(self.payload)

    def test_static_lease_id_is_rejected(self):
        self.payload["hardware_constraints"]["host_resource_broker_lease_id"] = "ACC-LEASE-8831"
        with self.assertRaises(BridgePolicyDenied):
            validate_payload(self.payload)

    def test_transcription_stage_is_mandatory(self):
        self.payload["pipeline_stages"] = [self.payload["pipeline_stages"][0], self.payload["pipeline_stages"][2]]
        with self.assertRaises(BridgePolicyDenied):
            validate_payload(self.payload)

    def test_cuda_launch_blocking_is_diagnostic_only(self):
        self.payload["runtime_environment"]["environment_variables"]["CUDA_LAUNCH_BLOCKING"] = "1"
        with self.assertRaises(BridgePolicyDenied):
            validate_payload(self.payload)
        self.payload["runtime_environment"]["profile"] = "DIAGNOSTIC"
        validate_payload(self.payload)

    def test_runtime_lease_expiry_is_fail_closed(self):
        self.lease["expires_at"] = "2026-09-14T05:00:00Z"
        with self.assertRaises(BridgePolicyDenied):
            validate_runtime_lease(self.lease, now=self.now)

    def test_gpu_identity_mismatch_is_fail_closed(self):
        self.zero_copy["nvenc_gpu_uuid"] = "GPU-OTHER"
        with self.assertRaises(BridgePolicyDenied):
            validate_zero_copy_evidence(self.zero_copy, self.lease)

    def test_boolean_intent_is_not_zero_copy_evidence(self):
        self.zero_copy["frame_to_tensor_zero_copy_observed"] = False
        with self.assertRaises(BridgePolicyDenied):
            validate_zero_copy_evidence(self.zero_copy, self.lease)

    def test_end_to_end_overclaim_is_rejected(self):
        self.zero_copy["end_to_end_gpu_resident_claim"] = True
        self.zero_copy["measured_end_to_end_gpu_resident"] = False
        with self.assertRaises(BridgePolicyDenied):
            validate_zero_copy_evidence(self.zero_copy, self.lease)

    def test_complete_current_host_evidence_can_pass_evaluator(self):
        evidence = {
            "zero_copy": self.zero_copy,
            "ffmpeg_build_trust_verified": True,
            "source_media_provenance_verified": True,
            "source_media_is_real_non_synthetic": True,
            "output_sha256_verified": True,
            "stt_result_hash_bound": True,
            "caption_qc_passed": True,
            "rollback_or_cleanup_verified": True,
        }
        report = evaluate_current_host_evidence(self.payload, self.lease, evidence, now=self.now)
        self.assertEqual("CURRENT_HOST_PRODUCTION_E2E_PASS", report["status"])
        self.assertFalse(report["end_to_end_gpu_resident_claim"])

    def test_reference_regression_matrix_passes(self):
        report = run_bridge_regressions()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(16, report["total"])
        self.assertEqual(16, report["passed"])
        self.assertFalse(report["current_host_runtime_claim"])


if __name__ == "__main__":
    unittest.main()
