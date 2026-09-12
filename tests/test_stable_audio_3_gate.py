import json
import unittest
from pathlib import Path
from fa3_stable_audio_3_gate import gate

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class StableAudioFreeOnlyTests(unittest.TestCase):
    def test_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertFalse(report["paid_routes_allowed"])

    def test_paid_large_route_is_removed(self):
        provider = load("canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json")
        self.assertEqual(provider["routes"]["large"], "REMOVED_PAID_ROUTE")
        self.assertEqual(provider["model_family"]["large"]["status"], "REMOVED_FROM_FA3_PAID_ONLY")
        self.assertFalse(provider["paid_routes_allowed"])
        self.assertFalse(provider["remote_paid_fallback"])

    def test_local_routes_remain(self):
        provider = load("canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json")
        self.assertEqual(provider["routes"]["small_music"], "CPU_LOCAL_CANDIDATE")
        self.assertEqual(provider["routes"]["small_sfx"], "CPU_LOCAL_CANDIDATE")
        self.assertEqual(provider["routes"]["medium"], "CUDA_LOCAL_CANDIDATE_SUBJECT_TO_HRB_E2E")
        self.assertEqual(provider["economics_policy"], "FA3-FREE-SELF-HOSTED-ONLY-001")


if __name__ == "__main__":
    unittest.main()
