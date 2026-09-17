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


class CurrentHostCapabilityTestOrchestratorTests(unittest.TestCase):
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

    def _record(self, root, cap="CAP-001"):
        evidence = json.loads((root / "evidence/evidence-registry.json").read_text())
        return next(row for row in evidence["records"] if row["subject_id"] == cap)

    def _registry(self, root):
        path = root / "canonical/current-host-capability-test-executors.json"
        return path, json.loads(path.read_text())

    def _adapter_source(self, mode="pass"):
        if mode == "exit-fail":
            return "raise SystemExit(7)\n"
        outside = mode == "outside-artifact"
        wrong_status = mode == "wrong-status"
        return f'''import hashlib\nimport json\nimport os\nfrom pathlib import Path\n\nroot = Path(os.environ["FA3_REPOSITORY_ROOT"])\nartifact_dir = Path(os.environ["FA3_TEST_ARTIFACT_DIR"])\nif {outside!r}:\n    artifact = root / ".fa3-current-host/outside-artifact.json"\n    artifact.parent.mkdir(parents=True, exist_ok=True)\nelse:\n    artifact = artifact_dir / "evidence.json"\nartifact.write_text(json.dumps({{"cap": os.environ["FA3_CAPABILITY_ID"], "kind": os.environ["FA3_TEST_KIND"]}}) + "\\n", encoding="utf-8")\ndigest = hashlib.sha256(artifact.read_bytes()).hexdigest()\nverdict = {{\n    "schema": "fa3.capability-current-host-test-verdict.v1",\n    "subject_id": os.environ["FA3_CAPABILITY_ID"],\n    "test_kind": os.environ["FA3_TEST_KIND"],\n    "test_id": os.environ["FA3_TEST_ID"],\n    "status": {"'FAIL'" if wrong_status else "'PASS'"},\n    "execution_scope": "CURRENT_HOST",\n    "current_host": True,\n    "synthetic": False,\n    "ci_reference_only": False,\n    "global_promotion_claim": False,\n    "evidence_class": "CAPABILITY_SPECIFIC_EXECUTABLE_TEST",\n    "artifact_path": artifact.relative_to(root).as_posix(),\n    "artifact_sha256": digest,\n}}\nprint(json.dumps(verdict))\n'''

    def _add_entry(self, root, *, kind="positive", mode="pass"):
        record = self._record(root)
        test_id = {
            "positive": record["required_positive_test"],
            "negative": record["required_negative_test"],
            "rollback": record["rollback_requirement"],
        }[kind]
        adapter = root / f"src/cap001-{kind}-adapter.py"
        adapter.parent.mkdir(parents=True, exist_ok=True)
        adapter.write_text(self._adapter_source(mode), encoding="utf-8")
        registry_path, registry = self._registry(root)
        registry["entries"].append({
            "subject_id": "CAP-001",
            "test_kind": kind,
            "test_id": test_id,
            "adapter_path": adapter.relative_to(root).as_posix(),
            "adapter_sha256": self._sha(adapter),
            "evidence_class": "CAPABILITY_SPECIFIC_EXECUTABLE_TEST",
            "execution_mode": "REAL_CURRENT_HOST_EXECUTION",
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "argv": [],
            "timeout_seconds": 30,
            "ttl_seconds": 3600,
        })
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        return adapter

    def _host(self, root):
        host = root / ".fa3-current-host/global-closure/host/host-fingerprint.json"
        host.parent.mkdir(parents=True, exist_ok=True)
        host.write_text(
            '{"schema":"fa3.host-fingerprint.evidence.v1","status":"COLLECTED_UNVALIDATED"}\n',
            encoding="utf-8",
        )
        return host

    def test_empty_registry_is_pending_without_execution_or_pass_claim(self):
        td, root = self._root()
        try:
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["status"], "PENDING_EXECUTOR_REGISTRATION")
            self.assertEqual(report["registered_executor_count"], 0)
            self.assertEqual(report["pending_executor_count"], 429)
            self.assertEqual(report["results_materialized"], 0)
            self.assertFalse(report["global_promotion_claim"])
        finally:
            td.cleanup()

    def test_registered_executor_is_not_run_without_execute(self):
        td, root = self._root()
        try:
            adapter = self._add_entry(root)
            marker = root / ".fa3-current-host/test-artifacts/capabilities/CAP-001/positive/evidence.json"
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["status"], "REGISTERED_EXECUTORS_NOT_EXECUTED")
            self.assertEqual(report["registered_executor_count"], 1)
            self.assertEqual(report["results_materialized"], 0)
            self.assertTrue(adapter.is_file())
            self.assertFalse(marker.exists())
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_registered_executor_materializes_typed_hash_bound_result(self):
        td, root = self._root()
        try:
            self._add_entry(root)
            self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["status"], "EXECUTED_REGISTERED_CAPABILITY_TESTS")
            self.assertEqual(report["results_materialized"], 1)
            result_path = root / ".fa3-current-host/test-results/capabilities/CAP-001/positive.json"
            self.assertTrue(result_path.is_file())
            result = json.loads(result_path.read_text())
            self.assertEqual(result["schema"], "fa3.capability-current-host-test-result.v1")
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["synthetic"])
            self.assertFalse(result["ci_reference_only"])
            self.assertFalse(result["global_promotion_claim"])
            self.assertTrue(
                result["artifact_path"].startswith(
                    ".fa3-current-host/test-artifacts/capabilities/CAP-001/positive/"
                )
            )
            artifact = root / result["artifact_path"]
            self.assertEqual(self._sha(artifact), result["artifact_sha256"])
            self.assertEqual(
                result["executor"]["artifact_scope"],
                ".fa3-current-host/test-artifacts/capabilities/CAP-001/positive",
            )
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_artifact_outside_obligation_scope_is_rejected(self):
        td, root = self._root()
        try:
            self._add_entry(root, mode="outside-artifact")
            self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["results_materialized"], 0)
            self.assertTrue(any(
                "obligation-scoped" in detail
                for finding in report["blocking_findings"]
                for detail in finding.get("findings", [])
            ))
            self.assertFalse(
                (root / ".fa3-current-host/test-results/capabilities/CAP-001/positive.json").exists()
            )
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_typed_verdict_is_required_not_exit_code_alone(self):
        td, root = self._root()
        try:
            self._add_entry(root, mode="wrong-status")
            self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["results_materialized"], 0)
            self.assertTrue(any(
                "status mismatch" in detail
                for finding in report["blocking_findings"]
                for detail in finding.get("findings", [])
            ))
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_failed_run_removes_partial_pass_result_manifests(self):
        td, root = self._root()
        try:
            self._add_entry(root, kind="positive", mode="pass")
            self._add_entry(root, kind="negative", mode="exit-fail")
            self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["results_materialized"], 0)
            self.assertFalse((root / ".fa3-current-host/test-results/capabilities").exists())
            self.assertEqual(report["executions"][0]["status"], "PASS")
            self.assertEqual(report["executions"][1]["status"], "REJECTED")
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_missing_host_fingerprint_blocks_real_execution(self):
        td, root = self._root()
        try:
            self._add_entry(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["results_materialized"], 0)
            self.assertTrue(any(item["code"] == "CHOR-004" for item in report["blocking_findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
