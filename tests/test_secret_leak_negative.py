import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_podman_secret_negative_gate as s


class TestSecretLeakNegative(unittest.TestCase):
    def _receipt(self):
        return {
            "schema": s.RECEIPT_SCHEMA,
            "gate_id": s.GATE_ID,
            "status": "PASS",
            "execution_context": "REAL_CURRENT_HOST",
            "required_runner_labels": sorted(s.RUNNER_LABELS),
            "rootless_podman": True,
            "image_reference": "sha256:" + "1" * 64,
            "image_id": "sha256:" + "2" * 64,
            "canary_sha256": "3" * 64,
            "raw_secret_value_persisted": False,
            "synthetic": False,
            "checks": {
                "unauthorized_mount_absent": True,
                "unauthorized_env_absent": True,
                "explicit_secret_control_works": True,
                "control_output_contains_no_raw_secret": True,
                "inspect_contains_no_raw_secret": True,
                "image_resolved_to_content_id": True,
                "secret_store_entry_exists_during_probe": True,
            },
            "current_host_runtime_promotion_claim": False,
            "global_promotion_claim": False,
        }

    def test_valid_real_current_host_receipt_passes(self):
        ok, errors = s.validate_receipt(self._receipt())
        self.assertTrue(ok, errors)

    def test_synthetic_receipt_denied(self):
        receipt = self._receipt()
        receipt["synthetic"] = True
        self.assertFalse(s.validate_receipt(receipt)[0])

    def test_missing_negative_check_denied(self):
        receipt = self._receipt()
        receipt["checks"]["unauthorized_mount_absent"] = False
        self.assertFalse(s.validate_receipt(receipt)[0])

    def test_raw_secret_persistence_claim_denied(self):
        receipt = self._receipt()
        receipt["raw_secret_value_persisted"] = True
        self.assertFalse(s.validate_receipt(receipt)[0])

    def test_hosted_mode_without_receipt_is_pending_not_pass_claim(self):
        with tempfile.TemporaryDirectory() as td:
            report = s.gate(Path(td), require_evidence=False)
            self.assertEqual("PASS", report["result"])
            self.assertEqual("PENDING_CURRENT_HOST", report["status"])
            self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_required_current_host_evidence_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            report = s.gate(Path(td), require_evidence=True)
            self.assertEqual("FAIL", report["result"])
            self.assertEqual("BLOCKED_CURRENT_HOST_EVIDENCE_REQUIRED", report["status"])


if __name__ == "__main__":
    unittest.main()
