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
            ROOT / "canonical/current-host-capability-test-registry.json",
            root / "canonical/current-host-capability-test-registry.json",
        )
        return td, root

    def _plan(self, root):
        evidence = json.loads((root / "evidence/evidence-registry.json").read_text())
        record = evidence["records"][0]
        registry_path = root / "canonical/current-host-capability-test-registry.json"
        registry = json.loads(registry_path.read_text())
        registry["records"] = [
            {
                "subject_id": "CAP-001",
                "enabled": True,
                "execution_scope": "CURRENT_HOST",
                "shell": False,
                "working_directory": ".",
                "ttl_seconds": 3600,
                "tests": {
                    "positive": {
                        "id": record["required_positive_test"],
                        "argv": [sys.executable, "-c", "print('positive-pass')"],
                        "timeout_seconds": 30,
                    },
                    "negative": {
                        "id": record["required_negative_test"],
                        "argv": [sys.executable, "-c", "print('negative-rejection-proven')"],
                        "timeout_seconds": 30,
                    },
                    "rollback": {
                        "id": record["rollback_requirement"],
                        "argv": [sys.executable, "-c", "print('rollback-pass')"],
                        "timeout_seconds": 30,
                    },
                },
            }
        ]
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        return registry

    def test_empty_registry_is_pending_not_pass_claim(self):
        td, root = self._root()
        try:
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["status"], "PENDING_CURRENT_HOST_TEST_PLAN_MATERIALIZATION")
            self.assertEqual(report["registered_plan_count"], 0)
            self.assertEqual(report["unregistered_capability_count"], 143)
            self.assertEqual(report["bundles_materialized"], 0)
            self.assertFalse(report["global_promotion_claim"])
        finally:
            td.cleanup()

    def test_valid_plan_is_registered_without_execution(self):
        td, root = self._root()
        try:
            self._plan(root)
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["registered_plan_count"], 1)
            self.assertEqual(report["unregistered_capability_count"], 142)
            self.assertEqual(report["bundles_materialized"], 0)
        finally:
            td.cleanup()

    def test_wrong_test_id_is_blocking(self):
        td, root = self._root()
        try:
            registry = self._plan(root)
            registry["records"][0]["tests"]["negative"]["id"] = "AT-WRONG"
            (root / "canonical/current-host-capability-test-registry.json").write_text(json.dumps(registry))
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertTrue(any(item["code"] == "CHT-009" for item in report["blocking_findings"]))
        finally:
            td.cleanup()

    def test_shell_execution_is_rejected(self):
        td, root = self._root()
        try:
            registry = self._plan(root)
            registry["records"][0]["shell"] = True
            (root / "canonical/current-host-capability-test-registry.json").write_text(json.dumps(registry))
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertTrue(any(
                "shell execution is forbidden" in finding
                for finding in report["blocking_findings"][0]["findings"]
            ))
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "current-host execution must be non-root")
    def test_execute_valid_plan_materializes_hash_bound_bundle(self):
        td, root = self._root()
        try:
            self._plan(root)
            host = root / ".fa3-current-host/global-closure/host/host-fingerprint.json"
            host.parent.mkdir(parents=True)
            host.write_text('{"schema":"fa3.host-fingerprint.evidence.v1","status":"COLLECTED_UNVALIDATED"}\n')
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["bundles_materialized"], 1)
            bundle_path = root / ".fa3-current-host/test-bundles/capabilities/CAP-001.json"
            self.assertTrue(bundle_path.is_file())
            bundle = json.loads(bundle_path.read_text())
            self.assertEqual(bundle["schema"], "fa3.capability-current-host-test-bundle.v1")
            self.assertEqual(bundle["status"], "PASS")
            self.assertFalse(bundle["synthetic"])
            self.assertFalse(bundle["ci_reference_only"])
            self.assertFalse(bundle["global_promotion_claim"])
            self.assertEqual({x["status"] for x in bundle["tests"].values()}, {"PASS"})
            paths = {x["path"] for x in bundle["evidence_artifacts"]}
            self.assertIn(".fa3-current-host/global-closure/host/host-fingerprint.json", paths)
            self.assertIn(".fa3-current-host/test-artifacts/CAP-001/positive.json", paths)
            self.assertIn(".fa3-current-host/test-artifacts/CAP-001/negative.json", paths)
            self.assertIn(".fa3-current-host/test-artifacts/CAP-001/rollback.json", paths)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
