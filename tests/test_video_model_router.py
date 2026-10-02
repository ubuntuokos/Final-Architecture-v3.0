import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fa3_video_model_router import VideoRouteDenied, select

KLING="FA3-PROVIDER-KLING-001"
H3="FA3-PROVIDER-MINIMAX-H3-001"

class VideoModelRouterTests(unittest.TestCase):
    def manifest(self,root,provider=KLING,cost="FREE_REMOTE"):
        admission=root/f"admission-{provider}.json"
        admission.write_text(json.dumps({"provider_id":provider,"status":"PASS","synthetic_or_mock_provider":False}))
        ah=hashlib.sha256(admission.read_bytes()).hexdigest()
        m=root/f"m-{provider}-{cost}.json"
        m.write_text(json.dumps({
            "schema":"fa3.motion-video-execution-manifest.v1",
            "status":"ADMITTED",
            "provider_id":provider,
            "service_provider":"Kling AI" if provider==KLING else "MiniMax",
            "model_family":"Kling" if provider==KLING else "MiniMax-H3",
            "model_id":"test",
            "model_version":"test",
            "capability_snapshot":{"TEXT_TO_VIDEO":True},
            "cost_class":cost,
            "execution_topology":"REMOTE",
            "silent_fallback_allowed":False,
            "admission_receipt":str(admission),
            "admission_receipt_sha256":ah
        }))
        return m

    def test_admitted_kling_routes_without_app_physical_pin(self):
        with tempfile.TemporaryDirectory() as td:
            m=self.manifest(Path(td))
            r=select({"schema":"fa3.motion-video-route-request.v1","request_id":"r1","operation":"TEXT_TO_VIDEO"},[m])
            self.assertEqual(r["provider_id"],KLING)
            self.assertEqual(r["service_provider"],"Kling AI")
            self.assertEqual(r["model_family"],"Kling")
            self.assertFalse(r["physical_provider_pin_in_application"])

    def test_application_provider_pin_denied(self):
        with tempfile.TemporaryDirectory() as td:
            m=self.manifest(Path(td))
            with self.assertRaises(VideoRouteDenied):
                select({"schema":"fa3.motion-video-route-request.v1","operation":"TEXT_TO_VIDEO","provider_id":KLING},[m])

    def test_billable_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as td:
            m=self.manifest(Path(td),"BILLABLE_REMOTE")
            with self.assertRaises(VideoRouteDenied):
                select({"schema":"fa3.motion-video-route-request.v1","operation":"TEXT_TO_VIDEO","allowed_cost_classes":["BILLABLE_REMOTE"]},[m])

    def test_retired_h3_never_routes_even_with_fake_admission(self):
        with tempfile.TemporaryDirectory() as td:
            m=self.manifest(Path(td),H3)
            with self.assertRaises(VideoRouteDenied):
                select({"schema":"fa3.motion-video-route-request.v1","operation":"TEXT_TO_VIDEO"},[m])

    def test_missing_capability_snapshot_is_ineligible(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);m=self.manifest(root)
            data=json.loads(m.read_text());data.pop("capability_snapshot");m.write_text(json.dumps(data))
            with self.assertRaises(VideoRouteDenied):
                select({"schema":"fa3.motion-video-route-request.v1","operation":"TEXT_TO_VIDEO"},[m])

if __name__=="__main__":
    unittest.main()
