import unittest
from fa3_video_refinement import build_plan, RefinementDenied
from fa3_motion_video_v3_gate import gate

class MotionVideoV3Tests(unittest.TestCase):
 def base(self):
  req={"schema":"fa3.video-refinement-request.v1","refinement_mode":"ONE_STEP_DISTILLED","quality_mode":"REFERENCE","draft_resolution":{"width":640,"height":360},"target_resolution":{"width":1280,"height":720},"draft_artifact_sha256":"a"*64}
  gen={"schema":"fa3.motion-video-execution-receipt.v2","status":"PASS","receipt_id":"g1","provider_id":"GEN"}
  sel={"schema":"fa3.video-refinement-selection-receipt.v1","authority":"FA3-AUTH-MODEL-ROUTER-001","status":"ROUTED","provider_id":"REF","refiner_id":"r1"}
  man={"schema":"fa3.video-refiner-manifest.v1","status":"ADMITTED","execution_enabled":True,"provider_id":"REF","refiner_id":"r1","silent_fallback_allowed":False,"backend_class":"CPU_REFERENCE","model_router_authority":"FA3-AUTH-MODEL-ROUTER-001","resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001"}
  return req,gen,sel,man
 def test_reference_plan(self):
  p=build_plan(*self.base());self.assertEqual(p["status"],"READY");self.assertFalse(p["silent_fallback_allowed"])
 def test_approximate_requires_disclosure(self):
  v=list(self.base());v[0]["quality_mode"]="APPROXIMATE"
  with self.assertRaises(RefinementDenied):build_plan(*v)
 def test_downscale_fails(self):
  v=list(self.base());v[0]["target_resolution"]={"width":320,"height":180}
  with self.assertRaises(RefinementDenied):build_plan(*v)
 def test_accelerated_requires_hrb(self):
  v=list(self.base());v[3]["backend_class"]="ROCM_HIP_OPTIONAL";v[3]["resource_authority"]="WRONG"
  with self.assertRaises(RefinementDenied):build_plan(*v)
 def test_repository_gate(self):
  self.assertEqual(gate()["result"],"PASS",gate())
if __name__=="__main__":unittest.main()
