import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_handoff import (
    ATTESTATION_SCHEMA,
    EVIDENCE_AUTHORITY,
    materialize,
)


class CurrentHostCapabilityHandoffTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        (root / ".fa3-current-host/attestations/capabilities").mkdir(parents=True)
        (root / "evidence/runtime/CAP-001").mkdir(parents=True)
        return td, root

    def _attestation(self, root):
        registry = json.loads((root / "evidence/evidence-registry.json").read_text())
        record = registry["records"][0]
        now = datetime.now(timezone.utc)

        runtime = root / "evidence/runtime/CAP-001/runtime.log"
        host = root / "evidence/runtime/CAP-001/host-fingerprint.json"
        runtime.write_text("real current-host executable trace\n")
        host.write_text('{"host":"test-current-host"}\n')
        runtime_sha = hashlib.sha256(runtime.read_bytes()).hexdigest()
        host_sha = hashlib.sha256(host.read_bytes()).hexdigest()

        return {
            "schema": ATTESTATION_SCHEMA,
            "subject_id": "CAP-001",
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "attestation_authority": EVIDENCE_AUTHORITY,
            "global_promotion_claim": False,
            "host_fingerprint_path": "evidence/runtime/CAP-001/host-fingerprint.json",
            "host_fingerprint_sha256": host_sha,
            "collected_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "tests": {
                "positive": {
                    "id": record["required_positive_test"],
                    "status": "PASS",
                    "artifact_sha256": runtime_sha,
                },
                "negative": {
                    "id": record["required_negative_test"],
                    "status": "PASS",
                    "artifact_sha256": runtime_sha,
                },
                "rollback": {
                    "id": record["rollback_requirement"],
                    "status": "PASS",
                    "artifact_sha256": runtime_sha,
                },
            },
            "evidence_artifacts": [
                {
                    "path": "evidence/runtime/CAP-001/runtime.log",
                    "sha256": runtime_sha,
                },
                {
                    "path": "evidence/runtime/CAP-001/host-fingerprint.json",
                    "sha256": host_sha,
                },
            ],
        }

    def _write_attestation(self, root, obj):
        path = root / ".fa3-current-host/attestations/capabilities/CAP-001.json"
        path.write_text(json.dumps(obj))
        return path

    def test_no_attestation_is_pending_not_pass_fabrication(self):
        td, root = self._root()
        try:
            report = materialize(root)
            self.assertEqual(report["handoff_integrity"], "PASS")
            self.assertEqual(report["materialization_status"], "PENDING_CURRENT_HOST_ATTESTATIONS")
            self.assertEqual(report["receipts_materialized"], 0)
            self.assertEqual(report["provider_receipts_promoted"], 0)
            self.assertFalse(report["global_promotion_claim"])
            self.assertFalse((root / "evidence/receipts/capabilities/CAP-001.json").exists())
        finally:
            td.cleanup()

    def test_valid_explicit_attestation_materializes_auditable_receipt(self):
        td, root = self._root()
        try:
            attestation = self._attestation(root)
            attestation_path = self._write_attestation(root, attestation)
            report = materialize(root)
            self.assertEqual(report["handoff_integrity"], "PASS")
            self.assertEqual(report["receipts_materialized"], 1)
            receipt_path = root / "evidence/receipts/capabilities/CAP-001.json"
            self.assertTrue(receipt_path.is_file())
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["schema"], "fa3.capability-current-host-evidence.v1")
            self.assertEqual(receipt["subject_id"], "CAP-001")
            self.assertFalse(receipt["handoff"]["provider_receipt_is_capability_authority"])
            self.assertFalse(receipt["handoff"]["global_promotion_claim"])
            self.assertEqual(
                receipt["attestation"]["sha256"],
                hashlib.sha256(attestation_path.read_bytes()).hexdigest(),
            )
            self.assertTrue(any(x["path"].endswith("CAP-001.json") for x in receipt["evidence_artifacts"]))
        finally:
            td.cleanup()

    def test_provider_receipt_schema_cannot_be_promoted(self):
        td, root = self._root()
        try:
            attestation = self._attestation(root)
            attestation["schema"] = "fa3.ai-infra-guard-current-host-receipt.v1"
            self._write_attestation(root, attestation)
            report = materialize(root)
            self.assertEqual(report["handoff_integrity"], "FAIL")
            self.assertEqual(report["receipts_materialized"], 0)
            self.assertTrue(any("schema mismatch" in x for x in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_provider_cannot_self_assign_evidence_authority(self):
        td, root = self._root()
        try:
            attestation = self._attestation(root)
            attestation["attestation_authority"] = "FA3-PROVIDER-AI-INFRA-GUARD-001"
            self._write_attestation(root, attestation)
            report = materialize(root)
            self.assertEqual(report["handoff_integrity"], "FAIL")
            self.assertTrue(any("authority mismatch" in x for x in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_synthetic_or_ci_reference_attestation_is_rejected(self):
        for field in ("synthetic", "ci_reference_only"):
            with self.subTest(field=field):
                td, root = self._root()
                try:
                    attestation = self._attestation(root)
                    attestation[field] = True
                    self._write_attestation(root, attestation)
                    report = materialize(root)
                    self.assertEqual(report["handoff_integrity"], "FAIL")
                    self.assertEqual(report["receipts_materialized"], 0)
                finally:
                    td.cleanup()

    def test_registry_test_identity_mismatch_is_rejected(self):
        td, root = self._root()
        try:
            attestation = self._attestation(root)
            attestation["tests"]["positive"]["id"] = "AT-WRONG"
            self._write_attestation(root, attestation)
            report = materialize(root)
            self.assertEqual(report["handoff_integrity"], "FAIL")
            self.assertTrue(any("test id mismatch" in x for x in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_unbound_or_mismatched_artifact_is_rejected(self):
        td, root = self._root()
        try:
            attestation = self._attestation(root)
            attestation["evidence_artifacts"][0]["sha256"] = "b" * 64
            self._write_attestation(root, attestation)
            report = materialize(root)
            self.assertEqual(report["handoff_integrity"], "FAIL")
            findings = report["blocking_findings"][0]["findings"]
            self.assertTrue(any("digest mismatch" in x for x in findings))
            self.assertTrue(any("not bound" in x for x in findings))
        finally:
            td.cleanup()

    def test_global_promotion_claim_in_attestation_is_rejected(self):
        td, root = self._root()
        try:
            attestation = self._attestation(root)
            attestation["global_promotion_claim"] = True
            self._write_attestation(root, attestation)
            report = materialize(root)
            self.assertEqual(report["handoff_integrity"], "FAIL")
            self.assertTrue(any("must not claim global promotion" in x for x in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
