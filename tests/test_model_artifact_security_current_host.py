from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fa3_model_artifact_security_current_host_gate import gate as current_host_gate
from fa3_model_artifact_security_gate import _base_receipt, admission_valid
from fa3_model_artifact_security_runtime import DANGEROUS_EXTENSIONS, SCANNER_IDS
from fa3_model_manager_security_hook import evaluate

ROOT = Path(__file__).resolve().parents[1]


class ModelArtifactSecurityCurrentHostTests(unittest.TestCase):
    def test_runtime_conformance_materialized_without_false_pass(self):
        x = json.loads((ROOT / "canonical/FA3-MODEL-ARTIFACT-SECURITY-RUNTIME-CONFORMANCE-001.json").read_text())
        self.assertEqual("MATERIALIZED_PENDING_REAL_CURRENT_HOST_EXECUTION", x["status"])
        self.assertEqual(143, x["capability_count"])
        self.assertFalse(x["new_capability"])
        self.assertFalse(x["new_architectural_authority"])
        self.assertTrue(x["production_e2e"]["real_local_model_required"])

    def test_full_scanner_portfolio_is_materialized(self):
        self.assertEqual({"modelaudit","clamav","yara","trivy","bandit","pip-audit","modelscan","picklescan","fickling","garak","cosign"}, set(SCANNER_IDS))
        self.assertEqual({".pkl", ".pickle", ".pt", ".pth", ".bin", ".ckpt"}, DANGEROUS_EXTENSIONS)

    def test_runtime_lock_uses_supported_sidecar_python_and_pins(self):
        lock = json.loads((ROOT / "canonical/model-artifact-security-runtime-lock.json").read_text())
        self.assertEqual("3.12", lock["runtime_python"]["preferred_current_host"])
        self.assertEqual("0.2.52", lock["python_components"]["modelaudit"]["version"])
        self.assertEqual("0.1.12", lock["python_components"]["fickling"]["version"])
        self.assertEqual("0.16.0", lock["python_components"]["garak"]["version"])
        self.assertEqual("0.74.0", lock["binary_components"]["trivy"]["version"])
        self.assertEqual("3.1.2", lock["binary_components"]["cosign"]["version"])
        self.assertFalse(lock["scan_time_network_egress"])

    def test_model_manager_hook_is_hash_bound_and_fail_closed(self):
        receipt = _base_receipt()
        digest = receipt["artifact"]["sha256"]
        self.assertTrue(admission_valid(receipt))
        self.assertTrue(evaluate(receipt, digest)["model_manager_promotion_eligible"])
        self.assertFalse(evaluate(receipt, "b" * 64)["model_manager_promotion_eligible"])

    def test_binding_forbids_direct_runtime_store_bypass(self):
        x = json.loads((ROOT / "canonical/model-manager-model-security-binding.json").read_text())
        self.assertEqual("SECURITY_ADMITTED", x["promotion_precondition"])
        self.assertEqual("FORBIDDEN", x["direct_provider_download_to_promoted_store"])
        self.assertTrue(x["artifact_hash_binding_required"])

    def test_current_host_gate_fails_without_real_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            report = current_host_gate(Path(d))
        self.assertEqual("FAIL", report["result"])
        self.assertEqual("MODEL-SEC-HOST-001", report["findings"][0]["code"])

    def test_bootstrap_separates_network_phase_and_rejects_system_python_314(self):
        s = (ROOT / "bin/fa3-model-artifact-security-bootstrap.sh").read_text()
        self.assertIn("FA3_MODEL_SECURITY_ALLOW_NETWORK_BOOTSTRAP", s)
        self.assertIn("python3.12", s)
        self.assertNotIn("python3.14 -m venv", s)
        self.assertIn("cosign 3.1.2", s)
        self.assertIn("trivy 0.74.0", s)

    def test_runtime_sandbox_is_network_and_secret_denied(self):
        s = (ROOT / "src/fa3_model_artifact_security_runtime.py").read_text()
        self.assertIn('"--unshare-net"', s)
        self.assertIn('"--clearenv"', s)
        self.assertIn('"PROMPTFOO_DISABLE_TELEMETRY", "1"', s)
        self.assertIn('"--tmpfs", str(user_home)', s)
        self.assertIn('"--tmpfs", "/run"', s)

    def test_current_host_workflow_targets_real_fa3_runner(self):
        s = (ROOT / ".github/workflows/fa3-model-artifact-security-current-host.yml").read_text()
        self.assertIn("self-hosted", s)
        self.assertIn("fa3-current-host", s)
        self.assertIn("collect-model-artifact-security-current-host.py", s)
        self.assertIn("model-artifact-security-current-host.json", s)


if __name__ == "__main__": unittest.main()
