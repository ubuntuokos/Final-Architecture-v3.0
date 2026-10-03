from __future__ import annotations
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_motion_video_quality import MotionVideoQualityError,accept_component_proof,build_edit_proposal,deterministic_render_key,normalize_motion_plan,validate_quality_profile,validate_review_binding,validate_verification_status
from fa3_motion_video_quality_gate import gate
class T(unittest.TestCase):
 def plan(self):return {"schema":"fa3.motion-plan.v1","motion_plan_id":"m1","revision":"1","project_id":"p1","project_revision":"pr1","timeline_revision":"tl1","timebase":{"fps":"24/1"},"beats":[],"actors":[],"transitions":[{"primitive":"OBJECT_HANDOFF"}],"camera_constraints":[],"motion_constraints":[],"continuity_constraints":[],"audio_cues":[],"quality_profile":{"profile_id":"commercial"},"render_intent":{"kind":"PREVIEW"},"source_artifact_refs":[],"provenance":{"test":True}}
 def test_plan_digest(self):self.assertEqual(len(normalize_motion_plan(self.plan())["digest"]),64)
 def test_stale(self):
  p=normalize_motion_plan(self.plan())
  with self.assertRaises(MotionVideoQualityError):build_edit_proposal(p,"wrong","tl1")
  with self.assertRaises(MotionVideoQualityError):build_edit_proposal(p,"pr1","wrong")
 def test_proposal(self):
  p=build_edit_proposal(normalize_motion_plan(self.plan()),"pr1","tl1");self.assertFalse(p["direct_native_project_mutation"]);self.assertTrue(p["rollback_reference_required"])
 def test_engine_intent(self):
  p=normalize_motion_plan(self.plan());r={"input_artifact_digest":"a"*64,"motion_plan_digest":p["digest"],"timeline_revision":"tl1","frame_or_range":{"frame":1},"engine_selection_intent":{"execution_requested":False},"render_profile":{"kind":"PREVIEW"}}
  self.assertEqual(len(deterministic_render_key(r)),64);r["engine_selection_intent"]["execution_requested"]=True
  with self.assertRaises(MotionVideoQualityError):deterministic_render_key(r)
 def test_review(self):
  validate_review_binding("p","r","v")
  with self.assertRaises(MotionVideoQualityError):validate_review_binding("x","x")
  with self.assertRaises(MotionVideoQualityError):validate_review_binding("p","r","p")
 def test_quality(self):
  q={k:{} for k in ("motion","temporal","audio","av_sync","layout","color","continuity","perceptual","determinism","delivery")};q["profile_id"]="commercial";self.assertEqual(validate_quality_profile(q)["profile_id"],"commercial");q["universal_thresholds"]={"lufs":-14}
  with self.assertRaises(MotionVideoQualityError):validate_quality_profile(q)
 def test_status(self):
  self.assertEqual(validate_verification_status("REGRESSION"),"REGRESSION")
  with self.assertRaises(MotionVideoQualityError):validate_verification_status("PASS")
 def test_component(self):
  p={"schema":"fa3.motion-component-proof.v1","component_id":"c","component_type":"TRANSITION","source_revision":"r","parameters_digest":"b"*64,"proof_frames":[1],"motion_proof_artifact":{},"measurement_receipt":{},"review_receipt":{},"output_digest":"e"*64,"status":"ACCEPTED_FOR_COMPOSITION"};self.assertTrue(accept_component_proof(p))
 def test_canonical(self):
  p=json.loads((ROOT/"canonical/profiles/FA3-SHARED-MOTION-VIDEO-QUALITY-001.json").read_text());self.assertEqual(p["capability_bindings"],["CAP-121","CAP-126","CAP-159","CAP-161"]);self.assertFalse(p["authority"])
 def test_gate(self):
  r=gate(ROOT);self.assertEqual(r["result"],"PASS",r["findings"]);self.assertFalse(r["current_host_runtime_promotion_claim"])
if __name__=="__main__":unittest.main()
