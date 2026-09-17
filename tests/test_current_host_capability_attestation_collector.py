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

from fa3_current_host_capability_attestation_collector import (
    ATTESTATION_SCHEMA,
    EVIDENCE_AUTHORITY,
    RESULT_SCHEMA,
    materialize,
)
from fa3_current_host_capability_handoff import materialize as handoff


class CurrentHostCapabilityAttestationCollectorTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        (root / ".fa3-current-host/input/capability-test-results/CAP-001").mkdir(parents=True)
        (root / "evidence/runtime/CAP-001").mkdir(parents=True)
        return td, root

    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _write_bundle(self, root, *, omit=None, mutate=None):
        registry = json.loads((root / "evidence/evidence-registry.json").read_text())
        record = registry["records"][0]
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)

        host = root / "evidence/runtime/CAP-001/host-fingerprint.json"
        host.write_text('{"schema":"fa3.host-fingerprint.evidence.v1","host":"real-current-host"}\n')
        host_sha = self._sha(host)

        ids = {
            "positive": record["required_positive_test"],
            "negative": record["required_negative_test"],
            "rollback": record["rollback_requirement"],
        }
        for kind in ("positive", "negative", "rollback"):
            if kind == omit:
                continue
            artifact = root / f"evidence/runtime/CAP-001/{kind}.log"
            artifact.write_text(f"real current-host {kind} executable trace\n")
            artifact_sha = self._sha(artifact)
            obj = {
                "schema": RESULT_SCHEMA,
                "subject_id": "CAP-001",
                "test_kind": kind,
                "test_id": ids[kind],
                "status": "PASS",
                "execution_scope": "CURRENT_HOST",
                "current_host": True,
                "synthetic": False,
                "ci_reference_only": False,
                "evidence_authority": EVIDENCE_AUTHORITY,
                "global_promotion_claim": False,
                "collected_at": now.isoformat(),
                "expires_at": expires.isoformat(),
                "host_fingerprint_path": "evidence/runtime/CAP-001/host-fingerprint.json",
                "host_fingerprint_sha256": host_sha,
                "result_artifact": {
                    "path": f"evidence/runtime/CAP-001/{kind}.log",
                    "sha256": artifact_sha,
                },
                "evidence_artifacts": [
                    {
                        "path": f"evidence/runtime/CAP-001/{kind}.log",
                        "sha256": artifact_sha,
                    },
                    {
                        "path": "evidence/runtime/CAP-001/host-fingerprint.json",
                        "sha256": host_sha,
                    },
                ],
            }
            if mutate is not None:
                mutate(kind, obj)
            path = root / f".fa3-current-host/input/capability-test-results/CAP-001/{kind}.json"
            path.write_text(json.dumps(obj))

    def test_empty_input_is_pending_and_never_fabricates_pass(self):
        td, root = self._root()
        try:
            report = materialize(root)
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["materialization_status"], "PENDING_CURRENT_HOST_TEST_RESULTS")
            self.assertEqual(report["attestations_materialized"], 0)
            self.assertEqual(report["pending_capabilities"], 143)
            self.assertFalse(report["global_promotion_claim"])
            self.assertFalse(report["test_execution_fabricated"])
            self.assertFalse((root / ".fa3-current-host/attestations/capabilities/CAP-001.json").exists())
        finally:
            td.cleanup()

    def test_complete_real_result_triplet_materializes_handoff_compatible_attestation(self):
        td, root = self._root()
        try:
            self._write_bundle(root)
            report = materialize(root)
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["attestations_materialized"], 1)
            attestation_path = root / ".fa3-current-host/attestations/capabilities/CAP-001.json"
            self.assertTrue(attestation_path.is_file())
            attestation = json.loads(attestation_path.read_text())
            self.assertEqual(attestation["schema"], ATTESTATION_SCHEMA)
            self.assertEqual(attestation["subject_id"], "CAP-001")
            self.assertEqual(attestation["attestation_authority"], EVIDENCE_AUTHORITY)
            self.assertFalse(attestation["synthetic"])
            self.assertFalse(attestation["ci_reference_only"])
            self.assertFalse(attestation["global_promotion_claim"])

            handoff_report = handoff(root)
            self.assertEqual(handoff_report["handoff_integrity"], "PASS")
            self.assertEqual(handoff_report["receipts_materialized"], 1)
        finally:
            td.cleanup()

    def test_incomplete_triplet_remains_pending_not_failed_or_passed(self):
        td, root = self._root()
        try:
            self._write_bundle(root, omit="rollback")
            report = materialize(root)
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["attestations_materialized"], 0)
            row = report["capabilities"][0]
            self.assertEqual(row["status"], "PENDING_INCOMPLETE_TEST_RESULTS")
        finally:
            td.cleanup()

    def test_registry_test_identity_mismatch_is_rejected(self):
        td, root = self._root()
        try:
            def mutate(kind, obj):
                if kind == "positive":
                    obj["test_id"] = "AT-CAP-999-POS"
            self._write_bundle(root, mutate=mutate)
            report = materialize(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertEqual(report["attestations_materialized"], 0)
            self.assertTrue(any("test id mismatch" in x for x in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_synthetic_or_ci_reference_result_is_rejected(self):
        for field in ("synthetic", "ci_reference_only"):
            with self.subTest(field=field):
                td, root = self._root()
                try:
                    def mutate(kind, obj, field=field):
                        if kind == "negative":
                            obj[field] = True
                    self._write_bundle(root, mutate=mutate)
                    report = materialize(root)
                    self.assertEqual(report["result"], "FAIL")
                    self.assertEqual(report["attestations_materialized"], 0)
                finally:
                    td.cleanup()

    def test_provider_cannot_self_assign_evidence_authority(self):
        td, root = self._root()
        try:
            def mutate(kind, obj):
                if kind == "rollback":
                    obj["evidence_authority"] = "FA3-PROVIDER-AI-INFRA-GUARD-001"
            self._write_bundle(root, mutate=mutate)
            report = materialize(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any("authority mismatch" in x for x in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_digest_mismatch_is_rejected(self):
        td, root = self._root()
        try:
            def mutate(kind, obj):
                if kind == "positive":
                    obj["evidence_artifacts"][0]["sha256"] = "a" * 64
            self._write_bundle(root, mutate=mutate)
            report = materialize(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any("digest mismatch" in x for x in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_mixed_host_fingerprints_are_rejected(self):
        td, root = self._root()
        try:
            other = root / "evidence/runtime/CAP-001/other-host.json"
            other.write_text('{"host":"different-host"}\n')
            other_sha = self._sha(other)

            def mutate(kind, obj):
                if kind == "negative":
                    obj["host_fingerprint_path"] = "evidence/runtime/CAP-001/other-host.json"
                    obj["host_fingerprint_sha256"] = other_sha
                    obj["evidence_artifacts"].append({
                        "path": "evidence/runtime/CAP-001/other-host.json",
                        "sha256": other_sha,
                    })
            self._write_bundle(root, mutate=mutate)
            report = materialize(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(
                "same host fingerprint" in item
                for finding in report["blocking_findings"]
                for item in finding.get("findings", [])
            ))
        finally:
            td.cleanup()

    def test_unknown_capability_directory_is_integrity_failure(self):
        td, root = self._root()
        try:
            (root / ".fa3-current-host/input/capability-test-results/CAP-999").mkdir()
            report = materialize(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertEqual(report["attestations_materialized"], 0)
            self.assertEqual(report["blocking_findings"][0]["code"], "CHA-003")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
