import json
import tempfile
import time
import unittest
import wave
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_whisper_stt_provider import (
    HRBLeaseDenied,
    HRB_LEASE_SCHEMA,
    HRB_PROFILE_ID,
    ModelTrustDenied,
    PolicyDenied,
    RuntimeOptions,
    execute_transcription,
    evidence_complete,
    load_allowlist,
    run_executable_conformance,
    sha256_file,
    validate_audio_contract,
    validate_cached_model,
    validate_hrb_lease_document,
    validate_provider_request,
    validate_runtime_version,
    validate_segments,
)
from fa3_whisper_stt_gate import gate

def write_wav(path:Path, rate=16000, channels=1, width=2):
    with wave.open(str(path),"wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(b"\x00"*(rate*channels*width//20))

class WhisperSTTTests(unittest.TestCase):
    def test_executable_conformance_all_18_pass(self):
        r=run_executable_conformance(ROOT)
        self.assertEqual(r["result"],"PASS")
        self.assertEqual(r["passed"],18)
        self.assertEqual(r["total"],18)

    def test_gate_passes_canonical_artifacts(self):
        r=gate(ROOT)
        self.assertEqual(r["result"],"PASS")
        self.assertEqual(r["reference"]["result"],"PASS")
        self.assertEqual(r["conformance"]["passed"],18)
        self.assertEqual(r["current_host_production_status"],"PENDING_REAL_HOST_EXECUTION")

    def test_arbitrary_checkpoint_path_rejected(self):
        allow=load_allowlist(ROOT)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.wav"; write_wav(p)
            req={"schema":"fa3.stt-media-request.v1","audio_path":str(p),"audio_hash":sha256_file(p),"language":"hu","time_origin":"RELATIVE_ZERO","required_result_schema":"fa3.stt-media-result.v1"}
            with self.assertRaises(PolicyDenied):
                validate_provider_request(req,RuntimeOptions(model="/tmp/evil.pt"),allow)

    def test_wrong_audio_contract_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.wav"; write_wav(p,rate=8000)
            with self.assertRaises(PolicyDenied):
                validate_audio_contract(p)

    def test_overlapping_segments_rejected(self):
        raw=[{"start":0,"end":2,"text":"a"},{"start":1,"end":3,"text":"b"}]
        with self.assertRaises(Exception):
            validate_segments(raw,require_words=False)

    def test_runtime_version_pin(self):
        with self.assertRaises(ModelTrustDenied):
            validate_runtime_version("0")

    def test_hrb_purpose_scope(self):
        now=int(time.time())
        lease={"schema":HRB_LEASE_SCHEMA,"lease_id":"L","issuer":HRB_PROFILE_ID,"accelerator_uuid":"GPU-X","memory_max_bytes":1024,
        "expires_epoch":now+60,"issued_epoch":now,"purpose":"FA3 Demucs","host":"h","status":"ACTIVE","nonce":"n",
        "placement":{"pci_bus_id":"0","numa_node":0},"enforcement":{},"signature":{"alg":"HMAC-SHA256","key_id":"host-local-v1","value":"a"*64}}
        with self.assertRaises(HRBLeaseDenied):
            validate_hrb_lease_document(lease)

    def test_bad_cached_model_hash_rejected(self):
        allow=load_allowlist(ROOT)
        with tempfile.TemporaryDirectory() as td:
            cache=Path(td); p=cache/allow["models"]["tiny"]["artifact_filename"]; p.write_bytes(b"bad")
            with self.assertRaises(ModelTrustDenied):
                validate_cached_model(cache,allow["models"]["tiny"],require_present=True)

if __name__=="__main__":
    unittest.main()
