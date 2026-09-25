from __future__ import annotations
import unittest
from pathlib import Path
from fa3_caption_subtitle import CaptionError, build_narration_plan, export_subtitle, parse_subtitle, shift_document, timing_repair, validate_document
from fa3_caption_subtitle_gate import gate

ROOT=Path(__file__).resolve().parents[1]

class CaptionSubtitleTests(unittest.TestCase):
    def sample(self):
        return "1\n00:00:01,000 --> 00:00:02,500\nÁrvíztűrő tükörfúrógép.\n\n2\n00:00:03,000 --> 00:00:04,250\nMásodik mondat.\n"
    def test_srt_roundtrip(self):
        doc=parse_subtitle(self.sample(),"srt",language="hu-HU"); self.assertEqual(2,validate_document(doc)["cues"]); self.assertIn("Árvíztűrő",export_subtitle(doc,"srt"))
    def test_vtt_ass_ttml_exports(self):
        doc=parse_subtitle(self.sample(),"srt"); self.assertTrue(export_subtitle(doc,"vtt").startswith("WEBVTT")); self.assertIn("[Events]",export_subtitle(doc,"ass")); self.assertIn("http://www.w3.org/ns/ttml",export_subtitle(doc,"ttml"))
    def test_shift_creates_revision(self):
        doc=parse_subtitle(self.sample(),"srt"); shifted=shift_document(doc,500); self.assertEqual(2,shifted["revision"]); self.assertEqual(1500,shifted["tracks"][0]["cues"][0]["start_ms"]); self.assertIn("parent_revision_sha256",shifted["provenance"])
    def test_overlap_fails_closed(self):
        bad="1\n00:00:01,000 --> 00:00:03,000\nA\n\n2\n00:00:02,000 --> 00:00:04,000\nB\n"
        with self.assertRaises(CaptionError): parse_subtitle(bad,"srt")
    def test_narration_delegates_to_voice_contract(self):
        doc=parse_subtitle(self.sample(),"srt",language="hu-HU"); plan=build_narration_plan(doc,voice_identity_ref="VOICE-A",narration_mode="DUBBING"); self.assertEqual("FA3-VOICE-001",plan["voice_authority"]); self.assertFalse(plan["provider_selection_owned_by_application"]); self.assertFalse(plan["silent_text_rewrite_for_timing"]); self.assertEqual("fa3.voice-synthesis-request.v2",plan["segments"][0]["voice_request"]["schema"])
    def test_timing_repair_requires_human_for_large_overrun(self):
        self.assertEqual("ACCEPT_AND_PAD_IF_NEEDED",timing_repair(1000,800)["decision"]); self.assertEqual("BOUNDED_RATE_ADJUSTMENT",timing_repair(1000,1100)["decision"]); r=timing_repair(1000,1400); self.assertEqual("HUMAN_REVIEW_TEXT_ADAPTATION_REQUIRED",r["decision"]); self.assertFalse(r["text_rewrite"])
    def test_canonical_gate(self):
        result=gate(ROOT); self.assertEqual("PASS",result["result"],result)
if __name__=="__main__": unittest.main()
