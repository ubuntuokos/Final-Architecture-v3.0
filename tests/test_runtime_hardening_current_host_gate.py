from __future__ import annotations

import copy
import json
from pathlib import Path

from src.fa3_runtime_hardening_current_host import (
    CAPABILITY_COUNT,
    frame_trace_findings,
    payload_sha256,
    pcie_copy_budget_findings,
    quadlet_security_findings,
    validate_current_host_envelope,
)
from src.fa3_runtime_hardening_current_host_gate import gate

ROOT = Path(__file__).resolve().parents[1]

GOOD_QUADLET = """[Container]
Image=ghcr.io/example/fa3-agent@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
ContainerName=fa3-agent-sandbox
Network=none
ReadOnly=true
NoNewPrivileges=true
DropCapability=all
Pull=never
GlobalArgs=--runtime=runsc
"""


def good_frame_trace():
    return {
        "schema": "fa3.cuda-copy-trace.v1",
        "status": "PASS",
        "collector": {"kind": "CUPTI", "version": "test"},
        "gpu_uuid": "GPU-test",
        "pci_bdf": "0000:65:00.0",
        "neural_segment": {
            "frame_count": 32,
            "host_to_device_frame_copy_count": 0,
            "device_to_host_frame_copy_count": 0,
            "host_frame_round_trips": 0,
            "dlpack_shared_gpu_memory": True,
        },
        "full_pipeline_zero_copy_claim": False,
        "full_pipeline_zero_copy_proven": False,
    }


def good_pcie():
    return {
        "status": "PASS",
        "semantics": "SUPPORTING_COPY_BUDGET_NOT_ZERO_COPY_PROOF",
        "gpu_uuid": "GPU-test",
        "pci_bdf": "0000:65:00.0",
        "sampling_interval_seconds": 0.02,
        "sample_count": 50,
        "max_tx_kb_s": 1000,
        "max_rx_kb_s": 2000,
        "budget_kb_s": 1_000_000,
        "budget_ratio": 0.05,
        "capacity_source": "LIVE_NEGOTIATED_PCIE_LINK_GEN_WIDTH",
    }


def modeled_envelope(*, synthetic: bool = False):
    payload = {
        "schema": "fa3.runtime-hardening-current-host.payload.v1",
        "real_current_host_execution": not synthetic,
        "resource_binding": {"gpu_uuid": "GPU-test", "pci_bdf": "0000:65:00.0"},
        "quadlet_sandbox": {"status": "PASS", "findings": []},
        "gvisor_runtime": {
            "status": "PASS",
            "runsc_available": True,
            "runtime_inspect_runsc": True,
            "gpu_projection_required": False,
            "nvproxy_supported_driver": True,
            "unsupported_driver_override": False,
        },
        "pcie_copy_budget": good_pcie(),
        "frame_copy_trace": good_frame_trace(),
        "checks": {
            "CRIT-020-QUADLET-GVISOR-SANDBOX": "PASS",
            "CRIT-021-AGENT-BOUNDARY": "PASS",
            "CRIT-022A-PCIE-COPY-BUDGET": "PASS",
            "CRIT-022B-GPU-FRAME-ZERO-HOST-ROUND-TRIP": "PASS",
        },
        "invariants": {
            "capability_count": CAPABILITY_COUNT,
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "global_promotion_claim": False,
        },
    }
    if synthetic:
        payload["fixture_semantics"] = "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST"
    return {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": "FA3-RUNTIME-HARDENING-MODELED-TEST",
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
            "generated_at": "2026-09-19T00:00:00Z",
            "artifact_digests": [],
        },
        "integrity": {"payload_sha256": payload_sha256(payload)},
        "result": {
            "status": "PASS",
            "scope": "COMPONENT_CURRENT_HOST_RUNTIME_HARDENING",
            "claims": ["CURRENT_HOST_RUNTIME_HARDENING_PASS"],
            "non_claims": [
                "GLOBAL_FA3_PROMOTION",
                "FULL_PIPELINE_TRUE_ZERO_COPY",
                "HOST_HARDWARE_PORTABILITY_REQUIREMENT",
            ],
        },
        "payload_schema_id": "fa3.runtime-hardening-current-host.payload.v1",
        "payload": payload,
        "promotion_authority": False,
    }


def test_quadlet_reference_security_contract():
    assert quadlet_security_findings(GOOD_QUADLET) == []
    assert "QUADLET_NETWORK_NOT_DENY_DEFAULT" in quadlet_security_findings(GOOD_QUADLET.replace("Network=none", "Network=host"))
    assert "QUADLET_IMAGE_NOT_DIGEST_PINNED" in quadlet_security_findings(
        GOOD_QUADLET.replace("@sha256:" + "a" * 64, ":latest")
    )
    assert "QUADLET_GVISOR_RUNSC_NOT_ENFORCED" in quadlet_security_findings(
        GOOD_QUADLET.replace("GlobalArgs=--runtime=runsc\n", "")
    )


def test_pcie_budget_is_supporting_evidence_not_zero_copy_proof():
    assert pcie_copy_budget_findings(good_pcie(), gpu_uuid="GPU-test", pci_bdf="0000:65:00.0") == []
    bad = {**good_pcie(), "semantics": "ZERO_COPY_PROOF"}
    assert "PCIE_COPY_BUDGET_SEMANTICS_INVALID" in pcie_copy_budget_findings(
        bad, gpu_uuid="GPU-test", pci_bdf="0000:65:00.0"
    )


def test_frame_trace_rejects_any_host_frame_copy():
    assert frame_trace_findings(good_frame_trace(), gpu_uuid="GPU-test", pci_bdf="0000:65:00.0") == []
    bad = copy.deepcopy(good_frame_trace())
    bad["neural_segment"]["device_to_host_frame_copy_count"] = 1
    assert "FRAME_TRACE_HOST_FRAME_COPY_OBSERVED" in frame_trace_findings(
        bad, gpu_uuid="GPU-test", pci_bdf="0000:65:00.0"
    )


def test_modeled_current_host_shape_valid_but_synthetic_fixture_is_rejected():
    assert validate_current_host_envelope(modeled_envelope()) == []
    findings = validate_current_host_envelope(modeled_envelope(synthetic=True))
    assert any(x["code"] == "RUNTIME-HARDENING-HOST-006" for x in findings)


def test_current_host_gate_fails_closed_on_synthetic_fixture(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(modeled_envelope(synthetic=True)), encoding="utf-8")
    report = gate(ROOT, receipt)
    assert report["result"] == "BLOCKED"
    assert report["decision"]["exit_code"] == 2
    assert report["decision"]["promotion_effect"] == "COMPONENT_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED"
    assert report["global_promotion_claim"] is False
    assert report["capability_count"] == 143


def test_reference_quadlet_template_is_non_runnable_placeholder():
    path = ROOT / "deployment/quadlet/fa3-agent-sandbox.container.in"
    text = path.read_text(encoding="utf-8")
    assert quadlet_security_findings(text, allow_image_placeholder=True) == []
    assert quadlet_security_findings(text)
