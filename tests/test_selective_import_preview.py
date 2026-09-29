"""S1 pure planning validation only: no actual file conversion or current-host claim."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_selective_import_preview import preflight_preview  # noqa: E402


def output(family="VIDEO", selector="TRANSCRIPT_ONLY", target="Subtitle Studio",
           *, translation="ORIGINAL_LANGUAGE", langs=None, stem="NONE", **kwargs):
    return {
        "family": family,
        "selector_id": selector,
        "target_application": target,
        "source_range": {"kind": "FULL"},
        "target_languages": list(langs if langs is not None else []),
        "translation_mode": translation,
        "delivery_class": "DERIVED_ONLY",
        "requested_stem_class": stem,
        **kwargs,
    }


def request(kind="VIDEO", mode="FILE", outputs=None):
    item = {
        "schema": "fa3.selective-production-import.v1",
        "production_ref": "ref:prod.1",
        "source_ref": "ref:source.1",
        "source_kind": kind,
        "source_mode": mode,
        "source_rights_ref": "ref:rights.1",
        "source_language": "fr",
        "original_policy": "PRESERVE_IMMUTABLE_SNAPSHOT",
        "requested_outputs": outputs or [output()],
        "execution_authorized": False,
        "preview_only": True,
    }
    if mode in {"FILE", "EXTERNAL_PROJECT"}:
        item["source_sha256"] = "0" * 64
    else:
        item["live_source_plan_ref"] = "ref:live.1"
    return item


class SelectiveImportS1PurePreviewTests(unittest.TestCase):
    def test_video_multi_output_one_original_many_translation_and_sound(self):
        x = request(outputs=[
            output(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor"),
            output(selector="TRANSCRIPT_ONLY", translation="MULTI_TRANSLATION",
                   langs=["hu-HU", "de-DE"]),
            output(selector="AMBIENCE_AND_SFX_ONLY", target="Sound Design",
                   stem="AMBIENCE_AND_SFX"),
            output(family="TEXT", selector="ORIGINAL_LANGUAGE",
                   target="Story/Screenplay"),
        ])
        result = preflight_preview(x)
        self.assertEqual(result["request_count"], 4)
        self.assertEqual(result["status"], "PREVIEW_ONLY")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["outputs"][1]["target_languages"], ["hu-HU", "de-DE"])
        self.assertEqual(result["outputs"][2]["status"],
                         "PENDING_ORIGINAL_TRACK_OR_ADMITTED_EXACT_STEM_MODEL")
        self.assertTrue(all(not leaf["execution_authorized"] for leaf in result["outputs"]))

    def test_separate_video_and_audio_transcript_family_namespaces(self):
        video = preflight_preview(request())
        audio = preflight_preview(request(
            kind="AUDIO", outputs=[output("AUDIO", "TRANSCRIPT_ONLY")]
        ))
        self.assertEqual(video["outputs"][0]["selector_id"], "TRANSCRIPT_ONLY")
        self.assertEqual(audio["outputs"][0]["selector_id"], "TRANSCRIPT_ONLY")
        self.assertEqual(video["outputs"][0]["family"], "VIDEO")
        self.assertEqual(audio["outputs"][0]["family"], "AUDIO")

    def test_original_document_and_translated_document(self):
        x = request(kind="TEXT", outputs=[
            output("TEXT", "ORIGINAL_LANGUAGE", "Story/Screenplay"),
            output("TEXT", "ONE_TRANSLATION", "Story/Screenplay",
                   translation="ONE_TRANSLATION", langs=["hu"]),
            output("TEXT", "MULTI_TRANSLATION", "FA3 Archive",
                   translation="MULTI_TRANSLATION", langs=["de", "en"]),
        ])
        self.assertEqual(preflight_preview(x)["request_count"], 3)

    def test_live_captions_are_text_only_and_no_sha_on_live_request(self):
        x = request(kind="LIVE_CAPTIONS", mode="LIVE_CAPTIONS", outputs=[
            output("TEXT", "ORIGINAL_PLUS_TRANSLATIONS", "Subtitle Studio",
                   translation="ORIGINAL_PLUS_TRANSLATIONS", langs=["hu", "de"])
        ])
        self.assertEqual(preflight_preview(x)["source_kind"], "LIVE_CAPTIONS")
        x["requested_outputs"] = [output(selector="VIDEO_WITHOUT_AUDIO")]
        with self.assertRaises(ValueError):
            preflight_preview(x)

    def test_unauthorized_execution_and_missing_preview_flag_blocked(self):
        x = request()
        x["execution_authorized"] = True
        with self.assertRaises(ValueError):
            preflight_preview(x)
        x["execution_authorized"] = False
        del x["preview_only"]
        with self.assertRaises(ValueError):
            preflight_preview(x)

    def test_missing_digest_opaque_ref_and_raw_urls_fail(self):
        x = request()
        del x["source_sha256"]
        with self.assertRaises(ValueError):
            preflight_preview(x)
        x = request()
        x["source_ref"] = "https://private.example/?token=secret"
        with self.assertRaises(ValueError):
            preflight_preview(x)
        x = request()
        x["source_rights_ref"] = ""
        with self.assertRaises(ValueError):
            preflight_preview(x)

    def test_no_silent_audio_video_family_expansion(self):
        x = request(kind="AUDIO", outputs=[output()])
        with self.assertRaises(ValueError):
            preflight_preview(x)
        x = request(kind="VIDEO", outputs=[output("AUDIO", "TRANSCRIPT_ONLY")])
        with self.assertRaises(ValueError):
            preflight_preview(x)

    def test_unapproved_stem_class_and_non_transcript_translation_fail(self):
        x = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY", stem="SPEECH")])
        with self.assertRaises(ValueError):
            preflight_preview(x)
        x = request(outputs=[output(selector="FULL_VIDEO", translation="ONE_TRANSLATION",
                                    langs=["hu"])])
        with self.assertRaises(ValueError):
            preflight_preview(x)

    def test_multilingual_target_cardinality_and_casefold_duplicates_fail(self):
        bad = [
            output(translation="ONE_TRANSLATION", langs=[]),
            output(translation="MULTI_TRANSLATION", langs=["hu"]),
            output(translation="MULTI_TRANSLATION", langs=["hu", "HU"]),
            output(translation="ORIGINAL_LANGUAGE", langs=["hu"]),
        ]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(ValueError):
                preflight_preview(request(outputs=[item]))

    def test_source_range_and_duplicate_leaf_fail(self):
        x = request(outputs=[output()])
        x["requested_outputs"][0]["source_range"] = {
            "kind": "VIDEO_PTS", "tick_start": 200, "tick_end": 100,
            "timebase_num": 1, "timebase_den": 25,
        }
        with self.assertRaises(ValueError):
            preflight_preview(x)
        x = request(outputs=[output(), copy.deepcopy(output())])
        with self.assertRaises(ValueError):
            preflight_preview(x)

    def test_same_selector_multiple_target_apps_allowed_with_distinct_receipts(self):
        x = request(outputs=[
            output(target="Subtitle Studio"),
            output(target="Story/Screenplay"),
        ])
        self.assertEqual(preflight_preview(x)["request_count"], 2)

    def test_many_ranges_from_same_selector_do_not_create_an_18th_choice(self):
        leaves = []
        for n in range(18):
            leaf = output(selector="FRAMES_OR_SCENES", target="Photo/Image Studio")
            leaf["source_range"] = {
                "kind": "VIDEO_PTS", "tick_start": n * 100,
                "tick_end": (n + 1) * 100,
                "timebase_num": 1, "timebase_den": 25,
            }
            leaves.append(leaf)
        self.assertEqual(preflight_preview(request(outputs=leaves))["request_count"], 18)

    def test_editable_project_request_never_implies_roundtrip_pass(self):
        leaf = output(selector="FULL_VIDEO", target="Video Editor")
        leaf["delivery_class"] = "COPY_EDITABLE_IF_ADMITTED"
        result = preflight_preview(request(outputs=[leaf]))
        self.assertEqual(result["outputs"][0]["status"],
                         "PENDING_EXTERNAL_FORMAT_ROUNDTRIP_EVIDENCE")

    def test_schema_declares_17_family_scoped_selections_and_preview_only(self):
        s = json.loads((ROOT / "canonical/schemas/selective-production-import.v1.json").read_text())
        self.assertEqual(s["x-fa3-policy"]["capability_count"], 175)
        self.assertFalse(s["x-fa3-policy"]["authority"])
        self.assertFalse(s["x-fa3-policy"]["new_architectural_authority"])
        self.assertEqual(s["properties"]["execution_authorized"]["const"], False)
        self.assertIn("preview_only", s["required"])
        rules = s["$defs"]["output"]["allOf"]
        by_family = {}
        for rule in rules:
            family = rule["if"]["properties"].get("family", {}).get("const")
            if family and "selector_id" in rule.get("then", {}).get("properties", {}):
                by_family[family] = rule["then"]["properties"]["selector_id"]["enum"]
        self.assertEqual({k: len(v) for k, v in by_family.items()},
                         {"TEXT": 4, "AUDIO": 6, "VIDEO": 7})
        self.assertEqual(len(set(by_family["AUDIO"]) & set(by_family["VIDEO"])), 1)
        self.assertEqual(set(by_family["AUDIO"]) & set(by_family["VIDEO"]), {"TRANSCRIPT_ONLY"})


if __name__ == "__main__":
    unittest.main()
