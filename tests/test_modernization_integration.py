#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(REPO/"src"))
from fa3_modernization_integration_gate import gate,regressions

class ModernizationIntegrationTests(unittest.TestCase):
    def test_static_gate_passes(self):
        report=gate(REPO); self.assertEqual(report["result"],"PASS",report); self.assertEqual(report["new_capabilities"],0); self.assertEqual(report["new_architectural_authorities"],0); self.assertFalse(report["current_host_promotion_claim"]); self.assertFalse(report["global_promotion_claim"])
    def test_positive_and_negative_regressions_pass(self):
        rows=regressions(); self.assertEqual(len(rows),9); self.assertTrue(all(row["result"]=="PASS" for row in rows),rows)
    def test_reference_candidates_remain_non_admitted(self):
        data=json.loads((REPO/"canonical/references/FA3-MODERNIZATION-PROVIDER-CANDIDATES-2026-09-25.json").read_text(encoding="utf-8"))
        self.assertEqual({c["candidate_id"] for c in data["candidates"]},{"VLLM","STABLEHLO","TVM","TETRAGON","LANCEDB"})
        for row in data["candidates"]: self.assertEqual(row["admission_status"],"NOT_ADMITTED_REFERENCE_ONLY"); self.assertTrue(row["supply_chain_admission_required"]); self.assertTrue(row["current_host_e2e_required"])
    def test_contract_reuses_federation_knowledge_and_explicit_reroute(self):
        data=json.loads((REPO/"canonical/contracts/FA3-MODERNIZATION-INTEGRATION-CONTRACTS-001.json").read_text(encoding="utf-8")); contracts=data["contracts"]
        self.assertEqual(contracts["cross_host_execution"]["coordination_profile"],"FA3-AGENT-FEDERATION-001"); self.assertFalse(contracts["cross_host_execution"]["federation_is_resource_authority"]); self.assertEqual(contracts["cross_host_execution"]["remote_resource_admission_authority"],"FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertTrue(contracts["structured_knowledge_metadata"]["metadata_is_derived_projection"]); self.assertTrue(contracts["structured_knowledge_metadata"]["native_source_preservation_required"])
        self.assertTrue(contracts["degraded_execution"]["explicit_reroute_receipt_required"]); self.assertTrue(contracts["degraded_execution"]["reroute_requires_new_resource_admission"])

    def test_mandatory_rule_sets_are_consistent(self):
        contract=json.loads((REPO/"canonical/contracts/FA3-MODERNIZATION-INTEGRATION-CONTRACTS-001.json").read_text(encoding="utf-8"))
        enforcement=json.loads((REPO/"canonical/modernization-integration-enforcement.json").read_text(encoding="utf-8"))
        gate_record=json.loads((REPO/"canonical/FA3-GATE-MODERNIZATION-INTEGRATION-001.json").read_text(encoding="utf-8"))
        policy=json.loads((REPO/"canonical/enforcement-policy.json").read_text(encoding="utf-8"))
        rules=enforcement["p0_invariants"]
        self.assertEqual(enforcement["mandatory_rule_count"],len(rules))
        self.assertEqual(contract["mandatory_invariants"],rules)
        self.assertEqual(gate_record["mandatory_rules"],rules)
        self.assertEqual(policy["modernization_integration_mandatory_p0_rules"],rules)
    def test_hardware_and_coexistence_are_vendor_neutral(self):
        intent=json.loads((REPO/"canonical/intents/FA3-MODERNIZATION-INTEGRATION-APPLICATION-INTENT-001.json").read_text(encoding="utf-8")); hw=intent["hardware_audit"]; self.assertTrue(hw["vendor_neutral"]); self.assertTrue(hw["cpu_only_viable"]); self.assertEqual(hw["accelerator_cardinality"],"0..N"); self.assertFalse(hw["global_accelerator_requirement"]); ns=intent["namespace_claims"]; self.assertFalse(ns["requires_upstream_uninstall"]); self.assertFalse(ns["global_environment_mutation"]); self.assertFalse(ns["claims_default_port"])
if __name__=="__main__": unittest.main()
