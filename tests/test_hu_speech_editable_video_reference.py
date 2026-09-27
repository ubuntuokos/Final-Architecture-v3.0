import json
import tempfile
import unittest
from pathlib import Path

from fa3_hu_speech_editable_video_reference import (
    ReferenceJourneyError,
    complete_from_stt,
    run_reference_e2e,
    synthetic_fixture,
)
from fa3_hu_speech_editable_video_reference_gate import gate


ROOT = Path(__file__).resolve().parents[1]


class HungarianSpeechEditableVideoReferenceTests(unittest.TestCase):
    def test_reference_e2e_materializes_editable_roundtrip_without_current_host_overclaim(self):
        result = run_reference_e2e(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertFalse(result["current_host_claim"])
        self.assertFalse(result["production_promotion_claim"])
        self.assertTrue(all(result["checks"].values()), result)

    def test_hungarian_requirement_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            handoff, stt = synthetic_fixture(workdir)
            stt["language"] = "en"
            with self.assertRaises(ReferenceJourneyError):
                complete_from_stt(
                    handoff,
                    stt,
                    workdir / "journey",
                    human_edit_text="Szia!",
                    inject_failure_once=True,
                )

    def test_canonical_reference_gate_passes_while_physical_host_can_remain_pending(self):
        result = gate(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertIn(result["current_host_status"], {"PENDING_CURRENT_HOST", "CURRENT_HOST_PASS"})
        self.assertFalse(result["current_host_runtime_promotion_claim"])
        self.assertEqual("PASS", result["reference_e2e"]["result"])

    def test_reference_record_is_zero_authority_and_keeps_175_baseline(self):
        ref = json.loads((ROOT / "canonical/references/FA3-HU-SPEECH-EDITABLE-VIDEO-REFERENCE-001.json").read_text())
        self.assertEqual(175, ref["capability_count"])
        self.assertFalse(ref["new_capability"])
        self.assertFalse(ref["new_architectural_authority"])
        self.assertEqual(["CAP-017", "CAP-121", "CAP-126", "CAP-168"], ref["capability_bindings"])
        self.assertEqual("hu-HU", ref["requested_locale"])
        self.assertEqual("OpenTimelineIO", ref["canonical_timeline_ir"])
        self.assertEqual("project.fa3video", ref["fa3_video_project_artifact"])
        self.assertFalse(ref["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
