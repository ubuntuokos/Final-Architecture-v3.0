"""Synthetic S3 language fan-out planning tests: no ASR, MT or source media."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fa3_selective_import_language_fanout import language_fanout_preview
from test_selective_import_preview import request, output
from test_selective_import_stream_binding import inventory


class S3LanguageFanoutPreviewTests(unittest.TestCase):
    def test_one_video_many_requested_outputs_two_translations(self):
        r = request(outputs=[
            output(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor"),
            output(selector="TRANSCRIPT_ONLY", target="Subtitle Studio",
                   translation="ORIGINAL_PLUS_TRANSLATIONS",
                   langs=["hu-HU", "de-DE"]),
            output(selector="MUSIC_OR_INSTRUMENTAL_ONLY",
                   target="Music Studio", stem="INSTRUMENTAL"),
        ])
        p = language_fanout_preview(r, inventory())
        self.assertEqual(p["skipped_non_text_leaves"], 2)
        self.assertEqual(p["languages_count"], 3)
        self.assertEqual([x["target_locale"] for x in p["branches"]],
                         ["fr", "hu-HU", "de-DE"])
        self.assertTrue(all(x["source_step"] == "EXISTING_STT_SOURCE_TRANSCRIPTION"
                            for x in p["branches"]))
        self.assertTrue(all(not x["execution_authorized"] and not x["verified"]
                            and not x["publish_audio"] and not x["publish_video"]
                            for x in p["branches"]))
        self.assertTrue(all(x["original_stream_indices"] == [1]
                            for x in p["branches"]))

    def test_caption_only_source_in_video_requires_explicit_origin_choice(self):
        r = request(outputs=[
            output("TEXT", "ORIGINAL_LANGUAGE", "Subtitle Studio")])
        p = language_fanout_preview(r, inventory())
        self.assertEqual(p["branches"][0]["status"],
                         "BLOCKED_SOURCE_STREAM_SELECTION_OR_AVAILABILITY")
        self.assertEqual(p["branches"][0]["steps"], [])
        chosen = language_fanout_preview(
            r, inventory(), [{"leaf_index": 0, "stream_indices": [2]}])
        self.assertEqual(chosen["branches"][0]["source_step"],
                         "CAPTION_SUBTITLE_ORIGINAL_TIMED_TEXT_INSPECT")
        self.assertEqual(chosen["branches"][0]["original_stream_indices"], [2])

    def test_audio_text_translation_never_exports_audio(self):
        r = request(kind="AUDIO", outputs=[
            output("TEXT", "MULTI_TRANSLATION", "Story/Screenplay",
                   translation="MULTI_TRANSLATION", langs=["hu", "de"])])
        i = inventory()
        i["streams"] = [i["streams"][1]]
        out = language_fanout_preview(r, i)
        self.assertEqual(out["languages_count"], 2)
        self.assertEqual(out["branches"][0]["source_step"],
                         "EXISTING_STT_SOURCE_TRANSCRIPTION")
        self.assertTrue(all(x["publish_audio"] is False for x in out["branches"]))

    def test_document_source_original_and_translation(self):
        r = request(kind="TEXT", outputs=[
            output("TEXT", "ORIGINAL_PLUS_TRANSLATIONS", "Story/Screenplay",
                   translation="ORIGINAL_PLUS_TRANSLATIONS", langs=["hu", "de"])])
        p = language_fanout_preview(r, inventory())
        self.assertEqual(p["languages_count"], 3)
        self.assertEqual(p["branches"][0]["source_step"],
                         "DOCUMENT_FABRIC_SOURCE_TEXT_INSPECT")
        self.assertEqual(p["branches"][0]["original_stream_indices"], [])

    def test_auto_source_locale_blocks_translation_until_detection(self):
        r = request(outputs=[
            output(selector="TRANSCRIPT_ONLY", translation="ONE_TRANSLATION",
                   langs=["hu"])])
        r["source_language"] = "auto"
        p = language_fanout_preview(r, inventory())
        self.assertEqual(p["branches"][0]["status"],
                         "PENDING_PER_SEGMENT_SOURCE_LANGUAGE_IDENTIFICATION")
        self.assertIn("LANGUAGE_FABRIC_IDENTIFY_SOURCE_LOCALE",
                      p["branches"][0]["steps"])

    def test_duplicate_destination_locale_marked_and_not_auto_merged(self):
        r = request(kind="TEXT", outputs=[
            output("TEXT", "ORIGINAL_LANGUAGE", "Story/Screenplay"),
            output("TEXT", "ORIGINAL_PLUS_TRANSLATIONS", "Story/Screenplay",
                   translation="ORIGINAL_PLUS_TRANSLATIONS", langs=["hu"])])
        p = language_fanout_preview(r, inventory())
        self.assertEqual(len(p["duplicate_destination_candidates"]), 1)
        self.assertEqual([b["status"] for b in p["branches"]].count(
            "PENDING_DUPLICATE_DESTINATION_REVIEW"), 2)
        self.assertEqual(p["languages_count"], 3)

    def test_missing_track_and_unauthorized_source_rejected_or_blocked(self):
        r = request(outputs=[output(selector="TRANSCRIPT_ONLY")])
        i = inventory()
        i["streams"] = [i["streams"][0]]
        p = language_fanout_preview(r, i)
        self.assertEqual(p["branches"][0]["status"],
                         "BLOCKED_SOURCE_STREAM_SELECTION_OR_AVAILABILITY")
        r["execution_authorized"] = True
        with self.assertRaises(ValueError):
            language_fanout_preview(r, i)

    def test_stem_and_video_only_selection_yield_no_text_branches(self):
        r = request(outputs=[
            output(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor"),
            output(selector="AMBIENCE_AND_SFX_ONLY", target="Sound Design",
                   stem="AMBIENCE_AND_SFX")])
        p = language_fanout_preview(r, inventory())
        self.assertEqual(p["languages_count"], 0)
        self.assertEqual(p["skipped_non_text_leaves"], 2)

    def test_schema_binds_no_runtime_and_175(self):
        s = json.loads(
            (ROOT / "canonical/schemas/selective-language-fanout.v1.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(s["x-fa3-policy"]["capability_count"], 175)
        self.assertFalse(s["x-fa3-policy"]["execution_authorized"])
        self.assertFalse(s["x-fa3-policy"]["authority"])


if __name__ == "__main__":
    unittest.main()
