from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_hrb_cuda_current_host_gate import EXPECTED, gate, validate_attestation, validate_receipt


def artifacts(byte_reverified: bool = True) -> list[dict]:
    return [
        {
            "id": evidence_id,
            "path": f"/external/{evidence_id}.json",
            "sha256": expected["sha256"],
            "status": "PASS",
            "byte_reverified": byte_reverified,
        }
        for evidence_id, expected in EXPECTED.items()
    ]


def attestation_fixture() -> dict:
    values = artifacts(False)
    for item in values:
        expected = EXPECTED[item["id"]]
        item.pop("byte_reverified")
        if expected["profile"] is not None:
            item["profile"] = expected["profile"]
            item["version"] = expected["version"]
    return {
        "schema": "fa3.external-current-host-digest-attestation.v1",
        "status": "PASS",
        "host": "horvath-precisiontower7910",
        "raw_artifacts_committed": False,
        "scope": "HRB_V1_0_LEASE_AUTH_AND_CUDA_V1_2_EXECUTION_ONLY",
        "artifacts": values,
        "canonical_reconciliation": {
            "hrb_profile_current_version": "1.4.0",
            "hrb_v1_4_full_runtime_promoted": False,
            "cuda_profile_current_version": "1.2.0",
            "cuda_scoped_component_promotion_eligible": True,
            "capability_count": 143,
            "global_promotion_claim": False,
        },
    }


def receipt_fixture() -> dict:
    registry = []
    for evidence_id in ("HRB-CONFORMANCE", "CUDA-BROKER-REGRESSION", "CUDA-AUTH-E2E"):
        expected = EXPECTED[evidence_id]
        registry.append({
            "id": evidence_id,
            "host": "horvath-precisiontower7910",
            "status": "PASS",
            "profile": expected["profile"],
            "version": expected["version"],
            "sha256": expected["sha256"],
        })
    return {
        "schema": "fa3.hrb-cuda-current-host-receipt.v1",
        "status": "PASS",
        "evidence_level": "SCOPED_CURRENT_HOST_HRB_V1_0_AUTHENTICATED_CUDA_V1_2_PRODUCTION_E2E_PASS",
        "host": "horvath-precisiontower7910",
        "live_source_reverified": True,
        "scope": {
            "hrb_implementation_version": "1.0.0",
            "cuda_python_version": "1.2.0",
            "canonical_hrb_profile_version": "1.4.0",
            "hrb_v1_4_full_runtime_claim": False,
            "cuda_component_promotion_eligible": True,
            "global_promotion_claim": False,
        },
        "artifacts": artifacts(True),
        "external_registry_records": registry,
        "authority_boundary": {
            "hrb": "ADMISSION_PLACEMENT_RESERVATION_LEASE_AUTHORITY",
            "cuda_python": "EXECUTION_PROVIDER_NOT_AUTHORITY",
        },
        "capability_count_after": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
    }


class HrbCudaCurrentHostGateTests(unittest.TestCase):
    def test_digest_attestation_passes(self):
        self.assertEqual(validate_attestation(attestation_fixture()), [])

    def test_digest_tamper_fails_closed(self):
        value = attestation_fixture()
        value["artifacts"][0]["sha256"] = "0" * 64
        self.assertTrue(validate_attestation(value))

    def test_complete_live_receipt_passes(self):
        self.assertEqual(validate_receipt(receipt_fixture()), [])

    def test_non_reverified_receipt_is_not_current_host_pass(self):
        value = receipt_fixture()
        value["live_source_reverified"] = False
        self.assertTrue(any(item["code"] == "HRB-CUDA-HOST-006" for item in validate_receipt(value)))

    def test_hrb_v1_0_evidence_cannot_promote_hrb_v1_4_full_scope(self):
        value = receipt_fixture()
        value["scope"]["hrb_v1_4_full_runtime_claim"] = True
        self.assertTrue(any(item["code"] == "HRB-CUDA-HOST-007" for item in validate_receipt(value)))

    def test_cuda_cannot_become_resource_authority(self):
        value = receipt_fixture()
        value["authority_boundary"]["cuda_python"] = "PLACEMENT_AUTHORITY"
        self.assertTrue(any(item["code"] == "HRB-CUDA-HOST-010" for item in validate_receipt(value)))

    def test_missing_receipt_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            report = gate(Path(temp))
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["findings"][0]["code"], "HRB-CUDA-HOST-000")

    def test_global_promotion_claim_fails_closed(self):
        value = receipt_fixture()
        value["global_promotion_claim"] = True
        self.assertTrue(any(item["code"] == "HRB-CUDA-HOST-010" for item in validate_receipt(value)))


if __name__ == "__main__":
    unittest.main()
