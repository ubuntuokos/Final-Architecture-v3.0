import json
import tempfile
import unittest
from pathlib import Path

from src.fa3_current_host_closure_assertion import assert_current_host_closure


class CurrentHostClosureAssertionTests(unittest.TestCase):
    def _write(self, root:Path, rel:str, value:dict):
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value)+"\n",encoding="utf-8")

    def _fixture(self, root:Path, *, acceptance_pass:bool=False, runtime_closure:str="PASS"):
        self._write(root,"reports/current-host-capability-qualification-constituent-producer-audit.json",{
            "audit_integrity":"PASS","registered_producer_count":429,"pending_producer_count":0,
            "required_constituent_count":429,"global_promotion_claim":False})
        self._write(root,"reports/current-host-capability-qualification-constituent-orchestrator.json",{
            "orchestrator_integrity":"PASS","execution_requested":True,"constituents_materialized":429,
            "selected_producer_count":429,"provider_receipts_promoted":0,"component_receipts_promoted":0,
            "global_promotion_claim":False})
        self._write(root,"reports/current-host-capability-test-executor-audit.json",{
            "audit_integrity":"PASS","required_test_obligation_count":429,"registered_executor_count":429,
            "pending_executor_count":0,"provider_receipts_promoted":0,"generic_host_evidence_promoted":0,
            "global_promotion_claim":False,"coverage_status":"COMPLETE_429_OF_429"})
        self._write(root,"reports/current-host-capability-test-orchestrator.json",{
            "orchestrator_integrity":"PASS","execution_requested":True,"results_materialized":429,
            "selected_executor_count":429,"provider_receipts_promoted":0,"generic_host_evidence_promoted":0,
            "global_promotion_claim":False,"status":"EXECUTED_REGISTERED_CAPABILITY_TESTS"})
        self._write(root,"reports/current-host-capability-test-bundle-assembler.json",{
            "assembler_integrity":"PASS","provider_receipts_promoted":0,"generic_host_evidence_promoted":0,
            "global_promotion_claim":False,"bundles_materialized":143,"pending_capability_count":0,
            "materialization_status":"ALL_CURRENT_HOST_TEST_BUNDLES_MATERIALIZED"})
        self._write(root,"reports/current-host-capability-attestation-producer.json",{
            "producer_integrity":"PASS","provider_receipts_promoted":0,"generic_host_evidence_promoted":0,
            "global_promotion_claim":False,"attestations_materialized":143,
            "materialization_status":"MATERIALIZED_EXPLICIT_CURRENT_HOST_ATTESTATIONS"})
        self._write(root,"reports/current-host-capability-handoff.json",{
            "handoff_integrity":"PASS","provider_receipts_promoted":0,"generic_host_evidence_promoted":0,
            "global_promotion_claim":False,"receipts_materialized":143,
            "materialization_status":"MATERIALIZED_EXPLICIT_ATTESTATIONS"})
        self._write(root,"reports/current-host-evidence-audit.json",{
            "audit_integrity":"PASS","runtime_closure":runtime_closure,"registry_pass_count":143 if runtime_closure=="PASS" else 0,
            "registry_pending_count":0 if runtime_closure=="PASS" else 143,
            "qualified_current_host_receipt_count":143 if runtime_closure=="PASS" else 0})
        if acceptance_pass:
            acceptance={"status":"PASS","decision":"ALLOW","static_gate":"PASS","runtime_gate":"PASS",
                        "criteria_passed":19,"criteria_total":19}
            promotion={"actual_state":"PROMOTED","promotion_allowed":True}
        else:
            acceptance={"status":"DENIED","decision":"DENY","static_gate":"FAIL","runtime_gate":"PASS",
                        "criteria_passed":0,"criteria_total":19}
            promotion={"actual_state":"PROMOTION_BLOCKED","promotion_allowed":False}
        self._write(root,"acceptance/acceptance-report.json",acceptance)
        self._write(root,"promotion/runtime-status.json",promotion)

    def test_full_429_runtime_closure_may_pass_while_global_promotion_remains_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root,acceptance_pass=False,runtime_closure="PASS")
            result=assert_current_host_closure(root,429)
            self.assertEqual(result["runtime_closure"],"PASS")
            self.assertEqual(result["registry_pass_count"],143)
            self.assertEqual(result["registry_pending_count"],0)
            self.assertEqual(result["acceptance"],"DENIED")
            self.assertEqual(result["promotion"],"PROMOTION_BLOCKED")

    def test_global_promotion_is_allowed_only_with_runtime_and_19_point_acceptance_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root,acceptance_pass=True,runtime_closure="PASS")
            result=assert_current_host_closure(root,429)
            self.assertEqual(result["acceptance"],"PASS")
            self.assertEqual(result["criteria_passed"],19)
            self.assertEqual(result["promotion"],"PROMOTED")

    def test_runtime_pass_cannot_coexist_with_unjustified_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root,acceptance_pass=False,runtime_closure="PASS")
            self._write(root,"promotion/runtime-status.json",{"actual_state":"PROMOTED","promotion_allowed":True})
            with self.assertRaises(AssertionError):
                assert_current_host_closure(root,429)

    def test_acceptance_pass_cannot_override_missing_runtime_closure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self._fixture(root,acceptance_pass=True,runtime_closure="PENDING")
            with self.assertRaises(AssertionError):
                assert_current_host_closure(root,429)


if __name__=="__main__":
    unittest.main()
