from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import src.fa3_voice_capability_current_host as voice


ROOT = Path(__file__).resolve().parents[1]


def make_wav(path: Path, *, sample_rate: int, channels: int = 1, frames: int = 800) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes((b"\x00\x00" * channels) * frames)


class VoiceCapabilityCurrentHostTests(unittest.TestCase):
    def _coverage_env(self, subject_id: str) -> dict[str, str]:
        ids = voice.expected_source_decisions(ROOT, subject_id)
        return {"FA3_COVERS_SOURCE_DECISION_IDS_JSON": json.dumps(ids, separators=(",", ":"))}

    def test_exact_registry_coverage_for_all_three_voice_capabilities(self):
        expected_counts = {"CAP-115": 15, "CAP-116": 15, "CAP-117": 13}
        for subject_id, count in expected_counts.items():
            ids = voice.expected_source_decisions(ROOT, subject_id)
            self.assertEqual(len(ids), count)
            self.assertIn(f"DEC-{subject_id}", ids)
            self.assertIn("FA3-DEC-COSYVOICE-2026-08-31", ids)
            self.assertIn("FA3-DEC-VOICE-SYNTHESIS-PORTFOLIO-2026-09-01", ids)
            self.assertEqual(len(ids), len(set(ids)))

    def test_audio_validator_remeasures_native_and_48k_media_wav(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            base = Path(td)
            bundle_path = base / "CAP-115.json"
            bundle_path.write_text("{}\n", encoding="utf-8")
            native = base / "native.wav"
            media = base / "media.wav"
            make_wav(native, sample_rate=24000)
            make_wav(media, sample_rate=48000)
            native_sha = voice.sha256_file(native)
            media_sha = voice.sha256_file(media)
            result = voice._validate_audio(
                bundle_path,
                {
                    "native_output": {
                        "path": "native.wav",
                        "sha256": native_sha,
                        "sample_rate_hz": 24000,
                        "channels": 1,
                    },
                    "media_projection": {
                        "path": "media.wav",
                        "sha256": media_sha,
                        "sample_rate_hz": 48000,
                        "channels": 1,
                        "sample_format": "PCM_S16LE",
                        "lineage": {
                            "source_sha256": native_sha,
                            "algorithm": "soxr-hq",
                        },
                    },
                },
            )
            self.assertEqual(result["native_sha256"], native_sha)
            self.assertEqual(result["media_sha256"], media_sha)

    def test_audio_validator_rejects_json_sample_rate_claim_that_differs_from_wav(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            base = Path(td)
            bundle_path = base / "CAP-115.json"
            bundle_path.write_text("{}\n", encoding="utf-8")
            native = base / "native.wav"
            media = base / "media.wav"
            make_wav(native, sample_rate=22050)
            make_wav(media, sample_rate=48000)
            with self.assertRaises(ValueError):
                voice._validate_audio(
                    bundle_path,
                    {
                        "native_output": {
                            "path": "native.wav",
                            "sha256": voice.sha256_file(native),
                            "sample_rate_hz": 24000,
                            "channels": 1,
                        },
                        "media_projection": {
                            "path": "media.wav",
                            "sha256": voice.sha256_file(media),
                            "sample_rate_hz": 48000,
                            "channels": 1,
                            "sample_format": "PCM_S16LE",
                            "lineage": {
                                "source_sha256": voice.sha256_file(native),
                                "algorithm": "soxr-hq",
                            },
                        },
                    },
                )

    def test_cap116_streaming_requires_real_time_factor_at_most_one(self):
        good = {
            "requested": True,
            "chunk_count": 3,
            "first_audio_ms": 80.0,
            "completion_ms": 900.0,
            "audio_duration_seconds": 1.0,
            "wall_time_seconds": 0.9,
            "real_time_factor": 0.9,
            "session_correlation_bound": True,
            "provider_session_authority": False,
        }
        self.assertEqual(voice._validate_streaming(good)["real_time_factor"], 0.9)
        bad = dict(good)
        bad.update({"wall_time_seconds": 1.2, "real_time_factor": 1.2, "completion_ms": 1200.0})
        with self.assertRaises(ValueError):
            voice._validate_streaming(bad)

    def test_cloning_consent_requires_scope_expiry_and_revocation_pass(self):
        good = {
            "status": "GRANTED",
            "scope": ["VOICE_SYNTHESIS", "VOICE_CLONING"],
            "subject_authorized": True,
            "purpose": "authorized production",
            "provenance_ref": "consent:fixture",
            "revocation_ref": "revocation:fixture",
            "revoked": False,
            "expires_at": "2999-01-01T00:00:00Z",
        }
        self.assertTrue(voice._consent_valid(good, cloning=True))
        expired = dict(good, expires_at="2000-01-01T00:00:00Z")
        self.assertFalse(voice._consent_valid(expired, cloning=True))
        revoked = dict(good, revoked=True)
        self.assertFalse(voice._consent_valid(revoked, cloning=True))
        narrow = dict(good, scope=["VOICE_SYNTHESIS"])
        self.assertFalse(voice._consent_valid(narrow, cloning=True))

    def test_cosyvoice_hungarian_experimental_receipt_cannot_be_provider_production_pass(self):
        collector = ROOT / "evidence/collect-cosyvoice-current-host.py"
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            base = Path(td)
            bundle_path = base / "CAP-117.json"
            bundle_path.write_text("{}\n", encoding="utf-8")
            audio_sha = "a" * 64
            receipt = {
                "schema": "fa3.cosyvoice-current-host-evidence.v1",
                "provider_id": "FA3-PROVIDER-COSYVOICE-001",
                "repository_head": voice.repo_head(ROOT),
                "current_host": True,
                "synthetic": False,
                "global_promotion_claim": False,
                "language": "hu",
                "language_promotion_status": "EXPERIMENTAL_LANGUAGE_NOT_PRODUCTION_PROMOTABLE",
                "output_audio_sha256": audio_sha,
            }
            receipt_path = base / "cosy.json"
            receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            provider = {
                "provider_id": "FA3-PROVIDER-COSYVOICE-001",
                "locale": "hu-HU",
                "current_host_production_e2e": True,
                "production_language_admitted": True,
                "local_execution": True,
                "optional_runtime_global_dependency": False,
                "architectural_authority": False,
                "runtime_identity": "cosyvoice:pinned",
                "model_identity": "FunAudioLLM/Fun-CosyVoice3",
                "collector": {
                    "path": "evidence/collect-cosyvoice-current-host.py",
                    "sha256": voice.sha256_file(collector),
                },
                "receipt": {
                    "path": "cosy.json",
                    "sha256": voice.sha256_file(receipt_path),
                },
            }
            with self.assertRaisesRegex(ValueError, "experimental Hungarian"):
                voice._validate_provider(ROOT, bundle_path, provider)

    def test_missing_xtts_collector_remains_explicit_physical_blocker(self):
        expected = voice.PROVIDER_COLLECTOR_BINDINGS["FA3-PROVIDER-XTTS-001"]
        self.assertEqual(expected, "evidence/collect-xtts-current-host.py")
        self.assertFalse((ROOT / expected).exists())

    def test_negative_policy_matrix_passes_for_each_voice_capability(self):
        for subject_id in voice.SUBJECTS:
            cases = voice._negative_cases(ROOT, subject_id)
            self.assertTrue(cases)
            self.assertTrue(all(cases.values()), (subject_id, cases))

    def test_rollback_probe_restores_exact_state_and_destroys_ephemeral_workspace(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            result = voice._rollback_probe(Path(td), "CAP-117")
        self.assertTrue(result["rollback_hash_equal"])
        self.assertTrue(result["ephemeral_workspace_destroyed"])
        self.assertEqual(result["pre_sha256"], result["post_sha256"])
        self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])

    def test_run_mode_remains_capability_specific_and_not_provider_receipt_only(self):
        for subject_id in voice.SUBJECTS:
            with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.dict(
                os.environ, self._coverage_env(subject_id), clear=False
            ), patch.object(
                voice,
                "validate_static_voice_gates",
                return_value={
                    "voice_synthesis_gate": "PASS",
                    "current_host_production_claim": False,
                    "hungarian_quality_claim": False,
                },
            ), patch.object(
                voice,
                "validate_bundle",
                return_value={
                    "schema": "fa3.voice-capability-current-host-validation.v1",
                    "subject_id": subject_id,
                    "result": "PASS",
                },
            ):
                positive = voice.run_mode(ROOT, subject_id, "positive", Path(td))
                negative = voice.run_mode(ROOT, subject_id, "negative", Path(td))
                rollback = voice.run_mode(ROOT, subject_id, "rollback", Path(td))
            self.assertEqual(positive["status"], "PASS")
            self.assertEqual(negative["status"], "PASS")
            self.assertEqual(rollback["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
