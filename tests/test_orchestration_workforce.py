from __future__ import annotations
import json,unittest
from pathlib import Path
from fa3_orchestration_workforce import DecisionAdvisoryError,WorkforceContractError,compile_cross_domain_plan,route_task
from fa3_orchestration_workforce_gate import gate
ROOT=Path(__file__).resolve().parents[1]
def receipt(pid):return {"schema":"fa3.orchestration-provider-current-host-admission.v1","provider_id":pid,"scope_id":"REFERENCE_TEST_ONLY","status":"ADMITTED","evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS","runtime_identity":{"reference_test_fixture":True},"production_e2e":{"result":"PASS","evidence_refs":["REFERENCE_TEST_FIXTURE_NOT_RUNTIME_EVIDENCE"]},"global_promotion_claim":False}
class Tests(unittest.TestCase):
 def test_routes(self):
  self.assertEqual(route_task(ROOT,{"task_id":"d","domain":"durable-workflow","required_capabilities":["durable_lifecycle"]})["provider"],"Temporal")
  self.assertEqual(route_task(ROOT,{"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"]})["specialist_id"],"FA3-MEDIA-PRODUCTION-DIRECTOR-001")
 def test_hrb_horizontal(self):self.assertEqual(route_task(ROOT,{"task_id":"r","domain":"resource-governance","required_capabilities":["host_resource_admission"],"required_authorities":["host_resource"]})["status"],"HUMAN_ESCALATION")
 def test_runtime_receipt(self):
  t={"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"]}
  self.assertEqual(route_task(ROOT,t,runtime_execution=True)["status"],"HUMAN_ESCALATION")
  self.assertEqual(route_task(ROOT,t,runtime_execution=True,admission_receipts={"FA3-PROVIDER-CREWAI-001":receipt("FA3-PROVIDER-CREWAI-001")})["provider_id"],"FA3-PROVIDER-CREWAI-001")
 def test_advisory_no_expand(self):
  t={"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"]};ids=route_task(ROOT,t)["decision_fabric"]["candidate_ids"]
  with self.assertRaises(DecisionAdvisoryError):route_task(ROOT,t,decision_advisory={"authority":False,"candidate_set_expanded":False,"candidate_ids":[*ids,"x"],"selected_specialist_id":"x","rollout":"ACTIVE","status":"DECIDED"})
 def test_media_plan(self):
  p=compile_cross_domain_plan(ROOT,json.loads((ROOT/"examples/orchestration-workforce-media.json").read_text()));self.assertEqual(p["status"],"READY");self.assertEqual(p["execution_fabric"],"FA3-UNIFIED-ACTION-FABRIC-001");self.assertEqual(len(p["decisions"]),4)
 def test_invalid(self):
  with self.assertRaises(WorkforceContractError):route_task(ROOT,{"task_id":"bad","domain":"integration"})
 def test_gate(self):
  r=gate(ROOT);self.assertEqual(r["result"],"PASS");self.assertFalse(r["details"]["runtime_provider_promotion_claimed"])
if __name__=="__main__":unittest.main()
