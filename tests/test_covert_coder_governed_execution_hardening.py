from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_extension_boundary_gate import validate_extension


class CovertCoderGovernedExecutionHardeningTests(unittest.TestCase):
    def load(self, rel: str):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_donor_is_accepted_reference_and_non_executing(self):
        registry = self.load("canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json")
        donors = {row["donor_id"]: row for row in registry["entries"]}
        donor = donors["FA3-DONOR-ANONYMOUSNOMAD-COVERT-CODER-001"]
        self.assertEqual(donor["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(donor["source"]["normalized_key"], "github:anonymousnomad/covert-coder")
        self.assertEqual(donor["source"]["observed_commit"], "81aff88b924db05c689dc734aa3e67605f4b18ce")
        self.assertFalse(donor["automatic_code_import"])
        self.assertFalse(donor["automatic_activation"])
        self.assertFalse(donor["automatic_provider_admission"])
        self.assertFalse(donor["automatic_model_selection"])
        self.assertEqual(registry["backfill"]["entry_count"], len(registry["entries"]))

    def test_four_explicit_usage_edges_exist_without_runtime_adoption(self):
        links = self.load("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
        expected = {
            "FA3-USAGE-COVERT-CODER-MODEL-ROUTER-001",
            "FA3-USAGE-COVERT-CODER-MCP-TYPED-EXECUTION-001",
            "FA3-USAGE-COVERT-CODER-EXTENSION-TRUST-001",
            "FA3-USAGE-COVERT-CODER-EVIDENCE-STATE-001",
        }
        rows = {
            row["id"]: row
            for row in links["donor_usage_records"]
            if row.get("donor_id") == "FA3-DONOR-ANONYMOUSNOMAD-COVERT-CODER-001"
        }
        self.assertEqual(set(rows), expected)
        for row in rows.values():
            self.assertEqual(row["usage_kind"], "ARCHITECTURE_PATTERN")
            self.assertEqual(row["status"], "ACTIVE")
            self.assertEqual(row["current_host_impact"]["classification"], "NO_RUNTIME_IMPACT")
            self.assertFalse(row["provenance"]["code_imported"])
            self.assertFalse(row["provenance"]["runtime_dependency"])

    def test_model_router_truth_states_and_observed_identity_are_mandatory(self):
        router = self.load("canonical/FA3-AUTH-MODEL-ROUTER-001.json")
        truth = router["truth_state_semantics"]
        self.assertEqual(
            truth["states"],
            ["DISCOVERED", "SELECTED", "CONFIGURED", "AUTHENTICATED", "QUALIFIED",
             "AUTHORIZED", "EXECUTED", "VERIFIED", "READY"],
        )
        self.assertTrue(truth["states_are_not_synonyms"])
        self.assertTrue(truth["later_state_may_not_be_inferred_from_earlier_state"])
        self.assertTrue(truth["observed_execution_identity_required_for_executed_or_later_claim"])
        self.assertTrue(router["routing_invariants"]["observed_provider_model_runtime_identity_receipt_required"])
        self.assertTrue(router["routing_invariants"]["fallback_transition_must_be_explicit_and_receipted"])

    def test_mcp_proposal_cannot_self_authorize(self):
        contracts = self.load("canonical/contracts/FA3-MCP-GATEWAY-CONTRACTS-001.json")
        chain = contracts["execution_chain"]
        self.assertEqual(chain["model_or_agent_output_is"], "UNTRUSTED_PROPOSAL")
        self.assertEqual(chain["stage_skipping"], "FORBIDDEN")
        self.assertFalse(chain["proposal_may_grant_execution_authority"])
        self.assertFalse(chain["verification_may_grant_execution_authority"])
        self.assertIn("POLICY_AUTHORIZE", chain["ordered_stages"])
        self.assertIn("INDEPENDENT_VERIFY", chain["ordered_stages"])

    def test_extension_presence_admission_and_readiness_are_separate(self):
        policy = self.load("canonical/FA3-EXTENSION-BOUNDARY-001.json")
        trust = policy["trust_boundary"]
        self.assertFalse(trust["presence_or_installation_implies_admission"])
        self.assertFalse(trust["admission_implies_runtime_readiness"])
        self.assertFalse(trust["extension_may_gain_raw_machine_authority"])

        report = validate_extension({
            "existing_capability_ids": ["CAP-001"],
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "device_selection_authority": False,
            "model_routing_authority": False,
            "runtime_evidence_ref": "runtime",
            "security_evidence_ref": "security",
            "admission_implied_by_presence": True,
        })
        self.assertEqual(report["result"], "FAIL")

    def test_failure_evidence_preservation_is_mandatory(self):
        gov = self.load("canonical/contracts/FA3-ORCHESTRATION-GOVERNANCE-CONTRACTS-001.json")
        contracts = {row["id"]: row for row in gov["contracts"]}
        self.assertEqual(contracts["FA3-ORCH-GOV-013"]["requirement"], "MUST")
        self.assertEqual(contracts["FA3-ORCH-GOV-014"]["requirement"], "MUST")
        self.assertIn("MUST NOT delete, overwrite or silently convert", contracts["FA3-ORCH-GOV-014"]["rule"])


if __name__ == "__main__":
    unittest.main()
