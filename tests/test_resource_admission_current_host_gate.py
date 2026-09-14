from __future__ import annotations

import copy
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


def fixture() -> dict:
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
            "diagnostic_aggregates": {"cu": 999, "tu": 999},
        },
        "workload_resource_envelope": {
            "schema": "fa3.workload-resource-envelope.v1",
            "workload_id": "fixture",
            "requirements": [{"metric": "gpu.vram_gib", "operator": ">=", "value": 4}],
        },
        "workload_resource_envelope_sha256": "b" * 64,
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
            "diagnostics": {"cu": 999, "tu": 999},
        },
        "provenance": {
            "collector_id": "TEST-FIXTURE-NOT-EVIDENCE",
            "collector_revision": "1.1.0",
            "generated_at": "2026-09-14T00:00:00Z",
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


class ResourceAdmissionCurrentHostTests(unittest.TestCase):
    def test_valid_fixture_contract_passes(self) -> None:
        self.assertEqual(validate_receipt(fixture()), [])

    def test_diagnostic_cu_tu_do_not_affect_valid_admission(self) -> None:
        receipt = fixture()
        receipt["execution_context"]["diagnostics"] = {"cu": -1, "tu": 10**9}
        self.assertEqual(validate_receipt(receipt), [])

    def test_cu_as_workload_requirement_is_blocked(self) -> None:
        receipt = fixture()
        receipt["payload"]["workload_resource_envelope"]["requirements"] = [
            {"metric": "cu", "operator": ">=", "value": 1}
        ]
        refresh_payload_hash(receipt)
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-011" for item in findings))

    def test_tampered_payload_is_blocked(self) -> None:
        receipt = fixture()
        receipt["payload"]["cu_tu_admission_authority"] = True
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-001" for item in findings))

    def test_global_promotion_non_claim_is_mandatory(self) -> None:
        receipt = fixture()
        receipt["result"]["non_claims"].remove("GLOBAL_FA3_PROMOTION")
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-005" for item in findings))

    def test_missing_broker_validation_is_blocked(self) -> None:
        receipt = fixture()
        receipt["payload"]["hrb_lease_identity"]["broker_validation"] = False
        refresh_payload_hash(receipt)
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-012" for item in findings))

    def test_expired_lease_is_rechecked_at_gate_time(self) -> None:
        receipt = fixture()
        receipt["payload"]["hrb_lease_identity"]["expires_epoch"] = 1
        refresh_payload_hash(receipt)
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-013" for item in findings))

    def test_attestation_hash_is_recomputed_not_trusted(self) -> None:
        receipt = fixture()
        receipt["payload"]["host_attestation"]["host"] = "tampered-host"
        refresh_payload_hash(receipt)
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-008" for item in findings))

    def test_eight_digit_and_four_digit_bdf_are_equivalent(self) -> None:
        receipt = fixture()
        receipt["payload"]["host_attestation"]["accelerators"][0]["pci_bdf"] = "0000:01:00.0"
        receipt["payload"]["hrb_lease_identity"]["pci_bus_id"] = "00000000:01:00.0"
        attestation = receipt["payload"]["host_attestation"]
        attestation_sha = canonical_sha256(attestation)
        receipt["payload"]["host_attestation_sha256"] = attestation_sha
        receipt["payload"]["compute_profile"]["host_attestation_sha256"] = attestation_sha
        refresh_payload_hash(receipt)
        self.assertEqual(validate_receipt(receipt), [])

    def test_lease_memory_budget_caps_effective_vram(self) -> None:
        receipt = fixture()
        receipt["payload"]["hrb_lease_identity"]["memory_max_bytes"] = 2 * 1024**3
        receipt["payload"]["compute_profile"]["metrics"]["gpu.lease_memory_gib"] = 2.0
        receipt["payload"]["compute_profile"]["metrics"]["gpu.vram_gib"] = 4.0
        refresh_payload_hash(receipt)
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-018" for item in findings))

    def test_workload_scope_binding_is_mandatory(self) -> None:
        receipt = fixture()
        receipt["payload"]["hrb_lease_identity"]["purpose"] = "different-workload"
        refresh_payload_hash(receipt)
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-015" for item in findings))

    def test_a1000_class_compute_capability_8_6_passes(self) -> None:
        receipt = fixture()
        self.assertEqual(validate_receipt(receipt), [])

    def test_compute_capability_below_floor_is_blocked(self) -> None:
        receipt = fixture()
        receipt["payload"]["host_attestation"]["accelerators"][0]["cuda_compute_capability"] = 8.0
        receipt["payload"]["compute_profile"]["metrics"]["gpu.cuda_compute_capability"] = 8.0
        attestation = receipt["payload"]["host_attestation"]
        attestation_sha = canonical_sha256(attestation)
        receipt["payload"]["host_attestation_sha256"] = attestation_sha
        receipt["payload"]["compute_profile"]["host_attestation_sha256"] = attestation_sha
        refresh_payload_hash(receipt)
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-019" for item in findings))

    def test_gate_passes_only_with_explicit_receipt_path(self) -> None:
        receipt = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            report = gate(ROOT, path)
            self.assertEqual(report["result"], "PASS")
            self.assertFalse(report["global_promotion_claim"])

    def test_missing_receipt_fails_closed(self) -> None:
        report = gate(ROOT, ROOT / "evidence/receipts/does-not-exist-resource-admission.json")
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["decision"]["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
