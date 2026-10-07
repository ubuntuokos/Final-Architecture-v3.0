import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_qualification_constituent_producer_audit import audit

QID = "FA3-QUAL-CAP-001-POS-001"
CID = "CAP001-POS-ALL"
PID = "FA3-QUAL-PRODUCER-CAP001-POS-ALL"


class QualificationConstituentProducerAuditTests(unittest.TestCase):
    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        (root / "canonical").mkdir(parents=True)
        (root / "src").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        shutil.copy(
            ROOT / "canonical/current-host-capability-test-qualifications.json",
            root / "canonical/current-host-capability-test-qualifications.json",
        )
        shutil.copy(
            ROOT / "canonical/current-host-capability-qualification-constituent-producers.json",
            root / "canonical/current-host-capability-qualification-constituent-producers.json",
        )
        for rel in (
            "canonical/current-host-capability-test-qualifications.json",
            "canonical/current-host-capability-qualification-constituent-producers.json",
        ):
            path = root / rel
            registry = json.loads(path.read_text())
            registry["entries"] = []
            path.write_text(json.dumps(registry))
        return td, root

    def _record(self, root):
        data = json.loads((root / "evidence/evidence-registry.json").read_text())
        return next(row for row in data["records"] if row["subject_id"] == "CAP-001")

    def _qualification(self, root):
        rec = self._record(root)
        path = root / "canonical/current-host-capability-test-qualifications.json"
        registry = json.loads(path.read_text())
        registry["entries"].append({
            "qualification_id": QID,
            "subject_id": "CAP-001",
            "test_kind": "positive",
            "test_id": rec["required_positive_test"],
            "coverage_semantics": "COMPLETE_CAPABILITY_OBLIGATION",
            "evidence_authority_id": "FA3-AUTH-OBS-EVIDENCE-001",
            "runtime_constituent_schema": "fa3.capability-current-host-qualification-constituent.v2",
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "max_constituent_ttl_seconds": 3600,
            "completeness_basis": {
                "type": "EXACT_EVIDENCE_REGISTRY_SOURCE_DECISION_COVERAGE",
                "source_decision_ids": rec["source_decision_ids"],
            },
            "required_constituents": [{
                "constituent_id": CID,
                "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION",
                "covers_source_decision_ids": rec["source_decision_ids"],
            }],
        })
        path.write_text(json.dumps(registry))
        return rec

    def _producer(self, root, *, decisions=None):
        rec = self._qualification(root)
        adapter = root / "src/cap001_positive_producer.py"
        adapter.write_text("print('fixture')\n")
        path = root / "canonical/current-host-capability-qualification-constituent-producers.json"
        registry = json.loads(path.read_text())
        registry["entries"].append({
            "producer_id": PID,
            "qualification_id": QID,
            "constituent_id": CID,
            "subject_id": "CAP-001",
            "test_kind": "positive",
            "test_id": rec["required_positive_test"],
            "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION",
            "covers_source_decision_ids": rec["source_decision_ids"] if decisions is None else decisions,
            "adapter_path": "src/cap001_positive_producer.py",
            "adapter_sha256": self._sha(adapter),
            "execution_mode": "REAL_CURRENT_HOST_EXECUTION",
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "argv": [],
            "timeout_seconds": 30,
            "ttl_seconds": 1800,
        })
        path.write_text(json.dumps(registry))
        return adapter, rec

    def test_no_qualification_definitions_means_zero_required_constituents(self):
        td, root = self._root()
        try:
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["required_constituent_count"], 0)
            self.assertEqual(report["registered_producer_count"], 0)
            self.assertEqual(report["coverage_status"], "PENDING_CAPABILITY_QUALIFICATION_DEFINITIONS")
        finally:
            td.cleanup()

    def test_qualification_without_producer_remains_pending(self):
        td, root = self._root()
        try:
            self._qualification(root)
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["required_constituent_count"], 1)
            self.assertEqual(report["registered_producer_count"], 0)
            self.assertEqual(report["pending_producer_count"], 1)
        finally:
            td.cleanup()

    def test_exact_registered_producer_is_accepted(self):
        td, root = self._root()
        try:
            self._producer(root)
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["registered_producer_count"], 1)
            self.assertEqual(report["pending_producer_count"], 0)
            self.assertEqual(report["accepted_producers"][0]["producer_id"], PID)
        finally:
            td.cleanup()

    def test_mismatched_decision_coverage_is_rejected(self):
        td, root = self._root()
        try:
            rec = self._record(root)
            self._producer(root, decisions=rec["source_decision_ids"][:-1])
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertEqual(report["registered_producer_count"], 0)
        finally:
            td.cleanup()

    def test_adapter_digest_tamper_is_rejected(self):
        td, root = self._root()
        try:
            adapter, _ = self._producer(root)
            adapter.write_text("tampered\n")
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertTrue(any(
                "digest mismatch" in detail
                for item in report["blocking_findings"]
                for detail in item.get("findings", [])
            ))
        finally:
            td.cleanup()

    def test_invariant_weakening_is_rejected(self):
        td, root = self._root()
        try:
            path = root / "canonical/current-host-capability-qualification-constituent-producers.json"
            registry = json.loads(path.read_text())
            registry["invariants"]["unregistered_manifest_allowed"] = True
            path.write_text(json.dumps(registry))
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertTrue(any(item["code"] == "QCPA-009" for item in report["blocking_findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
