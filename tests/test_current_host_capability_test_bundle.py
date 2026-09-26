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

from fa3_current_host_capability_test_bundle import (
    RESULT_SCHEMA,
    BUNDLE_SCHEMA,
    materialize,
)


class CurrentHostCapabilityTestBundleAssemblerTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        host_dir = root / ".fa3-current-host/global-closure/host"
        host_dir.mkdir(parents=True)
        host = host_dir / "host-fingerprint.json"
        host.write_text('{"schema":"fa3.host-fingerprint.evidence.v1","host":"test-current-host"}\n')
        return td, root, host

    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _write_result(self, root, host, kind, **overrides):
        registry = json.loads((root / "evidence/evidence-registry.json").read_text())
        record = registry["records"][0]
        expected = {
            "positive": record["required_positive_test"],
            "negative": record["required_negative_test"],
            "rollback": record["rollback_requirement"],
        }[kind]
        cap_dir = root / ".fa3-current-host/test-results/capabilities/CAP-001"
        cap_dir.mkdir(parents=True, exist_ok=True)
        artifact = cap_dir / f"{kind}.log"
        artifact.write_text(f"real current-host {kind} trace\n")
        now = datetime.now(timezone.utc)
        obj = {
            "schema": RESULT_SCHEMA,
            "subject_id": "CAP-001",
            "test_kind": kind,
            "test_id": expected,
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "global_promotion_claim": False,
            "collected_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "host_fingerprint_path": ".fa3-current-host/global-closure/host/host-fingerprint.json",
            "host_fingerprint_sha256": self._sha(host),
            "artifact_path": f".fa3-current-host/test-results/capabilities/CAP-001/{kind}.log",
            "artifact_sha256": self._sha(artifact),
            "executor": {
                "id": f"TEST-CURRENT-HOST-{kind.upper()}",
                "mode": "REAL_CURRENT_HOST_EXECUTION",
                "synthetic": False,
            },
        }
        obj.update(overrides)
        path = cap_dir / f"{kind}.json"
        path.write_text(json.dumps(obj))
        return path

    def _write_complete_cap001(self, root, host):
        for kind in ("positive", "negative", "rollback"):
            self._write_result(root, host, kind)

    def test_empty_results_are_pending_and_emit_exact_143_plan(self):
        td, root, _ = self._root()
        try:
            report = materialize(root)
            self.assertEqual(report["assembler_integrity"], "PASS")
            self.assertEqual(report["materialization_status"], "PENDING_CURRENT_HOST_TEST_RESULTS")
            self.assertEqual(report["bundles_materialized"], 0)
            self.assertEqual(report["pending_capability_count"], 175)
            plan = json.loads((root / ".fa3-current-host/test-plan/capabilities.json").read_text())
            self.assertEqual(plan["capability_count"], 175)
            self.assertEqual(len(plan["capabilities"]), 175)
            self.assertEqual(plan["capabilities"][0]["tests"]["positive"]["test_id"], "AT-CAP-001-POS")
            self.assertFalse(plan["provider_receipt_substitution_allowed"])
        finally:
            td.cleanup()

    def test_three_valid_real_results_materialize_one_bundle(self):
        td, root, host = self._root()
        try:
            self._write_complete_cap001(root, host)
            report = materialize(root)
            self.assertEqual(report["assembler_integrity"], "PASS")
            self.assertEqual(report["bundles_materialized"], 1)
            self.assertEqual(report["pending_capability_count"], 142)
            bundle_path = root / ".fa3-current-host/test-bundles/capabilities/CAP-001.json"
            self.assertTrue(bundle_path.is_file())
            bundle = json.loads(bundle_path.read_text())
            self.assertEqual(bundle["schema"], BUNDLE_SCHEMA)
            self.assertEqual(bundle["execution_scope"], "CURRENT_HOST")
            self.assertFalse(bundle["synthetic"])
            self.assertEqual(bundle["tests"]["positive"]["id"], "AT-CAP-001-POS")
            self.assertEqual(bundle["tests"]["negative"]["id"], "AT-CAP-001-NEG")
            self.assertEqual(bundle["tests"]["rollback"]["id"], "ROLLBACK-CAP-001")
            artifact_paths = {item["path"] for item in bundle["evidence_artifacts"]}
            self.assertIn(".fa3-current-host/test-results/capabilities/CAP-001/positive.json", artifact_paths)
            self.assertIn(".fa3-current-host/global-closure/host/host-fingerprint.json", artifact_paths)
        finally:
            td.cleanup()

    def test_partial_results_remain_pending_without_fabricating_bundle(self):
        td, root, host = self._root()
        try:
            self._write_result(root, host, "positive")
            report = materialize(root)
            self.assertEqual(report["assembler_integrity"], "PASS")
            self.assertEqual(report["bundles_materialized"], 0)
            row = report["capabilities"][0]
            self.assertEqual(row["status"], "PENDING_TEST_RESULTS")
            self.assertEqual(row["missing_test_kinds"], ["negative", "rollback"])
        finally:
            td.cleanup()

    def test_wrong_registry_test_identity_is_rejected(self):
        td, root, host = self._root()
        try:
            self._write_complete_cap001(root, host)
            path = root / ".fa3-current-host/test-results/capabilities/CAP-001/negative.json"
            obj = json.loads(path.read_text())
            obj["test_id"] = "AT-WRONG"
            path.write_text(json.dumps(obj))
            report = materialize(root)
            self.assertEqual(report["assembler_integrity"], "FAIL")
            self.assertEqual(report["bundles_materialized"], 0)
            self.assertTrue(any("test_id mismatch" in item for item in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_synthetic_ci_or_provider_style_result_is_rejected(self):
        cases = [
            ("synthetic", True),
            ("ci_reference_only", True),
            ("schema", "fa3.ai-infra-guard-current-host-receipt.v1"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                td, root, host = self._root()
                try:
                    self._write_complete_cap001(root, host)
                    path = root / ".fa3-current-host/test-results/capabilities/CAP-001/positive.json"
                    obj = json.loads(path.read_text())
                    obj[field] = value
                    path.write_text(json.dumps(obj))
                    report = materialize(root)
                    self.assertEqual(report["assembler_integrity"], "FAIL")
                    self.assertEqual(report["bundles_materialized"], 0)
                finally:
                    td.cleanup()

    def test_artifact_digest_mismatch_is_rejected(self):
        td, root, host = self._root()
        try:
            self._write_complete_cap001(root, host)
            artifact = root / ".fa3-current-host/test-results/capabilities/CAP-001/rollback.log"
            artifact.write_text("tampered\n")
            report = materialize(root)
            self.assertEqual(report["assembler_integrity"], "FAIL")
            self.assertTrue(any("digest mismatch" in item for item in report["blocking_findings"][0]["findings"]))
        finally:
            td.cleanup()

    def test_mixed_host_fingerprints_are_rejected(self):
        td, root, host = self._root()
        try:
            self._write_complete_cap001(root, host)
            other = root / ".fa3-current-host/global-closure/host/other-host.json"
            other.write_text('{"host":"other"}\n')
            path = root / ".fa3-current-host/test-results/capabilities/CAP-001/rollback.json"
            obj = json.loads(path.read_text())
            obj["host_fingerprint_path"] = ".fa3-current-host/global-closure/host/other-host.json"
            obj["host_fingerprint_sha256"] = self._sha(other)
            path.write_text(json.dumps(obj))
            report = materialize(root)
            self.assertEqual(report["assembler_integrity"], "FAIL")
            self.assertTrue(any(
                "one host fingerprint" in item
                for finding in report["blocking_findings"]
                for item in finding.get("findings", [])
            ))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
