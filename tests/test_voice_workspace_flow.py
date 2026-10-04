from __future__ import annotations
import sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_voice_workspace import VoiceWorkspaceDenied, VoiceWorkspaceStore

class VoiceWorkspaceFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=VoiceWorkspaceStore(Path(self.tmp.name)/"workspace.json",ROOT)
        self.store.upsert_profile({"voice_profile_id":"voice-narrator-hu","name":"Narrator HU","languages":["hu-HU"],"identity_kind":"SYNTHETIC","consent_status":"NOT_REQUIRED"})
        self.req={"request_id":"req-1","text":"teszt","language":"hu-HU","mode":"plain","voice_identity_ref":"voice-narrator-hu","execution_mode":"OFFLINE_LOCAL","output_intent":"MEDIA_MEZZANINE","silent_fallback":False}
    def tearDown(self): self.tmp.cleanup()

    def test_capture_local_first(self):
        row=self.store.create_capture("hu-HU","local-audio-ref","eredeti szöveg")
        self.assertEqual(row["status"],"TRANSCRIBED")
        self.assertEqual(row["raw_transcript"],"eredeti szöveg")
        self.assertFalse(row["provenance"]["network_egress_authorized"])

    def test_generation_blocks_without_admission(self):
        row=self.store.submit_generation(self.req,admitted_providers=set())
        self.assertEqual(row["status"],"BLOCKED_NOT_ADMITTED")
        self.assertFalse(row["runtime_execution_allowed"])
        self.assertIsNone(row["provider_decision"])

    def test_route_ready_only_for_explicit_admission(self):
        row=self.store.submit_generation(self.req,admitted_providers={"FA3-PROVIDER-XTTS-001"})
        self.assertEqual(row["status"],"ROUTE_READY")
        self.assertEqual(row["provider_decision"]["selected_provider_id"],"FA3-PROVIDER-XTTS-001")
        self.assertEqual(row["provider_decision"]["selected_model_id"],"RESOLVED_BY_MODEL_ROUTER_RUNTIME")

    def test_transcription_staging_and_result_binding(self):
        capture=self.store.create_capture("hu-HU","local-audio-ref","")
        staged=self.store.stage_transcription(capture["capture_id"],"hu-HU",False)
        self.assertEqual(staged["status"],"TRANSCRIBING")
        result={
            "status":"PASS","provider_id":"FA3-PROVIDER-WHISPER-001","language":"hu",
            "segments":[{"text":"szia"}],"execution_evidence":{"runtime_version":"test"}
        }
        accepted=self.store.accept_transcription_result(capture["capture_id"],result)
        self.assertEqual(accepted["status"],"TRANSCRIBED")
        self.assertEqual(accepted["raw_transcript"],"szia")

    def test_result_rejected_before_dispatch(self):
        job=self.store.submit_generation(self.req,admitted_providers={"FA3-PROVIDER-XTTS-001"})
        result={"provider_id":"FA3-PROVIDER-XTTS-001","model_id":"runtime-model","model_revision":"rev-1","audio_path":"local-output.wav","audio_sha256":"a"*64,"sample_rate_hz":24000,"channels":1,"voice_identity_ref":"voice-narrator-hu","language":"hu-HU","synthetic_disclosure":"SYNTHETIC_AUDIO","license_and_rights_ref":"rights:1","execution_evidence":"evidence:1"}
        with self.assertRaises(VoiceWorkspaceDenied):
            self.store.accept_generation_result(job["job_id"],result)

    def test_quick_dub_requires_known_profile(self):
        with self.assertRaises(VoiceWorkspaceDenied):
            self.store.quick_dub_plan("en-US","hu-HU",[{"speaker":"A","voice_profile_id":"missing"}],True)
        plan=self.store.quick_dub_plan("en-US","hu-HU",[{"speaker":"A","voice_profile_id":"voice-narrator-hu"}],True)
        self.assertEqual(plan["status"],"PLAN_READY")
        self.assertIn("OPTIONAL_TRANSLATION",plan["stages"])

    def test_result_handoff_and_cancel(self):
        job=self.store.submit_generation(self.req,admitted_providers={"FA3-PROVIDER-XTTS-001"})
        result={"provider_id":"FA3-PROVIDER-XTTS-001","model_id":"runtime-model","model_revision":"rev-1","audio_path":"local-output.wav","audio_sha256":"a"*64,"sample_rate_hz":24000,"channels":1,"voice_identity_ref":"voice-narrator-hu","language":"hu-HU","synthetic_disclosure":"SYNTHETIC_AUDIO","license_and_rights_ref":"rights:1","execution_evidence":"evidence:1"}
        dispatched=self.store.authorize_dispatch(job["job_id"],"uaf:test","hrb:test")
        self.assertEqual(dispatched["status"],"DISPATCHED")
        self.assertEqual(dispatched["temporal_dispatch"]["workflow_type"],"fa3.voice.generate")
        completed=self.store.accept_generation_result(job["job_id"],result)
        self.assertEqual(completed["status"],"COMPLETED")
        handoff=self.store.timeline_handoff(job["job_id"],"clip-1","align:1",True)
        self.assertTrue(handoff["editable"])
        self.assertFalse(handoff["host_mutation_authorized"])
        blocked=self.store.submit_generation(dict(self.req,request_id="req-cancel"),admitted_providers=set())
        first=self.store.cancel_job(blocked["job_id"],"user")
        second=self.store.cancel_job(blocked["job_id"],"again")
        self.assertEqual(first["status"],"CANCELLED")
        self.assertEqual(second["status"],"CANCELLED")
        self.assertFalse(self.store.status()["activity"]["visible"])

if __name__=="__main__": unittest.main()
