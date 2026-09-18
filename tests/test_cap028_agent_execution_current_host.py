import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.fa3_cap028_agent_execution_current_host as cap028


ROOT = Path(__file__).resolve().parents[1]


class Cap028AgentExecutionCurrentHostTests(unittest.TestCase):
    def _coverage_env(self):
        ids = cap028._expected_source_decisions(ROOT)
        return {"FA3_COVERS_SOURCE_DECISION_IDS_JSON": json.dumps(ids, separators=(",", ":"))}

    def test_exact_source_decision_coverage_matches_evidence_registry(self):
        ids = cap028._expected_source_decisions(ROOT)
        self.assertIn("DEC-CAP-028", ids)
        self.assertIn("FA3-DEC-AUTOGPT-2026-08-30", ids)
        self.assertIn("FA3-DEC-CODEX-ADAPTER-2026-08-31", ids)
        self.assertIn("FA3-DEC-OPENHANDS-2026-09-01", ids)
        self.assertIn("FA3-DEC-LOOP-ENGINEERING-2026-09-03", ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_canonical_provider_boundaries_pass_without_making_runtime_provider_dependency(self):
        reports = cap028._validate_canonical_boundaries(ROOT)
        self.assertEqual(reports["autogpt"]["result"], "PASS")
        self.assertEqual(reports["codex"]["result"], "PASS")
        self.assertEqual(reports["openhands"]["result"], "PASS")
        self.assertEqual(reports["loop_engineering"]["result"], "PASS")
        self.assertEqual(reports["developer_coordination"]["result"], "PASS")
        self.assertEqual(reports["runtime_hardening"]["result"], "PASS")

    def test_positive_logic_requires_provider_neutral_sandbox(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.dict(
            os.environ, self._coverage_env(), clear=False
        ), patch.object(
            cap028, "_validate_canonical_boundaries", return_value={"all": {"result": "PASS"}}
        ), patch.object(
            cap028,
            "_run_wasmtime",
            return_value={
                "binary": "/usr/bin/wasmtime",
                "module_sha256": "a" * 64,
                "returncode": 0,
                "filesystem_preopens": [],
                "network_lease": False,
                "host_subprocess_agent_execution": False,
            },
        ):
            result = cap028.run_mode(ROOT, Path(td), "positive")
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["provider_runtime_dependency_required"])
        self.assertFalse(result["real_sandbox_execution"]["host_subprocess_agent_execution"])
        self.assertTrue(result["real_sandbox_execution"]["compatibility_evidence"])

    def test_negative_matrix_rejects_host_subprocess_mcp_and_authority_expansion(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.dict(
            os.environ, self._coverage_env(), clear=False
        ), patch.object(
            cap028, "_validate_canonical_boundaries", return_value={"all": {"result": "PASS"}}
        ), patch.object(
            cap028,
            "_run_wasmtime",
            return_value={
                "binary": "/usr/bin/wasmtime",
                "version": "wasmtime test",
                "module_sha256": "b" * 64,
                "returncode": 0,
                "compatibility_evidence": True,
                "filesystem_preopens": [],
                "network_lease": False,
                "host_subprocess_agent_execution": False,
            },
        ):
            result = cap028.run_mode(ROOT, Path(td), "negative")
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["cases"].values()))

    def test_rollback_restores_exact_descriptor_and_destroys_ephemeral_workspace(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.dict(
            os.environ, self._coverage_env(), clear=False
        ), patch.object(
            cap028, "_validate_canonical_boundaries", return_value={"all": {"result": "PASS"}}
        ), patch.object(
            cap028,
            "_run_wasmtime",
            return_value={
                "binary": "/usr/bin/wasmtime",
                "version": "wasmtime test",
                "module_sha256": "c" * 64,
                "returncode": 0,
                "compatibility_evidence": True,
                "filesystem_preopens": [],
                "network_lease": False,
                "host_subprocess_agent_execution": False,
            },
        ):
            result = cap028.run_mode(ROOT, Path(td), "rollback")
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["fault_rejected"])
        self.assertTrue(result["rollback_hash_equal"])
        self.assertTrue(result["ephemeral_workspace_destroyed"])
        self.assertEqual(result["pre_sha256"], result["post_sha256"])
        self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])

    def test_sandbox_policy_rejects_host_subprocess_backend(self):
        self.assertTrue(cap028._sandbox_policy_ok())


if __name__ == "__main__":
    unittest.main()
