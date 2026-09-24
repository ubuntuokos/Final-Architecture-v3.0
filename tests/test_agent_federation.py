from __future__ import annotations
import copy
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.fa3_agent_federation import ClaimLedger, FederationContractError, ReplayGuard, admit_adaptive_worker, admit_remote_execution, build_execution_trajectory, create_pattern_candidate, derive_child_budget, payload_digest, project_lifecycle_event, review_pattern_candidate, validate_envelope
from src.fa3_agent_federation_gate import gate, regression_cases

ROOT=Path(__file__).resolve().parents[1]

class AgentFederationTests(unittest.TestCase):
    def test_regression_cases(self):
        report=regression_cases(); self.assertEqual("PASS",report["result"],report)

    def test_canonical_gate(self):
        report=gate(ROOT); self.assertEqual("PASS",report["result"],report)

    def test_replay_and_tamper_fail_closed(self):
        now=datetime(2026,9,24,17,0,0,tzinfo=timezone.utc)
        payload={"communication_mode":"HUMAN_LANGUAGE","language_tag":"en","human_readable_text":"bounded task","human_readable_authoritative":True}
        budget={"max_hops":1,"max_tokens":100,"max_wall_time_seconds":60,"max_children":1,"max_remote_delegations":1,"max_model_cost_microunits":1000,"max_cpu_seconds":10,"max_gpu_seconds":10}
        env={"schema":"fa3.federation-envelope.v1","message_id":"m","task_id":"t","sender_peer_id":"a","sender_agent_id":"aa","recipient_peer_id":"b","recipient_agent_id":"bb","issued_at":(now-timedelta(seconds=1)).isoformat(),"expires_at":(now+timedelta(minutes=1)).isoformat(),"nonce":"n","hop":0,"max_hops":1,"budget":budget,"payload_digest":payload_digest(payload),"payload":payload,"signature_algorithm":"ED25519","signing_key_id":"k","signature":"ok"}
        verifier=lambda k,data,s: s=="ok"; replay=ReplayGuard()
        validate_envelope(copy.deepcopy(env),verifier,replay_guard=replay,now=now)
        with self.assertRaises(FederationContractError): validate_envelope(copy.deepcopy(env),verifier,replay_guard=replay,now=now)
        bad=copy.deepcopy(env); bad["payload"]["human_readable_text"]="changed"
        with self.assertRaises(FederationContractError): validate_envelope(bad,verifier,now=now)

    def test_claim_and_budget_boundaries(self):
        ledger=ClaimLedger(); claim=ledger.acquire(claim_id="c",resource_id="file:path",task_id="t",owner_peer_id="p1",owner_agent_id="a1",now=100,ttl_seconds=30); self.assertEqual("ACTIVE",claim.status)
        with self.assertRaises(FederationContractError): ledger.handoff("file:path",from_peer_id="p2",from_agent_id="a2",to_peer_id="p3",to_agent_id="a3",now=101,ttl_seconds=30)
        parent={"max_hops":3,"max_tokens":100,"max_wall_time_seconds":60,"max_children":2,"max_remote_delegations":2,"max_model_cost_microunits":1000,"max_cpu_seconds":100,"max_gpu_seconds":100}; child=dict(parent); child["max_tokens"]=50
        self.assertEqual(child,derive_child_budget(parent,child)); child["max_tokens"]=101
        with self.assertRaises(FederationContractError): derive_child_budget(parent,child)

    def test_remote_admission_requires_existing_authorities(self):
        a={"peer_identity_verified":True,"security_authorized":True,"agent_runtime_admitted":True,"uaf_route_present":True,"remote_hrb_admission_present":True,"provider_runtime_admission_present":True}
        self.assertEqual("ADMITTED",admit_remote_execution(a)["status"]); a["security_authorized"]=False
        with self.assertRaises(FederationContractError): admit_remote_execution(a)


    def test_adaptive_learning_is_reviewed_and_non_authoritative(self):
        now="2026-09-24T17:00:00+00:00"
        e1=project_lifecycle_event(event_id="e1",event_type="TASK_STARTED",task_id="t",run_id="r",timestamp=now,human_readable_text="start",evidence_ids=["a"])
        e2=project_lifecycle_event(event_id="e2",event_type="TASK_COMPLETED",task_id="t",run_id="r",timestamp=now,human_readable_text="done",evidence_ids=["b"])
        trajectory=build_execution_trajectory(trajectory_id="tr",events=[e1,e2],outcome="SUCCESS",evidence_ids=["outcome"])
        candidate=create_pattern_candidate(candidate_id="pc",trajectory=trajectory,proposal={"hint":"reuse"})
        self.assertFalse(candidate["automatic_promotion"])
        with self.assertRaises(FederationContractError):
            create_pattern_candidate(candidate_id="bad",trajectory=trajectory,proposal={},capability_grants=["CAP-X"])
        with self.assertRaises(FederationContractError):
            review_pattern_candidate(candidate,review_state="APPROVED",review_evidence_ids=["review"],risk_class="HIGH",human_approved=False)
        receipt=review_pattern_candidate(candidate,review_state="APPROVED",review_evidence_ids=["review"],risk_class="LOW",human_approved=False)
        self.assertEqual("PROMOTED",receipt["state"])
        self.assertFalse(receipt["authorization_expansion"])

    def test_adaptive_worker_reuses_existing_boundaries(self):
        admitted=admit_adaptive_worker(trigger_mode="EVENT_DRIVEN",early_exit=False,budget_gate=False,noop_path=False,temporal_bound=True,uaf_bound=True,hrb_bound=True,hidden_resident_worker=False)
        self.assertEqual("ADMITTED",admitted["status"])
        with self.assertRaises(FederationContractError):
            admit_adaptive_worker(trigger_mode="FIXED_POLLING",early_exit=False,budget_gate=False,noop_path=False,temporal_bound=True,uaf_bound=True,hrb_bound=True,hidden_resident_worker=False)

if __name__=="__main__": unittest.main()
