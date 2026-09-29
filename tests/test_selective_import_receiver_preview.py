"""S6 synthetic exact receiver/host/format matching. No host/runtime E2E."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from fa3_selective_import_delivery_preview import delivery_preview
from fa3_selective_import_receiver_preview import receiver_handoff_preview
from test_selective_import_preview import output, request
from test_selective_import_stream_binding import inventory


def s5_one(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor", **kwargs):
    return delivery_preview(request(outputs=[
        output(selector=selector, target=target, **kwargs)
    ]), inventory())


def claim(leaf, fmt="video/mp4", version="1", *, editable=False, host="ref:nodeA"):
    kind = leaf["requested_publication"]
    content = "TEXT" if kind["text"] else (
        "AUDIO_VIDEO" if kind["audio"] and kind["video"] else
        "AUDIO" if kind["audio"] else "VIDEO"
    )
    return {
        "schema": "fa3.receiver-capability-claims.v1",
        "inventory_claim_ref": "ref:unverified.inventory.1",
        "receivers": [{
            "application": leaf["target_application"],
            "host_ref": host,
            "machine_role_ref": "ref:unverified.machine.role",
            "app_version": "0.1",
            "receiver_claim_ref": "ref:unverified.app.capabilities",
            "advertised_formats": [{
                "family": leaf["family"],
                "selector_id": leaf["selector_id"],
                "delivery_class": leaf["delivery_class"],
                "content_kind": content,
                "format_id": fmt,
                "format_version": version,
                "editable_roundtrip_claim": editable,
            }],
        }],
    }


def place(leaf, fmt="video/mp4", version="1", host="ref:nodeA"):
    return {"deliverable_ref": leaf["deliverable_ref"], "target_host_ref": host,
            "format_id": fmt, "format_version": version}


class ReceiverHandoffTests(unittest.TestCase):
    def test_exact_video_host_claim_is_pending_not_approved(self):
        p = s5_one()
        leaf = p["deliverables"][0]
        out = receiver_handoff_preview(p, claim(leaf), [place(leaf)])
        got = out["deliverables"][0]
        self.assertEqual(out["pending_receiver_count"], 1)
        self.assertEqual(got["status"], "PENDING_INDEPENDENT_RECEIVER_HANDSHAKE_AND_ADMISSION")
        self.assertEqual(got["target_host_ref"], "ref:nodeA")
        self.assertEqual(got["requested_publication"], {"text": False, "audio": False, "video": True})
        self.assertFalse(out["execution_authorized"])
        self.assertTrue(all(got[k] is False for k in ("publish_audio", "publish_video",
                                                       "receiver_verified", "format_verified")))
        self.assertIn("EXISTING_UAF_CROSS_APPLICATION_DELIVERY_APPROVAL", got["required_independent_checks"])

    def test_transcript_only_never_publishes_intermediate_audio_or_video(self):
        p = s5_one("TRANSCRIPT_ONLY", "Subtitle Studio",
                   translation="ORIGINAL_PLUS_TRANSLATIONS", langs=["hu", "de"])
        inv = claim(p["deliverables"][0], fmt="text/vtt")
        chosen = [place(leaf, fmt="text/vtt") for leaf in p["deliverables"]]
        out = receiver_handoff_preview(p, inv, chosen)
        self.assertEqual(out["pending_receiver_count"], 3)
        self.assertEqual([x["target_locale"] for x in out["deliverables"]], ["fr", "hu", "de"])
        self.assertTrue(all(x["requested_publication"] ==
                            {"text": True, "audio": False, "video": False}
                            for x in out["deliverables"]))
        self.assertTrue(all(not x["publish_text"] for x in out["deliverables"]))
        self.assertEqual(len({x["idempotency_intent_key"] for x in out["deliverables"]}), 3)

    def test_explicit_placement_no_silent_host_or_app_fallback(self):
        p = s5_one()
        leaf = p["deliverables"][0]
        without = receiver_handoff_preview(p, claim(leaf), [])
        self.assertEqual(without["deliverables"][0]["status"], "PENDING_EXPLICIT_HOST_AND_FORMAT_CHOICE")
        missing = receiver_handoff_preview(p, claim(leaf), [place(leaf, host="ref:nodeB")])
        self.assertEqual(missing["deliverables"][0]["status"],
                         "BLOCKED_RECEIVER_NOT_ADVERTISED_FOR_EXACT_APP_AND_HOST")
        altered = claim(leaf)
        altered["receivers"][0]["application"] = "QuickClip"
        other = receiver_handoff_preview(p, altered, [place(leaf)])
        self.assertEqual(other["pending_receiver_count"], 0)

    def test_no_silent_format_version_or_content_substitute(self):
        p = s5_one()
        leaf = p["deliverables"][0]
        out = receiver_handoff_preview(p, claim(leaf), [place(leaf, version="2")])
        self.assertEqual(out["deliverables"][0]["status"],
                         "BLOCKED_EXACT_FORMAT_SELECTOR_OR_CONTENT_NOT_ADVERTISED")
        inv = claim(leaf)
        inv["receivers"][0]["advertised_formats"][0]["content_kind"] = "AUDIO_VIDEO"
        out = receiver_handoff_preview(p, inv, [place(leaf)])
        self.assertEqual(out["pending_receiver_count"], 0)

    def test_editable_requires_bidirectional_app_claim_and_real_roundtrip(self):
        q = request(outputs=[output(selector="FULL_VIDEO", target="Video Editor")])
        q["requested_outputs"][0]["delivery_class"] = "COPY_EDITABLE_IF_ADMITTED"
        p = delivery_preview(q, inventory())
        leaf = p["deliverables"][0]
        inv = claim(leaf, "application/x-fa3video")
        choice = [place(leaf, "application/x-fa3video")]
        out = receiver_handoff_preview(p, inv, choice)
        self.assertEqual(out["deliverables"][0]["status"], "BLOCKED_EDITABLE_ROUNDTRIP_NOT_ADVERTISED")
        inv["receivers"][0]["advertised_formats"][0]["editable_roundtrip_claim"] = True
        out = receiver_handoff_preview(p, inv, choice)
        self.assertEqual(out["pending_receiver_count"], 1)
        self.assertIn("EXACT_FORMAT_PAIR_VERSION_AND_FEATURE_ROUNDTRIP",
                      out["deliverables"][0]["required_independent_checks"])
        self.assertFalse(out["deliverables"][0]["editable_project_verified"])

    def test_unavailable_stem_stays_blocked_even_when_receiver_claims_support(self):
        p = s5_one("AMBIENCE_AND_SFX_ONLY", "Sound Design", stem="AMBIENCE_AND_SFX")
        leaf = p["deliverables"][0]
        inv = claim(leaf, "audio/wav")
        out = receiver_handoff_preview(p, inv, [place(leaf, "audio/wav")])
        self.assertEqual(out["pending_receiver_count"], 0)
        self.assertEqual(out["blocked_or_unplaced_count"], 1)

    def test_duplicate_unknown_and_duplicate_receiver_claims_fail_closed(self):
        p = s5_one()
        leaf = p["deliverables"][0]
        inv, ch = claim(leaf), place(leaf)
        with self.assertRaises(ValueError):
            receiver_handoff_preview(p, inv, [ch, ch])
        with self.assertRaises(ValueError):
            receiver_handoff_preview(p, inv, [{**ch, "deliverable_ref": "unsolicited"}])
        inv["receivers"].append(copy.deepcopy(inv["receivers"][0]))
        with self.assertRaises(ValueError):
            receiver_handoff_preview(p, inv, [ch])

    def test_forged_s5_success_and_malformed_receiver_metadata_rejected(self):
        p = s5_one()
        leaf = p["deliverables"][0]
        inv, ch = claim(leaf), place(leaf)
        for key in ("execution_authorized", "independent_evidence_verified", "publish_video"):
            bad = copy.deepcopy(p)
            bad["deliverables"][0][key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                receiver_handoff_preview(bad, inv, [ch])
        inv["receivers"][0]["advertised_formats"][0]["selector_id"] = "INVENTED"
        with self.assertRaises(ValueError):
            receiver_handoff_preview(p, inv, [ch])

    def test_multilingual_and_media_have_independent_target_hosts(self):
        q = request(outputs=[
            output(selector="VIDEO_WITHOUT_AUDIO", target="Video Editor"),
            output(selector="TRANSCRIPT_ONLY", target="Subtitle Studio",
                   translation="ONE_TRANSLATION", langs=["hu"]),
        ])
        p = delivery_preview(q, inventory())
        video, text = p["deliverables"]
        inv = claim(video)
        text_inv = claim(text, "text/vtt", host="ref:nodeB")
        inv["receivers"].extend(text_inv["receivers"])
        out = receiver_handoff_preview(
            p, inv, [place(video), place(text, "text/vtt", host="ref:nodeB")])
        self.assertEqual(out["pending_receiver_count"], 2)
        self.assertEqual([x["target_host_ref"] for x in out["deliverables"]],
                         ["ref:nodeA", "ref:nodeB"])
        self.assertEqual(out["deliverables"][1]["requested_publication"]["audio"], False)

    def test_schema_and_17_options_175_unchanged(self):
        s = json.loads((ROOT / "canonical/schemas/selective-receiver-handoff-preview.v1.json")
                       .read_text(encoding="utf-8"))
        self.assertEqual(s["x-fa3-policy"]["capability_count"], 175)
        self.assertFalse(s["x-fa3-policy"]["current_host_runtime_promotion_claim"])
        self.assertFalse(s["properties"]["execution_authorized"]["const"])
        inp = json.loads((ROOT / "canonical/schemas/selective-production-import.v1.json")
                         .read_text(encoding="utf-8"))
        selectors = {rule["if"]["properties"]["family"]["const"]:
                     len(rule["then"]["properties"]["selector_id"]["enum"])
                     for rule in inp["$defs"]["output"]["allOf"]
                     if "family" in rule["if"]["properties"] and
                     "selector_id" in rule.get("then", {}).get("properties", {})}
        self.assertEqual(selectors, {"TEXT": 4, "AUDIO": 6, "VIDEO": 7})


if __name__ == "__main__":
    unittest.main()
