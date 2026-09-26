import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_test_qualification_audit import audit

QID = "FA3-QUAL-CAP-001-POS-001"

class QualificationAuditTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        (root / "canonical").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        shutil.copy(ROOT / "canonical/current-host-capability-test-qualifications.json", root / "canonical/current-host-capability-test-qualifications.json")
        qpath = root / "canonical/current-host-capability-test-qualifications.json"
        qreg = json.loads(qpath.read_text())
        qreg["entries"] = []
        qpath.write_text(json.dumps(qreg))
        return td, root

    def _record(self, root):
        data = json.loads((root / "evidence/evidence-registry.json").read_text())
        return next(row for row in data["records"] if row["subject_id"] == "CAP-001")

    def _add(self, root, *, partial=False, overlap=False, qid=QID):
        rec = self._record(root)
        decisions = list(rec["source_decision_ids"])
        covered = decisions[:-1] if partial else decisions
        constituents = [{
            "constituent_id": "CAP001-POS-ALL",
            "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION",
            "covers_source_decision_ids": covered,
        }]
        if overlap:
            constituents.append({
                "constituent_id": "CAP001-POS-OVERLAP",
                "source_evidence_class": "COMPONENT_CURRENT_HOST_EXECUTION",
                "covers_source_decision_ids": [decisions[0]],
            })
        path = root / "canonical/current-host-capability-test-qualifications.json"
        registry = json.loads(path.read_text())
        registry["entries"].append({
            "qualification_id": qid,
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
                "source_decision_ids": decisions,
            },
            "required_constituents": constituents,
        })
        path.write_text(json.dumps(registry))

    def test_empty_registry_is_pending(self):
        td, root = self._root()
        try:
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["qualified_definition_count"], 0)
            self.assertEqual(report["pending_definition_count"], 525)
        finally:
            td.cleanup()

    def test_exact_complete_definition_is_accepted(self):
        td, root = self._root()
        try:
            self._add(root)
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["qualified_definition_count"], 1)
            self.assertEqual(report["accepted_qualifications"][0]["qualification_id"], QID)
        finally:
            td.cleanup()

    def test_partial_and_overlapping_decision_coverage_are_rejected(self):
        for mode in ("partial", "overlap"):
            td, root = self._root()
            try:
                self._add(root, partial=mode == "partial", overlap=mode == "overlap")
                report = audit(root)
                self.assertEqual(report["audit_integrity"], "FAIL")
                self.assertEqual(report["qualified_definition_count"], 0)
            finally:
                td.cleanup()

    def test_qualification_id_must_encode_exact_capability_and_kind(self):
        td, root = self._root()
        try:
            self._add(root, qid="FA3-QUAL-CAP-002-POS-001")
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            details = [d for finding in report["blocking_findings"] for d in finding.get("findings", [])]
            self.assertTrue(any("exact subject_id/test_kind" in d for d in details))
        finally:
            td.cleanup()

if __name__ == "__main__":
    unittest.main()
