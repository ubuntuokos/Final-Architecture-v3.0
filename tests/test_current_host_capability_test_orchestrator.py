import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_test_orchestrator import orchestrate

QID = "FA3-QUAL-CAP-001-POS-001"

class OrchestratorTests(unittest.TestCase):
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
        return td, root

    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _add_valid(self, root):
        evidence = json.loads((root / "evidence/evidence-registry.json").read_text())
        rec = next(row for row in evidence["records"] if row["subject_id"] == "CAP-001")
        qpath = root / "canonical/current-host-capability-test-qualifications.json"
        qreg = json.loads(qpath.read_text())
        qreg["entries"].append({
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
            "required_constituents": [{"constituent_id": "CAP001-POS-ALL", "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION", "covers_source_decision_ids": rec["source_decision_ids"]}],
        })
        qpath.write_text(json.dumps(qreg))
        adapter = root / "src/fa3_current_host_capability_test_qualifier.py"
        epath = root / "canonical/current-host-capability-test-executors.json"
        ereg = json.loads(epath.read_text())
        ereg["entries"].append({
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
            "timeout_seconds": 30,
            "ttl_seconds": 3600,
        })
        epath.write_text(json.dumps(ereg))
        return adapter

    def test_empty_registry_is_pending_without_pass_claim(self):
        td, root = self._root()
        try:
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["status"], "PENDING_EXECUTOR_REGISTRATION")
            self.assertEqual(report["results_materialized"], 0)
        finally:
            td.cleanup()

    def test_qualified_registered_executor_is_not_run_in_hosted_dry_run(self):
        td, root = self._root()
        try:
            self._add_valid(root)
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["status"], "REGISTERED_EXECUTORS_NOT_EXECUTED")
            self.assertEqual(report["registered_executor_count"], 1)
            self.assertEqual(report["results_materialized"], 0)
        finally:
            td.cleanup()

    def test_direct_component_adapter_is_blocked_before_execution(self):
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
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["results_materialized"], 0)
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_missing_host_fingerprint_blocks_real_execution(self):
        td, root = self._root()
        try:
            self._add_valid(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertTrue(any(item["code"] == "CHOR-004" for item in report["blocking_findings"]))
            self.assertEqual(report["results_materialized"], 0)
        finally:
            td.cleanup()

if __name__ == "__main__":
    unittest.main()
