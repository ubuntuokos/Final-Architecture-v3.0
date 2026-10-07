import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_lavasr_provider import (
    AdmissionError,
    MODEL_ASSETS,
    reference_policy_conformance,
    reject_dangerous_source_artifact,
    select_execution_provider,
    validate_audio_contract,
    validate_denoise_policy,
)


class LavaSRProviderPolicyTests(unittest.TestCase):
    def test_reference_policy_conformance_passes(self):
        report = reference_policy_conformance()
        self.assertEqual(report["result"], "PASS", report)
        self.assertFalse(report["current_host_runtime_promoted"])

    def test_model_manifest_has_complete_sha256_identity(self):
        self.assertEqual(len(MODEL_ASSETS), 5)
        for size, digest in MODEL_ASSETS.values():
            self.assertGreater(size, 0)
            self.assertEqual(len(digest), 64)
            int(digest, 16)

    def test_silent_execution_provider_fallback_rejected(self):
        with self.assertRaises(AdmissionError):
            select_execution_provider("CUDAExecutionProvider", ["CPUExecutionProvider"], "HRB-OK")

    def test_accelerator_without_hrb_rejected(self):
        with self.assertRaises(AdmissionError):
            select_execution_provider("CUDAExecutionProvider", ["CUDAExecutionProvider"])

    def test_non_native_rate_requires_explicit_projection(self):
        with self.assertRaises(AdmissionError):
            validate_audio_contract(48000, 1)
        validate_audio_contract(48000, 1, explicit_resample_projection=True)

    def test_external_rate_range_is_fail_closed(self):
        with self.assertRaises(AdmissionError):
            validate_audio_contract(7999, 1, explicit_resample_projection=True)
        with self.assertRaises(AdmissionError):
            validate_audio_contract(48001, 1, explicit_resample_projection=True)

    def test_non_mono_requires_explicit_projection(self):
        with self.assertRaises(AdmissionError):
            validate_audio_contract(16000, 2)
        validate_audio_contract(16000, 2, explicit_channel_projection=True)

    def test_implicit_double_denoise_rejected(self):
        with self.assertRaises(AdmissionError):
            validate_denoise_policy(True, True, False)
        validate_denoise_policy(True, True, True)

    def test_dangerous_source_checkpoint_rejected(self):
        for name in ["pytorch_model.bin", "weights.pt", "weights.pth", "weights.pkl", "model.ckpt"]:
            with self.assertRaises(AdmissionError):
                reject_dangerous_source_artifact(name)


if __name__ == "__main__":
    unittest.main()
