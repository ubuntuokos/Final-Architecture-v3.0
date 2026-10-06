from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from fa3_application_agent_adapter import ApplicationCommunicationError, SharedApplicationAgentAdapter, application_ready_admission, validate_relationship
from fa3_application_runtime_lifecycle import evaluate_transition
from fa3_future_application_communication_gate import gate
ROOT=Path(__file__).resolve().parents[1]

def future_entry(app_id="fa3.future-test"):
    return {"application_id":app_id,"canonical_identity":{"application_id":app_id,"identity_revision":"1","application_class":"INTERNAL_APPLICATION","provenance_refs":["test:identity"]},"operation_descriptor":{"schema":"fa3.application-operation-descriptor.v1","application_id":app_id,"descriptor_revision":"1","operations":[{"operation_ref":"future.test.execute","direction":"BIDIRECTIONAL","effectful":True,"capability_refs":["CAP-011"],"uaf_action_ref":"future.test.execute"}],"provenance_refs":["test:descriptor"]},"agent_adapter":{"adapter_id":"FA3-SHARED-APPLICATION-AGENT-ADAPTER-001","binding_revision":"1"},"self_communication_admission":{"sender":"PASS","receiver":"PASS","round_trip":"PASS","result":"PASS","evidence_refs":["evidence:test:self"]}}

class FutureApplicationCommunicationTests(unittest.TestCase):
    def test_repository_gate_passes(self): self.assertEqual("PASS",gate(ROOT)["result"],gate(ROOT))
    def test_existing_policy_epoch_application_remains_compatible(self): self.assertTrue(application_ready_admission("fa3.control-center",root=ROOT).allowed)
    def test_future_application_fails_closed_without_readiness_entry(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"canonical").mkdir()
            (root/"canonical/FA3-FUTURE-APPLICATION-COMMUNICATION-BASELINE-20261006.json").write_text(json.dumps({"grandfathered_application_ids":["legacy.app"]}))
            (root/"canonical/FA3-APPLICATION-COMMUNICATION-READINESS-REGISTRY-001.json").write_text(json.dumps({"applications":[]}))
            self.assertFalse(application_ready_admission("future.app",root=root).allowed)
    def test_future_application_ready_passes_only_with_required_contracts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"canonical").mkdir()
            (root/"canonical/FA3-FUTURE-APPLICATION-COMMUNICATION-BASELINE-20261006.json").write_text(json.dumps({"grandfathered_application_ids":[]}))
            (root/"canonical/FA3-APPLICATION-COMMUNICATION-READINESS-REGISTRY-001.json").write_text(json.dumps({"applications":[future_entry("future.app")]}))
            req={"application_id":"future.app","current_state":"INSTALLED","requested_state":"READY","actor_identity":"user:test","operation_ref":"application.lifecycle.ready","authorization_decision":"ALLOW","source_revision":"test","provenance_refs":["test"]}
            self.assertTrue(evaluate_transition(req,root=root).allowed)
    def test_shared_adapter_denies_undeclared_operation(self):
        adapter=SharedApplicationAgentAdapter(future_entry())
        with self.assertRaises(ApplicationCommunicationError): adapter.prepare_handoff("unknown.operation","target.app",correlation_id="c1",work_context_ref="work:1",capability_grant_ref="grant:1",provenance_refs=["test"])
    def test_relationship_requires_bilateral_sender_receiver_and_round_trip(self):
        rel={"application_a":"app.a","application_b":"app.b","a_to_b":{"sender_admission":"PASS","receiver_admission":"PASS"},"b_to_a":{"sender_admission":"PASS","receiver_admission":"PASS"},"round_trip":{"result":"PASS","evidence_refs":["evidence:rt"]},"result":"PASS"}; validate_relationship(rel); rel["b_to_a"]["receiver_admission"]="FAIL"
        with self.assertRaises(ApplicationCommunicationError): validate_relationship(rel)

if __name__=="__main__": unittest.main()
