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
 def test_task_group_policy(self):
  r=route_task(ROOT,{"task_id":"k","task_group_id":"F15","domain":"knowledge","required_capabilities":["rag_pipeline","retrieval"]})
  self.assertEqual(r["status"],"ROUTED")
  self.assertEqual(r["task_group_policy"]["task_group_id"],"F15")
  self.assertEqual(len(r["task_group_policy"]["digest"]),64)
  self.assertEqual(r["resource_boundary"]["workload_mode"],"FA3-WORKLOAD-MODE-FRAMEWORK-001")
 def test_task_group_alias(self):
  r=route_task(ROOT,{"task_id":"k","task_group_id":"research-intelligence","domain":"knowledge","required_capabilities":["rag_pipeline","retrieval"]})
  self.assertEqual(r["task_group_policy"]["task_group_id"],"F15")
  self.assertEqual(r["task_group_policy"]["submitted_task_group_id"],"research-intelligence")
 def test_unknown_task_group_fails_closed(self):
  with self.assertRaises(WorkforceContractError):route_task(ROOT,{"task_id":"bad-group","task_group_id":"F99","domain":"knowledge","required_capabilities":["retrieval"]})
 def test_authority_bound_group_not_routed_as_specialist(self):
  r=route_task(ROOT,{"task_id":"sec","task_group_id":"F09","domain":"governed-agent-team","required_capabilities":["governed_agent_team"]})
  self.assertEqual(r["status"],"HUMAN_ESCALATION")
  self.assertEqual(r["reason"],"TASK_GROUP_HORIZONTAL_AUTHORITY_REQUIRED")
  self.assertIn("FA3-AUTH-SECURITY-GOV-001",r["required_authority_refs"])
 def test_f07_temporal_exclusive(self):
  r=route_task(ROOT,{"task_id":"dur","task_group_id":"F07","domain":"durable-workflow","required_capabilities":["durable_lifecycle"]})
  self.assertEqual(r["provider"],"Temporal")
  self.assertEqual(r["task_group_policy"]["classification"],"TEMPORAL_EXCLUSIVE")
 def test_invalid(self):
  with self.assertRaises(WorkforceContractError):route_task(ROOT,{"task_id":"bad","domain":"integration"})
 def test_governance_projection(self):
  t={"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"],"objective_ancestry":["project","scene","c"],"budget_envelope":{"parallelism":2}}
  r=route_task(ROOT,t)
  self.assertEqual(r["governance_projection"]["objective_ancestry"],["project","scene","c"])
  self.assertFalse(r["governance_projection"]["monitoring_authority"])
  p=compile_cross_domain_plan(ROOT,{"goal":"g","tasks":[t]})
  self.assertEqual(p["governance_contract"],"FA3-ORCHESTRATION-GOVERNANCE-CONTRACTS-001")
  self.assertFalse(p["monitor_projection"]["authority"])
  self.assertEqual(json.loads((ROOT/"canonical/FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001.json").read_text())["capability_count"],175)
 def test_gate(self):
  r=gate(ROOT);self.assertEqual(r["result"],"PASS");self.assertFalse(r["details"]["runtime_provider_promotion_claimed"])
if __name__=="__main__":unittest.main()
