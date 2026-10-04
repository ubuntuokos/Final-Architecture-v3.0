from __future__ import annotations
import sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_voice_workspace import VoiceWorkspaceDenied, VoiceWorkspaceStore, fit_to_clip_plan, validate_generation_request, validate_voice_profile

class VoiceWorkspacePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.state=Path(self.tmp.name)/"workspace.json"
        self.store=VoiceWorkspaceStore(self.state,ROOT)
        self.profile={"voice_profile_id":"voice-narrator-hu","name":"Narrator HU","languages":["hu-HU"],"identity_kind":"SYNTHETIC","consent_status":"NOT_REQUIRED"}
    def tearDown(self): self.tmp.cleanup()

    def test_profile_and_consent(self):
        self.store.upsert_profile(self.profile)
        self.assertEqual(VoiceWorkspaceStore(self.state,ROOT).get_profile("voice-narrator-hu")["name"],"Narrator HU")
        bad=dict(self.profile,identity_kind="HUMAN_AUTHORIZED",consent_status="NOT_REQUIRED")
        with self.assertRaises(VoiceWorkspaceDenied): validate_voice_profile(bad)
        good=dict(self.profile,voice_profile_id="human",identity_kind="HUMAN_AUTHORIZED",consent_status="GRANTED",consent_proof_ref="consent:1")
        self.assertEqual(validate_voice_profile(good)["consent_status"],"GRANTED")

    def test_physical_pins_forbidden(self):
        for field in ("provider_id","model_id","device","cuda_device","endpoint","model_path"):
            bad=dict(self.profile); bad[field]="forbidden"
            with self.assertRaises(VoiceWorkspaceDenied): validate_voice_profile(bad)

    def test_generation_request_has_no_physical_route(self):
        base={"request_id":"req","text":"teszt","language":"hu-HU","mode":"plain","voice_identity_ref":"voice-narrator-hu","execution_mode":"OFFLINE_LOCAL","output_intent":"MEDIA_MEZZANINE","silent_fallback":False}
        self.assertEqual(validate_generation_request(base)["language"],"hu-HU")
        for field in ("provider_id","model_id","device","cuda_device","endpoint","model_path"):
            bad=dict(base); bad[field]="forbidden"
            with self.assertRaises(VoiceWorkspaceDenied): validate_generation_request(bad)

    def test_fit_to_clip_never_silent_rewrite(self):
        plan=fit_to_clip_plan(27800,31200)
        self.assertFalse(plan["silent_text_rewrite"])
        actions={x["action"]:x for x in plan["options"]}
        self.assertIn("BOUNDED_RATE_ADJUSTMENT",actions)
        self.assertTrue(actions["SCRIPT_SHORTENING_PROPOSAL"]["approval_required"])
        self.assertFalse(actions["SCRIPT_SHORTENING_PROPOSAL"]["silent_apply"])

if __name__=="__main__": unittest.main()
