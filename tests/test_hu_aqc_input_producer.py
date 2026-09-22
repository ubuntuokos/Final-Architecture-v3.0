from __future__ import annotations

import json
import platform
import socket
import tempfile
import unittest
import wave
from pathlib import Path

from src.fa3_host_attestation import build_artifact, utcnow
from src.fa3_hu_aqc_input import produce_bundle, validate_bundle
from src.fa3_runtime_hardening_current_host import repo_head, sha256_file


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def host_attestation_fixture() -> dict:
    return {
        "schema": "fa3.host-attestation.v1",
        "host_attestation_id": "FA3-HOST-HU-AQC-TEST",
        "captured_at": utcnow(),
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "os_release": {"ID": "test"},
        "cpu_model": "test-cpu",
        "cpu_microcode": ["test"],
        "cpu_topology": {"schema": "fa3.cpu-topology-descriptor.v2"},
        "numa_topology": {"nodes": 1},
        "memory_total_bytes": 1024,
        "accelerators": [],
        "driver_versions": {},
        "runtime_versions": {"python": platform.python_version()},
        "pcie_topology": [],
        "storage_identity": {"status": "OBSERVED"},
        "thermal_power_state": {"status": "UNAVAILABLE"},
        "collector_version": "test",
        "secret_collection": "PROHIBITED",
    }


class HuAqcInputProducerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.audio = self.base / "hu.wav"
        with wave.open(str(self.audio), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            samples = [1000 if index % 2 else -1000 for index in range(8000)]
            wf.writeframes(b"".join(int(value).to_bytes(2, "little", signed=True) for value in samples))
        self.reference = self.base / "reference.txt"
        self.reference.write_text("Árvíztűrő tükörfúrógép", encoding="utf-8")
        self.host = self.base / "host.json"
        write_json(self.host, build_artifact(host_attestation_fixture()))
        self.host_ref = json.loads(self.host.read_text())["host_attestation_ref"]
        self.receipts = self._write_receipts()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_receipts(self) -> dict[str, Path]:
        measurements = {
            "asr": {"transcript": "Árvíztűrő tükörfúrógép"},
            "language": {"language_confidence": 0.99},
            "grammar": {"grammar_score": 0.95, "register_consistent": True},
            "toxicity": {"toxicity_score": 0.01},
            "perceptual": {"perceptual_quality": 0.90},
        }
        paths: dict[str, Path] = {}
        for name, values in measurements.items():
            path = self.base / f"{name}.json"
            write_json(path, {
                "schema": "fa3.hu-aqc-scorer-receipt.v1",
                "scorer": name,
                "measurement_id": f"measurement-{name}",
                "repository_head": repo_head(ROOT),
                "captured_at": utcnow(),
                "current_host_measured": True,
                "synthetic": False,
                "host_attestation_ref": self.host_ref,
                "subject": {
                    "audio_sha256": sha256_file(self.audio),
                    "reference_text_sha256": sha256_file(self.reference),
                },
                "model": {
                    "id": f"model-{name}",
                    "version": "1.0",
                    "sha256": "a" * 64,
                    "license_status": "ADMITTED",
                    "license_evidence_ref": f"license:{name}",
                },
                "measurements": values,
            })
            paths[name] = path
        return paths

    def test_real_scorer_receipts_produce_valid_bundle(self) -> None:
        bundle = produce_bundle(
            ROOT,
            audio=self.audio,
            reference_text_file=self.reference,
            host_attestation=self.host,
            scorer_receipts=self.receipts,
            cloning=False,
        )
        self.assertEqual("fa3.hu-aqc-current-host-input.v2", bundle["schema"])
        self.assertEqual([], validate_bundle(ROOT, audio=self.audio, bundle=bundle))
        self.assertFalse(bundle["producer"]["default_scores_used"])

    def test_unadmitted_scorer_license_fails_closed(self) -> None:
        value = json.loads(self.receipts["perceptual"].read_text())
        value["model"]["license_status"] = "DENIED"
        write_json(self.receipts["perceptual"], value)
        with self.assertRaisesRegex(ValueError, "perceptual scorer license not admitted"):
            produce_bundle(
                ROOT,
                audio=self.audio,
                reference_text_file=self.reference,
                host_attestation=self.host,
                scorer_receipts=self.receipts,
                cloning=False,
            )

    def test_bundle_cannot_override_real_scorer_measurement(self) -> None:
        bundle = produce_bundle(
            ROOT,
            audio=self.audio,
            reference_text_file=self.reference,
            host_attestation=self.host,
            scorer_receipts=self.receipts,
            cloning=False,
        )
        bundle["perceptual_quality"] = 1.0
        self.assertIn(
            "perceptual scorer measurement differs from the producer bundle",
            validate_bundle(ROOT, audio=self.audio, bundle=bundle),
        )

    def test_audio_binding_tamper_fails_closed(self) -> None:
        value = json.loads(self.receipts["asr"].read_text())
        value["subject"]["audio_sha256"] = "b" * 64
        write_json(self.receipts["asr"], value)
        with self.assertRaisesRegex(ValueError, "asr scorer audio binding mismatch"):
            produce_bundle(
                ROOT,
                audio=self.audio,
                reference_text_file=self.reference,
                host_attestation=self.host,
                scorer_receipts=self.receipts,
                cloning=False,
            )

    def test_cloning_requires_speaker_receipt(self) -> None:
        with self.assertRaisesRegex(ValueError, "speaker"):
            produce_bundle(
                ROOT,
                audio=self.audio,
                reference_text_file=self.reference,
                host_attestation=self.host,
                scorer_receipts=self.receipts,
                cloning=True,
            )


if __name__ == "__main__":
    unittest.main()
