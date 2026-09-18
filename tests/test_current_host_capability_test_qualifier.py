import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_test_qualifier import qualify

QID = "FA3-QUAL-CAP-001-POS-001"
CID = "CAP001-POS-ALL"

class QualifierTests(unittest.TestCase):
    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        (root / "canonical").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        shutil.copy(ROOT / "canonical/current-host-capability-test-qualifications.json", root / "canonical/current-host-capability-test-qualifications.json")
        rec = next(row for row in json.loads((root / "evidence/evidence-registry.json").read_text())["records"] if row["subject_id"] == "CAP-001")
        path = root / "canonical/current-host-capability-test-qualifications.json"
        registry = json.loads(path.read_text())
        registry["entries"].append({
            "qualification_id": QID,
            "subject_id": "CAP-001",
            "test_kind": "positive",
            "test_id": rec["required_positive_test"],
            "coverage_semantics": "COMPLETE_CAPABILITY_OBLIGATION",
            "evidence_authority_id": "FA3-AUTH-OBS-EVIDENCE-001",
            "runtime_constituent_schema": "fa3.capability-current-host-qualification-constituent.v1",
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "max_constituent_ttl_seconds": 3600,
            "completeness_basis": {"type": "EXACT_EVIDENCE_REGISTRY_SOURCE_DECISION_COVERAGE", "source_decision_ids": rec["source_decision_ids"]},
            "required_constituents": [{"constituent_id": CID, "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION", "covers_source_decision_ids": rec["source_decision_ids"]}],
        })
        path.write_text(json.dumps(registry))
        host = root / ".fa3-current-host/global-closure/host/host-fingerprint.json"
        host.parent.mkdir(parents=True, exist_ok=True)
        host.write_text('{"host":"fixture"}\n')
        source = root / ".fa3-current-host/source/cap001-positive.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('{"status":"PASS"}\n')
        out = root / ".fa3-current-host/test-artifacts/capabilities/CAP-001/positive"
        out.mkdir(parents=True, exist_ok=True)
        return td, root, rec, host, source, out

    @contextmanager
    def _env(self, root, rec, host, out):
        values = {
            "FA3_CAPABILITY_ID": "CAP-001",
            "FA3_TEST_KIND": "positive",
            "FA3_TEST_ID": rec["required_positive_test"],
            "FA3_HOST_FINGERPRINT_PATH": host.relative_to(root).as_posix(),
            "FA3_HOST_FINGERPRINT_SHA256": self._sha(host),
            "FA3_TEST_ARTIFACT_DIR": str(out),
            "FA3_REPOSITORY_ROOT": str(root),
        }
        old = {key: os.environ.get(key) for key in values}
        os.environ.update(values)
        try:
            yield
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _manifest(self, root, rec, host, source, *, expired=False, source_override=None):
        now = datetime.now(timezone.utc)
        actual_source = source_override or source
        path = root / f".fa3-current-host/qualification-constituents/{QID}/{CID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema": "fa3.capability-current-host-qualification-constituent.v1",
            "qualification_id": QID,
            "constituent_id": CID,
            "subject_id": "CAP-001",
            "test_kind": "positive",
            "test_id": rec["required_positive_test"],
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "evidence_authority_id": "FA3-AUTH-OBS-EVIDENCE-001",
            "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION",
            "covers_source_decision_ids": rec["source_decision_ids"],
            "host_fingerprint_path": host.relative_to(root).as_posix(),
            "host_fingerprint_sha256": self._sha(host),
            "collected_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now - timedelta(seconds=1) if expired else now + timedelta(minutes=30)).isoformat(),
            "source_artifact_path": actual_source.relative_to(root).as_posix(),
            "source_artifact_sha256": self._sha(actual_source),
        }
        path.write_text(json.dumps(manifest))

    def test_complete_fresh_host_bound_constituent_yields_typed_verdict(self):
        td, root, rec, host, source, out = self._root()
        try:
            self._manifest(root, rec, host, source)
            with self._env(root, rec, host, out):
                verdict, findings = qualify(root, QID)
            self.assertEqual(findings, [])
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(verdict["qualification_id"], QID)
            self.assertTrue((root / verdict["artifact_path"]).is_file())
        finally:
            td.cleanup()

    def test_missing_and_expired_constituents_are_rejected(self):
        for expired in (False, True):
            td, root, rec, host, source, out = self._root()
            try:
                if expired:
                    self._manifest(root, rec, host, source, expired=True)
                with self._env(root, rec, host, out):
                    verdict, findings = qualify(root, QID)
                self.assertIsNone(verdict)
                self.assertTrue(findings)
            finally:
                td.cleanup()

    def test_circular_test_artifact_cannot_be_source_evidence(self):
        td, root, rec, host, source, out = self._root()
        try:
            circular = root / ".fa3-current-host/test-artifacts/other.json"
            circular.parent.mkdir(parents=True, exist_ok=True)
            circular.write_text("{}")
            self._manifest(root, rec, host, source, source_override=circular)
            with self._env(root, rec, host, out):
                verdict, findings = qualify(root, QID)
            self.assertIsNone(verdict)
            self.assertTrue(any("forbidden" in item for item in findings))
        finally:
            td.cleanup()

if __name__ == "__main__":
    unittest.main()
