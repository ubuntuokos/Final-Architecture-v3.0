from __future__ import annotations

import unittest
from pathlib import Path

from fa3_agency_agents_gate import (
    agent_source_allowed,
    communication_allowed,
    converted_output_activation_allowed,
    coordination_projection_allowed,
    decision_input_allowed,
    gate,
    run_regressions,
)

ROOT = Path(__file__).resolve().parents[1]


class AgencyAgentsGateTests(unittest.TestCase):
    def test_regression_matrix_exact_pass(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["total"], 24)
        self.assertEqual(report["passed"], 24)
        self.assertTrue(report["case_ids_exact"])

    def test_persona_cannot_grant_authority(self):
        source = {
            "provider_id": "FA3-PROVIDER-AGENCY-AGENTS-001",
            "source_commit": "053ddbbf392a1688fc7043d81529f47ef2cf86c8",
            "trust_class": "UNTRUSTED_SCOPED_CONTEXT",
            "task_scope": "agent.reference.test",
            "global_auto_injection": False,
            "persona_is_security_identity": False,
            "persona_grants_capability": False,
            "persona_grants_tool_permission": False,
            "persona_grants_secret_or_resource_access": False,
            "direct_tool_execution": False,
            "direct_provider_execution": False,
            "converted_output_auto_install": False,
        }
        self.assertTrue(agent_source_allowed(source))
        source["persona_grants_capability"] = True
        self.assertFalse(agent_source_allowed(source))

    def test_nexus_runbook_is_not_orchestrator_authority(self):
        projection = {
            "contract": "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001",
            "runbook_is_orchestrator_authority": False,
            "task_contract": "AgentTask",
            "delegation_contract": "AgentDelegation",
            "handoff_contract": "AgentMessage",
            "result_contract": "AgentResult",
            "escalation_contract": "HumanEscalation",
            "evidence_contract": "ExecutionEvidence",
            "human_auditable": True,
            "max_hops": 4,
        }
        self.assertTrue(coordination_projection_allowed(projection))
        projection["runbook_is_orchestrator_authority"] = True
        self.assertFalse(coordination_projection_allowed(projection))

    def test_imported_rank_cannot_authorize_or_expand_candidates(self):
        decision = {
            "decision_profile": "FA3-DECISION-FABRIC-001",
            "candidate_set_from_calling_fa3_authority": True,
            "candidate_set_expansion": False,
            "imported_rank_is_authorization": False,
            "direct_tool_execution": False,
        }
        self.assertTrue(decision_input_allowed(decision))
        decision["candidate_set_expansion"] = True
        self.assertFalse(decision_input_allowed(decision))

    def test_private_agent_language_fails_closed(self):
        message = {
            "contract": "FA3-AI-COMMS-CONTRACTS-001",
            "human_readable_authoritative": True,
            "human_readable_text": "Human readable handoff.",
            "private_model_language": False,
            "emergent_codebook": False,
            "model_only_slang": False,
        }
        self.assertTrue(communication_allowed(message))
        message["private_model_language"] = True
        self.assertFalse(communication_allowed(message))

    def test_converted_output_requires_separate_admission(self):
        activation = {
            "source_provider": "FA3-PROVIDER-AGENCY-AGENTS-001",
            "separate_admission_pass": True,
            "fa3_authority_preserved": True,
            "direct_runtime_install": False,
            "direct_agents_md_override": False,
            "direct_secret_access": False,
            "direct_tool_bypass": False,
        }
        self.assertTrue(converted_output_activation_allowed(activation))
        activation["separate_admission_pass"] = False
        self.assertFalse(converted_output_activation_allowed(activation))

    def test_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)


if __name__ == "__main__":
    unittest.main()
