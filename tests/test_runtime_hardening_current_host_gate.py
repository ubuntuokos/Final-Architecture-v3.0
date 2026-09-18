import copy
import tempfile
import unittest
from pathlib import Path

from src.fa3_runtime_hardening_current_host import (
    repo_head,
    utcnow,
    validate_hu_aqc_receipt,
    validate_media_zero_receipt,
    validate_runtime_sandbox_receipt,
    validate_shadow_receipt,
)
from src.fa3_runtime_hardening_current_host_gate import gate


ROOT = Path(__file__).resolve().parents[1]


def base(schema, surface):
    return {
        "schema": schema,
        "surface": surface,
        "repository_head": repo_head(ROOT),
        "captured_at": utcnow(),
        "synthetic": False,
        "global_promotion_claim": False,
        "result": "PASS",
        "status": "CURRENT_HOST_PASS",
    }


class RuntimeHardeningCurrentHostTests(unittest.TestCase):
    def test_materialization_passes_without_fabricating_current_host_pass(self):
        report = gate(ROOT, require_evidence=False)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["status"], "PENDING_CURRENT_HOST")
        self.assertEqual(report["surface_pass_count"], 0)
        self.assertFalse(report["global_promotion_claim"])

    def test_required_evidence_fails_closed_when_receipts_are_missing(self):
        with tempfile.TemporaryDirectory() as td:
            report = gate(ROOT, require_evidence=True, receipt_dir=Path(td))
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["status"], "PENDING_CURRENT_HOST")
        self.assertEqual(report["blocking_findings"], 4)

    def test_runtime_sandbox_requires_production_gvisor_proof_not_smoke_only(self):
        receipt = base(
            "fa3.runtime-isolation-sandbox-current-host-receipt.v1",
            "RUNTIME_ISOLATION_AGENT_SANDBOX",
        )
        receipt.update({
            "cgroup_v2": {"present": True},
            "rootless_oci": {
                "status": "PASS", "rootless": True, "network_none": True,
                "read_only": True, "cap_drop_all": True, "pull_never": True,
                "real_execution": True,
            },
            "wasmtime_wasi": {
                "status": "PASS", "real_execution": True,
                "explicit_preopens": [], "network_lease_provided": False,
            },
            "gvisor": {
                "compatibility_smoke_status": "PASS",
                "production_oci_isolation_status": "PENDING",
                "host_fs_default_exposure": None,
                "network_default_deny_verified": False,
                "explicit_mount_allowlist_verified": False,
                "ephemeral_overlay_verified": False,
            },
        })
        ok, reasons = validate_runtime_sandbox_receipt(receipt, root=ROOT)
        self.assertFalse(ok)
        self.assertTrue(any("gVisor" in reason for reason in reasons))
        receipt["gvisor"].update({
            "production_oci_isolation_status": "PASS",
            "host_fs_default_exposure": False,
            "network_default_deny_verified": True,
            "explicit_mount_allowlist_verified": True,
            "ephemeral_overlay_verified": True,
        })
        ok, reasons = validate_runtime_sandbox_receipt(receipt, root=ROOT)
        self.assertTrue(ok, reasons)

    def test_media_zero_copy_requires_pointer_identity_and_never_overclaims_full_pipeline(self):
        receipt = base(
            "fa3.media-gpu-zerocopy-current-host-receipt.v1",
            "MEDIA_GPU_ZERO_HOST_ROUND_TRIP",
        )
        receipt.update({
            "hrb_binding": {"status": "PASS", "gpu_uuid": "GPU-test", "pci_bdf": "0000:01:00.0", "gpu_index": 0},
            "pynvvideocodec": {
                "status": "PASS", "version": "2.2.3", "device_memory_decode": True,
                "module_sha256": "a" * 64,
            },
            "dlpack": {
                "status": "PASS", "cuda_device_type": True, "pointer_identity": True,
                "torch_tensor_is_cuda": True, "torch_cuda_device_match": True,
                "host_frame_round_trips": 0,
            },
            "copy_telemetry": {
                "present": True, "scope": "NEURAL_SEGMENT_AFTER_DEVICE_MEMORY_DECODE",
                "samples": [{"rx_mb_s": 0.0, "tx_mb_s": 0.0}],
            },
            "full_pipeline_zero_copy_claim": False,
        })
        ok, reasons = validate_media_zero_receipt(receipt, root=ROOT)
        self.assertTrue(ok, reasons)
        bad = copy.deepcopy(receipt)
        bad["dlpack"]["pointer_identity"] = False
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["full_pipeline_zero_copy_claim"] = True
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])

    def test_hu_aqc_rejects_single_metric_or_failed_dimension(self):
        receipt = base("fa3.hu-aqc-current-host-receipt.v1", "HU_AQC")
        receipt.update({
            "locale": "hu-HU",
            "audio_sha256": "b" * 64,
            "signal_metrics_recomputed_locally": True,
            "asr_error_rates_recomputed_locally": True,
            "scorer_provenance_admitted": True,
            "aqc": {
                "passed": True,
                "single_metric_authority": False,
                "dimensions": {
                    "text_language": True,
                    "grammar_style": True,
                    "toxicity_policy": True,
                    "intelligibility": True,
                    "naturalness": True,
                    "signal_integrity": True,
                    "speaker_identity": True,
                },
            },
        })
        self.assertTrue(validate_hu_aqc_receipt(receipt, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["aqc"]["single_metric_authority"] = True
        self.assertFalse(validate_hu_aqc_receipt(bad, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["aqc"]["dimensions"]["intelligibility"] = False
        self.assertFalse(validate_hu_aqc_receipt(bad, root=ROOT)[0])

    def test_shadow_cannot_be_authoritative_or_promoting(self):
        receipt = base("fa3.promotion-shadow-current-host-receipt.v1", "PROMOTION_SHADOW")
        receipt.update({
            "sandbox_dependency_status": "PASS",
            "execution_allowed": True,
            "authoritative_output": False,
            "external_side_effects": False,
            "output_quarantined": True,
            "workspace_destroyed": True,
            "promotion_authority": False,
            "may_assign_promoted": False,
        })
        self.assertTrue(validate_shadow_receipt(receipt, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["authoritative_output"] = True
        self.assertFalse(validate_shadow_receipt(bad, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["promotion_authority"] = True
        self.assertFalse(validate_shadow_receipt(bad, root=ROOT)[0])

    def test_synthetic_component_receipt_never_qualifies(self):
        receipt = base("fa3.promotion-shadow-current-host-receipt.v1", "PROMOTION_SHADOW")
        receipt.update({
            "sandbox_dependency_status": "PASS",
            "execution_allowed": True,
            "authoritative_output": False,
            "external_side_effects": False,
            "output_quarantined": True,
            "workspace_destroyed": True,
            "promotion_authority": False,
            "may_assign_promoted": False,
            "synthetic": True,
        })
        self.assertFalse(validate_shadow_receipt(receipt, root=ROOT)[0])


if __name__ == "__main__":
    unittest.main()
