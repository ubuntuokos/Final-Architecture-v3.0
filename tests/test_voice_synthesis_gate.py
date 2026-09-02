from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_voice_synthesis_gate import VoicePolicyDenied, gate, resolve_route


class VoiceSynthesisGateTests(unittest.TestCase):
    def test_canonical_gate_passes_all_32_rules(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(32, report["passed"])
        self.assertFalse(report["current_host_production_claim"])
        self.assertFalse(report["hungarian_quality_claim"])

    def test_hungarian_cloning_selects_xtts_only(self):
        result = resolve_route(
            {"language": "hu-HU", "mode": "voice_clone"},
            {"FA3-PROVIDER-XTTS-001", "FA3-PROVIDER-PIPER-001"},
        )
        self.assertEqual("FA3-PROVIDER-XTTS-001", result["selected_provider_id"])
        self.assertFalse(result["silent_fallback"])

    def test_hungarian_plain_tts_uses_piper_if_xtts_not_admitted(self):
        result = resolve_route(
            {"language": "hu", "mode": "plain"},
            {"FA3-PROVIDER-PIPER-001"},
        )
        self.assertEqual("FA3-PROVIDER-PIPER-001", result["selected_provider_id"])

    def test_piper_cannot_satisfy_hungarian_cloning(self):
        with self.assertRaises(VoicePolicyDenied):
            resolve_route(
                {"language": "hu-HU", "mode": "voice_clone"},
                {"FA3-PROVIDER-PIPER-001"},
            )

    def test_voxcpm_cannot_satisfy_hungarian_request(self):
        with self.assertRaises(VoicePolicyDenied):
            resolve_route(
                {"language": "hu-HU", "mode": "plain"},
                {"FA3-PROVIDER-VOXCPM-001"},
            )

    def test_no_admitted_hungarian_route_fails_closed(self):
        with self.assertRaises(VoicePolicyDenied):
            resolve_route({"language": "hu-HU", "mode": "plain"}, set())

    def test_provider_authority_drift_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "canonical", root / "canonical")
            shutil.copytree(ROOT / "evidence", root / "evidence")
            path = root / "canonical/providers/FA3-PROVIDER-VOXCPM-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["architectural_authority"] = True
            path.write_text(json.dumps(obj), encoding="utf-8")
            self.assertEqual("FAIL", gate(root)["result"])

    def test_mms_production_admission_drift_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "canonical", root / "canonical")
            shutil.copytree(ROOT / "evidence", root / "evidence")
            path = root / "canonical/providers/FA3-PROVIDER-MMS-TTS-HUN-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["routing_policy"]["production"] = "ALLOW"
            path.write_text(json.dumps(obj), encoding="utf-8")
            self.assertEqual("FAIL", gate(root)["result"])

    def test_ci_evidence_cannot_claim_current_host(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "canonical", root / "canonical")
            shutil.copytree(ROOT / "evidence", root / "evidence")
            path = root / "evidence/reference/voice-synthesis-ci-2026-09-01.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["current_host_production_claim"] = True
            path.write_text(json.dumps(obj), encoding="utf-8")
            self.assertEqual("FAIL", gate(root)["result"])


if __name__ == "__main__":
    unittest.main()
