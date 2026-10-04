from __future__ import annotations
import tempfile, unittest
from pathlib import Path

from src.fa3_uaf import ActionDispatcher, ActionRegistry, ActionRequest, ExecutionContext, ProviderRegistry, UafError
from src.fa3_voice_uaf import register_voice_providers, whisper_current_host_binding
from src.fa3_voice_workspace import VoiceWorkspaceStore

ROOT=Path(__file__).resolve().parents[1]

class VoiceUafTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=VoiceWorkspaceStore(Path(self.tmp.name)/"workspace.json",ROOT)
        self.registry=ActionRegistry.from_directory(ROOT/"canonical/actions")
        self.providers=ProviderRegistry()
        register_voice_providers(self.providers,self.store,ROOT)
        self.evidence=[]
        self.dispatcher=ActionDispatcher(
            self.registry,self.providers,
            authorize=lambda request,contract: True,
            acquire_resources=lambda request,contract,provider: {"lease_id":"hrb-test","issuer":"FA3-AUTH-HOST-RESOURCE-BROKER-001"},
            release_resources=lambda lease: None,
            evidence_sink=self.evidence.append,
        )
        self.ctx=ExecutionContext("voice-uaf-test",application="FA3-VOICE-STUDIO-001")

    def tearDown(self): self.tmp.cleanup()

    def run_action(self,action,args):
        return self.dispatcher.execute(ActionRequest(
            action_id=action,arguments=args,principal={"id":"user:test"},context=self.ctx
        ))

    def test_profile_and_fit_actions_use_uaf(self):
        profile={"voice_profile_id":"voice-uaf","name":"UAF Voice","languages":["hu-HU"],"identity_kind":"SYNTHETIC","consent_status":"NOT_REQUIRED"}
        saved=self.run_action("voice.profile.upsert",{"voice_profile":profile})
        self.assertEqual(saved.output["voice_profile_id"],"voice-uaf")
        listed=self.run_action("voice.profile.list",{})
        self.assertEqual(len(listed.output["profiles"]),1)
        fit=self.run_action("voice.fit-to-clip.plan",{"target_duration_ms":27800,"generated_duration_ms":31200})
        self.assertFalse(fit.output["plan"]["silent_text_rewrite"])
        self.assertGreaterEqual(len(self.evidence),3)

    def test_dispatch_requires_hrb_and_produces_temporal_handoff(self):
        self.store.upsert_profile({"voice_profile_id":"voice-uaf","name":"UAF Voice","languages":["hu-HU"],"identity_kind":"SYNTHETIC","consent_status":"NOT_REQUIRED"})
        job=self.store.submit_generation({
            "request_id":"req-uaf","text":"teszt","language":"hu-HU","mode":"plain",
            "voice_identity_ref":"voice-uaf","execution_mode":"OFFLINE_LOCAL",
            "output_intent":"MEDIA_MEZZANINE","silent_fallback":False
        },admitted_providers={"FA3-PROVIDER-XTTS-001"})
        out=self.run_action("voice.generate.dispatch",{"job_id":job["job_id"]})
        self.assertEqual(out.output["status"],"DISPATCHED")
        self.assertEqual(out.output["temporal_dispatch"]["workflow_type"],"fa3.voice.generate")
        self.assertEqual(out.evidence["resource_lease_ref"],"hrb-test")

    def test_transcribe_is_not_connected_without_cpu_current_host_receipt(self):
        self.assertIsNone(whisper_current_host_binding(ROOT))
        cap=self.store.create_capture("hu-HU","local-audio-ref","")
        with self.assertRaises(UafError) as cm:
            self.run_action("voice.transcribe",{"capture_id":cap["capture_id"],"language":"hu-HU","refine":False})
        self.assertEqual(cm.exception.code,"UAF-NO-COMPATIBLE-PROVIDER")

if __name__=="__main__": unittest.main()
