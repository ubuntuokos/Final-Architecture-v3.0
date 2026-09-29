"""Static S4.2 QC planning/registry tests; no media, model or current-host proof."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from fa3_selective_import_audio_qc import audio_qc_plan_preview
from test_selective_import_preview import request, output
from test_selective_import_stream_binding import inventory


def candidate(*classes):
    return {
        "provider_ref": "ref:proposed.sep",
        "model_weight_sha256": "a" * 64,
        "declared_stem_classes": list(classes),
        "license_review_ref": "ref:review.pending",
    }


class AudioQcPreviewTests(unittest.TestCase):
    def test_claimed_original_instrumental_is_not_verified_or_published(self):
        q = request(outputs=[output(selector="MUSIC_OR_INSTRUMENTAL_ONLY",
                                    target="Music Studio", stem="INSTRUMENTAL")])
        inv = inventory()
        inv["streams"][1]["role"] = "INSTRUMENTAL"
        inv["streams"][1]["source_stem_attestation_ref"] = "ref:outside.claim"
        p = audio_qc_plan_preview(q, inv)
        x = p["outputs"][0]
        self.assertEqual(x["origin"], "CLAIMED_ORIGINAL_TRACK")
        self.assertIn("INDEPENDENT_ORIGINAL_STEM_ATTESTATION",
                      x["required_independent_evidence_checks"])
        self.assertIn("OPTIONAL_SOURCE_RELINK_FINGERPRINT_ADVISORY_ONLY",
                      x["advisory_measurement_methods"])
        self.assertFalse(x["independent_evidence_verified"])
        self.assertFalse(x["publish_audio"])
        self.assertFalse(p["execution_authorized"])

    def test_estimated_stem_model_declaration_and_operator_optin_not_proof(self):
        q = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                    target="Sound Design", stem="AMBIENCE_AND_SFX")])
        p = audio_qc_plan_preview(
            q, inventory(), untrusted_model_candidates=[candidate("AMBIENCE_AND_SFX")],
            estimate_opt_in_leaf_indices=[0])
        x = p["outputs"][0]
        self.assertEqual(x["origin"], "PROPOSED_ESTIMATED_STEM")
        self.assertEqual(x["quality_readiness"],
                         "PENDING_INDEPENDENT_ESTIMATED_STEM_ADMISSION")
        self.assertIn("SOURCE_REFERENCE_METRICS_ONLY_WITH_VERIFIED_ISOLATED_REFERENCES",
                      x["required_independent_evidence_checks"])
        self.assertFalse(x["quality_metrics_claimed_as_proof"])
        self.assertFalse(x["human_quality_review_approved"])
        self.assertFalse(x["publish_audio"])

    def test_no_optin_yields_no_model_admission_pretence(self):
        q = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                    target="Sound Design", stem="AMBIENCE_AND_SFX")])
        p = audio_qc_plan_preview(q, inventory(),
                                  untrusted_model_candidates=[candidate("AMBIENCE_AND_SFX")])
        self.assertEqual(p["outputs"][0]["origin"], "NONE")
        self.assertEqual(p["outputs"][0]["quality_readiness"],
                         "UNSUPPORTED_OR_BLOCKED_WITH_CURRENT_METADATA")
        self.assertFalse(p["publish_audio"])

    def test_denoiser_residual_not_ambience_or_sfx(self):
        q = request(kind="AUDIO", outputs=[
            output("AUDIO", "DENOISED_SPEECH", "Audio Fabric", stem="DENOISED_SPEECH"),
            output("AUDIO", "AMBIENCE_AND_SFX", "Sound Design", stem="AMBIENCE_AND_SFX"),
        ])
        inv = inventory()
        inv["streams"] = [inv["streams"][1]]
        p = audio_qc_plan_preview(q, inv)
        speech, effects = p["outputs"]
        self.assertEqual(speech["origin"], "DENOISE_DERIVATIVE_ONLY")
        self.assertIn("DENOISER_RESIDUAL_CANNOT_PROVE_AMBIENCE_OR_SFX",
                      speech["required_independent_evidence_checks"])
        self.assertEqual(effects["origin"], "NONE")
        self.assertFalse(effects["publish_audio"])

    def test_transcript_only_and_picture_only_produce_no_audio_qc_output(self):
        q = request(outputs=[
            output(selector="TRANSCRIPT_ONLY", target="Subtitle Studio"),
            output(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor"),
        ])
        p = audio_qc_plan_preview(q, inventory())
        self.assertEqual(p["outputs"], [])
        self.assertEqual(p["output_count"], 0)
        self.assertFalse(p["publish_audio"])

    def test_proposed_authority_and_malformed_model_candidate_are_rejected(self):
        q = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                    target="Sound Design", stem="AMBIENCE_AND_SFX")])
        q["execution_authorized"] = True
        with self.assertRaises(ValueError):
            audio_qc_plan_preview(q, inventory())
        q.pop("execution_authorized")
        with self.assertRaises(ValueError):
            audio_qc_plan_preview(q, inventory(), untrusted_model_candidates=[
                {**candidate("AMBIENCE_AND_SFX"), "direct_network_endpoint": "https://example.org"}])

    def test_schema_and_new_three_donors_with_existing_175_baseline(self):
        schema = json.loads((ROOT / "canonical/schemas/selective-audio-qc-plan.v1.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(schema["x-fa3-policy"]["capability_count"], 175)
        self.assertFalse(schema["x-fa3-policy"]["authority"])
        self.assertFalse(schema["x-fa3-policy"]["current_host_runtime_promotion_claim"])
        self.assertEqual(schema["properties"]["publish_audio"]["const"], False)
        self.assertEqual(schema["properties"]["execution_authorized"]["const"], False)
        reg = json.loads((ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json")
                         .read_text(encoding="utf-8"))
        entries = reg["entries"]
        self.assertEqual(reg["capability_count"], 175)
        self.assertEqual(reg["backfill"]["entry_count"], len(entries))
        self.assertEqual(len({r["donor_id"] for r in entries}), len(entries))
        self.assertEqual(len({r["source"]["normalized_key"] for r in entries}),
                         len(entries))
        for name in ("jiixyj/libebur128", "acoustid/chromaprint",
                     "bastibe/python-soundfile"):
            rows = [r for r in entries if r["source"]["normalized_key"] ==
                    "github:" + name]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["status"], "CANDIDATE")
            self.assertFalse(row["authority"])
            self.assertFalse(row["automatic_install"])
            self.assertFalse(row["automatic_code_import"])
            self.assertFalse(row["automatic_provider_admission"])


if __name__ == "__main__":
    unittest.main()
