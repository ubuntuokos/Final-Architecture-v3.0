import json
import tempfile
import unittest
from pathlib import Path

import fa3_pyrit_gate as g


class PyRITGateTests(unittest.TestCase):
    def test_regressions_pass(self):
        result = g.run_regressions()
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(8, result["passed"])
        self.assertEqual(8, result["total"])

    def test_undetermined_score_cannot_pass(self):
        self.assertTrue(g.score_status_valid("UNDETERMINED", False))
        self.assertFalse(g.score_status_valid("UNDETERMINED", True))

    def test_runtime_promotion_requires_real_current_host(self):
        self.assertTrue(g.runtime_promotion_valid(
            current_host_e2e=True,
            synthetic=False,
            immutable_runtime_pin=True,
            isolation_pass=True,
        ))
        self.assertFalse(g.runtime_promotion_valid(
            current_host_e2e=False,
            synthetic=True,
            immutable_runtime_pin=True,
            isolation_pass=True,
        ))

    def test_execution_policy_denies_direct_gpu_placement(self):
        policy = {
            "explicit_target_allowlist_required": True,
            "deny_by_default_network_egress": True,
            "secret_environment_passthrough": False,
            "arbitrary_host_shell": False,
            "arbitrary_mcp_capability_access": False,
            "canonical_memory_write": False,
            "provider_local_operational_memory_only": True,
            "test_data_separation_required": True,
            "resource_limits_required": True,
            "immutable_run_identity_required": True,
            "evidence_projection_required": True,
            "direct_gpu_or_device_placement": True,
            "model_execution_via_existing_fa3_router": True,
            "undetermined_score_is_security_pass": False,
        }
        self.assertFalse(g.execution_policy_valid(policy))

    def test_execution_policy_denies_canonical_memory_write(self):
        policy = {
            "explicit_target_allowlist_required": True,
            "deny_by_default_network_egress": True,
            "secret_environment_passthrough": False,
            "arbitrary_host_shell": False,
            "arbitrary_mcp_capability_access": False,
            "canonical_memory_write": True,
            "provider_local_operational_memory_only": True,
            "test_data_separation_required": True,
            "resource_limits_required": True,
            "immutable_run_identity_required": True,
            "evidence_projection_required": True,
            "direct_gpu_or_device_placement": False,
            "model_execution_via_existing_fa3_router": True,
            "undetermined_score_is_security_pass": False,
        }
        self.assertFalse(g.execution_policy_valid(policy))

    def test_authority_assignment_scan_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical").mkdir()
            (root / "canonical/bad.json").write_text(
                json.dumps({"security_authority": g.PROVIDER_ID}),
                encoding="utf-8",
            )
            result = g.scan_canonical_authority_assignments(root)
            self.assertEqual("FAIL", result["result"])


if __name__ == "__main__":
    unittest.main()
