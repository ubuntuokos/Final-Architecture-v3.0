import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_developer_agent_coordination as d
import fa3_developer_agent_coordination_gate as g


class DeveloperAgentCoordinationTests(unittest.TestCase):
    def test_canonical_contract_is_child_of_agent_execution_profile(self):
        contract = json.loads(
            (ROOT / "canonical/contracts/FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["parent_profile"], "FA3-AGENT-EXEC-001")
        self.assertTrue(contract["provider_neutral"])
        self.assertFalse(contract["new_capability"])
        self.assertFalse(contract["new_architectural_authority"])
        self.assertEqual(contract["capability_count"], 143)

    def test_workspace_collision_denied(self):
        self.assertFalse(d.workspace_plan_valid({"a": "w", "b": "w"}, ["a", "b"]))
        self.assertTrue(d.workspace_plan_valid({"a": "wa", "b": "wb"}, ["a", "b"]))

    def test_worker_direct_main_commit_denied(self):
        self.assertFalse(d.commit_intent_allowed(actor_role="WORKER", target_branch="main"))
        self.assertTrue(d.commit_intent_allowed(actor_role=d.INTEGRATION_ACTOR, target_branch="main"))

    def test_hop_budget_terminates(self):
        self.assertEqual(d.message_hop_action(hop=4, max_hops=4, act="request"), "TERMINATE")
        self.assertEqual(d.message_hop_action(hop=3, max_hops=4, act="request"), "ALLOW")

    def test_destructive_without_approval_denied(self):
        self.assertFalse(d.mutation_allowed(risk_class="DESTRUCTIVE", approved=False))
        self.assertTrue(d.mutation_allowed(risk_class="DESTRUCTIVE", approved=True))

    def test_cleanup_leak_denied(self):
        self.assertFalse(d.cleanup_state_valid(live_processes=1, worktrees=0, active_leases=0, pending_messages=0))
        self.assertTrue(d.cleanup_state_valid(live_processes=0, worktrees=0, active_leases=0, pending_messages=0))

    def test_provider_cannot_be_authority(self):
        self.assertFalse(d.provider_authority_assignment_allowed(provider_id="p", authority_owner="p"))
        self.assertTrue(d.provider_authority_assignment_allowed(provider_id="p", authority_owner="FA3-AUTH-SECURITY-GOV-001"))

    def test_reference_runtime_e2e_passes(self):
        report = d.run_reference_e2e()
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["status"], "CI_REFERENCE_RUNTIME_E2E_PASS")
        self.assertFalse(report["current_host_production_claim"])
        self.assertEqual(report["positive_flow"]["worker_count"], 3)
        self.assertEqual(report["positive_flow"]["workspace_count"], 3)
        self.assertEqual(report["positive_flow"]["mailbox_first"], "PROCESS")
        self.assertEqual(report["positive_flow"]["mailbox_replay"], "NOOP")
        self.assertEqual(report["positive_flow"]["integration_author"], "FA3 Integration")
        self.assertTrue(all(report["negative_cases"].values()))
        self.assertTrue(d.cleanup_state_valid(**report["positive_flow"]["cleanup"]))

    def test_gate_passes(self):
        report = g.gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["reference"]["result"], "PASS")
        self.assertEqual(report["regressions"]["result"], "PASS")
        self.assertEqual(report["e2e"]["status"], "CI_REFERENCE_RUNTIME_E2E_PASS")


if __name__ == "__main__":
    unittest.main()
