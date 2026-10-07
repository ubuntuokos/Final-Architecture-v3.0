import importlib.util, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_gtcrn_provider import AdmissionError, select_execution_provider, validate_audio_contract, validate_model, reference_policy_conformance

class GTCRNProviderTests(unittest.TestCase):
    def test_reference_policy_conformance(self):
        self.assertEqual(reference_policy_conformance()["result"], "PASS")
    def test_no_silent_fallback(self):
        with self.assertRaises(AdmissionError):
            select_execution_provider("CUDAExecutionProvider", ["CPUExecutionProvider"])
    def test_accelerator_requires_hrb(self):
        with self.assertRaises(AdmissionError):
            select_execution_provider("CUDAExecutionProvider", ["CUDAExecutionProvider"])
        s = select_execution_provider("CUDAExecutionProvider", ["CUDAExecutionProvider"], "HRB-1")
        self.assertTrue(s.accelerator)
    def test_wrong_audio_format_denied(self):
        with self.assertRaises(AdmissionError):
            validate_audio_contract(48000, 1)
        with self.assertRaises(AdmissionError):
            validate_audio_contract(16000, 2)
    def test_dangerous_checkpoint_denied_before_read(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "model.tar"; p.write_bytes(b"x")
            with self.assertRaises(AdmissionError):
                validate_model(p, "0" * 64)

class GTCRNSpectralRoundTripTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("numpy"), "numpy not installed")
    def test_passthrough_spectral_e2e_preserves_length_and_finiteness(self):
        import numpy as np
        from fa3_gtcrn_provider import enhance_waveform
        class Passthrough:
            def run(self, _outs, feed):
                return [feed["mix"], feed["conv_cache"], feed["tra_cache"], feed["inter_cache"]]
        t = np.arange(0, 1600, dtype=np.float32) / 16000.0
        x = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        y, perf = enhance_waveform(Passthrough(), x)
        self.assertEqual(len(y), len(x)); self.assertTrue(np.isfinite(y).all()); self.assertEqual(perf["clipped_samples"], 0)

if __name__ == "__main__":
    unittest.main()
