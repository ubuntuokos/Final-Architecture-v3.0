from __future__ import annotations
import unittest
from pathlib import Path

from fa3_caption_subtitle import parse_subtitle
from fa3_caption_uaf import build_native_provider
from fa3_caption_workflows import (
    ACTION_IDS, NATIVE_ACTION_IDS, build_audio_description_gap_plan,
    build_browser_overlay_projection, build_editorial_projection,
    build_hardsub_recovery_request, caption_quality_report, edit_cue,
    execute_native_action, synchronize_document,
)
from fa3_uaf import ActionDispatcher, ActionRegistry, ActionRequest, ExecutionContext, ProviderRegistry

ROOT=Path(__file__).resolve().parents[1]

class CaptionWorkflowTests(unittest.TestCase):
    def doc(self):
        return parse_subtitle("1\n00:00:01,000 --> 00:00:02,000\nHello.\n\n2\n00:00:04,000 --> 00:00:05,500\nWorld.\n","srt",language="en")
    def test_edit_is_revisioned_and_preserves_source(self):
        d=edit_cue(self.doc(),"cue-000001","Hello edited.")
        self.assertEqual(2,d["revision"]); self.assertEqual("Hello.",d["tracks"][0]["cues"][0]["source_text"])
    def test_sync_offset_and_drift_are_explicit(self):
        d=synchronize_document(self.doc(),offset_ms=100,drift_ppm=1000)
        self.assertEqual(1101,d["tracks"][0]["cues"][0]["start_ms"]); self.assertEqual(2,d["revision"])
    def test_qc_and_projections(self):
        d=self.doc(); self.assertEqual("PASS",caption_quality_report(d)["status"])
        self.assertTrue(build_browser_overlay_projection(d)["presentation_only"])
        self.assertEqual("OpenTimelineIO",build_editorial_projection(d,"QuickClip")["canonical_timeline_ir"])
    def test_hardsub_is_fail_closed_provider_request(self):
        r=build_hardsub_recovery_request("media:sha256:test",language="hu-HU")
        self.assertEqual("PENDING_ADMITTED_OCR_PROVIDER",r["runtime_status"]); self.assertFalse(r["direct_provider_selection"])
    def test_audio_description_only_finds_gaps(self):
        r=build_audio_description_gap_plan(self.doc(),8000,min_gap_ms=1000)
        self.assertTrue(r["gaps"]); self.assertFalse(r["generated_description_text"])
    def test_uaf_dispatcher_status_semantics(self):
        registry=ActionRegistry.from_directory(ROOT/"canonical/actions")
        providers=ProviderRegistry(); providers.register(build_native_provider())
        evidence=[]
        dispatcher=ActionDispatcher(registry,providers,authorize=lambda req,contract: True,evidence_sink=evidence.append)
        result=dispatcher.execute(ActionRequest(
            action_id="caption.qc",
            arguments={"document":self.doc()},
            principal={"id":"test:user"},
            context=ExecutionContext("ctx-caption",application="FA3-SUBTITLE-STUDIO-001"),
        ))
        self.assertEqual("success",result.status)
        self.assertEqual("PASS",result.output["status"])
        self.assertEqual("FA3-PROVIDER-CAPTION-NATIVE-001",result.provider_id)
        self.assertTrue(evidence)

    def test_uaf_contracts_and_native_provider(self):
        registry=ActionRegistry.from_directory(ROOT/"canonical/actions")
        ids={c.action_id for c in registry.list()}
        self.assertTrue(set(ACTION_IDS).issubset(ids))
        provider=build_native_provider()
        self.assertEqual("FA3-PROVIDER-CAPTION-NATIVE-001",provider.descriptor.provider_id)
        self.assertEqual(set(NATIVE_ACTION_IDS),set(provider.descriptor.action_ids))
        result=execute_native_action("caption.qc",{"document":self.doc()})
        self.assertEqual("PASS",result["status"])

if __name__=="__main__": unittest.main()