import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fa3_ai_infra_guard_gate as g
import fa3_ai_infra_guard_adapter as a


class AISecurityValidationTests(unittest.TestCase):
    def test_regression_corpus_passes(self):
        r = g.run_regressions()
        self.assertEqual("PASS", r["result"], r)
        self.assertEqual(16, r["passed"])
        self.assertEqual(16, r["total"])

    def test_llm_only_pass_denied(self):
        self.assertFalse(g.deterministic_first_valid(
            deterministic_checks_run=False, deterministic_evidence_ids=[],
            llm_analysis_present=True, llm_is_sole_verdict_basis=True))

    def test_unknown_coverage_denied(self):
        self.assertFalse(g.coverage_valid(
            examined_artifacts=[], excluded_artifacts=[], unsupported_artifacts=[],
            scan_depth="", analysis_modes=[]))

    def test_runtime_reachable_pyc_omission_denied(self):
        self.assertFalse(g.runtime_surface_complete(
            runtime_reachable_artifacts=["main.py", "__pycache__/payload.pyc"],
            examined_artifacts=["main.py"], unsupported_artifacts=["__pycache__/payload.pyc"],
            verdict="PASS"))

    def test_unversioned_ruleset_denied(self):
        self.assertFalse(g.ruleset_identity_valid(
            ruleset_id="aig:rules", version="", digest="latest"))

    def test_unscoped_scanner_execution_denied(self):
        self.assertFalse(g.capability_scope_valid(
            caller_identity="scanner", capability_scope=["*"],
            policy_authority=g.PROVIDER_ID, policy_decision="ALLOW",
            arbitrary_shell=True, unrestricted_egress=True))

    def test_model_provider_mismatch_denied(self):
        self.assertFalse(g.model_provider_identity_valid(
            requested_identity="provider:model:a", observed_identity="provider:model:b",
            attestation_valid=False, mismatch_allowed=True))

    def test_unresolved_critical_finding_blocks_promotion(self):
        self.assertFalse(g.promotion_guard_valid(
            unresolved_critical_findings=1, scanner_ui_override=False,
            canonical_policy_decision="ALLOW"))

    def test_scanner_cannot_be_authority(self):
        self.assertFalse(g.scanner_conformance_valid(
            regression_status="PASS", coverage_status="PASS",
            scanner_is_architectural_authority=True, scanner_is_promotion_authority=False,
            capability_count=143))

    def test_gate_fails_on_provider_authority_assignment(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical").mkdir()
            (root / "canonical/bad.json").write_text(
                json.dumps({"security_authority": g.PROVIDER_ID}), encoding="utf-8")
            r = g.scan_canonical_authority_assignments(root)
            self.assertEqual("FAIL", r["result"])

    def test_adapter_regressions_pass(self):
        r = a.regression_check()
        self.assertEqual("PASS", r["result"], r)
        self.assertEqual(r["total"], r["passed"])

    def test_adapter_denies_remote_target(self):
        with self.assertRaises(a.AdmissionDenied):
            a.validate_loopback_target("https://example.com:443/")

    def test_adapter_drops_secret_and_proxy_environment(self):
        env = a.safe_environment({
            "PATH": "/usr/bin",
            "HOME": "/tmp",
            "OPENAI_API_KEY": "secret",
            "HTTPS_PROXY": "http://proxy",
        })
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("HTTPS_PROXY", env)

    def test_current_host_receipt_contract(self):
        receipt = {
            "schema": "fa3.ai-infra-guard-current-host-receipt.v1",
            "provider_id": g.PROVIDER_ID,
            "adapter_id": g.ADAPTER_ID,
            "admission_id": g.ADMISSION_ID,
            "status": "PASS",
            "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
            "collector_mode": "REAL_AI_INFRA_GUARD_NATIVE_SCAN_REAL_CURRENT_HOST_OLLAMA",
            "synthetic_scanner": False,
            "synthetic_target": False,
            "runtime_admission_eligible": True,
            "upstream": {
                "release": g.REFERENCE_RELEASE,
                "release_commit": g.REFERENCE_COMMIT,
                "source_archive_sha256": "1523b3e9f54c520b9a602e332a05f846c4e72c02e65a50feadd96533856c0ed4",
            },
            "build": {
                "release": g.REFERENCE_RELEASE,
                "release_commit": g.REFERENCE_COMMIT,
                "source_archive_sha256": "1523b3e9f54c520b9a602e332a05f846c4e72c02e65a50feadd96533856c0ed4",
                "non_root_build": True,
            },
            "adapter_regression": {"result": "PASS"},
            "target": {
                "type": "REAL_CURRENT_HOST_OLLAMA_SERVICE",
                "service": {
                    "api_version": "1.0.0",
                    "root_identity": "Ollama is running",
                    "base_url": "http://127.0.0.1:11434",
                },
                "guard_proxy": {
                    "bind": "http://127.0.0.1:30000",
                    "fixed_upstream": "http://127.0.0.1:11434",
                    "external_redirect_forwarding": False,
                    "request_count": 2,
                    "paths": ["/", "/api/version"],
                },
            },
            "production_e2e": {
                "provider_id": g.PROVIDER_ID,
                "adapter_id": g.ADAPTER_ID,
                "command_surface": "ai-infra-guard scan",
                "returncode": 0,
                "scan_result": {"ollama_fingerprint_observed": True},
                "isolation": {
                    "non_root_required": True,
                    "no_new_privs": True,
                    "secret_env_passthrough": False,
                    "proxy_env_passthrough": False,
                    "target_scope": "LOOPBACK_GUARD_PROXY_ONLY",
                    "arbitrary_headers": False,
                },
                "output_sha256": "a" * 64,
                "stdout_sha256": "b" * 64,
            },
            "authority": {
                "scanner_is_security_authority": False,
                "scanner_is_promotion_authority": False,
                "scanner_output_requires_fa3_attestation": True,
            },
            "isolation_verdict": "PASS",
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "capability_count_after": 143,
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / g.CURRENT_HOST_RECEIPT_PATH
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(receipt), encoding="utf-8")
            r = g.validate_current_host_receipt(root)
            self.assertEqual("PASS", r["result"], r)


if __name__ == "__main__":
    unittest.main()
