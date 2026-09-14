from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_resource_admission_current_host_gate import gate, validate_receipt  # noqa: E402
from fa3_resource_evidence_normalization_gate import _canonical_payload_hash  # noqa: E402


def fixture() -> dict:
    payload = {
        "schema": "fa3.resource-admission-current-host.payload.v1",
        "host_attestation": {
            "schema": "fa3.host-attestation.v1",
            "host_attestation_id": "FA3-HOST-TEST",
            "secret_collection": "PROHIBITED",
            "accelerators": [{"uuid": "GPU-TEST", "pci_bdf": "0000:01:00.0"}],
        },
        "host_attestation_sha256": "a" * 64,
        "compute_profile": {
            "schema": "fa3.compute-profile.v1",
            "host_attestation_sha256": "a" * 64,
            "metrics": {"gpu.vram_gib": 24, "cpu.physical_cores": 16},
            "diagnostic_aggregates": {"cu": 999, "tu": 999},
        },
        "workload_resource_envelope": {
            "schema": "fa3.workload-resource-envelope.v1",
            "workload_id": "fixture",
            "requirements": [{"metric": "gpu.vram_gib", "operator": ">=", "value": 24}],
        },
        "workload_resource_envelope_sha256": "b" * 64,
        "hrb_lease_identity": {
            "schema": "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1",
            "lease_id": "lease-test",
            "issuer": "FA3-HOST-RESOURCE-BROKER-001",
            "accelerator_uuid": "GPU-TEST",
            "pci_bus_id": "0000:01:00.0",
            "purpose": "fixture",
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
            "collector_revision": "1.0.0",
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
        receipt["integrity"]["payload_sha256"] = _canonical_payload_hash(receipt["payload"])
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-010" for item in findings))

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
        receipt["integrity"]["payload_sha256"] = _canonical_payload_hash(receipt["payload"])
        findings = validate_receipt(receipt)
        self.assertTrue(any(item["code"] == "RA-HOST-011" for item in findings))

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
