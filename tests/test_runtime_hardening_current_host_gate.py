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
from src.fa3_runtime_hardening_evidence import (
    canonical_payload_hash,
    quadlet_security_reasons,
)


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


def evidence_envelope(payload):
    return {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": "FA3-TEST-RUNTIME-HARDENING",
        "evidence_class": "CURRENT_HOST_RUNTIME",
        "subject": {
            "profile_id": "FA3-MEDIA-GPU-ZEROCOPY-001",
            "provider_id": "FA3-PROVIDER-PYNVVIDEOCODEC-001",
            "gate_id": "FA3-GATE-RUNTIME-HARDENING-CURRENT-HOST-001",
        },
        "canonical_context": {
            "architecture_release": "2026-08-23/v3.0.11",
            "release_baseline_id": "FA3-RELEASE-CAPABILITY-BASELINE-001",
            "release_manifest_digest": "sha256:" + "a" * 64,
        },
        "execution_context": {
            "host_attestation_ref": "FA3-HOST-TEST",
            "compute_profile_ref": "INLINE_SHA256:test",
            "workload_resource_envelope_ref": "fixture",
            "hrb_lease_ref": "fixture",
            "diagnostics": {},
        },
        "provenance": {
            "collector_id": "TEST",
            "collector_revision": "1",
            "generated_at": utcnow(),
            "artifact_digests": [],
        },
        "integrity": {"payload_sha256": canonical_payload_hash(payload)},
        "result": {
            "status": "PASS",
            "scope": "COMPONENT_CURRENT_HOST_RUNTIME",
            "claims": [
                "CURRENT_HOST_GPU_ZERO_HOST_ROUND_TRIP_PASS",
                "CURRENT_HOST_PCIE_COPY_BUDGET_PASS",
            ],
            "non_claims": ["GLOBAL_FA3_PROMOTION", "FULL_PIPELINE_TRUE_ZERO_COPY"],
        },
        "payload_schema_id": "fa3.media-gpu-zerocopy-current-host.payload.v2",
        "payload": payload,
        "promotion_authority": False,
    }


def media_receipt():
    receipt = base(
        "fa3.media-gpu-zerocopy-current-host-receipt.v1",
        "MEDIA_GPU_ZERO_HOST_ROUND_TRIP",
    )
    payload = {
        "schema": "fa3.media-gpu-zerocopy-current-host.payload.v2",
        "resource_admission_evidence_id": "FA3-RESOURCE-TEST",
        "gpu_uuid": "GPU-test",
        "pci_bdf": "0000:01:00.0",
        "pynvvideocodec_module_sha256": "a" * 64,
        "dlpack_pointer_identity": True,
        "frame_copy_trace_sha256": "b" * 64,
        "pcie_copy_budget": {
            "max_tx_kb_s": 1000,
            "max_rx_kb_s": 1000,
            "budget_kb_s": 100000,
            "sample_count": 25,
            "sampling_interval_seconds": 0.02,
        },
        "claim_semantics": "ZERO_HOST_FRAME_ROUND_TRIP_DURING_NEURAL_SEGMENT",
        "pcie_copy_budget_is_zero_copy_proof": False,
    }
    receipt.update({
        "hrb_binding": {
            "status": "PASS",
            "resource_admission_evidence_id": "FA3-RESOURCE-TEST",
            "broker_validation": True,
            "gpu_uuid": "GPU-test",
            "pci_bdf": "0000:01:00.0",
            "gpu_index": 0,
        },
        "pynvvideocodec": {
            "status": "PASS",
            "version": "2.2.3",
            "device_memory_decode": True,
            "module_sha256": "a" * 64,
        },
        "dlpack": {
            "status": "PASS",
            "cuda_device_type": True,
            "pointer_identity": True,
            "torch_tensor_is_cuda": True,
            "torch_cuda_device_match": True,
        },
        "copy_telemetry": {
            "present": True,
            "status": "PASS",
            "scope": "NEURAL_SEGMENT_AFTER_DEVICE_MEMORY_DECODE",
            "semantics": "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF",
            "gpu_uuid": "GPU-test",
            "pci_bdf": "0000:01:00.0",
            "sampling_interval_seconds": 0.02,
            "sample_count": 25,
            "max_tx_kb_s": 1000,
            "max_rx_kb_s": 1000,
            "budget_kb_s": 100000,
            "budget_ratio": 0.05,
            "capacity_source": "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH",
        },
        "frame_copy_trace": {
            "schema": "fa3.cuda-copy-trace.v1",
            "status": "PASS",
            "collector": {"kind": "CUPTI", "version": "test"},
            "gpu_uuid": "GPU-test",
            "pci_bdf": "0000:01:00.0",
            "neural_segment": {
                "frame_count": 32,
                "host_to_device_frame_copy_count": 0,
                "device_to_host_frame_copy_count": 0,
                "host_frame_round_trips": 0,
                "dlpack_shared_gpu_memory": True,
            },
            "full_pipeline_zero_copy_claim": False,
            "full_pipeline_zero_copy_proven": False,
        },
        "evidence_payload": payload,
        "evidence_envelope": evidence_envelope(payload),
        "full_pipeline_zero_copy_claim": False,
    })
    return receipt


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

    def test_runtime_sandbox_requires_installed_quadlet_and_actual_runsc(self):
        receipt = base(
            "fa3.runtime-isolation-sandbox-current-host-receipt.v1",
            "RUNTIME_ISOLATION_AGENT_SANDBOX",
        )
        receipt.update({
            "cgroup_v2": {"present": True},
            "quadlet": {
                "status": "PASS",
                "installed_instance": True,
                "security_findings": [],
                "image_digest_pinned": True,
            },
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
                "production_oci_isolation_status": "PASS",
                "actual_runtime_runsc": True,
                "host_fs_default_exposure": False,
                "network_default_deny_verified": True,
                "explicit_mount_allowlist_verified": True,
                "ephemeral_overlay_verified": True,
                "gpu_projection_required": False,
                "nvproxy_supported_driver": True,
                "unsupported_driver_override": False,
            },
        })
        ok, reasons = validate_runtime_sandbox_receipt(receipt, root=ROOT)
        self.assertTrue(ok, reasons)
        bad = copy.deepcopy(receipt)
        bad["gvisor"]["actual_runtime_runsc"] = False
        self.assertFalse(validate_runtime_sandbox_receipt(bad, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["quadlet"]["installed_instance"] = False
        self.assertFalse(validate_runtime_sandbox_receipt(bad, root=ROOT)[0])
        bad = copy.deepcopy(receipt)
        bad["gvisor"]["gpu_projection_required"] = True
        bad["gvisor"]["nvproxy_supported_driver"] = False
        self.assertFalse(validate_runtime_sandbox_receipt(bad, root=ROOT)[0])

    def test_media_zero_host_round_trip_requires_trace_budget_and_envelope(self):
        receipt = media_receipt()
        ok, reasons = validate_media_zero_receipt(receipt, root=ROOT)
        self.assertTrue(ok, reasons)

        bad = copy.deepcopy(receipt)
        bad["dlpack"]["pointer_identity"] = False
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])

        bad = copy.deepcopy(receipt)
        bad["frame_copy_trace"]["neural_segment"]["device_to_host_frame_copy_count"] = 1
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])

        bad = copy.deepcopy(receipt)
        bad["copy_telemetry"]["semantics"] = "ZERO_COPY_PROOF"
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])

        bad = copy.deepcopy(receipt)
        bad["copy_telemetry"]["sampling_interval_seconds"] = 0.5
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])

        bad = copy.deepcopy(receipt)
        bad["evidence_payload"]["gpu_uuid"] = "GPU-tampered"
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])

        bad = copy.deepcopy(receipt)
        bad["full_pipeline_zero_copy_claim"] = True
        self.assertFalse(validate_media_zero_receipt(bad, root=ROOT)[0])

    def test_reference_quadlet_template_is_hardened_but_non_runnable(self):
        path = ROOT / "deployment/quadlet/fa3-agent-sandbox.container.in"
        text = path.read_text(encoding="utf-8")
        self.assertEqual(quadlet_security_reasons(text, allow_image_placeholder=True), [])
        self.assertTrue(quadlet_security_reasons(text))

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
