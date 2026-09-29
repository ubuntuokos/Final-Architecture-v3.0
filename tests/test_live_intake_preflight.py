"""No-network planning fixtures for independent subtitles, audio podcasts and video.

This is NOT an EBU/HLS receiver test, an admission receipt or current-host proof.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from fa3_live_intake_preflight import (
    AUDIO, TEXT, VIDEO, LiveIntakePreflightError, preflight,
)

ROOT = Path(__file__).resolve().parents[1]


def caption_request() -> dict:
    return {
        "schema": "fa3.live-production-source.v1",
        "source_mode": "LIVE_CAPTIONS",
        "source_protocol": "EBU_TT_LIVE_WS",
        "authorized_endpoint_ref": "ref:authorized-ebu-feed",
        "rights_receipt_ref": "ref:operator-rights",
        "approved_capture_scope_ref": "ref:caption-only-scope",
        "independence_inspection_ref": "ref:inspected-caption-endpoint",
        "delivery_mode": "CAPTION_ONLY",
        "no_av_fetch": True,
        "no_media_persist": True,
        "requested_outputs": ["ORIGINAL_LANGUAGE", "MULTI_TRANSLATION"],
        "source_language": "en-GB",
        "target_languages": ["hu-HU", "de-DE"],
        "buffer_max_bytes": 1048576,
        "max_duration_seconds": 3600,
        "destination_application": "Subtitle Studio",
    }


class LiveSourcePreflightTests(unittest.TestCase):
    def test_17_source_rows_share_only_one_selector_id(self):
        src = (ROOT / "docs/production-import-selective-content-plan-2026-09-29.md").read_text()
        rows = re.findall(
            r"^\\|\\s*(TEXT|AUDIO|VIDEO)\\s*\\|\\s*`([A-Z_]+)`\\s*\\|",
            src, re.MULTILINE,
        )
        self.assertEqual(len(rows), 17)
        self.assertEqual([sum(r[0] == k for r in rows) for k in ("TEXT", "AUDIO", "VIDEO")], [4, 6, 7])
        self.assertEqual(sum(r[1] == "TRANSCRIPT_ONLY" for r in rows), 2)
        self.assertEqual(len({r[1] for r in rows}), 16)
        self.assertEqual({r[1] for r in rows}, TEXT | AUDIO | VIDEO)

    def test_schema_and_registry_invariants(self):
        schema = json.loads((ROOT / "canonical/schemas/live-production-source.v1.json").read_text())
        self.assertFalse(schema["x-fa3-policy"]["authority"])
        self.assertEqual(schema["x-fa3-policy"]["capability_baseline"], 175)
        self.assertEqual(schema["x-fa3-policy"]["displayed_selection_count"], 17)
        self.assertEqual(schema["x-fa3-policy"]["unique_selector_id_count"], 16)
        self.assertEqual(set(schema["properties"]["requested_outputs"]["items"]["enum"]), TEXT | AUDIO | VIDEO)
        self.assertEqual(schema["additionalProperties"], False)

    def test_caption_only_has_zero_prospective_av_workers_and_no_runtime_authority(self):
        p = preflight(caption_request())
        self.assertEqual(p["prospective_audio_workers_for_independent_captions"], 0)
        self.assertEqual(p["prospective_video_workers_for_independent_captions"], 0)
        self.assertFalse(p["runtime_execution_authorized"])
        self.assertFalse(p["recording_authorized_by_preflight"])
        self.assertFalse(p["media_persistence_permitted"])
        self.assertTrue(p["existing_inspector_must_verify_refs_before_execution"])

    def test_independent_hls_caption_playlist(self):
        req = caption_request()
        req["source_protocol"] = "HLS_SUBTITLES"
        self.assertEqual(preflight(req)["source_protocol"], "HLS_SUBTITLES")

    def test_recorded_video_caption_only_requires_av_ingress_and_no_media_persist(self):
        req = caption_request()
        req.update(source_mode="LIVE_VIDEO", source_protocol="HLS_EMBEDDED_CC",
                   no_av_fetch=False, requested_outputs=["TRANSCRIPT_ONLY"])
        req.pop("independence_inspection_ref")
        result = preflight(req)
        self.assertFalse(result["no_av_fetch_required"])
        self.assertFalse(result["media_persistence_permitted"])

    def test_authorized_audio_podcast_transcript_and_translation(self):
        req = caption_request()
        req.update(source_mode="LIVE_AUDIO", source_protocol="ICECAST",
                   no_av_fetch=False, requested_outputs=["TRANSCRIPT_ONLY", "ONE_TRANSLATION"],
                   target_languages=["hu-HU"], delivery_mode="SELECTIVE_CAPTURE",
                   no_media_persist=True, destination_application="Story/Screenplay")
        req.pop("independence_inspection_ref")
        self.assertEqual(preflight(req)["selected_outputs"], ["TRANSCRIPT_ONLY", "ONE_TRANSLATION"])

    def test_negative_policy_cases(self):
        mutators = {
            "no AV bypass of embedded HLS captions": lambda r: r.update(
                source_mode="LIVE_VIDEO", source_protocol="HLS_EMBEDDED_CC"),
            "fake raw URL": lambda r: r.update(authorized_endpoint_ref="https://user:secret@host/live"),
            "missing independent caption inspector proof": lambda r: r.pop("independence_inspection_ref"),
            "capture AV from caption feed": lambda r: r.update(requested_outputs=["FULL_VIDEO"]),
            "caption-only AV persistence": lambda r: r.update(no_media_persist=False),
            "unsolicited outgoing recording": lambda r: r.update(delivery_mode="AUTHORIZED_RECORD_AND_DERIVE"),
            "duplicate output": lambda r: r.update(requested_outputs=["ORIGINAL_LANGUAGE", "ORIGINAL_LANGUAGE"]),
            "multilingual fanout missing target": lambda r: r.update(target_languages=[]),
            "buffer unbounded": lambda r: r.update(buffer_max_bytes=99999999999),
            "unknown transport": lambda r: r.update(source_protocol="PROPRIETARY_URL_SCRAPE"),
            "unrecognized imperative payload": lambda r: r.update(embedded_script="rm -rf"),
            "wrong source type": lambda r: r.update(source_mode="FILE"),
            "sneaky media worker": lambda r: r.update(no_av_fetch=False),
        }
        for label, mutate in mutators.items():
            with self.subTest(label=label):
                req = caption_request()
                mutate(req)
                with self.assertRaises(LiveIntakePreflightError):
                    preflight(req)

    def test_partial_source_original_plus_translation_requires_target(self):
        req = caption_request()
        req.update(requested_outputs=["ORIGINAL_PLUS_TRANSLATIONS"], target_languages=["fr-FR"])
        self.assertEqual(preflight(req)["target_languages"], ["fr-FR"])
        req["target_languages"] = []
        with self.assertRaises(LiveIntakePreflightError):
            preflight(req)


if __name__ == "__main__":
    unittest.main()
