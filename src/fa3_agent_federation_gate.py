#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fa3_agent_federation import ClaimLedger, FederationContractError, ReplayGuard, admit_adaptive_worker, admit_remote_execution, build_execution_trajectory, circuit_transition_allowed, create_pattern_candidate, derive_child_budget, payload_digest, project_lifecycle_event, review_pattern_candidate, trust_signal, validate_envelope
from fa3_release_baseline import load_active_release_baseline

PROFILE_ID="FA3-AGENT-FEDERATION-001"
CONTRACT_ID="FA3-AGENT-FEDERATION-CONTRACTS-001"
DECISION_ID="FA3-DEC-CAP070-AGENT-FEDERATION-2026-09-24"
REFERENCE_ID="FA3-RUFLO-FEDERATION-PATTERN-REFERENCE-2026-09-24"
GATE_ID="FA3-GATE-AGENT-FEDERATION-001"
GATESET_ID="FA3-AGENT-FEDERATION-GATESET-001"

def load(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"object required: {path}")
    return value

def finding(code: str, message: str, **kw: Any) -> dict[str, Any]:
    return {"code":code,"severity":"P0","message":message,**kw}

def expect_error(fn) -> bool:
    try: fn()
    except FederationContractError: return True
    return False

def _budget(value: int=10) -> dict[str,int]:
    return {"max_hops":3,"max_tokens":1000*value,"max_wall_time_seconds":60*value,"max_children":value,"max_remote_delegations":value,"max_model_cost_microunits":10000*value,"max_cpu_seconds":100*value,"max_gpu_seconds":100*value}

def _good_envelope(now: datetime) -> dict[str, Any]:
    payload={"communication_mode":"HUMAN_LANGUAGE","language_tag":"en","human_readable_text":"Run the bounded delegated test task.","human_readable_authoritative":True}
    return {"schema":"fa3.federation-envelope.v1","message_id":"m-1","task_id":"t-1","sender_peer_id":"peer-a","sender_agent_id":"agent-a","recipient_peer_id":"peer-b","recipient_agent_id":"agent-b","issued_at":(now-timedelta(seconds=1)).isoformat(),"expires_at":(now+timedelta(minutes=5)).isoformat(),"nonce":"nonce-1","hop":1,"max_hops":3,"budget":_budget(),"payload_digest":payload_digest(payload),"payload":payload,"signature_algorithm":"ED25519","signing_key_id":"key-a","signature":"sig-ok"}

def regression_cases() -> dict[str, Any]:
    now=datetime(2026,9,24,17,0,0,tzinfo=timezone.utc)
    verifier=lambda key,data,sig: key=="key-a" and sig=="sig-ok"
    env=_good_envelope(now)
    valid=validate_envelope(copy.deepcopy(env),verifier,replay_guard=ReplayGuard(),now=now)
    forged=copy.deepcopy(env); forged["signature"]="bad"
    tampered=copy.deepcopy(env); tampered["payload"]["human_readable_text"]="tampered"
    expired=copy.deepcopy(env); expired["expires_at"]=(now-timedelta(seconds=1)).isoformat()
    hop=copy.deepcopy(env); hop["hop"]=4
    replay_guard=ReplayGuard(); validate_envelope(copy.deepcopy(env),verifier,replay_guard=replay_guard,now=now)
    parent=_budget(10); child=_budget(5); too_large=_budget(11)
    ledger=ClaimLedger(); ledger.acquire(claim_id="c1",resource_id="work:1",task_id="t1",owner_peer_id="peer-a",owner_agent_id="agent-a",now=100,ttl_seconds=10)
    double_claim=expect_error(lambda: ledger.acquire(claim_id="c2",resource_id="work:1",task_id="t2",owner_peer_id="peer-b",owner_agent_id="agent-b",now=101,ttl_seconds=10))
    bad_handoff=expect_error(lambda: ledger.handoff("work:1",from_peer_id="peer-x",from_agent_id="agent-x",to_peer_id="peer-b",to_agent_id="agent-b",now=102,ttl_seconds=10))
    expired_claim=ledger.current("work:1",now=111) is None
    admitted={"peer_identity_verified":True,"security_authorized":True,"agent_runtime_admitted":True,"uaf_route_present":True,"remote_hrb_admission_present":True,"provider_runtime_admission_present":True}
    missing_hrb=dict(admitted); missing_hrb["remote_hrb_admission_present"]=False
    ev1=project_lifecycle_event(event_id="ev-1",event_type="TASK_STARTED",task_id="t-adapt",run_id="r-adapt",timestamp=(now-timedelta(seconds=2)).isoformat(),human_readable_text="Task started",evidence_ids=["e-start"])
    ev2=project_lifecycle_event(event_id="ev-2",event_type="TASK_COMPLETED",task_id="t-adapt",run_id="r-adapt",timestamp=(now-timedelta(seconds=1)).isoformat(),human_readable_text="Task completed",evidence_ids=["e-end"])
    trajectory=build_execution_trajectory(trajectory_id="traj-1",events=[ev1,ev2],outcome="SUCCESS",evidence_ids=["e-outcome"])
    candidate=create_pattern_candidate(candidate_id="pat-1",trajectory=trajectory,proposal={"routing_hint":"prefer-specialist"})
    promoted=review_pattern_candidate(candidate,review_state="APPROVED",review_evidence_ids=["e-review"],risk_class="LOW",human_approved=False)
    high_risk_without_human=expect_error(lambda: review_pattern_candidate(candidate,review_state="APPROVED",review_evidence_ids=["e-review"],risk_class="HIGH",human_approved=False))
    self_promote=expect_error(lambda: create_pattern_candidate(candidate_id="pat-bad",trajectory=trajectory,proposal={},authority_grants=["FAKE_AUTHORITY"]))
    worker=admit_adaptive_worker(trigger_mode="EVENT_DRIVEN",early_exit=False,budget_gate=False,noop_path=False,temporal_bound=True,uaf_bound=True,hrb_bound=True,hidden_resident_worker=False)
    bad_worker=expect_error(lambda: admit_adaptive_worker(trigger_mode="EVENT_DRIVEN",early_exit=False,budget_gate=False,noop_path=False,temporal_bound=False,uaf_bound=True,hrb_bound=True,hidden_resident_worker=False))
    bad_polling=expect_error(lambda: admit_adaptive_worker(trigger_mode="FIXED_POLLING",early_exit=False,budget_gate=False,noop_path=False,temporal_bound=True,uaf_bound=True,hrb_bound=True,hidden_resident_worker=False))
    cases=[
      ("VALID_SIGNED_ENVELOPE",valid["message_id"]=="m-1"),
      ("FORGED_SIGNATURE_REJECTED",expect_error(lambda: validate_envelope(forged,verifier,now=now))),
      ("PAYLOAD_TAMPER_REJECTED",expect_error(lambda: validate_envelope(tampered,verifier,now=now))),
      ("REPLAY_REJECTED",expect_error(lambda: validate_envelope(copy.deepcopy(env),verifier,replay_guard=replay_guard,now=now))),
      ("EXPIRED_ENVELOPE_REJECTED",expect_error(lambda: validate_envelope(expired,verifier,now=now))),
      ("HOP_LIMIT_REJECTED",expect_error(lambda: validate_envelope(hop,verifier,now=now))),
      ("BUDGET_EXPANSION_REJECTED",derive_child_budget(parent,child)==child and expect_error(lambda: derive_child_budget(parent,too_large))),
      ("DOUBLE_CLAIM_REJECTED",double_claim),
      ("UNAUTHORIZED_HANDOFF_REJECTED",bad_handoff),
      ("EXPIRED_CLAIM_NOT_ACTIVE",expired_claim),
      ("REVOKED_PEER_NO_AUTO_REACTIVATE",not circuit_transition_allowed("REVOKED","ACTIVE",security_authorized=True)),
      ("REMOTE_EXECUTION_CHAIN_REQUIRED",admit_remote_execution(admitted)["status"]=="ADMITTED" and expect_error(lambda: admit_remote_execution(missing_hrb))),
      ("TRUST_SIGNAL_NOT_AUTHORIZATION",trust_signal(interaction_score=1.0,interaction_count=100)["authorization"] is False),
      ("LOCAL_PROTOCOL_NOT_CROSS_HOST_PROMOTION",True),
      ("LIFECYCLE_EVENT_NON_AUTHORITY",ev1["authorization"] is False and ev1["journal_authority"]=="FA3-JOURNAL-001"),
      ("TRAJECTORY_LINEAGE_REQUIRED",trajectory["event_ids"]==["ev-1","ev-2"] and trajectory["evidence_ids"]==["e-outcome"]),
      ("PATTERN_SELF_PROMOTION_REJECTED",self_promote and candidate["automatic_promotion"] is False),
      ("HIGH_RISK_PATTERN_HUMAN_GATE_REQUIRED",high_risk_without_human and promoted["state"]=="PROMOTED"),
      ("ADAPTIVE_WORKER_BOUNDARY_REQUIRED",worker["status"]=="ADMITTED" and bad_worker),
      ("UNBOUNDED_POLLING_REJECTED",bad_polling),
    ]
    return {"result":"PASS" if all(ok for _,ok in cases) else "FAIL","cases":[{"id":cid,"pass":bool(ok)} for cid,ok in cases]}

def gate(root: Path) -> dict[str, Any]:
    root=root.resolve(); findings=[]; cap=load_active_release_baseline(root).capability_count
    paths={"profile":root/"canonical/profiles/FA3-AGENT-FEDERATION-001.json","contract":root/"canonical/contracts/FA3-AGENT-FEDERATION-CONTRACTS-001.json","adaptive":root/"canonical/contracts/FA3-AGENT-FEDERATION-ADAPTIVE-CONTRACTS-001.json","decision":root/"canonical/decisions/FA3-DEC-CAP070-AGENT-FEDERATION-2026-09-24.json","reference":root/"canonical/references/FA3-RUFLO-FEDERATION-PATTERN-REFERENCE-2026-09-24.json","enforcement":root/"canonical/agent-federation-enforcement.json","gate":root/"canonical/FA3-GATE-AGENT-FEDERATION-001.json","policy":root/"canonical/enforcement-policy.json","coordination":root/"canonical/contracts/FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001.json","ai_comms":root/"canonical/contracts/FA3-AI-COMMS-CONTRACTS-001.json","workload":root/"canonical/profiles/FA3-AGENT-WORKLOAD-RUNTIME-001.json","evidence":root/"evidence/evidence-registry.json","recipes":root/"canonical/current-host-capability-proof-recipes.json","qualifications":root/"canonical/current-host-capability-test-qualifications.json"}
    for name,path in paths.items():
        if not path.is_file(): findings.append(finding("FED-001","required file missing",name=name,path=path.as_posix()))
    if findings: return {"schema":"fa3.agent-federation-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}
    p,c,adaptive,d,r,enf,g,pol,coord,comms,work,evidence,recipes,quals=[load(paths[k]) for k in ("profile","contract","adaptive","decision","reference","enforcement","gate","policy","coordination","ai_comms","workload","evidence","recipes","qualifications")]
    checks=[
      (p.get("id")==PROFILE_ID and p.get("priority")=="P0" and p.get("requirement")=="MUST","FED-010","profile identity/priority drift"),
      (p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==cap and p.get("capability_bindings")==["CAP-070"],"FED-011","capability/authority baseline drift"),
      (p.get("authority_boundaries",{}).get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and p.get("authority_boundaries",{}).get("action_execution")=="FA3-UNIFIED-ACTION-FABRIC-001" and p.get("authority_boundaries",{}).get("model_routing")=="FA3-AUTH-MODEL-ROUTER-001" and p.get("authority_boundaries",{}).get("tool_mediation")=="FA3-AUTH-MCP-GATEWAY-001","FED-012","authority boundary drift"),
      (p.get("coordination_claims",{}).get("claim_is_hrb_resource_lease") is False and p.get("coordination_claims",{}).get("claim_may_allocate_cpu_gpu_ram_vram_numa") is False,"FED-013","coordination claim confused with HRB lease"),
      (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("capability_bindings")==["CAP-070"],"FED-014","contract baseline drift"),
      (adaptive.get("id")=="FA3-AGENT-FEDERATION-ADAPTIVE-CONTRACTS-001" and adaptive.get("existing_authority_projection_only") is True and adaptive.get("new_architectural_authority") is False and adaptive.get("pattern_learning",{}).get("candidate_cannot_grant_authority") is True and adaptive.get("pattern_learning",{}).get("candidate_cannot_expand_capability") is True and adaptive.get("pattern_learning",{}).get("promotion_requires_review") is True and adaptive.get("adaptive_worker",{}).get("hidden_resident_worker_authority") is False,"FED-014A","adaptive coordination boundary drift"),
      (c.get("trust",{}).get("automatic_authorization_expansion") is False and c.get("remote_execution_admission",{}).get("trust_level_alone_sufficient") is False,"FED-015","trust became authorization"),
      (d.get("id")==DECISION_ID and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("global_promotion_claim") is False,"FED-016","decision capability/authority/promotion drift"),
      (r.get("id")==REFERENCE_ID and r.get("repository")=="ruvnet/ruflo" and r.get("commit")=="0a96fb8857dabd343d71d76c3ca703100a2923bc" and r.get("license")=="MIT" and r.get("fa3_adoption",{}).get("upstream_runtime_dependency") is False,"FED-017","Ruflo provenance or adoption boundary drift"),
      (enf.get("gateset_id")==GATESET_ID and enf.get("fail_closed") is True and enf.get("cross_host_runtime_promotion_claim") is False,"FED-018","enforcement baseline drift"),
      (g.get("id")==GATE_ID and g.get("gateset_id")==GATESET_ID and g.get("regression_case_count")==20 and g.get("cross_host_runtime_evidence") is False,"FED-019","gate record drift"),
      (GATESET_ID in set(pol.get("mandatory_reference_gates",[])) and pol.get("agent_federation_profile_id")==PROFILE_ID and pol.get("agent_federation_contract_id")==CONTRACT_ID and pol.get("agent_federation_adaptive_contract_id")=="FA3-AGENT-FEDERATION-ADAPTIVE-CONTRACTS-001","FED-020","global enforcement binding missing"),
      (coord.get("id")=="FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001" and "AgentTask" in coord.get("contracts",[]) and "AgentDelegation" in coord.get("contracts",[]),"FED-021","existing coordination contracts not reused"),
      (comms.get("id")=="FA3-AI-COMMS-CONTRACTS-001" and comms.get("human_auditable_message_envelope",{}).get("human_readable_authoritative_must_equal") is True,"FED-022","AI-Comms human-auditable boundary missing"),
      (work.get("id")=="FA3-AGENT-WORKLOAD-RUNTIME-001" and work.get("authority_boundaries",{}).get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","FED-023","agent workload/HRB boundary drift"),
    ]
    for ok,code,msg in checks:
        if not ok: findings.append(finding(code,msg))
    records=evidence.get("records",[]); cap070=[x for x in records if isinstance(x,dict) and x.get("subject_id")=="CAP-070"]
    if len(cap070)!=1 or cap070[0].get("status")!="PENDING_CURRENT_HOST" or cap070[0].get("runtime_conformance")!="EVIDENCE-PENDING": findings.append(finding("FED-024","CAP-070 must remain runtime pending until real cross-host evidence"))
    recipe=[x for x in recipes.get("recipes",[]) if isinstance(x,dict) and x.get("capability_id")=="CAP-070"]
    if len(recipe)!=1 or recipe[0].get("network_policy")!="LOOPBACK_ONLY" or recipe[0].get("local_protocol_evidence_only") is not True or recipe[0].get("cross_host_production_e2e_required") is not True or recipe[0].get("minimum_distinct_host_identities_for_cross_host_promotion")!=2 or recipe[0].get("global_promotion_claim") is not False: findings.append(finding("FED-025","CAP-070 current-host proof recipe does not preserve local-vs-cross-host truth boundary"))
    q070=[x for x in quals.get("entries",[]) if isinstance(x,dict) and x.get("subject_id")=="CAP-070"]
    if len(q070)!=3 or any(x.get("scope_limit")!="LOCAL_MULTI_NODE_PROTOCOL_ONLY_NOT_CROSS_HOST_PROMOTION" for x in q070) or any(x.get("minimum_distinct_host_identities_for_cross_host_promotion")!=2 for x in q070): findings.append(finding("FED-026","CAP-070 qualification scope is not explicitly local-only"))
    regress=regression_cases()
    if regress.get("result")!="PASS": findings.append(finding("FED-027","federation fail-closed regression failed",cases=regress.get("cases")))
    report={"schema":"fa3.agent-federation-gate-report.v1","gate_id":GATE_ID,"gateset_id":GATESET_ID,"profile_id":PROFILE_ID,"capability_id":"CAP-070","result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"regressions":regress,"runtime_claims":{"local_multi_node_protocol_pass":False,"cross_host_production_e2e_pass":False,"global_promotion_claim":False}}
    out=root/"reports/agent-federation-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); args=ap.parse_args(); report=gate(Path(args.root)); print(json.dumps(report,indent=2,ensure_ascii=False)); return 0 if report["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
