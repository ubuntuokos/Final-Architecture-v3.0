import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_blackhole_kdenlive import (
    PreparationRequest,
    PolicyDenied,
    SubtitleProjectionFailed,
    build_extract_command,
    build_stt_normalize_command,
    project_subtitles,
    run_executable_conformance,
    validate_preparation_request,
    validate_stt_command,
    validate_stt_result,
)
from fa3_blackhole_kdenlive_gate import gate

class BlackholeKdenliveTests(unittest.TestCase):
    def test_executable_conformance_passes(self):
        report=run_executable_conformance(ROOT)
        self.assertEqual(report["result"],"PASS")
        self.assertGreaterEqual(report["passed"],16)
        self.assertEqual(report["passed"],report["total"])

    def test_stt_without_demucs_is_valid(self):
        req=PreparationRequest(input_media="/tmp/x.wav",output_dir="/tmp/o",preprocessing="none")
        validate_preparation_request(req,require_existing_input=False)

    def test_invalid_zone_is_fail_closed(self):
        with self.assertRaises(PolicyDenied):
            validate_preparation_request(
                PreparationRequest(input_media="/tmp/x",output_dir="/tmp/o",zone_start_seconds=4,zone_end_seconds=2),
                require_existing_input=False,
            )

    def test_ffmpeg_commands_are_explicit(self):
        req=PreparationRequest(input_media="/tmp/x.mov",output_dir="/tmp/o")
        extract=build_extract_command(req,Path("/tmp/o/source.wav"))
        normalize=build_stt_normalize_command(req,Path("/tmp/source.wav"),Path("/tmp/stt.wav"))
        self.assertIn("0:a:0",extract)
        self.assertIn("44100",extract)
        self.assertIn("16000",normalize)
        self.assertIn("pcm_s16le",normalize)

    def test_stt_provider_command_requires_typed_artifacts(self):
        validate_stt_command(("/usr/bin/stt","--request","{request}","--result","{result}"))
        with self.assertRaises(PolicyDenied):
            validate_stt_command(("/usr/bin/stt","--request","{request}"))

    def test_audio_hash_binding_is_enforced(self):
        handoff={"stt_input_audio":{"sha256":"abc"}}
        result={"schema":"fa3.stt-media-result.v1","status":"PASS","audio_hash":"wrong","segments":[{"start":0,"end":1,"text":"x"}]}
        with self.assertRaises(SubtitleProjectionFailed):
            validate_stt_result(result,handoff)

    def test_kdenlive_projection_is_sidecar_only(self):
        handoff={"stt_input_audio":{"sha256":"abc"},"timeline_range":{"start_seconds":5.0}}
        result={
            "schema":"fa3.stt-media-result.v1","status":"PASS","audio_hash":"abc","segments":[
                {"start":0,"end":1,"text":"Hello"}
            ]
        }
        with tempfile.TemporaryDirectory() as td:
            descriptor=project_subtitles(handoff,result,td)
            self.assertFalse(descriptor["direct_kdenlive_xml_mutation"])
            self.assertEqual(descriptor["project_mutation"],"NONE")
            self.assertTrue(Path(descriptor["preferred_import"]["path"]).is_file())
            caption=json.loads(Path(descriptor["caption_track"]["path"]).read_text())
            self.assertEqual(caption["segments"][0]["timeline_start"],5.0)

    def test_canonical_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual(report["result"],"PASS")
        self.assertEqual(report["reference"]["result"],"PASS")
        self.assertEqual(report["conformance"]["result"],"PASS")

if __name__=="__main__":
    unittest.main()
