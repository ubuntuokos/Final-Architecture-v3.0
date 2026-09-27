import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_evidence_validation import validate_capability_receipt
from fa3_enforce import runtime_check


class EvidenceValidationCoreTests(unittest.TestCase):
    SOURCE = "a" * 40

    def _fixture(self, expired=False):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence/receipts/capabilities").mkdir(parents=True)
        (root / "evidence/runtime/CAP-001").mkdir(parents=True)
        record = {
            "subject_id": "CAP-001",
            "required_positive_test": "AT-CAP-001-POS",
            "required_negative_test": "AT-CAP-001-NEG",
            "rollback_requirement": "ROLLBACK-CAP-001",
        }
        runtime = root / "evidence/runtime/CAP-001/runtime.log"
        host = root / "evidence/runtime/CAP-001/host-fingerprint.json"
        runtime.write_text("physical trace\n")
        host.write_text('{"host":"fixture"}\n')
        rh = hashlib.sha256(runtime.read_bytes()).hexdigest()
        hh = hashlib.sha256(host.read_bytes()).hexdigest()
        now = datetime.now(timezone.utc)
        collected = now - timedelta(days=2) if expired else now - timedelta(hours=1)
        expires = now - timedelta(days=1) if expired else now + timedelta(days=7)
        receipt = {
            "schema": "fa3.capability-current-host-evidence.v1",
            "subject_id": "CAP-001",
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "source_commit": self.SOURCE,
            "host_fingerprint_path": "evidence/runtime/CAP-001/host-fingerprint.json",
            "host_fingerprint_sha256": hh,
            "collected_at": collected.isoformat(),
            "expires_at": expires.isoformat(),
            "tests": {
                "positive": {"id": "AT-CAP-001-POS", "status": "PASS", "artifact_sha256": rh},
                "negative": {"id": "AT-CAP-001-NEG", "status": "PASS", "artifact_sha256": rh},
                "rollback": {"id": "ROLLBACK-CAP-001", "status": "PASS", "artifact_sha256": rh},
            },
            "evidence_artifacts": [
                {"path": "evidence/runtime/CAP-001/runtime.log", "sha256": rh},
                {"path": "evidence/runtime/CAP-001/host-fingerprint.json", "sha256": hh},
            ],
        }
        path = root / "evidence/receipts/capabilities/CAP-001.json"
        path.write_text(json.dumps(receipt))
        return td, root, record, receipt

    def test_valid_receipt_qualifies_for_exact_source(self):
        td, root, record, _ = self._fixture()
        try:
            result = validate_capability_receipt(root, record, expected_source_commit=self.SOURCE)
            self.assertTrue(result["qualified"], result)
        finally:
            td.cleanup()

    def test_expired_pass_receipt_is_rejected(self):
        td, root, record, _ = self._fixture(expired=True)
        try:
            result = validate_capability_receipt(root, record, expected_source_commit=self.SOURCE)
            self.assertFalse(result["qualified"])
            self.assertIn("receipt expired", result["findings"])
        finally:
            td.cleanup()

    def test_receipt_from_other_source_commit_is_rejected(self):
        td, root, record, _ = self._fixture()
        try:
            result = validate_capability_receipt(root, record, expected_source_commit="b" * 40)
            self.assertFalse(result["qualified"])
            self.assertIn("source_commit does not match current repository HEAD", result["findings"])
        finally:
            td.cleanup()

    def test_modified_artifact_is_rejected(self):
        td, root, record, _ = self._fixture()
        try:
            (root / "evidence/runtime/CAP-001/runtime.log").write_text("tampered\n")
            result = validate_capability_receipt(root, record, expected_source_commit=self.SOURCE)
            self.assertFalse(result["qualified"])
            self.assertTrue(any("digest mismatch" in x for x in result["findings"]))
        finally:
            td.cleanup()

    def test_runtime_gate_requalifies_pass_records_before_decision(self):
        td, root, _, receipt = self._fixture(expired=True)
        try:
            records = []
            for i in range(1, 176):
                cap = f"CAP-{i:03d}"
                records.append({
                    "subject_id": cap,
                    "status": "PASS" if i == 1 else "PENDING_CURRENT_HOST",
                    "required_positive_test": f"AT-{cap}-POS",
                    "required_negative_test": f"AT-{cap}-NEG",
                    "rollback_requirement": f"ROLLBACK-{cap}",
                })
            registry = {
                "architecture_release": "TEST-RELEASE",
                "records": records,
            }
            (root / "evidence/evidence-registry.json").write_text(json.dumps(registry))
            (root / "reports").mkdir(parents=True)
            with patch("fa3_enforce.active_release_values", return_value=("TEST-RELEASE", 175)),                  patch("fa3_enforce.git_head", return_value=self.SOURCE):
                report = runtime_check(root)
            finding = next(x for x in report["findings"] if x["code"] == "FA3-RUNTIME-004")
            self.assertIn("CAP-001", finding["sample"])
            detail = next(x for x in finding["details"] if x["subject_id"] == "CAP-001")
            self.assertIn("receipt expired", detail["findings"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
