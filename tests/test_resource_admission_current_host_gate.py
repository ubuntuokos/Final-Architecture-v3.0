from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_resource_admission_current_host_gate import gate, validate_receipt  # noqa: E402
from fa3_resource_evidence_normalization_gate import _canonical_payload_hash  # noqa: E402


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def refresh_payload_hash(receipt: dict) -> None:
    receipt["integrity"]["payload_sha256"] = _canonical_payload_hash(receipt["payload"])


def base_envelope(payload: dict) -> dict:
    return {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": "TEST-CURRENT-HOST-RESOURCE-ADMISSION",
        "evidence_class": "CURRENT_HOST_ADMISSION",
        "subject": {
            "profile_id": "FA3-RESOURCE-ADMISSION-CONTRACTS-001",
            "provider_id": None,
            "gate_id": "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001",
        },
        "canonical_context": {
            "architecture_release": "2026-08-23/v3.0.11",
            "release_baseline_id": "FA3-RELEASE-CAPABILITY-BASELINE-001",
            "release_manifest_digest": "sha256:test",
        },
        "execution_context": {
            "host_attestation_ref": "FA3-HOST-TEST",
            "compute_profile_ref": "INLINE_SHA256:test",
            "workload_resource_envelope_ref": "fixture",
            "hrb_lease_ref": "fixture",
            "diagnostics": {},
        },
        "provenance": {
            "collector_id": "TEST-FIXTURE-NOT-EVIDENCE",
            "collector_revision": "2.0.0",
            "generated_at": "2026-09-16T00:00:00Z",
            "artifact_digests": [],
        },
        "integrity": {"payload_sha256": _canonical_payload_hash(payload)},
        "result": {
            "status": "PASS",
            "scope": "COMPONENT_CURRENT_HOST_RESOURCE_ADMISSION",
            "claims": ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"],
            "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E", "END_TO_END_ZERO_COPY"],
        },
        "payload_schema_id": "fa3.resource-admission-current-host.payload.v1",
        "payload": payload,
    }


def gpu_fixture() -> dict:
    attestation = {
        "schema": "fa3.host-attestation.v1",
        "host_attestation_id": "FA3-HOST-TEST",
        "host": "test-host",
        "secret_collection": "PROHIBITED",
        "accelerators": [{
            "uuid": "GPU-TEST",
            "pci_bdf": "0000:01:00.0",
            "vendor": "NVIDIA",
            "memory_total_bytes": 8 * 1024**3,
            "cuda_compute_capability": 8.6,
        }],
    }
    attestation_sha = canonical_sha256(attestation)
    payload = {
        "schema": "fa3.resource-admission-current-host.payload.v1",
        "host_attestation": attestation,
        "host_attestation_sha256": attestation_sha,
        "compute_profile": {
            "schema": "fa3.compute-profile.v1",
            "host_attestation_sha256": attestation_sha,
            "metrics": {
                "gpu.physical_vram_gib": 8.0,
                "gpu.lease_memory_gib": 4.0,
                "gpu.vram_gib": 4.0,
                "gpu.vendor": "NVIDIA",
                "gpu.cuda_compute_capability": 8.6,
                "gpu.device_uuid": "GPU-TEST",
                "gpu.pci_bdf": "0000:01:00.0",
                "cpu.physical_cores": 16,
            },
            "diagnostic_aggregates": {},
        },
        "workload_resource_envelope": {
            "schema": "fa3.workload-resource-envelope.v1",
            "workload_id": "fixture",
            "requirements": [{"metric": "gpu.vram_gib", "operator": ">=", "value": 4}],
        },
        "workload_resource_envelope_sha256": "b" * 64,
        "requested_resource_classes": ["accelerator"],
        "accelerator_required": True,
        "hrb_authorization": {
            "authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "authorization_id": "lease-test",
            "status": "VALID",
            "workload_id": "fixture",
            "workload_envelope_sha256": "b" * 64,
            "requested_resource_classes": ["accelerator"],
            "accelerator_required": True,
            "host": "test-host",
            "issued_epoch": int(time.time()) - 5,
            "expires_epoch": 9999999999,
            "broker_validation": True,
            "source": "ACCELERATOR_EXECUTION_LEASE",
        },
        "hrb_lease_identity": {
            "schema": "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1",
            "lease_id": "lease-test",
            "issuer": "FA3-HOST-RESOURCE-BROKER-001",
            "status": "ACTIVE",
            "host": "test-host",
            "accelerator_uuid": "GPU-TEST",
            "pci_bus_id": "00000000:01:00.0",
            "numa_node": 0,
            "memory_max_bytes": 4 * 1024**3,
            "purpose": "fixture",
            "issued_epoch": int(time.time()) - 5,
            "expires_epoch": 9999999999,
            "lease_file_sha256": "c" * 64,
            "broker_validation": True,
        },
        "admission": {
            "schema_id": "FA3-ENFORCEMENT-RESULT-001",
            "result": "PASS",
            "decision": {"reason_code": "RESOURCE_ENVELOPE_AND_HRB_PASS", "exit_code": 0},
        },
        "errors": [],
        "cross_metric_compensation": False,
        "cu_tu_admission_authority": False,
    }
    return base_envelope(payload)


def cpu_fixture() -> dict:
    attestation = {
        "schema": "fa3.host-attestation.v1",
        "host_attestation_id": "FA3-HOST-CPU",
        "host": "cpu-host",
        "secret_collection": "PROHIBITED",
        "accelerators": [],
    }
    attestation_sha = canonical_sha256(attestation)
    payload = {
        "schema": "fa3.resource-admission-current-host.payload.v1",
        "host_attestation": attestation,
        "host_attestation_sha256": attestation_sha,
        "compute_profile": {
            "schema": "fa3.compute-profile.v1",
            "host_attestation_sha256": attestation_sha,
            "metrics": {"cpu.physical_cores": 16, "memory.total_gib": 64.0},
            "diagnostic_aggregates": {},
        },
        "workload_resource_envelope": {
            "schema": "fa3.workload-resource-envelope.v1",
            "workload_id": "cpu-fixture",
            "requirements": [
                {"metric": "cpu.physical_cores", "operator": ">=", "value": 8},
                {"metric": "memory.total_gib", "operator": ">=", "value": 16},
            ],
        },
        "workload_resource_envelope_sha256": "d" * 64,
        "requested_resource_classes": ["cpu", "memory"],
        "accelerator_required": False,
        "hrb_authorization": {
            "schema": "fa3.hrb-admission-authorization.v1",
            "authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "authorization_id": "hrb-auth-cpu-fixture",
            "status": "VALID",
            "workload_id": "cpu-fixture",
            "workload_envelope_sha256": "d" * 64,
            "requested_resource_classes": ["cpu", "memory"],
            "accelerator_required": False,
            "host": "cpu-host",
            "issued_epoch": int(time.time()) - 5,
            "expires_epoch": 9999999999,
            "broker_validation": True,
            "source": "ADMISSION_AUTHORIZATION",
        },
        "hrb_lease_identity": {},
        "admission": {
            "schema_id": "FA3-ENFORCEMENT-RESULT-001",
            "result": "PASS",
            "decision": {"reason_code": "RESOURCE_ENVELOPE_AND_HRB_PASS", "exit_code": 0},
        },
        "errors": [],
        "cross_metric_compensation": False,
        "cu_tu_admission_authority": False,
    }
    return base_envelope(payload)


class ResourceAdmissionCurrentHostTests(unittest.TestCase):
    def test_accelerator_fixture_passes(self) -> None:
        self.assertEqual(validate_receipt(gpu_fixture()), [])

    def test_cpu_only_fixture_passes_without_accelerator_or_accelerator_lease(self) -> None:
        receipt = cpu_fixture()
        self.assertEqual(receipt["payload"]["host_attestation"]["accelerators"], [])
        self.assertFalse(receipt["payload"]["accelerator_required"])
        self.assertEqual(validate_receipt(receipt), [])

    def test_cpu_only_receipt_cannot_claim_accelerator_required(self) -> None:
        receipt = cpu_fixture()
        receipt["payload"]["accelerator_required"] = True
        refresh_payload_hash(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-025" for item in validate_receipt(receipt)))

    def test_cpu_only_workload_rejects_accelerator_lease_leakage(self) -> None:
        receipt = cpu_fixture()
        receipt["payload"]["hrb_lease_identity"] = {"schema": "unexpected"}
        refresh_payload_hash(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-026" for item in validate_receipt(receipt)))

    def test_hrb_authorization_is_mandatory_for_cpu_only(self) -> None:
        receipt = cpu_fixture()
        receipt["payload"]["hrb_authorization"]["broker_validation"] = False
        refresh_payload_hash(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-012" for item in validate_receipt(receipt)))

    def test_generic_authorization_digest_mismatch_is_blocked(self) -> None:
        receipt = cpu_fixture()
        receipt["payload"]["hrb_authorization"]["workload_envelope_sha256"] = "e" * 64
        refresh_payload_hash(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-029" for item in validate_receipt(receipt)))

    def test_cu_as_workload_requirement_is_blocked(self) -> None:
        receipt = gpu_fixture()
        receipt["payload"]["workload_resource_envelope"]["requirements"] = [{"metric": "cu", "operator": ">=", "value": 1}]
        receipt["payload"]["requested_resource_classes"] = ["other"]
        receipt["payload"]["accelerator_required"] = False
        receipt["payload"]["hrb_lease_identity"] = {}
        refresh_payload_hash(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-011" for item in validate_receipt(receipt)))

    def test_expired_accelerator_lease_is_blocked(self) -> None:
        receipt = gpu_fixture()
        receipt["payload"]["hrb_lease_identity"]["expires_epoch"] = 1
        refresh_payload_hash(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-013" for item in validate_receipt(receipt)))

    def test_lease_memory_budget_caps_effective_vram(self) -> None:
        receipt = gpu_fixture()
        receipt["payload"]["hrb_lease_identity"]["memory_max_bytes"] = 2 * 1024**3
        receipt["payload"]["compute_profile"]["metrics"]["gpu.lease_memory_gib"] = 2.0
        receipt["payload"]["compute_profile"]["metrics"]["gpu.vram_gib"] = 4.0
        refresh_payload_hash(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-018" for item in validate_receipt(receipt)))

    def test_no_fixed_nvidia_cuda_floor_is_applied_by_generic_gate(self) -> None:
        receipt = gpu_fixture()
        receipt["payload"]["host_attestation"]["accelerators"][0]["vendor"] = "OTHER"
        receipt["payload"]["host_attestation"]["accelerators"][0]["cuda_compute_capability"] = 0.0
        receipt["payload"]["compute_profile"]["metrics"]["gpu.vendor"] = "OTHER"
        receipt["payload"]["compute_profile"]["metrics"]["gpu.cuda_compute_capability"] = 0.0
        attestation = receipt["payload"]["host_attestation"]
        attestation_sha = canonical_sha256(attestation)
        receipt["payload"]["host_attestation_sha256"] = attestation_sha
        receipt["payload"]["compute_profile"]["host_attestation_sha256"] = attestation_sha
        refresh_payload_hash(receipt)
        self.assertEqual(validate_receipt(receipt), [])

    def test_global_promotion_non_claim_is_mandatory(self) -> None:
        receipt = gpu_fixture()
        receipt["result"]["non_claims"].remove("GLOBAL_FA3_PROMOTION")
        self.assertTrue(any(item["code"] == "RA-HOST-005" for item in validate_receipt(receipt)))

    def test_gate_passes_only_with_explicit_receipt_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(cpu_fixture()), encoding="utf-8")
            report = gate(ROOT, path)
            self.assertEqual(report["result"], "PASS")
            self.assertFalse(report["global_promotion_claim"])

    def test_missing_receipt_fails_closed(self) -> None:
        report = gate(ROOT, ROOT / "evidence/receipts/does-not-exist-resource-admission.json")
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["decision"]["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
