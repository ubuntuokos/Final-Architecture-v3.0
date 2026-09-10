import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fa3_kdenlive_audio_conditioning import build_execution_plan, AudioConditioningPolicyError
from fa3_kdenlive_audio_conditioning_gate import gate, PATHS


class KdenliveAudioConditioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_reference_gate_passes(self):
        self.assertEqual(gate(self.root)["result"], "PASS")

    def test_clean_dialogue_is_provider_neutral_and_48k(self):
        plan = build_execution_plan({
            "request_id": "t1",
            "source_artifact_ref": "src",
            "output_artifact_ref": "dst",
            "preset": "clean-dialogue",
        })
        self.assertTrue(plan["provider_neutral"])
        self.assertEqual(plan["editorial_label"], "AI · Clean Dialogue")
        self.assertTrue(any(stage.get("output_sample_rate_hz") == 48000 for stage in plan["stages"]))

    def test_implicit_double_denoise_fails_closed(self):
        with self.assertRaises(AudioConditioningPolicyError):
            build_execution_plan({
                "request_id": "t2",
                "source_artifact_ref": "src",
                "output_artifact_ref": "dst",
                "preset": "clean-dialogue",
                "restoration_denoise": True,
            })

    def test_source_overwrite_fails_closed(self):
        with self.assertRaises(AudioConditioningPolicyError):
            build_execution_plan({
                "request_id": "t3",
                "source_artifact_ref": "same",
                "output_artifact_ref": "same",
                "preset": "noise-reduction",
            })

    def test_accelerator_without_hrb_fails_closed(self):
        with self.assertRaises(AudioConditioningPolicyError):
            build_execution_plan({
                "request_id": "t4",
                "source_artifact_ref": "src",
                "output_artifact_ref": "dst",
                "preset": "noise-reduction",
                "execution_provider": "CUDAExecutionProvider",
            })

    def test_negative_silero_authority_claim_fails_gate(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for rel in PATHS.values():
                src = self.root / rel
                dst = td / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
            provider = td / PATHS["silero_provider"]
            data = json.loads(provider.read_text())
            data["authority_boundaries"]["workflow"] = True
            provider.write_text(json.dumps(data))
            self.assertEqual(gate(td)["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
