from pathlib import Path
import tempfile,unittest
from fa3_voice_workspace import VoiceWorkspace,VoiceWorkspaceError
ROOT=Path(__file__).resolve().parents[1]
class VoiceWorkspaceTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.ws=VoiceWorkspace(ROOT,Path(self.t.name))
 def tearDown(self): self.ws.close(); self.t.cleanup()
 def test_health(self):
  h=self.ws.health(); self.assertEqual("ok",h["status"]); self.assertEqual(175,h["capability_baseline"]); self.assertFalse(h["production_provider_claim"])
 def test_profile_requires_consent_for_human(self):
  with self.assertRaises(VoiceWorkspaceError): self.ws.put_profile({"id":"P","human_voice":True})
  self.assertEqual("P",self.ws.put_profile({"id":"P","human_voice":True,"consent_ref":"CONSENT-1"})["id"])
 def test_fit(self):
  self.assertEqual("ACCEPT_AND_PAD",self.ws.fit_to_clip(1000,900)["decision"])
  self.assertEqual("BOUNDED_RATE_ADJUSTMENT",self.ws.fit_to_clip(1000,1100)["decision"])
  self.assertEqual("HUMAN_REVIEW_REQUIRED",self.ws.fit_to_clip(1000,1500)["decision"])
 def test_quick_dub_no_provider_authority(self):
  p=self.ws.quick_dub_plan({"source_media_ref":"x","source_language":"en","target_language":"hu-HU"})
  self.assertFalse(p["provider_selection_owned_by_application"]); self.assertIn("FA3-VOICE-001",p["stages"])
 def test_generation_fails_closed_without_executor(self):
  with self.assertRaises(VoiceWorkspaceError):
   self.ws.generate({"text":"x","language":"hu-HU","voice_identity_ref":"V","license_and_rights_ref":"R","mode":"voice_clone"})
  self.assertEqual("FAILED",self.ws.list_jobs()[0]["state"])
if __name__=="__main__": unittest.main()
