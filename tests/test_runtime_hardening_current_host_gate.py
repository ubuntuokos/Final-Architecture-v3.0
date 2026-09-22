import copy
import tempfile
import unittest
from pathlib import Path

from src.fa3_runtime_hardening_current_host import (
    repo_head,
    utcnow,
    validate_hu_aqc_receipt,
    validate_media_residency_receipt,
    validate_runtime_sandbox_receipt,
    validate_shadow_receipt,
)
from src.fa3_runtime_hardening_current_host_gate import gate
from src.fa3_resource_evidence_normalization_gate import _canonical_payload_hash


ROOT = Path(__file__).resolve().parents[1]


def envelope(surface, payload=None):
    payload = payload or {"surface": surface, "test": True}
    return {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": "FA3-TEST-" + surface,
        "evidence_class": "CURRENT_HOST_RUNTIME",
        "subject": {
            "profile_id": "FA3-TEST",
            "provider_id": None,
            "gate_id": "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001",
        },
        "canonical_context": {
            "architecture_release": "2026-08-23/v3.0.11",
            "release_baseline_id": "FA3-RELEASE-CAPABILITY-BASELINE-001",
            "release_manifest_digest": "sha256:" + "a" * 64,
        },
        "execution_context": {
            "host_attestation_ref": "FA3-HOST-TEST",
            "compute_profile_ref": None,
            "workload_resource_envelope_ref": None,
            "hrb_lease_ref": None,
            "diagnostics": {},
        },
        "provenance": {
            "collector_id": "TEST",
            "collector_revision": "1",
            "generated_at": "2026-09-19T00:00:00Z",
            "artifact_digests": [],
        },
        "integrity": {"payload_sha256": _canonical_payload_hash(payload)},
        "result": {
            "status": "PASS",
            "scope": surface,
            "claims": ["TEST_PASS"],
            "non_claims": ["GLOBAL_FA3_PROMOTION"],
        },
        "payload_schema_id": "fa3.test.payload.v1",
        "payload": payload,
        "promotion_authority": False,
    }


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
        self.assertEqual(report["blocking_findings"], 3)
        self.assertEqual(report["surfaces"]["media_accelerator_memory_residency"]["status"], "NOT_APPLICABLE")

    def test_media_evidence_is_required_only_when_accelerator_residency_is_claimed(self):
        with tempfile.TemporaryDirectory() as td:
            report = gate(
                ROOT,
                require_evidence=True,
                require_media_claim=True,
                receipt_dir=Path(td),
            )
        self.assertEqual(report["result"], "FAIL")
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
                "runtime_inspect_runsc": False,
                "gpu_projection_required": False,
                "nvproxy_supported_driver": True,
                "unsupported_driver_override": False,
            },
            "quadlet": {
                "status": "PASS",
                "network_none": True,
                "read_only": True,
                "no_new_privileges": True,
                "drop_capability_all": True,
                "pull_never": True,
                "image_digest_pinned": True,
                "runtime_runsc": True,
                "forbidden_host_mounts_present": False,
            },
        })
        receipt["evidence_envelope"] = envelope("RUNTIME_ISOLATION_AGENT_SANDBOX")
        ok, reasons = validate_runtime_sandbox_receipt(receipt, root=ROOT)
        self.assertFalse(ok)
        self.assertTrue(any("gVisor" in reason for reason in reasons))
        receipt["gvisor"].update({
            "production_oci_isolation_status": "PASS",
            "host_fs_default_exposure": False,
            "network_default_deny_verified": True,
            "explicit_mount_allowlist_verified": True,
            "ephemeral_overlay_verified": True,
            "runtime_inspect_runsc": True,
            "gpu_projection_required": False,
            "nvproxy_supported_driver": True,
            "unsupported_driver_override": False,
        })
        ok, reasons = validate_runtime_sandbox_receipt(receipt, root=ROOT)
        self.assertTrue(ok, reasons)

    def test_media_residency_requires_provider_proof_and_never_overclaims_full_pipeline(self):
        receipt = base(
            "fa3.media-accelerator-residency-current-host-receipt.v1",
            "MEDIA_ACCELERATOR_MEMORY_RESIDENCY",
        )
        receipt.update({
            "provider_id": "FA3-PROVIDER-PYNVVIDEOCODEC-001",
            "hrb_binding": {
                "status": "PASS",
                "stable_accelerator_id": "GPU-test",
                "provider_binding": "FA3-PROVIDER-PYNVVIDEOCODEC-001",
            },
            "pynvvideocodec": {
                "status": "PASS", "version": "2.2.3", "device_memory_decode": True,
                "module_sha256": "a" * 64,
            },
            "memory_residency": {
                "status": "PASS",
                "provider_memory_domain": "CUDA_DEVICE",
                "shared_buffer_identity": True,
                "host_frame_round_trips": 0,
            },
            "copy_telemetry": {
                "present": True,
                "scope": "NEURAL_SEGMENT_AFTER_DEVICE_MEMORY_DECODE",
                "semantics": "ADVISORY_TRANSFER_TELEMETRY_NOT_ZERO_COPY_PROOF",
                "capacity_source": "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH",
                "sampling_interval_seconds": 0.02,
                "max_rx_kb_s": 1000.0,
                "max_tx_kb_s": 2000.0,
                "samples": [{"rx_kb_s": 1000.0, "tx_kb_s": 2000.0}] * 10,
            },
            "frame_copy_trace": {
                "schema": "fa3.accelerator-copy-trace.v1",
                "status": "PASS",
                "collector": {"kind": "CUPTI", "version": "test"},
                "neural_segment": {
                    "frame_count": 8,
                    "host_to_device_frame_copy_count": 0,
                    "device_to_host_frame_copy_count": 0,
                    "host_frame_round_trips": 0,
                    "shared_accelerator_memory": True,
                },
            },
            "classification": "ZERO_COPY_PROVEN",
            "full_pipeline_zero_copy_claim": False,
        })
        receipt["evidence_envelope"] = envelope("MEDIA_ACCELERATOR_MEMORY_RESIDENCY")
        ok, reasons = validate_media_residency_receipt(receipt, root=ROOT)
        self.assertTrue(ok, reasons)
        bad = copy.deepcopy(receipt)
        bad["memory_residency"]["shared_buffer_identity"] = False
        self.assertFalse(validate_media_residency_receipt(bad, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["full_pipeline_zero_copy_claim"] = True
        self.assertFalse(validate_media_residency_receipt(bad, root=ROOT)[0])

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
