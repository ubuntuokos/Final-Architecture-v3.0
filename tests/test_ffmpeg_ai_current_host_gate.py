from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from fa3_ffmpeg_ai_current_host import (
    HRB_LEASE_SCHEMA,
    build_identity_onnx,
    build_trust_receipt_valid,
    hrb_lease_valid,
    live_hardware_snapshot_valid,
    make_reference_receipt,
    normalize_bdf,
    observed_onnx_provider,
    quality_valid,
    real_media_provenance_valid,
    resolved_runtime_index,
    validate_current_host_receipt,
)
from fa3_ffmpeg_ai_current_host_gate import gate


class FFmpegAICurrentHostTests(unittest.TestCase):
    def test_reference_contract_fixture_passes_validator(self):
        receipt = make_reference_receipt()
        self.assertEqual([], validate_current_host_receipt(receipt))

    def test_gate_rejects_unit_fixture_as_live_production_evidence(self):
        receipt = make_reference_receipt()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "receipt.json"
            path.write_text(json.dumps(receipt))
            report = gate(root, path)
        self.assertEqual("FAIL", report["result"])
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-015" for x in report["findings"]))

    def test_reference_host_model_is_not_admission_identity(self):
        receipt = make_reference_receipt()
        hw = deepcopy(receipt["hardware"])
        hw["machine"] = "Completely Different Qualified Host"
        hw["cpu_models"] = ["Different CPU Family"]
        hw["packages"] = 2
        hw["physical_cores"] = 24
        hw["logical_cpus"] = 48
        hw["numa_domains"] = 2
        hw["physical_cores_per_package"] = {"0": 12, "1": 12}
        self.assertTrue(live_hardware_snapshot_valid(hw))
        receipt["hardware"] = hw
        self.assertEqual([], validate_current_host_receipt(receipt))

    def test_hardware_evidence_must_be_live_and_non_normative(self):
        receipt = make_reference_receipt()
        bad = deepcopy(receipt["hardware"])
        bad["current_host_facts_are_evidence_only"] = False
        self.assertFalse(live_hardware_snapshot_valid(bad))
        bad = deepcopy(receipt["hardware"])
        bad["reference_host_match_required"] = True
        self.assertFalse(live_hardware_snapshot_valid(bad))

    def test_runtime_sources_do_not_hardcode_reference_workstation_identity(self):
        root = Path(__file__).resolve().parents[1]
        runtime_text = "\n".join([
            (root / "src/fa3_ffmpeg_ai_current_host.py").read_text(encoding="utf-8"),
            (root / "evidence/collect-ffmpeg-ai-current-host.py").read_text(encoding="utf-8"),
            (root / "bin/fa3-ffmpeg-ai-current-host.sh").read_text(encoding="utf-8"),
        ])
        for forbidden in ("EXPECTED_MACHINE", "EXPECTED_CPU_TOKEN", "Dell Precision Tower 7910", "E5-2696 v4"):
            self.assertNotIn(forbidden, runtime_text)
        self.assertNotIn('packages"] == 2', runtime_text)
        self.assertNotIn('logical_cpus"] == 88', runtime_text)

    def test_canonical_hrb_accelerator_lease_uuid_bdf_and_expiry_are_required(self):
        receipt = make_reference_receipt()
        lease = receipt["hrb_lease"]
        gpus = receipt["live_gpus"]
        self.assertEqual(HRB_LEASE_SCHEMA, lease["schema"])
        self.assertTrue(hrb_lease_valid(lease, gpus))
        self.assertEqual(3, resolved_runtime_index(lease, gpus))

        bad = deepcopy(lease)
        bad["accelerator_uuid"] = "GPU-other"
        self.assertFalse(hrb_lease_valid(bad, gpus))

        bad = deepcopy(lease)
        bad["placement"]["pci_bus_id"] = "0000:42:00.0"
        self.assertFalse(hrb_lease_valid(bad, gpus))

        bad = deepcopy(lease)
        bad["broker_validation"] = "UNKNOWN"
        self.assertFalse(hrb_lease_valid(bad, gpus))

        bad = deepcopy(lease)
        bad["signature"]["alg"] = "NONE"
        self.assertFalse(hrb_lease_valid(bad, gpus))

    def test_extended_nvidia_pci_domain_normalizes_to_canonical_bdf(self):
        self.assertEqual("0000:05:00.0", normalize_bdf("00000000:05:00.0"))
        self.assertEqual("0000:a5:00.0", normalize_bdf("A5:00.0"))

    def test_silent_cuda_cpu_fallback_is_denied(self):
        self.assertEqual("FALLBACK_CPU", observed_onnx_provider("Failed to enable CUDA. Falling back to CPU"))
        receipt = make_reference_receipt()
        receipt["real_media_neural_e2e"]["observed_provider"] = "FALLBACK_CPU"
        receipt["real_media_neural_e2e"]["silent_cpu_fallback_observed"] = True
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-008" for x in validate_current_host_receipt(receipt)))

    def test_production_input_requires_real_media_provenance(self):
        receipt = make_reference_receipt()
        provenance = receipt["input_media_provenance"]
        media_hash = receipt["input_media"]["sha256"]
        self.assertTrue(real_media_provenance_valid(provenance, media_hash))
        bad = deepcopy(provenance)
        bad["synthetic"] = True
        self.assertFalse(real_media_provenance_valid(bad, media_hash))
        receipt["input_media_provenance"] = bad
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-007" for x in validate_current_host_receipt(receipt)))

    def test_build_trust_binds_ffmpeg_and_ffprobe(self):
        receipt = make_reference_receipt()
        trust = receipt["ffmpeg_build_trust"]
        features = receipt["ffmpeg_feature_manifest"]
        self.assertTrue(build_trust_receipt_valid(trust, features["ffmpeg_binary_sha256"], features["ffprobe_binary_sha256"]))
        bad = deepcopy(trust)
        bad.pop("installed_ffprobe_binary_sha256")
        self.assertFalse(build_trust_receipt_valid(bad, features["ffmpeg_binary_sha256"], features["ffprobe_binary_sha256"]))

    def test_quality_gate_is_fail_closed_and_fixture_scoped(self):
        receipt = make_reference_receipt()
        self.assertTrue(quality_valid(receipt["quality"]))
        bad = deepcopy(receipt["quality"])
        bad["vmaf"] = 79.9
        self.assertFalse(quality_valid(bad))
        bad = deepcopy(receipt["quality"])
        bad["timestamps_monotonic"] = False
        self.assertFalse(quality_valid(bad))
        bad = deepcopy(receipt["quality"])
        bad["fixture_profile_is_evidence_only_not_provider_limit"] = False
        self.assertFalse(quality_valid(bad))

    def test_zero_copy_claim_is_forbidden_for_stable_dnn_baseline(self):
        receipt = make_reference_receipt()
        receipt["copy_boundary_evidence"]["zero_copy_claimed"] = True
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-010" for x in validate_current_host_receipt(receipt)))

    def test_identity_onnx_is_deterministic_and_nonempty(self):
        first = build_identity_onnx(320, 180)
        second = build_identity_onnx(320, 180)
        self.assertEqual(first, second)
        self.assertGreater(len(first), 50)
        self.assertIn(b"Identity", first)
        self.assertIn(b"fa3_ffmpeg_identity_graph", first)

    def test_capability_and_global_promotion_drift_are_denied(self):
        receipt = make_reference_receipt()
        receipt["capability_count_after"] = 144
        receipt["global_promotion_claim"] = True
        self.assertTrue(any(x["code"] == "FFMPEG-AI-HOST-014" for x in validate_current_host_receipt(receipt)))


if __name__ == "__main__":
    unittest.main()
