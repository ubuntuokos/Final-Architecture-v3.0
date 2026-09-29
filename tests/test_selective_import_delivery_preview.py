"""S5 cross-app fan-out tests. Synthetic plans only; never physical E2E."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from fa3_selective_import_delivery_preview import delivery_preview
from test_selective_import_preview import output, request
from test_selective_import_stream_binding import inventory


def proposal(*classes):
    return {"provider_ref": "ref:proposed.sep",
            "model_weight_sha256": "a" * 64,
            "declared_stem_classes": list(classes),
            "license_review_ref": "ref:license.pending"}


class S5DeliveryTests(unittest.TestCase):
    def test_one_film_4_requests_5_delivery_leaves(self):
        q = request(outputs=[
            output(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor"),
            output(selector="TRANSCRIPT_ONLY", target="Subtitle Studio",
                   translation="ORIGINAL_PLUS_TRANSLATIONS", langs=["hu", "de"]),
            output(selector="FULL_AUDIO_ONLY", target="Audio Fabric"),
            output(selector="AMBIENCE_AND_SFX_ONLY", target="Sound Design",
                   stem="AMBIENCE_AND_SFX"),
        ])
        p = delivery_preview(q, inventory())
        self.assertEqual(p["requested_output_count"], 4)
        self.assertEqual(p["planned_deliverable_count"], 6)
        self.assertEqual(p["language_branch_count"], 3)
        self.assertEqual(p["audio_qc_leaf_count"], 1)
        self.assertEqual([v["target_locale"] for v in p["deliverables"][1:4]],
                         ["fr", "hu", "de"])
        self.assertEqual(p["deliverables"][0]["requested_publication"],
                         {"text": False, "audio": False, "video": True})
        self.assertEqual(p["deliverables"][4]["requested_publication"],
                         {"text": False, "audio": True, "video": False})
        self.assertIn("UNSUPPORTED", p["deliverables"][5]["status"])
        self.assertTrue(all(not row["execution_authorized"]
                            and not any(row[f"publish_{kind}"] for kind in
                                        ("text", "audio", "video"))
                            for row in p["deliverables"]))

    def test_original_and_translated_text_no_av(self):
        q = request(kind="TEXT", outputs=[
            output("TEXT", "ORIGINAL_PLUS_TRANSLATIONS", "Story/Screenplay",
                   translation="ORIGINAL_PLUS_TRANSLATIONS", langs=["en", "hu"])
        ])
        i = inventory()
        i["streams"] = []
        p = delivery_preview(q, i)
        self.assertEqual(p["planned_deliverable_count"], 3)
        self.assertTrue(all(row["requested_publication"] ==
                            {"text": True, "audio": False, "video": False}
                            for row in p["deliverables"]))
        self.assertTrue(all(row["source_stream_indices"] == []
                            for row in p["deliverables"]))

    def test_original_instrumental_claim_requires_evidence(self):
        q = request(outputs=[
            output(selector="MUSIC_OR_INSTRUMENTAL_ONLY",
                   target="Music Studio", stem="INSTRUMENTAL")])
        i = inventory()
        i["streams"][1]["role"] = "INSTRUMENTAL"
        i["streams"][1]["source_stem_attestation_ref"] = "ref:outside.claim"
        p = delivery_preview(q, i)
        leaf = p["deliverables"][0]
        self.assertEqual(leaf["variant"], "CLAIMED_ORIGINAL_TRACK")
        self.assertIn("INDEPENDENT_ORIGINAL_STEM_ATTESTATION",
                      leaf["required_independent_checks"])
        self.assertFalse(leaf["independent_evidence_verified"])
        self.assertFalse(leaf["publish_audio"])

    def test_estimated_stem_opt_in_is_still_not_admission(self):
        q = request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                    target="Sound Design", stem="AMBIENCE_AND_SFX")])
        p = delivery_preview(
            q, inventory(), untrusted_model_candidates=[proposal("AMBIENCE_AND_SFX")],
            estimate_opt_in_leaf_indices=[0])
        item = p["deliverables"][0]
        self.assertEqual(item["variant"], "PROPOSED_ESTIMATED_STEM")
        self.assertIn("PENDING_INDEPENDENT_ESTIMATED_STEM_ADMISSION", item["status"])
        self.assertFalse(item["execution_authorized"])

    def test_empty_audio_on_full_video_no_invented_audio(self):
        q = request(outputs=[output(selector="FULL_VIDEO", target="Video Editor")])
        i = inventory()
        i["streams"] = [i["streams"][0]]
        p = delivery_preview(q, i)
        self.assertEqual(p["deliverables"][0]["requested_publication"],
                         {"text": False, "audio": False, "video": True})

    def test_duplicate_language_target_and_editable_roundtrip_are_visible(self):
        q = request(kind="TEXT", outputs=[
            output("TEXT", "ORIGINAL_LANGUAGE", "Story/Screenplay"),
            output("TEXT", "ORIGINAL_PLUS_TRANSLATIONS", "Story/Screenplay",
                   translation="ORIGINAL_PLUS_TRANSLATIONS", langs=["en"]),
        ])
        q["requested_outputs"][1]["delivery_class"] = "COPY_EDITABLE_IF_ADMITTED"
        i = inventory()
        i["streams"] = []
        p = delivery_preview(q, i)
        self.assertEqual(len(p["duplicate_language_destinations"]), 1)
        self.assertEqual([x["status"] for x in p["deliverables"]].count(
            "PENDING_DUPLICATE_DESTINATION_REVIEW"), 2)
        self.assertTrue(all(x["editable_project_verified"] is False
                            for x in p["deliverables"]))
        self.assertIn("EXACT_FORMAT_PAIR_VERSION_AND_FEATURE_ROUNDTRIP",
                      p["deliverables"][1]["required_independent_checks"])

    def test_cross_app_no_approval_ref_and_malformed_source_fail_closed(self):
        q = request(outputs=[output(selector="VIDEO_WITHOUT_AUDIO",
                                    target="Video Editor")])
        p = delivery_preview(q, inventory())
        self.assertIn("EXISTING_UAF_CROSS_APP_AUTHORIZATION",
                      p["deliverables"][0]["required_independent_checks"])
        q["execution_authorized"] = True
        with self.assertRaises(ValueError):
            delivery_preview(q, inventory())
        q["execution_authorized"] = False
        i = inventory()
        i["source_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            delivery_preview(q, i)

    def test_schema_and_fixed_17_source_selectors_175(self):
        s = json.loads((ROOT / "canonical/schemas/selective-delivery-preview.v1.json")
                       .read_text(encoding="utf-8"))
        self.assertEqual(s["x-fa3-policy"]["capability_count"], 175)
        self.assertFalse(s["x-fa3-policy"]["authority"])
        self.assertFalse(s["x-fa3-policy"]["current_host_runtime_promotion_claim"])
        for kind in ("text", "audio", "video"):
            self.assertIs(s["properties"]["publish_" + kind]["const"], False)
        self.assertIs(s["properties"]["execution_authorized"]["const"], False)
        inp = json.loads((ROOT / "canonical/schemas/selective-production-import.v1.json")
                         .read_text(encoding="utf-8"))
        families = {
            rule["if"]["properties"]["family"]["const"]: rule["then"]["properties"]["selector_id"]["enum"]
            for rule in inp["$defs"]["output"]["allOf"]
            if "family" in rule["if"]["properties"]
            and "selector_id" in rule.get("then", {}).get("properties", {})
        }
        self.assertEqual({k: len(v) for k, v in families.items()},
                         {"TEXT": 4, "AUDIO": 6, "VIDEO": 7})


if __name__ == "__main__":
    unittest.main()
