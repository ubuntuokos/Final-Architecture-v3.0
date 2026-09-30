import json
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_scope_authority_guard import evaluate,guard_orchestration_delegation,guard_transition,load_registry,make_envelope
from fa3_orchestration_workforce import route_task

class ScopeAuthorityGuardTests(unittest.TestCase):
    def test_registry_is_fail_closed_and_175(self):
        r=load_registry(ROOT)
        self.assertEqual(r["capability_count"],175);self.assertEqual(r["default_policy"],"DENY")
        self.assertEqual(r["new_architectural_authorities"],0)

    def test_unknown_actor_and_intent_fail_closed(self):
        self.assertEqual(evaluate(ROOT,make_envelope(task_id="x",actor_id="unknown",intent="orchestration.plan"))["result"],"DENY")
        self.assertEqual(evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="model.route"))["result"],"DENY")

    def test_director_cannot_execute_side_effect(self):
        d=evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.plan",side_effect_class="WRITE"))
        self.assertEqual(d["reason"],"SIDE_EFFECT_OUTSIDE_ACTOR_CONTRACT")

    def test_delegation_target_and_authority_are_bounded(self):
        ok=evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.delegate",target_actor="FA3-SPECIALIST-DURABLE-LIFECYCLE-001",requested_authorities=["durable_lifecycle"],parent_scope=["durable_lifecycle"]))
        self.assertEqual(ok["result"],"DELEGATE")
        bad=evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.delegate",target_actor="FA3-SPECIALIST-X",requested_authorities=["host_resource"],parent_scope=["host_resource"]))
        self.assertEqual(bad["reason"],"DELEGATION_AUTHORITY_EXPANSION")

    def test_parent_scope_and_replan_cannot_expand(self):
        d=guard_transition(ROOT,actor_id="FA3-ORCHESTRATION-DIRECTOR-001",transition="replan",previous_scope=[],requested_scope=["durable_lifecycle"])
        self.assertEqual(d["result"],"DENY")

    def test_layer_contracts_are_not_interchangeable(self):
        self.assertEqual(evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-AUTH-HOST-RESOURCE-BROKER-001",intent="model.route"))["result"],"DENY")
        self.assertEqual(evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-AUTH-MODEL-ROUTER-001",intent="resource.lease"))["result"],"DENY")
        self.assertEqual(evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-AUTH-OBS-EVIDENCE-001",intent="tool.execute"))["result"],"DENY")

    def test_guard_decision_does_not_grant_execution_authority(self):
        d=evaluate(ROOT,make_envelope(task_id="x",actor_id="FA3-AUTH-MODEL-ROUTER-001",intent="model.route",requested_authorities=["model_routing"]))
        self.assertEqual(d["result"],"ALLOW");self.assertFalse(d["execution_authority"]);self.assertFalse(d["authority_expansion"])

    def test_specialist_guard_rechecks_workforce_contract(self):
        reg=json.loads((ROOT/"canonical/FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001.json").read_text())
        s=next(x for x in reg["specialists"] if x["id"]=="FA3-SPECIALIST-DURABLE-LIFECYCLE-001")
        task={"task_id":"durable","domain":"durable-workflow","required_capabilities":["durable_lifecycle"],"required_authorities":["durable_lifecycle"]}
        self.assertEqual(guard_orchestration_delegation(ROOT,task,s)["result"],"DELEGATE")
        bad={**task,"domain":"media-production"}
        self.assertEqual(guard_orchestration_delegation(ROOT,bad,s)["result"],"DENY")

    def test_route_task_exposes_guard_decision(self):
        task={"task_id":"durable","domain":"durable-workflow","required_capabilities":["durable_lifecycle"],"required_authorities":["durable_lifecycle"]}
        d=route_task(ROOT,task)
        self.assertEqual(d["status"],"ROUTED")
        self.assertEqual(d["scope_guard"]["result"],"DELEGATE")
        self.assertFalse(d["scope_guard"]["execution_authority"])

if __name__=="__main__":unittest.main()
