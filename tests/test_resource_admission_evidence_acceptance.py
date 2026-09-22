from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src/fa3_resource_admission_evidence_acceptance.py"
spec = importlib.util.spec_from_file_location("fa3_resource_admission_evidence_acceptance", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def canonical_payload_hash(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def attestation_hash(attestation):
    raw = json.dumps(attestation, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def valid_receipt(expires_epoch=2000):
    attestation = {"host": "fixture-host", "accelerators": [{"vendor": "NVIDIA"}]}
    payload = {
        "host_attestation": attestation,
        "host_attestation_sha256": attestation_hash(attestation),
        "workload_resource_envelope": {
            "schema": "fa3.workload-resource-envelope.v1",
            "workload_id": "fa3-resource-admission-current-host-smoke-v1",
            "requirements": [{"metric": "gpu.vram_gib", "operator": ">=", "value": 1}],
        },
        "hrb_lease_identity": {
            "status": "ACTIVE",
            "broker_validation": True,
            "expires_epoch": expires_epoch,
        },
        "admission": {"result": "PASS"},
        "errors": [],
        "cross_metric_compensation": False,
        "cu_tu_admission_authority": False,
    }
    return {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": "FA3-RESOURCE-ADMISSION-CURRENT-HOST-FIXTURE",
        "evidence_class": "CURRENT_HOST_ADMISSION",
        "subject": {"gate_id": "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001"},
        "canonical_context": {
            "architecture_release": "fixture",
            "release_baseline_id": "fixture",
            "release_manifest_digest": "sha256:fixture",
        },
        "execution_context": {"host_attestation_ref": "sha256:" + "a" * 64},
        "provenance": {
            "collector_id": "fixture",
            "collector_revision": "1",
            "generated_at": "2026-09-15T00:00:00Z",
            "artifact_digests": [],
        },
        "integrity": {"payload_sha256": canonical_payload_hash(payload)},
        "result": {
            "status": "PASS",
            "scope": "COMPONENT_CURRENT_HOST_RESOURCE_ADMISSION",
            "claims": ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"],
            "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E"],
        },
        "payload_schema_id": "fa3.resource-admission-current-host.payload.v1",
        "payload": payload,
    }


class ResourceAdmissionEvidenceAcceptanceTests(unittest.TestCase):
    def write_receipt(self, receipt):
        temp = tempfile.TemporaryDirectory()
        path = Path(temp.name) / "receipt.json"
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return temp, path

    def test_valid_receipt_builds_sanitized_acceptance(self):
        temp, path = self.write_receipt(valid_receipt())
        self.addCleanup(temp.cleanup)
        record = mod.build_acceptance(path, now_epoch=1000, workflow_run_id="42", workflow_run_url="https://example/run/42", git_sha="abc")
        self.assertEqual(record["status"], "REAL_EXECUTION_PASS_CAPTURED_PER_WORKLOAD_READMISSION_REQUIRED")
        self.assertEqual(record["subject"]["capability_id"], "CAP-006")
        self.assertTrue(record["source_evidence"]["receipt_sha256"])
        serialized = json.dumps(record)
        self.assertNotIn("fixture-host", serialized)
        self.assertNotIn("accelerator_uuid", serialized)
        self.assertFalse(record["archival_semantics"]["current_or_future_workload_authorization"])
        self.assertFalse(record["projection_semantics"]["global_promotion_claim"])
        self.assertEqual(mod.verify_acceptance(record), [])

    def test_expired_lease_blocks_acceptance(self):
        receipt = valid_receipt(expires_epoch=999)
        temp, path = self.write_receipt(receipt)
        self.addCleanup(temp.cleanup)
        with self.assertRaises(mod.AcceptanceError):
            mod.build_acceptance(path, now_epoch=1000)

    def test_payload_tamper_blocks_acceptance(self):
        receipt = valid_receipt()
        receipt["payload"]["errors"] = ["tampered"]
        temp, path = self.write_receipt(receipt)
        self.addCleanup(temp.cleanup)
        with self.assertRaises(mod.AcceptanceError):
            mod.build_acceptance(path, now_epoch=1000)

    def test_global_promotion_nonclaim_is_mandatory(self):
        receipt = valid_receipt()
        receipt["result"]["non_claims"] = ["PROVIDER_RUNTIME_E2E"]
        receipt["integrity"]["payload_sha256"] = canonical_payload_hash(receipt["payload"])
        temp, path = self.write_receipt(receipt)
        self.addCleanup(temp.cleanup)
        with self.assertRaises(mod.AcceptanceError):
            mod.build_acceptance(path, now_epoch=1000)

    def test_acceptance_cannot_authorize_future_workloads(self):
        temp, path = self.write_receipt(valid_receipt())
        self.addCleanup(temp.cleanup)
        record = mod.build_acceptance(path, now_epoch=1000)
        record["archival_semantics"]["current_or_future_workload_authorization"] = True
        self.assertIn("ARCHIVAL_RECORD_MUST_NOT_AUTHORIZE_FUTURE_WORKLOADS", mod.verify_acceptance(record))


if __name__ == "__main__":
    unittest.main()
