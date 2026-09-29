"""S4 metadata-only stem strategy regressions. No media, model or runtime proof."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from fa3_selective_import_stem_plan import stem_plan_preview
from test_selective_import_preview import request, output
from test_selective_import_stream_binding import inventory


def candidate(*classes):
    return {
        "provider_ref": "ref:proposed.sep",
        "model_weight_sha256": "a" * 64,
        "declared_stem_classes": list(classes),
        "license_review_ref": "ref:review.pending",
    }


class StemPlanPreviewTests(unittest.TestCase):
    def test_exact_original_music_track_remains_attestation_pending(self):
        q = request(outputs=[output(selector="MUSIC_OR_INSTRUMENTAL_ONLY",
                                    target="Music Studio", stem="INSTRUMENTAL")])
        inv = inventory()
        inv["streams"][1]["role"] = "INSTRUMENTAL"
        inv["streams"][1]["source_stem_attestation_ref"] = "ref:external.claim"
        p = stem_plan_preview(q, inv)
        leaf = p["outputs"][0]
        self.assertEqual(leaf["origin"], "CLAIMED_ORIGINAL_TRACK")
        self.assertEqual(leaf["claimed_source_attestation_refs"], ["ref:external.claim"])
        self.assertFalse(leaf["original_exactness_verified"])
        self.assertFalse(leaf["publish_audio"])
        self.assertFalse(leaf["execution_authorized"])

    def test_mixed_audio_not_treated_as_clean_ambience_without_model(self):
        q = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                    target="Sound Design", stem="AMBIENCE_AND_SFX")])
        leaf = stem_plan_preview(q, inventory())["outputs"][0]
        self.assertEqual(leaf["status"],
                         "UNSUPPORTED_EXACT_STEM_WITH_AVAILABLE_PREVIEW_METADATA")
        self.assertEqual(leaf["origin"], "NONE")
        self.assertEqual(leaf["source_stream_indices"], [1])

    def test_untrusted_model_declaration_never_grants_admission(self):
        q = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                    target="Sound Design", stem="AMBIENCE_AND_SFX")])
        x = stem_plan_preview(q, inventory(),
                              untrusted_model_candidates=[candidate("AMBIENCE_AND_SFX")])
        self.assertEqual(x["outputs"][0]["status"],
                         "ESTIMATE_REQUIRES_EXPLICIT_OPERATOR_OPT_IN")
        x = stem_plan_preview(q, inventory(),
                              untrusted_model_candidates=[candidate("AMBIENCE_AND_SFX")],
                              estimate_opt_in_leaf_indices=[0])
        leaf = x["outputs"][0]
        self.assertEqual(leaf["origin"], "PROPOSED_ESTIMATED_STEM")
        self.assertEqual(leaf["status"],
                         "PENDING_INDEPENDENT_LICENSE_MODEL_HRB_AND_QUALITY_ADMISSION")
        self.assertFalse(leaf["execution_authorized"])
        self.assertFalse(leaf["model_license_verified"])
        self.assertFalse(leaf["physical_host_verified"])

    def test_vocals_claim_not_speech_or_singing_exact(self):
        q = request(kind="AUDIO", outputs=[
            output("AUDIO", "SPEECH_OR_SINGING_SEPARATE", "Audio Fabric", stem="SPEECH")
        ])
        inv = inventory()
        inv["streams"] = [inv["streams"][1]]
        inv["streams"][0]["role"] = "VOCALS"
        inv["streams"][0]["source_stem_attestation_ref"] = "ref:claim.vocals"
        leaf = stem_plan_preview(q, inv)["outputs"][0]
        self.assertEqual(leaf["origin"], "NONE")
        x = stem_plan_preview(q, inv,
                              untrusted_model_candidates=[candidate("VOCALS")],
                              estimate_opt_in_leaf_indices=[0])
        self.assertEqual(x["outputs"][0]["origin"], "NONE")

    def test_denoiser_never_satisfies_ambience_and_sfx(self):
        q = request(kind="AUDIO", outputs=[
            output("AUDIO", "DENOISED_SPEECH", "Audio Fabric",
                   stem="DENOISED_SPEECH"),
            output("AUDIO", "AMBIENCE_AND_SFX", "Sound Design",
                   stem="AMBIENCE_AND_SFX"),
        ])
        inv = inventory()
        inv["streams"] = [inv["streams"][1]]
        x = stem_plan_preview(q, inv)
        self.assertEqual(x["outputs"][0]["origin"], "DENOISE_DERIVATIVE_ONLY")
        self.assertEqual(x["outputs"][1]["origin"], "NONE")

    def test_no_unrequested_video_or_transcript_publication(self):
        q = request(outputs=[
            output(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor"),
            output(selector="TRANSCRIPT_ONLY", target="Subtitle Studio"),
            output(selector="AMBIENCE_AND_SFX_ONLY", target="Sound Design",
                   stem="AMBIENCE_AND_SFX"),
        ])
        x = stem_plan_preview(q, inventory())
        self.assertEqual(x["stem_leaf_count"], 1)
        self.assertEqual(x["outputs"][0]["parent_leaf_index"], 2)
        self.assertFalse(x["outputs"][0]["publish_audio"])

    def test_missing_track_and_ambiguous_multiple_audio_tracks(self):
        q = request(outputs=[output(selector="MUSIC_OR_INSTRUMENTAL_ONLY",
                                    target="Music Studio", stem="INSTRUMENTAL")])
        inv = inventory()
        inv["streams"] = [inv["streams"][0]]
        self.assertEqual(stem_plan_preview(q, inv)["outputs"][0]["status"],
                         "BLOCKED_MISSING_AUDIO")
        inv = inventory()
        inv["streams"].append({
            "index": 4, "codec_type": "audio", "time_base_num": 1,
            "time_base_den": 48000, "start_pts": 0, "sample_rate": 48000,
            "channels": 2
        })
        self.assertEqual(stem_plan_preview(q, inv)["outputs"][0]["status"],
                         "PENDING_OPERATOR_STREAM_CHOICE")

    def test_reject_unbounded_untrusted_model_or_nonstem_optin(self):
        q = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                    target="Sound Design", stem="AMBIENCE_AND_SFX")])
        inv = inventory()
        for malformed in (
            [{**candidate("SPEECH"), "direct_url": "https://unknown"}],
            [{**candidate("SPEECH"), "model_weight_sha256": "bad"}],
            [candidate("INVALID")],
            [candidate("SPEECH"), candidate("SPEECH")],
        ):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                stem_plan_preview(q, inv, untrusted_model_candidates=malformed)
        with self.assertRaises(ValueError):
            stem_plan_preview(q, inv, untrusted_model_candidates={})
        with self.assertRaises(ValueError):
            stem_plan_preview(q, inv, estimate_opt_in_leaf_indices={})
        with self.assertRaises(ValueError):
            stem_plan_preview(q, inv, estimate_opt_in_leaf_indices=[0, 0])
        x = request(outputs=[output(selector="FULL_AUDIO_ONLY", target="Audio Fabric")])
        with self.assertRaises(ValueError):
            stem_plan_preview(x, inv, estimate_opt_in_leaf_indices=[0])

    def test_live_and_fake_authorization_rejected(self):
        q = request(mode="LIVE_VIDEO")
        with self.assertRaises(ValueError):
            stem_plan_preview(q, inventory())
        q = request(outputs=[output(selector="MUSIC_OR_INSTRUMENTAL_ONLY",
                                    target="Music Studio", stem="INSTRUMENTAL")])
        q["execution_authorized"] = True
        with self.assertRaises(ValueError):
            stem_plan_preview(q, inventory())

    def test_schema_baseline_175_and_no_execution_authority(self):
        s = json.loads((ROOT / "canonical/schemas/selective-audio-stem-plan.v1.json")
                       .read_text(encoding="utf-8"))
        p = s["x-fa3-policy"]
        self.assertEqual(p["capability_count"], 175)
        self.assertFalse(p["authority"])
        self.assertFalse(p["execution_authorized"])
        self.assertFalse(p["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
