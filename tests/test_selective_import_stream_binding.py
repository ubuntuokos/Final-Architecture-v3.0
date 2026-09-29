"""S2 stream binding tests: synthetic metadata only, not current-host media tests."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_selective_import_stream_binding import inspect_binding
from test_selective_import_preview import request, output

def inventory():
    return {
        "schema": "fa3.selective-source-stream-inventory.v1",
        "source_ref": "ref:source.1", "source_sha256": "0"*64,
        "inspector_receipt_ref": "ref:inspect.1",
        "inspector_authority": "file.convert.inspect",
        "inspector_status": "INSPECTED_ONLY",
        "streams": [
            {"index":0, "codec_type":"video", "time_base_num":1,
             "time_base_den":24000, "start_pts":0, "duration_ts":96000,
             "width":1920, "height":1080},
            {"index":1, "codec_type":"audio", "time_base_num":1,
             "time_base_den":48000, "start_pts":0, "duration_ts":192000,
             "sample_rate":48000, "channels":2, "channel_layout":"stereo"},
            {"index":2, "codec_type":"subtitle", "time_base_num":1,
             "time_base_den":1000, "start_pts":0, "duration_ts":4000},
        ],
    }

class S2Tests(unittest.TestCase):
    def test_four_requested_outputs_one_source(self):
        q=request(outputs=[
            output(selector="VIDEO_WITHOUT_AUDIO",target="Video Editor"),
            output(selector="TRANSCRIPT_ONLY",translation="MULTI_TRANSLATION",
                   langs=["hu-HU","de-DE"]),
            output(selector="FULL_AUDIO_ONLY",target="Audio Fabric"),
            output(selector="FRAMES_OR_SCENES",target="Photo/Image Studio")])
        out=inspect_binding(q,inventory())["outputs"]
        self.assertEqual([x["original_stream_indices"] for x in out],
                         [[0],[1],[1],[0]])
        self.assertFalse(out[1]["publish_audio"])
        self.assertFalse(out[1]["publish_video"])
        self.assertTrue(out[1]["internal_audio_dependency_only"])
        self.assertEqual(out[1]["target_languages"],["hu-HU","de-DE"])
        self.assertEqual(out[1]["original_timebases"][0]["denominator"],48000)
        self.assertTrue(all(not x["execution_authorized"] and
                            not x["original_exactness_verified"] for x in out))
    def test_full_video_retains_original_discrete_tracks(self):
        q=request(outputs=[output(selector="FULL_VIDEO",target="Video Editor")])
        o=inspect_binding(q,inventory())["outputs"][0]
        self.assertEqual(o["original_stream_indices"],[0,1,2])
        self.assertTrue(o["publish_video"])
        self.assertTrue(o["publish_audio"])
    def test_mixed_stem_only_pending(self):
        q=request(outputs=[output(selector="AMBIENCE_AND_SFX_ONLY",
                                  target="Sound Design",stem="AMBIENCE_AND_SFX")])
        r=inspect_binding(q,inventory())["outputs"][0]
        self.assertEqual(r["status"],"PENDING_EXACT_STEM_PROVIDER_OR_UNSUPPORTED")
    def test_verified_original_stem_is_still_pending_evidence(self):
        q=request(outputs=[output(selector="MUSIC_OR_INSTRUMENTAL_ONLY",
                                  target="Music Studio",stem="INSTRUMENTAL")])
        x=inventory()
        x["streams"][1]["role"]="INSTRUMENTAL"
        x["streams"][1]["source_stem_attestation_ref"]="ref:proof.1"
        r=inspect_binding(q,x)["outputs"][0]
        self.assertEqual(r["status"],"PENDING_ORIGINAL_STEM_ATTESTATION_VERIFICATION")
        self.assertFalse(r["original_exactness_verified"])
    def test_two_audio_streams_require_choice(self):
        x=inventory()
        x["streams"].append({"index":4,"codec_type":"audio","time_base_num":1,
                             "time_base_den":48000,"start_pts":0,"sample_rate":48000,
                             "channels":6,"channel_layout":"5.1"})
        q=request(outputs=[output(selector="TRANSCRIPT_ONLY")])
        r=inspect_binding(q,x)["outputs"][0]
        self.assertEqual(r["status"],"PENDING_EXPLICIT_SOURCE_STREAM_SELECTION")
        r=inspect_binding(q,x,[{"leaf_index":0,"stream_indices":[4]}])["outputs"][0]
        self.assertEqual(r["original_stream_indices"],[4])
    def test_reject_bad_source_wrong_kind_duplicate_or_unauthorized_receipt(self):
        q=request()
        for field,value in [("source_sha256","f"*64),
                             ("inspector_receipt_ref","https://wrong.example"),
                             ("inspector_status","EXACT_VERIFIED")]:
            with self.subTest(field=field):
                x=inventory()
                x[field]=value
                with self.assertRaises(ValueError):inspect_binding(q,x)
        x=inventory()
        x["streams"][1]["index"]=0
        with self.assertRaises(ValueError):inspect_binding(q,x)
        with self.assertRaises(ValueError):
            inspect_binding(q,inventory(),[{"leaf_index":0,"stream_indices":[0]}])
        with self.assertRaises(ValueError):
            inspect_binding(q,inventory(),[{"leaf_index":0,"stream_indices":[1,1]}])
    def test_missing_audio_and_live_are_separately_blocked(self):
        q=request(kind="AUDIO",outputs=[output("AUDIO","TRANSCRIPT_ONLY")])
        x=inventory()
        x["streams"]=[x["streams"][0]]
        self.assertEqual(inspect_binding(q,x)["outputs"][0]["status"],
                         "BLOCKED_MISSING_REQUIRED_SOURCE_STREAM")
        q=request(mode="LIVE_VIDEO")
        with self.assertRaises(ValueError):inspect_binding(q,inventory())

if __name__=="__main__":
    unittest.main()
