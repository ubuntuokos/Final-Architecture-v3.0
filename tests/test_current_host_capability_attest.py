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

from fa3_current_host_capability_attest import (
    BUNDLE_SCHEMA,
    materialize,
)


class CurrentHostCapabilityAttestationProducerTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        (root / ".fa3-current-host/test-bundles/capabilities").mkdir(parents=True)
        (root / "evidence/runtime/CAP-001").mkdir(parents=True)
        return td, root

    def _bundle(self, root):
        registry = json.loads((root / "evidence/evidence-registry.json").read_text())
        record = registry["records"][0]
        now = datetime.now(timezone.utc)
        runtime = root / "evidence/runtime/CAP-001/runtime.log"
        negative = root / "evidence/runtime/CAP-001/negative.log"
        rollback = root / "evidence/runtime/CAP-001/rollback.log"
        host = root / "evidence/runtime/CAP-001/host-fingerprint.json"
        runtime.write_text("real current-host positive trace\n")
        negative.write_text("real current-host negative trace\n")
        rollback.write_text("real current-host rollback trace\n")
        host.write_text('{"host":"test-current-host"}\n')

        def sha(path):
            return hashlib.sha256(path.read_bytes()).hexdigest()

        return {
            "schema": BUNDLE_SCHEMA,
            "subject_id": "CAP-001",
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "global_promotion_claim": False,
            "collected_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "host_fingerprint_path": "evidence/runtime/CAP-001/host-fingerprint.json",
            "host_fingerprint_sha256": sha(host),
            "tests": {
                "positive": {
                    "id": record["required_positive_test"],
                    "status": "PASS",
                    "artifact_path": "evidence/runtime/CAP-001/runtime.log",
                    "artifact_sha256": sha(runtime),
                },
                "negative": {
                    "id": record["required_negative_test"],
                    "status": "PASS",
                    "artifact_path": "evidence/runtime/CAP-001/negative.log",
                    "artifact_sha256": sha(negative),
                },
                "rollback": {
                    "id": record["rollback_requirement"],
                    "status": "PASS",
                    "artifact_path": "evidence/runtime/CAP-001/rollback.log",
                    "artifact_sha256": sha(rollback),
                },
            },
            "evidence_artifacts": [
                {"path": "evidence/runtime/CAP-001/runtime.log", "sha256": sha(runtime)},
                {"path": "evidence/runtime/CAP-001/negative.log", "sha256": sha(negative)},
                {"path": "evidence/runtime/CAP-001/rollback.log", "sha256": sha(rollback)},
                {"path": "evidence/runtime/CAP-001/host-fingerprint.json", "sha256": sha(host)},
            ],
        }

    def _write_bundle(self, root, obj):
        path = root / ".fa3-current-host/test-bundles/capabilities/CAP-001.json"
        path.write_text(json.dumps(obj))
        return path

    def test_empty_bundle_directory_is_pending_not_pass(self):
        td, root = self._root()
        try:
            report = materialize(root)
            self.assertEqual(report["producer_integrity"], "PASS")
            self.assertEqual(report["materialization_status"], "PENDING_CAPABILITY_TEST_BUNDLES")
            self.assertEqual(report["attestations_materialized"], 0)
            self.assertEqual(report["provider_receipts_promoted"], 0)
            self.assertFalse(report["global_promotion_claim"])
        finally:
            td.cleanup()

    def test_valid_current_host_bundle_materializes_attestation(self):
        td, root = self._root()
        try:
            self._write_bundle(root, self._bundle(root))
            report = materialize(root)
            self.assertEqual(report["producer_integrity"], "PASS")
            self.assertEqual(report["attestations_materialized"], 1)
            path = root / ".fa3-current-host/attestations/capabilities/CAP-001.json"
            self.assertTrue(path.is_file())
            attestation = json.loads(path.read_text())
            self.assertEqual(attestation["schema"], "fa3.capability-current-host-attestation.v1")
            self.assertEqual(attestation["attestation_authority"], "FA3-AUTH-OBS-EVIDENCE-001")
            self.assertFalse(attestation["producer"]["provider_receipt_is_attestation_authority"])
            self.assertFalse(attestation["producer"]["automatic_promotion"])
        finally:
            td.cleanup()

    def test_provider_receipt_schema_cannot_be_used_as_bundle(self):
        td, root = self._root()
        try:
            bundle = self._bundle(root)
            bundle["schema"] = "fa3.ai-infra-guard-current-host-receipt.v1"
            self._write_bundle(root, bundle)
            report = materialize(root)
            self.assertEqual(report["producer_integrity"], "FAIL")
            self.assertEqual(report["attestations_materialized"], 0)
            self.assertTrue(any(
                "schema mismatch" in finding
                for finding in report["blocking_findings"][0]["findings"]
            ))
        finally:
            td.cleanup()

    def test_exact_registry_test_identity_is_required(self):
        td, root = self._root()
        try:
            bundle = self._bundle(root)
            bundle["tests"]["negative"]["id"] = "AT-WRONG"
            self._write_bundle(root, bundle)
            report = materialize(root)
            self.assertEqual(report["producer_integrity"], "FAIL")
            self.assertTrue(any(
                "test id mismatch" in finding
                for finding in report["blocking_findings"][0]["findings"]
            ))
        finally:
            td.cleanup()

    def test_test_artifact_must_be_hash_bound(self):
        td, root = self._root()
        try:
            bundle = self._bundle(root)
            bundle["tests"]["rollback"]["artifact_path"] = "evidence/runtime/CAP-001/runtime.log"
            self._write_bundle(root, bundle)
            report = materialize(root)
            self.assertEqual(report["producer_integrity"], "FAIL")
            self.assertTrue(any(
                "not bound" in finding
                for finding in report["blocking_findings"][0]["findings"]
            ))
        finally:
            td.cleanup()

    def test_synthetic_ci_reference_or_global_promotion_claim_is_rejected(self):
        for field, value in (("synthetic", True), ("ci_reference_only", True), ("global_promotion_claim", True)):
            with self.subTest(field=field):
                td, root = self._root()
                try:
                    bundle = self._bundle(root)
                    bundle[field] = value
                    self._write_bundle(root, bundle)
                    report = materialize(root)
                    self.assertEqual(report["producer_integrity"], "FAIL")
                    self.assertEqual(report["attestations_materialized"], 0)
                finally:
                    td.cleanup()


if __name__ == "__main__":
    unittest.main()
