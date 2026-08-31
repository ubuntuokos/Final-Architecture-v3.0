import hashlib, tempfile, unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_cosyvoice_provider import (
    MODEL_ID, ModelTrustDenied, PolicyDenied,
    run_executable_conformance, validate_language, validate_request
)
from fa3_cosyvoice_gate import gate

class CosyVoiceGateTests(unittest.TestCase):
    def _request(self, td:Path):
        audio=td/"ref.wav"
        audio.write_bytes(b"RIFF-fa3-reference-audio")
        return {
            "schema":"fa3.voice-synthesis-request.v1",
            "request_id":"req-1",
            "text":"Hello",
            "language":"en",
            "mode":"zero_shot",
            "model_id":MODEL_ID,
            "voice_identity_ref":"voice:test:001",
            "consent_proof":{"status":"GRANTED","scope":["VOICE_SYNTHESIS"],"subject_authorized":True,"provenance_ref":"consent:test:001"},
            "reference_audio_path":str(audio),
            "reference_audio_sha256":hashlib.sha256(audio.read_bytes()).hexdigest(),
            "prompt_text":"Hello reference speaker"
        }

    def test_executable_conformance_21_pass(self):
        r=run_executable_conformance(ROOT)
        self.assertEqual(r["result"],"PASS")
        self.assertEqual((r["passed"],r["total"]),(21,21))

    def test_canonical_gate_passes_without_claiming_current_host(self):
        r=gate(ROOT)
        self.assertEqual(r["result"],"PASS")
        self.assertFalse(r["current_host_production_claim"])
        self.assertEqual(r["current_host_production_status"],"PENDING_REAL_HOST_EXECUTION")

    def test_hungarian_requires_explicit_experimental_ack(self):
        with self.assertRaises(PolicyDenied):
            validate_language({"language":"hu"})
        self.assertEqual(validate_language({"language":"hu","experimental_language_ack":True}),"EXPERIMENTAL_LANGUAGE_NOT_PRODUCTION_PROMOTABLE")

    def test_voice_reference_requires_consent(self):
        with tempfile.TemporaryDirectory() as d:
            req=self._request(Path(d)); req.pop("consent_proof")
            with self.assertRaises(PolicyDenied):
                validate_request(ROOT,req)

    def test_reference_audio_hash_is_bound(self):
        with tempfile.TemporaryDirectory() as d:
            req=self._request(Path(d)); req["reference_audio_sha256"]="0"*64
            with self.assertRaises(PolicyDenied):
                validate_request(ROOT,req)

    def test_arbitrary_model_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            req=self._request(Path(d)); req["model_id"]="/tmp/arbitrary.pt"
            with self.assertRaises(ModelTrustDenied):
                validate_request(ROOT,req)

    def test_valid_official_language_request_passes_policy(self):
        with tempfile.TemporaryDirectory() as d:
            req=self._request(Path(d))
            self.assertEqual(validate_request(ROOT,req)["language_status"],"PRODUCTION_LANGUAGE_ELIGIBLE")

if __name__=="__main__":
    unittest.main()
