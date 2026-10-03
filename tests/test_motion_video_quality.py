from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_motion_video_quality import *
from fa3_motion_video_quality_gate import gate
class T(unittest.TestCase):
 def p(self):
  x={"schema":"fa3.motion-plan.v1","motion_plan_id":"m1","revision":"1","project_id":"p1","project_revision":"10","timeline_revision":"20","timebase":{"fps":"25/1"},"beats":[],"actors":[],"transitions":[{"primitive":"OBJECT_HANDOFF"}],"camera_constraints":[],"motion_constraints":[],"continuity_constraints":[],"audio_cues":[],"quality_profile":{"id":"film"},"render_intent":{"class":"EDITORIAL_PREVIEW","required_capabilities":["CAP-121"]},"source_artifact_refs":[],"provenance":{"source":"test"}};x["digest"]=canonical_digest(x);return x
 def test_plan(self):self.assertEqual(validate_motion_plan(self.p())["motion_plan_id"],"m1")
 def test_engine_forbidden(self):
  x=self.p();x["render_intent"]["engine_id"]="FA3-ENGINE-MLT-001";x["digest"]=canonical_digest({k:v for k,v in x.items() if k!="digest"})
  with self.assertRaises(MotionVideoQualityError):validate_motion_plan(x)
 def test_stale(self):
  with self.assertRaises(MotionVideoQualityError):assert_revision_binding(self.p(),"11","20")
 def test_self_review(self):
  with self.assertRaises(MotionVideoQualityError):validate_independent_review("a","a")
 def test_states(self):
  for s in VERIFY_STATES:self.assertEqual(validate_verification_state(s),s)
  with self.assertRaises(MotionVideoQualityError):validate_verification_state("PASS")
 def test_gate(self):self.assertEqual(gate(ROOT)["result"],"PASS")
if __name__=="__main__":unittest.main()
