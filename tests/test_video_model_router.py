import hashlib,json,tempfile,unittest
from pathlib import Path
from fa3_video_model_router import VideoRouteDenied,select

class VideoModelRouterTests(unittest.TestCase):
 def manifest(self,root,cost="FREE_LOCAL"):
  admission=root/"admission.json"
  admission.write_text(json.dumps({"provider_id":"FA3-PROVIDER-WAN22-001","status":"PASS","synthetic_or_mock_provider":False}))
  ah=hashlib.sha256(admission.read_bytes()).hexdigest()
  m=root/f"m-{cost}.json"
  m.write_text(json.dumps({"schema":"fa3.motion-video-execution-manifest.v1","status":"ADMITTED","provider_id":"FA3-PROVIDER-WAN22-001","cost_class":cost,"execution_topology":"LOCAL" if cost=="FREE_LOCAL" else "REMOTE","silent_fallback_allowed":False,"admission_receipt":str(admission),"admission_receipt_sha256":ah}))
  return m
 def test_free_admitted_provider_routes(self):
  with tempfile.TemporaryDirectory() as td:
   m=self.manifest(Path(td))
   r=select({"schema":"fa3.motion-video-route-request.v1","request_id":"r1","operation":"TEXT_TO_VIDEO"},[m])
   self.assertEqual(r["provider_id"],"FA3-PROVIDER-WAN22-001");self.assertEqual(r["cost_class"],"FREE_LOCAL");self.assertFalse(r["physical_provider_pin_in_application"])
 def test_application_provider_pin_denied(self):
  with tempfile.TemporaryDirectory() as td:
   m=self.manifest(Path(td))
   with self.assertRaises(VideoRouteDenied):select({"schema":"fa3.motion-video-route-request.v1","operation":"TEXT_TO_VIDEO","provider_id":"FA3-PROVIDER-WAN22-001"},[m])
 def test_billable_requires_explicit_permission(self):
  with tempfile.TemporaryDirectory() as td:
   m=self.manifest(Path(td),"BILLABLE_REMOTE")
   with self.assertRaises(VideoRouteDenied):select({"schema":"fa3.motion-video-route-request.v1","operation":"TEXT_TO_VIDEO","allowed_cost_classes":["BILLABLE_REMOTE"]},[m])
if __name__=="__main__":unittest.main()
