from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_voice_synthesis_gate import VoicePolicyDenied, gate, resolve_route, validate_transformation_request


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


    def _base_transformation(self, mode="VOICE_CONVERSION"):
        return {
            "request_id": "voice-transform:test",
            "mode": mode,
            "source_audio_ref": "artifact:source",
            "target_voice_identity_ref": "voice:target",
            "execution_mode": "OFFLINE_LOCAL",
            "output_intent": "MEDIA_MEZZANINE",
            "consent_proof": {"status": "GRANTED", "scope": [mode]},
            "license_and_rights_ref": "rights:approved",
            "silent_fallback": False,
        }

    def test_transformation_valid_target_voice_request_passes_preflight(self):
        result = validate_transformation_request(
            self._base_transformation(),
            rights_admitted=True,
            provider_status="PRODUCTION_ADMITTED",
        )
        self.assertEqual("VOICE_CONVERSION", result["mode"])
        self.assertFalse(result["silent_fallback"])

    def test_transformation_missing_or_wrong_consent_fails_closed(self):
        request = self._base_transformation()
        request["consent_proof"] = {"status": "GRANTED", "scope": ["VOICE_SYNTHESIS"]}
        with self.assertRaises(VoicePolicyDenied):
            validate_transformation_request(
                request, rights_admitted=True, provider_status="ADMITTED"
            )

    def test_transformation_silent_fallback_fails_closed(self):
        request = self._base_transformation()
        request["silent_fallback"] = True
        with self.assertRaises(VoicePolicyDenied):
            validate_transformation_request(
                request, rights_admitted=True, provider_status="ADMITTED"
            )

    def test_transformation_unknown_rights_fail_closed(self):
        with self.assertRaises(VoicePolicyDenied):
            validate_transformation_request(
                self._base_transformation(),
                rights_admitted=False,
                provider_status="ADMITTED",
            )

    def test_transformation_accelerator_without_hrb_lease_fails_closed(self):
        request = self._base_transformation()
        request["accelerator_requested"] = True
        with self.assertRaises(VoicePolicyDenied):
            validate_transformation_request(
                request, rights_admitted=True, provider_status="ADMITTED"
            )

    def test_transformation_reference_only_provider_fails_closed(self):
        with self.assertRaises(VoicePolicyDenied):
            validate_transformation_request(
                self._base_transformation(),
                rights_admitted=True,
                provider_status="ADMITTED",
                provider_reference_only=True,
            )

    def test_speech_representation_does_not_require_target_identity(self):
        request = self._base_transformation("SPEECH_REPRESENTATION")
        request.pop("target_voice_identity_ref")
        request["consent_proof"] = {"status": "GRANTED", "scope": ["SPEECH_REPRESENTATION"]}
        result = validate_transformation_request(
            request, rights_admitted=True, provider_status="ADMITTED"
        )
        self.assertEqual("SPEECH_REPRESENTATION", result["mode"])

    def test_realtime_transformation_requires_latency_budget(self):
        request = self._base_transformation("REALTIME_VOICE_CONVERSION")
        with self.assertRaises(VoicePolicyDenied):
            validate_transformation_request(
                request, rights_admitted=True, provider_status="ADMITTED"
            )
        request["latency_requirement"] = 80
        result = validate_transformation_request(
            request, rights_admitted=True, provider_status="ADMITTED"
        )
        self.assertEqual("REALTIME_VOICE_CONVERSION", result["mode"])


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
