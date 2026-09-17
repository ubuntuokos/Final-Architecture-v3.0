import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_test_executor_audit import audit


class CurrentHostCapabilityTestExecutorAuditTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        (root / "canonical").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        shutil.copy(
            ROOT / "canonical/current-host-capability-test-executors.json",
            root / "canonical/current-host-capability-test-executors.json",
        )
        return td, root

    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _registry(self, root):
        path = root / "canonical/current-host-capability-test-executors.json"
        return path, json.loads(path.read_text())

    def _add_valid_entry(self, root, *, kind="positive", test_id="AT-CAP-001-POS"):
        adapter = root / "bin/cap001-test"
        adapter.parent.mkdir(parents=True, exist_ok=True)
        adapter.write_text("#!/usr/bin/env python3\nprint('capability-specific current-host verifier')\n")
        path, registry = self._registry(root)
        registry["entries"].append({
            "subject_id": "CAP-001",
            "test_kind": kind,
            "test_id": test_id,
            "adapter_path": "bin/cap001-test",
            "adapter_sha256": self._sha(adapter),
            "evidence_class": "CAPABILITY_SPECIFIC_EXECUTABLE_TEST",
            "execution_mode": "REAL_CURRENT_HOST_EXECUTION",
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "argv": [],
        })
        path.write_text(json.dumps(registry))
        return adapter

    def test_empty_registry_is_integrity_pass_but_429_pending(self):
        td, root = self._root()
        try:
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["coverage_status"], "PENDING_EXECUTOR_REGISTRATION")
            self.assertEqual(report["required_test_obligation_count"], 429)
            self.assertEqual(report["registered_executor_count"], 0)
            self.assertEqual(report["pending_executor_count"], 429)
            self.assertEqual(len(report["pending_obligations"]), 429)
            self.assertEqual(report["pending_obligations"][0]["test_id"], "AT-CAP-001-POS")
            self.assertFalse(report["truth_constraints"]["unregistered_test_may_emit_pass_result"])
        finally:
            td.cleanup()

    def test_one_exact_registration_gives_partial_coverage_only(self):
        td, root = self._root()
        try:
            self._add_valid_entry(root)
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "PASS")
            self.assertEqual(report["coverage_status"], "PARTIAL_EXPLICIT_EXECUTOR_COVERAGE")
            self.assertEqual(report["registered_executor_count"], 1)
            self.assertEqual(report["pending_executor_count"], 428)
            self.assertEqual(report["registered_obligations"][0]["test_id"], "AT-CAP-001-POS")
            self.assertFalse(report["global_promotion_claim"])
        finally:
            td.cleanup()

    def test_wrong_test_identity_is_rejected(self):
        td, root = self._root()
        try:
            self._add_valid_entry(root, test_id="AT-WRONG")
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertEqual(report["registered_executor_count"], 0)
            self.assertTrue(any(
                "test_id mismatch" in detail
                for finding in report["blocking_findings"]
                for detail in finding.get("findings", [])
            ))
        finally:
            td.cleanup()

    def test_duplicate_registration_is_rejected(self):
        td, root = self._root()
        try:
            adapter = self._add_valid_entry(root)
            path, registry = self._registry(root)
            duplicate = dict(registry["entries"][0])
            duplicate["adapter_sha256"] = self._sha(adapter)
            registry["entries"].append(duplicate)
            path.write_text(json.dumps(registry))
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertTrue(any(
                "duplicate" in detail
                for finding in report["blocking_findings"]
                for detail in finding.get("findings", [])
            ))
        finally:
            td.cleanup()

    def test_provider_or_synthetic_substitution_is_rejected(self):
        for field in ("provider_receipt_only", "generic_host_collection_only", "synthetic", "ci_reference_only"):
            with self.subTest(field=field):
                td, root = self._root()
                try:
                    self._add_valid_entry(root)
                    path, registry = self._registry(root)
                    registry["entries"][0][field] = True
                    path.write_text(json.dumps(registry))
                    report = audit(root)
                    self.assertEqual(report["audit_integrity"], "FAIL")
                    self.assertEqual(report["registered_executor_count"], 0)
                finally:
                    td.cleanup()

    def test_adapter_digest_mismatch_is_rejected(self):
        td, root = self._root()
        try:
            adapter = self._add_valid_entry(root)
            adapter.write_text("tampered\n")
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertTrue(any(
                "digest mismatch" in detail
                for finding in report["blocking_findings"]
                for detail in finding.get("findings", [])
            ))
        finally:
            td.cleanup()

    def test_shell_or_privilege_escalation_argv_is_rejected(self):
        for token in ("sudo", "bash", "-c"):
            with self.subTest(token=token):
                td, root = self._root()
                try:
                    self._add_valid_entry(root)
                    path, registry = self._registry(root)
                    registry["entries"][0]["argv"] = [token]
                    path.write_text(json.dumps(registry))
                    report = audit(root)
                    self.assertEqual(report["audit_integrity"], "FAIL")
                finally:
                    td.cleanup()

    def test_registry_invariant_weakening_is_rejected(self):
        td, root = self._root()
        try:
            path, registry = self._registry(root)
            registry["invariants"]["provider_receipt_substitution_allowed"] = True
            path.write_text(json.dumps(registry))
            report = audit(root)
            self.assertEqual(report["audit_integrity"], "FAIL")
            self.assertTrue(any(f["code"] == "CHEX-008" for f in report["blocking_findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
