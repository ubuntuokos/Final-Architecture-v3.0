import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fa3_motion_video_provider_adapter import (
    BILLABLE_ACK,
    MotionVideoDenied,
    execute,
    validate_billing,
    validate_selection,
)

class MotionVideoAdapterTests(unittest.TestCase):
    def base_selection(self):
        return {
            "schema":"fa3.motion-video-route-selection-receipt.v1",
            "authority":"FA3-AUTH-MODEL-ROUTER-001",
            "status":"ROUTED",
            "provider_id":"FA3-PROVIDER-TEST-VIDEO-001",
        }

    def base_manifest(self):
        return {
            "schema":"fa3.motion-video-execution-manifest.v1",
            "status":"ADMITTED",
            "provider_id":"FA3-PROVIDER-TEST-VIDEO-001",
            "provider_selection_authority":"FA3-AUTH-MODEL-ROUTER-001",
            "resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "transport":"FA3_EXECUTOR_COMMAND",
            "cost_class":"FREE_LOCAL",
            "execution_topology":"LOCAL",
            "requires_accelerator":False,
            "silent_fallback_allowed":False,
        }

    def test_selection_and_manifest_must_match(self):
        m=self.base_manifest()
        self.assertEqual(validate_selection(self.base_selection(),m),"FA3-PROVIDER-TEST-VIDEO-001")
        m["provider_id"]="OTHER"
        with self.assertRaises(MotionVideoDenied):
            validate_selection(self.base_selection(),m)

    def test_manifest_rejects_embedded_secret(self):
        m=self.base_manifest(); m["api_key"]="secret"
        with self.assertRaises(MotionVideoDenied):
            validate_selection(self.base_selection(),m)

    def test_billable_remote_requires_manual_ack(self):
        m=self.base_manifest();m["cost_class"]="BILLABLE_REMOTE";m["execution_topology"]="REMOTE"
        with mock.patch.dict(os.environ,{},clear=True):
            with self.assertRaises(MotionVideoDenied):
                validate_billing(m)
        with mock.patch.dict(os.environ,{"FA3_VIDEO_BILLABLE_E2E_ACK":BILLABLE_ACK},clear=True):
            validate_billing(m)

    def test_free_execution_does_not_require_billing_ack(self):
        with mock.patch.dict(os.environ,{},clear=True):
            validate_billing(self.base_manifest())

    def test_real_command_transport_executes_pinned_binary(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            executable=root/"provider.py"
            executable.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib,sys\n"
                "out=pathlib.Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b'video-bytes')\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            digest=hashlib.sha256(executable.read_bytes()).hexdigest()
            selection=root/"selection.json";manifest=root/"manifest.json";ir=root/"ir.json";artifact=root/"out.bin";admission=root/"admission.json"
            selection.write_text(json.dumps(self.base_selection()),encoding="utf-8")
            admission.write_text(json.dumps({"provider_id":"FA3-PROVIDER-TEST-VIDEO-001","status":"PASS","synthetic_or_mock_provider":False}),encoding="utf-8")
            admission_digest=hashlib.sha256(admission.read_bytes()).hexdigest()
            m=self.base_manifest();m.update({"executable":str(executable),"executable_sha256":digest,"argv":["{ir}","{output}"],"admission_receipt":str(admission),"admission_receipt_sha256":admission_digest})
            manifest.write_text(json.dumps(m),encoding="utf-8")
            ir.write_text(json.dumps({"schema":"fa3.video-generation-ir.v1","request_id":"T"}),encoding="utf-8")
            receipt=execute(selection,manifest,ir,hrb_path=None,output_path=artifact,timeout=10)
            self.assertEqual(receipt["status"],"PASS")
            self.assertEqual(receipt["provider_id"],"FA3-PROVIDER-TEST-VIDEO-001")
            self.assertFalse(receipt["silent_fallback_used"])
            self.assertTrue(artifact.is_file())
            self.assertEqual(receipt["artifact_sha256"],hashlib.sha256(b"video-bytes").hexdigest())

if __name__=="__main__":
    unittest.main()
