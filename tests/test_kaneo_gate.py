import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_kaneo_gate import (
    capability_surface_parity_valid,
    change_surface_closed,
    common_authorization_boundary_valid,
    distributed_security_state_valid,
    gate,
    run_regressions,
)


class KaneoGateTests(unittest.TestCase):
    def test_regression_suite_passes_all_four_p0_invariants(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 4)
        self.assertEqual(report["total"], 4)

    def test_agent_bypass_is_rejected(self):
        auth = "FA3-AUTH-SECURITY-GOV-001"
        self.assertFalse(
            common_authorization_boundary_valid(
                human_policy_ref=auth,
                agent_policy_ref="AGENT-BYPASS",
                authoritative_policy_ref=auth,
                agent_bypass=True,
            )
        )

    def test_capability_surface_widening_is_rejected(self):
        canonical = {"task.read", "task.update"}
        projections = {
            "api": set(canonical),
            "mcp": {"task.read", "task.update", "admin.write"},
        }
        self.assertFalse(capability_surface_parity_valid(canonical, projections, {"api", "mcp"}))

    def test_missing_change_surface_evidence_is_rejected(self):
        self.assertFalse(
            change_surface_closed(
                {"authorization", "api", "mcp"},
                {"authorization": "PASS", "api": "PASS"},
            )
        )

    def test_replica_local_security_state_is_rejected_for_distributed_flow(self):
        self.assertFalse(
            distributed_security_state_valid(
                crosses_replicas=True,
                shared_state=False,
                expiry=True,
                atomic_consume=False,
                replay_protection=False,
            )
        )

    def test_reference_gate_passes_with_canonical_artifacts(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["reference"]["result"], "PASS")
        self.assertEqual(report["regressions"]["passed"], 4)
        self.assertFalse(report["runtime_provider_required"])

    def test_optional_provider_cannot_be_promoted_to_authority(self):
        provider_path = ROOT / "canonical/providers/FA3-PROVIDER-KANEO-001.json"
        original = provider_path.read_text()
        try:
            provider = json.loads(original)
            provider["architectural_authority"] = True
            provider_path.write_text(json.dumps(provider))
            report = gate(ROOT)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "KANEO-REF-010" for x in report["reference"]["findings"]))
        finally:
            provider_path.write_text(original)


if __name__ == "__main__":
    unittest.main()
