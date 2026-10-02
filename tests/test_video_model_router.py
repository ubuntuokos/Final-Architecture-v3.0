import hashlib, json, tempfile, unittest
from pathlib import Path
from fa3_video_model_router import VideoRouteDenied, select

KLING="FA3-PROVIDER-KLING-001"
class RouterV2Tests(unittest.TestCase):
    def manifest(self,root,cost="FREE_REMOTE",outputs=None):
        a=root/"admission.json"; a.write_text(json.dumps({"provider_id":KLING,"status":"PASS","synthetic_or_mock_provider":False}))
        ah=hashlib.sha256(a.read_bytes()).hexdigest()
        m=root/"manifest.json"
        m.write_text(json.dumps({
          "schema":"fa3.motion-video-execution-manifest.v2","status":"ADMITTED","provider_id":KLING,
          "service_provider":"Kling AI","model_family":"Kling","model_id":"test","model_version":"1",
          "capability_snapshot":{"schema":"fa3.video-capability-snapshot.v2","conditioning":["TEXT","IMAGE"],"generation_modes":["TEXT_TO_VIDEO","IMAGE_TO_VIDEO"],"output_modes":outputs or ["VIDEO_ONLY"],"execution_topologies":["REMOTE_PROVIDER"],"temporal_modes":["FIXED_CLIP"],"backend_family":"REMOTE_API"},
          "cost_class":cost,"execution_topology":"REMOTE","execution_topology_class":"REMOTE_PROVIDER","silent_fallback_allowed":False,
          "admission_receipt":str(a),"admission_receipt_sha256":ah
        }))
        return m

    def request(self):
        return {"schema":"fa3.motion-video-route-request.v2","request_id":"r","requirements":{"conditioning":["TEXT"],"generation_modes":["TEXT_TO_VIDEO"],"output_modes":["VIDEO_ONLY"],"execution_topologies":["REMOTE_PROVIDER"],"temporal_modes":["FIXED_CLIP"]}}

    def test_multidimensional_route(self):
        with tempfile.TemporaryDirectory() as td:
            r=select(self.request(),[self.manifest(Path(td))])
            self.assertEqual(r["provider_id"],KLING)
            self.assertEqual(r["selection_policy"],"ADMITTED_MULTIDIMENSIONAL_CAPABILITY_COST_TOPOLOGY_DETERMINISTIC")

    def test_missing_output_mode_denied(self):
        with tempfile.TemporaryDirectory() as td:
            q=self.request(); q["requirements"]["output_modes"]=["SYNCHRONIZED_AV"]
            with self.assertRaises(VideoRouteDenied): select(q,[self.manifest(Path(td))])

    def test_application_pin_denied(self):
        with tempfile.TemporaryDirectory() as td:
            q=self.request(); q["provider_id"]=KLING
            with self.assertRaises(VideoRouteDenied): select(q,[self.manifest(Path(td))])

    def test_billable_requires_permission(self):
        with tempfile.TemporaryDirectory() as td:
            q=self.request(); q["allowed_cost_classes"]=["BILLABLE_REMOTE"]
            with self.assertRaises(VideoRouteDenied): select(q,[self.manifest(Path(td),cost="BILLABLE_REMOTE")])

if __name__=="__main__": unittest.main()
