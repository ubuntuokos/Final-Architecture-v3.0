import json
import tempfile
import unittest
from pathlib import Path

from fa3_motion_video_current_host_gate import gate

ROOT=Path(__file__).resolve().parents[1]

class MotionVideoCurrentHostGateTests(unittest.TestCase):
    def test_missing_receipt_fails_closed(self):
        report=gate(ROOT,ROOT/"does-not-exist-motion-video-receipt.json")
        self.assertEqual(report["result"],"FAIL")

    def test_bound_real_provider_receipt_passes_gate(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"receipt.json"
            p.write_text(json.dumps({
              "schema":"fa3.motion-video-execution-receipt.v1",
              "status":"PASS",
              "provider_id":"FA3-PROVIDER-TEST-VIDEO-001",
              "selection_receipt_sha256":"a"*64,
              "provider_manifest_sha256":"b"*64,
              "video_generation_ir_sha256":"c"*64,
              "hrb_receipt_sha256":None,
              "transport":"FA3_EXECUTOR_COMMAND",
              "cost_class":"FREE_LOCAL",
              "execution_topology":"LOCAL",
              "requires_accelerator":False,
              "artifact_reference":"/tmp/video.bin",
              "silent_fallback_used":False,
              "raw_secret_present":False,
              "evidence_scope":"REAL_PROVIDER_CURRENT_HOST",
              "synthetic_or_mock_provider":False
            }),encoding="utf-8")
            report=gate(ROOT,p)
            self.assertEqual(report["result"],"PASS")

if __name__=="__main__":
    unittest.main()
