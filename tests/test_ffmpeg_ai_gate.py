from __future__ import annotations

import unittest
from pathlib import Path

from fa3_ffmpeg_ai_gate import (
    CAPABILITY_COUNT,
    RUNTIME_STATUS,
    accelerator_execution_allowed,
    gate,
    model_admission_allowed,
    regression_cases,
    standard_filter_claim_allowed,
    zero_copy_claim_allowed,
)

ROOT = Path(__file__).resolve().parents[1]


class FFmpegAIGateTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(24, report["regression_count"])
        self.assertEqual("NOT_CLAIMED", report["current_host_runtime_evidence"])

    def test_all_positive_negative_regressions_pass(self):
        cases = regression_cases()
        self.assertEqual(24, len(cases))
        self.assertTrue(all(x["positive"] for x in cases), cases)
        self.assertTrue(all(x["negative_refusal"] for x in cases), cases)

    def test_onnx_model_admission_fails_closed(self):
        good = {"rank": 4, "layout": "NCHW", "dtype": "FLOAT32", "single_input": True}
        self.assertTrue(model_admission_allowed(good))
        self.assertFalse(model_admission_allowed({**good, "dtype": "UINT8"}))
        self.assertFalse(model_admission_allowed({**good, "layout": "NHWC"}))
        self.assertFalse(model_admission_allowed({**good, "single_input": False}))

    def test_requested_cuda_cannot_silently_become_cpu(self):
        good = {
            "requested_provider": "cuda",
            "observed_provider": "cuda",
            "hrb_lease_valid": True,
            "gpu_uuid": "GPU-uuid",
            "pci_bdf": "0000:05:00.0",
            "ordinal_resolved_from_uuid_bdf": True,
        }
        self.assertTrue(accelerator_execution_allowed(good))
        self.assertFalse(accelerator_execution_allowed({**good, "observed_provider": "cpu"}))
        self.assertFalse(accelerator_execution_allowed({**good, "hrb_lease_valid": False}))
        self.assertFalse(accelerator_execution_allowed({**good, "gpu_uuid": ""}))

    def test_zero_copy_claim_requires_real_copy_evidence(self):
        good = {
            "stable_release_capability": True,
            "cuda_hwframe_dnn_supported": True,
            "observed_host_device_copies": 0,
            "copy_telemetry_present": True,
        }
        self.assertTrue(zero_copy_claim_allowed(good))
        self.assertFalse(zero_copy_claim_allowed({**good, "observed_host_device_copies": 1}))
        self.assertFalse(zero_copy_claim_allowed({**good, "cuda_hwframe_dnn_supported": False}))

    def test_fake_upstream_filter_claims_are_rejected(self):
        self.assertTrue(standard_filter_claim_allowed("scale_cuda"))
        self.assertFalse(standard_filter_claim_allowed("real_esrgan"))
        self.assertFalse(standard_filter_claim_allowed("python_script"))

    def test_reference_pass_does_not_claim_current_host(self):
        self.assertEqual(143, CAPABILITY_COUNT)
        self.assertEqual("PENDING_REAL_CURRENT_HOST_E2E", RUNTIME_STATUS)


if __name__ == "__main__":
    unittest.main()
