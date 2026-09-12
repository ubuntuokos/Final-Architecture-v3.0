from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fa3_human_motion_current_host import GEM_REV, SOMA_REV, EVIDENCE_LEVEL, CONFORMANCE_ID, RECEIPT_SCHEMA, validate_receipt
from fa3_human_motion_current_host_gate import gate


def receipt() -> dict:
    now = datetime.now(timezone.utc)
    sha = "a" * 64
    return {
        "schema": RECEIPT_SCHEMA,
        "conformance_id": CONFORMANCE_ID,
        "status": "PASS",
        "evidence_level": EVIDENCE_LEVEL,
        "real_current_host_execution": True,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
        "global_promotion_claim": False,
        "sources": {"gem_x": {"revision": GEM_REV, "clean": True}, "soma_x": {"revision": SOMA_REV, "clean": True}},
        "checkpoint": {"sha256": sha, "admission": {"artifact_sha256": sha, "admitted": True}},
        "model_license": {"license_name": "NVIDIA Open Model License Agreement", "accepted": True, "artifact_sha256": sha},
        "soma_assets": {"admitted": True, "tree_sha256": "b" * 64},
        "smplx": {"license_receipt_valid": True, "model_assets_present": True, "asset_sha256": "c" * 64},
        "hrb": {
            "valid": True,
            "authority_id": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "device_uuid": "GPU-abc",
            "pci_bdf": "0000:05:00.0",
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "static_runtime_ordinal_as_identity": False,
            "compute_role_admitted": True,
            "accelerator_role": "COMPUTE",
            "compute_eligible": True,
            "display_role": False,
        },
        "gpu": {"uuid": "GPU-abc", "pci_bdf": "0000:05:00.0", "display_active": False, "numa_node": 0},
        "hardware_conformance": {
            "hrb_compute_role_admitted": True,
            "non_display_gpu": True,
            "uuid_bdf_live_identity": True,
            "numa_locality_evidence": True,
            "cuda_execution": True,
            "no_fallback": True,
            "topology_revalidated_at_admission": True,
            "cpu_memory_accelerator_one_placement": True,
            "accelerator_numa_node": 0,
            "compute_cpu_set": [0, 1, 2, 3],
            "memory_numa_nodes": [0],
            "locality_mode": "NUMA_LOCAL",
        },
        "input_video": {"sha256": "d" * 64, "frames": 12, "duration_seconds": 0.4, "admission": {"artifact_sha256": "d" * 64, "synthetic": False, "rights_or_consent_confirmed": True}},
        "runtime_policy": {"network_fetch_disabled": True, "automatic_model_download_observed": False},
        "execution": {"requested_backend": "cuda", "observed_cuda": True, "silent_cpu_fallback_observed": False, "cross_accelerator_fallback_observed": False, "gpu_uuid": "GPU-abc", "cuda_device_count_inside_sandbox": 1},
        "keypoints_2d": {"joint_count": 77, "frame_count": 12, "finite": True},
        "motion": {"finite": True, "nan_inf_count": 0, "frame_count": 12, "timestamps_monotonic": True, "world_space_present": True, "dynamic_camera_trajectory_present": True, "continuity_max_step_m": 0.25, "foot_sliding_rms_m": 0.02, "hand_jitter_rms_m": 0.01},
        "interchange": {"soma_npz_valid": True, "soma_npz_joint_count": 77, "soma_npz_sha256": "e" * 64, "smplx_roundtrip_pass": True, "usd_export_pass": True, "usd_sha256": "f" * 64},
        "dcc_smoke": {"status": "PASS", "application": "Bforartists", "imported_object_count": 1}
    }


class HumanMotionCurrentHostTests(unittest.TestCase):
    def test_reference_receipt_contract_passes(self):
        self.assertEqual([], validate_receipt(receipt()))

    def test_missing_real_receipt_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            report = gate(Path(td))
            self.assertEqual("FAIL", report["result"])

    def test_hosted_or_synthetic_evidence_cannot_promote(self):
        r = receipt(); r["real_current_host_execution"] = False
        self.assertTrue(any(x["code"] == "HM-HOST-002" for x in validate_receipt(r)))
        r = receipt(); r["fixture_semantics"] = "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "r.json"; p.write_text(json.dumps(r), encoding="utf-8")
            self.assertEqual("FAIL", gate(Path(td), p)["result"])

    def test_wrong_source_revision_fails(self):
        r = receipt(); r["sources"]["gem_x"]["revision"] = "0" * 40
        self.assertTrue(any(x["code"] == "HM-HOST-004" for x in validate_receipt(r)))

    def test_checkpoint_and_model_license_are_separate_and_bound(self):
        r = receipt(); r["model_license"]["artifact_sha256"] = "9" * 64
        self.assertTrue(any(x["code"] == "HM-HOST-008" for x in validate_receipt(r)))

    def test_hrb_compute_role_is_mandatory(self):
        r = receipt(); r["hrb"]["compute_role_admitted"] = False
        self.assertTrue(any(x["code"] == "HM-HOST-011" for x in validate_receipt(r)))
        r = receipt(); r["hrb"]["accelerator_role"] = "DISPLAY"
        self.assertTrue(any(x["code"] == "HM-HOST-011" for x in validate_receipt(r)))

    def test_display_gpu_is_rejected(self):
        r = receipt(); r["gpu"]["display_active"] = True; r["hardware_conformance"]["non_display_gpu"] = False
        self.assertTrue(any(x["code"] == "HM-HOST-012" for x in validate_receipt(r)))

    def test_uuid_bdf_live_identity_is_mandatory(self):
        r = receipt(); r["gpu"]["pci_bdf"] = "0000:a5:00.0"
        self.assertTrue(any(x["code"] == "HM-HOST-013" for x in validate_receipt(r)))
        r = receipt(); r["hrb"]["static_runtime_ordinal_as_identity"] = True
        self.assertTrue(any(x["code"] == "HM-HOST-013" for x in validate_receipt(r)))

    def test_expired_hrb_fails(self):
        r = receipt(); r["hrb"]["expires_at"] = "2020-01-01T00:00:00Z"
        self.assertTrue(any(x["code"] == "HM-HOST-014" for x in validate_receipt(r)))

    def test_numa_locality_evidence_is_mandatory(self):
        r = receipt(); r["hardware_conformance"]["numa_locality_evidence"] = False
        self.assertTrue(any(x["code"] == "HM-HOST-015" for x in validate_receipt(r)))
        r = receipt(); r["hardware_conformance"]["memory_numa_nodes"] = [1]
        self.assertTrue(any(x["code"] == "HM-HOST-015" for x in validate_receipt(r)))
        r = receipt(); r["hardware_conformance"]["compute_cpu_set"] = []
        self.assertTrue(any(x["code"] == "HM-HOST-015" for x in validate_receipt(r)))

    def test_video_must_be_real_and_rights_admitted(self):
        r = receipt(); r["input_video"]["admission"]["synthetic"] = True
        self.assertTrue(any(x["code"] == "HM-HOST-016" for x in validate_receipt(r)))

    def test_network_fetch_fails(self):
        r = receipt(); r["runtime_policy"]["network_fetch_disabled"] = False
        self.assertTrue(any(x["code"] == "HM-HOST-017" for x in validate_receipt(r)))

    def test_cuda_execution_is_mandatory(self):
        r = receipt(); r["execution"]["observed_cuda"] = False
        self.assertTrue(any(x["code"] == "HM-HOST-018" for x in validate_receipt(r)))
        r = receipt(); r["execution"]["cuda_device_count_inside_sandbox"] = 2
        self.assertTrue(any(x["code"] == "HM-HOST-018" for x in validate_receipt(r)))

    def test_cpu_and_cross_accelerator_fallback_fail(self):
        r = receipt(); r["execution"]["silent_cpu_fallback_observed"] = True
        self.assertTrue(any(x["code"] == "HM-HOST-019" for x in validate_receipt(r)))
        r = receipt(); r["execution"]["cross_accelerator_fallback_observed"] = True
        self.assertTrue(any(x["code"] == "HM-HOST-019" for x in validate_receipt(r)))

    def test_quality_and_interchange_fail_closed(self):
        r = receipt(); r["motion"]["nan_inf_count"] = 1; r["interchange"]["usd_export_pass"] = False
        codes = {x["code"] for x in validate_receipt(r)}
        self.assertIn("HM-HOST-021", codes); self.assertIn("HM-HOST-027", codes)

    def test_dcc_import_required(self):
        r = receipt(); r["dcc_smoke"]["imported_object_count"] = 0
        self.assertTrue(any(x["code"] == "HM-HOST-028" for x in validate_receipt(r)))


if __name__ == "__main__":
    unittest.main()
