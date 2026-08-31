import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fa3_ai_infra_guard_gate as g


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


if __name__ == "__main__":
    unittest.main()
