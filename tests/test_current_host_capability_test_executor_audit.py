import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_test_executor_audit import audit

QID = "FA3-QUAL-CAP-001-POS-001"

class ExecutorAuditTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        (root / "canonical").mkdir(parents=True)
        (root / "src").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        shutil.copy(ROOT / "canonical/current-host-capability-test-executors.json", root / "canonical/current-host-capability-test-executors.json")
        shutil.copy(ROOT / "canonical/current-host-capability-test-qualifications.json", root / "canonical/current-host-capability-test-qualifications.json")
        shutil.copy(ROOT / "src/fa3_current_host_capability_test_qualifier.py", root / "src/fa3_current_host_capability_test_qualifier.py")
        for rel in (
            "canonical/current-host-capability-test-executors.json",
            "canonical/current-host-capability-test-qualifications.json",
        ):
            path = root / rel
            registry = json.loads(path.read_text())
            registry["entries"] = []
            path.write_text(json.dumps(registry))
        return td, root

    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _record(self, root):
        data = json.loads((root / "evidence/evidence-registry.json").read_text())
        return next(row for row in data["records"] if row["subject_id"] == "CAP-001")

    def _qualify(self, root):
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
            "completeness_basis": {"type": "EXACT_EVIDENCE_REGISTRY_SOURCE_DECISION_COVERAGE", "source_decision_ids": rec["source_decision_ids"]},
            "required_constituents": [{"constituent_id": "CAP001-POS-ALL", "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION", "covers_source_decision_ids": rec["source_decision_ids"]}],
        })
        path.write_text(json.dumps(registry))
        return rec

    def _add_valid(self, root):
        rec = self._qualify(root)
        adapter = root / "src/fa3_current_host_capability_test_qualifier.py"
        path = root / "canonical/current-host-capability-test-executors.json"
        registry = json.loads(path.read_text())
        registry["entries"].append({
            "subject_id": "CAP-001",
            "test_kind": "positive",
            "test_id": rec["required_positive_test"],
            "qualification_id": QID,
            "adapter_path": "src/fa3_current_host_capability_test_qualifier.py",
            "adapter_sha256": self._sha(adapter),
            "evidence_class": "CAPABILITY_SPECIFIC_EXECUTABLE_TEST",
            "execution_mode": "REAL_CURRENT_HOST_EXECUTION",
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "argv": ["--qualification-id", QID],
        })
        path.write_text(json.dumps(registry))
        return adapter

    def test_empty_registry_is_integrity_pass_but_525_pending(self):
        td, root = self._root()
        try:
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["registered_executor_count"], 0)
            self.assertEqual(report["pending_executor_count"], 525)
            self.assertEqual(report["qualified_definition_count"], 0)
        finally:
            td.cleanup()

    def test_exact_qualified_registration_gives_partial_coverage(self):
        td, root = self._root()
        try:
            self._add_valid(root)
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["coverage_status"], "PARTIAL_EXPLICIT_EXECUTOR_COVERAGE")
            self.assertEqual(report["registered_executor_count"], 1)
            self.assertEqual(report["qualified_definition_count"], 1)
        finally:
            td.cleanup()

    def test_direct_component_adapter_is_rejected(self):
        td, root = self._root()
        try:
            self._add_valid(root)
            direct = root / "bin/component-test"
            direct.parent.mkdir(parents=True)
            direct.write_text("#!/usr/bin/env python3\n")
            path = root / "canonical/current-host-capability-test-executors.json"
            registry = json.loads(path.read_text())
            registry["entries"][0]["adapter_path"] = "bin/component-test"
            registry["entries"][0]["adapter_sha256"] = self._sha(direct)
            path.write_text(json.dumps(registry))
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            details = [d for f in report["blocking_findings"] for d in f.get("findings", [])]
            self.assertTrue(any("direct component/provider adapters are forbidden" in d for d in details))
        finally:
            td.cleanup()

    def test_wrong_qualification_binding_is_rejected(self):
        td, root = self._root()
        try:
            self._add_valid(root)
            path = root / "canonical/current-host-capability-test-executors.json"
            registry = json.loads(path.read_text())
            registry["entries"][0]["qualification_id"] = "FA3-QUAL-CAP-001-POS-999"
            registry["entries"][0]["argv"] = ["--qualification-id", "FA3-QUAL-CAP-001-POS-999"]
            path.write_text(json.dumps(registry))
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertEqual(report["registered_executor_count"], 0)
        finally:
            td.cleanup()

    def test_adapter_digest_tamper_is_rejected(self):
        td, root = self._root()
        try:
            adapter = self._add_valid(root)
            adapter.write_text("tampered\n")
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertTrue(any("digest mismatch" in d for f in report["blocking_findings"] for d in f.get("findings", [])))
        finally:
            td.cleanup()

    def test_registry_invariant_weakening_is_rejected(self):
        td, root = self._root()
        try:
            path = root / "canonical/current-host-capability-test-executors.json"
            registry = json.loads(path.read_text())
            registry["invariants"]["direct_component_adapter_allowed"] = True
            path.write_text(json.dumps(registry))
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertTrue(any(item["code"] == "CHEX-008" for item in report["blocking_findings"]))
        finally:
            td.cleanup()

if __name__ == "__main__":
    unittest.main()
