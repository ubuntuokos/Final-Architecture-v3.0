#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
from fa3_scope_authority_guard import evaluate, guard_transition, make_envelope

GATE_ID="FA3-SCOPE-AUTHORITY-GUARD-GATESET-001"
CAPABILITY_COUNT=175
PATHS={
 "profile":"canonical/profiles/FA3-SCOPE-AUTHORITY-GUARD-001.json",
 "contract":"canonical/contracts/FA3-SCOPE-AUTHORITY-GUARD-CONTRACTS-001.json",
 "registry":"canonical/FA3-AUTHORITY-CONTRACT-REGISTRY-001.json",
 "intent":"canonical/intents/FA3-SCOPE-AUTHORITY-GUARD-APPLICATION-INTENT-001.json",
 "assessment":"canonical/assessments/FA3-SCOPE-AUTHORITY-GUARD-REUSE-ASSESSMENT-001.json",
 "gate":"canonical/FA3-GATE-SCOPE-AUTHORITY-GUARD-001.json",
 "enforcement":"canonical/scope-authority-guard-enforcement.json",
 "policy":"canonical/enforcement-policy.json",
 "gate_registry":"canonical/FA3-GATE-REGISTRY-001.json",
}

def loadj(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def finding(code:str,message:str)->dict[str,Any]:
    return {"code":code,"severity":"P0","message":message}

def regressions(root:Path)->list[dict[str,Any]]:
    cases=[]
    def add(name:str, ok:bool):
        cases.append({"name":name,"result":"PASS" if ok else "FAIL"})
    add("director-delegation-allowed", evaluate(root,make_envelope(task_id="a",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.delegate",target_actor="FA3-SPECIALIST-DURABLE-LIFECYCLE-001",requested_authorities=["durable_lifecycle"],parent_scope=["durable_lifecycle"]))["result"]=="DELEGATE")
    add("unknown-actor-denied", evaluate(root,make_envelope(task_id="b",actor_id="UNKNOWN",intent="orchestration.plan"))["result"]=="DENY")
    add("director-model-route-denied", evaluate(root,make_envelope(task_id="c",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="model.route"))["result"]=="DENY")
    add("director-side-effect-denied", evaluate(root,make_envelope(task_id="d",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.plan",side_effect_class="WRITE"))["result"]=="DENY")
    add("wrong-target-denied", evaluate(root,make_envelope(task_id="e",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.delegate",target_actor="FA3-AUTH-HOST-RESOURCE-BROKER-001"))["result"]=="DENY")
    add("delegation-expansion-denied", evaluate(root,make_envelope(task_id="f",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.delegate",target_actor="FA3-SPECIALIST-X",requested_authorities=["host_resource"],parent_scope=["host_resource"]))["result"]=="DENY")
    add("parent-expansion-denied", evaluate(root,make_envelope(task_id="g",actor_id="FA3-ORCHESTRATION-DIRECTOR-001",intent="orchestration.delegate",target_actor="FA3-SPECIALIST-X",requested_authorities=["durable_lifecycle"],parent_scope=[]))["result"]=="DENY")
    add("retry-expansion-denied", guard_transition(root,actor_id="FA3-ORCHESTRATION-DIRECTOR-001",transition="replan",previous_scope=[],requested_scope=["durable_lifecycle"],task_id="h")["result"]=="DENY")
    add("hrb-model-route-denied", evaluate(root,make_envelope(task_id="i",actor_id="FA3-AUTH-HOST-RESOURCE-BROKER-001",intent="model.route"))["result"]=="DENY")
    add("router-resource-denied", evaluate(root,make_envelope(task_id="j",actor_id="FA3-AUTH-MODEL-ROUTER-001",intent="resource.lease"))["result"]=="DENY")
    add("evidence-tool-execute-denied", evaluate(root,make_envelope(task_id="k",actor_id="FA3-AUTH-OBS-EVIDENCE-001",intent="tool.execute"))["result"]=="DENY")
    add("guard-is-not-authority", all(evaluate(root,make_envelope(task_id="l",actor_id="FA3-AUTH-MODEL-ROUTER-001",intent="model.route",requested_authorities=["model_routing"]))[k] is False for k in ("execution_authority","authority_expansion")))
    return cases

def gate(root:Path)->dict[str,Any]:
    root=root.resolve(); findings=[]; data={}
    for key,rel in PATHS.items():
        try:data[key]=loadj(root/rel)
        except Exception as exc:findings.append(finding("SAGF-000",f"unreadable {rel}: {exc!r}"))
    if not findings:
        p,c,r,i,a,g,e,pol,greg=(data[k] for k in ("profile","contract","registry","intent","assessment","gate","enforcement","policy","gate_registry"))
        if not (p.get("id")=="FA3-SCOPE-AUTHORITY-GUARD-001" and p.get("capability_count")==CAPABILITY_COUNT and p.get("new_capability") is False and p.get("new_architectural_authority") is False): findings.append(finding("SAGF-001","profile baseline/authority drift"))
        if not (c.get("id")=="FA3-SCOPE-AUTHORITY-GUARD-CONTRACTS-001" and c.get("fail_closed") is True and c.get("capability_count")==CAPABILITY_COUNT and c.get("new_architectural_authority") is False): findings.append(finding("SAGF-002","contract drift"))
        if not (r.get("default_policy")=="DENY" and r.get("capability_count")==CAPABILITY_COUNT and r.get("new_architectural_authorities")==0): findings.append(finding("SAGF-003","registry is not fail-closed/non-authoritative"))
        director=next((x for x in r.get("actors",[]) if x.get("actor_id")=="FA3-ORCHESTRATION-DIRECTOR-001"),{})
        if not (director.get("may_execute_side_effects") is False and director.get("may_expand_scope") is False and director.get("may_self_verify") is False and "model.route" in director.get("forbidden_intents",[])): findings.append(finding("SAGF-004","director scope contract weakened"))
        if not (i.get("declared_new_capabilities")==[] and i.get("proposed_authority_roles")==[]): findings.append(finding("SAGF-005","intent attempts capability/authority expansion"))
        if not (a.get("result")=="PASS" and a.get("donor_registry_blob_sha")=="7e900cac93936d2f319e132def4c172b2a415d4d" and a.get("new_architectural_authorities")==0): findings.append(finding("SAGF-006","reuse assessment/source binding drift"))
        if not (g.get("gateset_id")==GATE_ID and g.get("fail_closed") is True and g.get("regression_case_count")==12): findings.append(finding("SAGF-007","gate record drift"))
        if not (e.get("gate_id")==GATE_ID and e.get("fail_closed") is True and e.get("authority_delta")==0): findings.append(finding("SAGF-008","enforcement record drift"))
        if GATE_ID not in pol.get("mandatory_reference_gates",[]): findings.append(finding("SAGF-009","permanent policy binding missing"))
        if GATE_ID not in greg.get("mandatory_reference_gates",[]): findings.append(finding("SAGF-010","gate registry binding missing"))
        if pol.get("scope_authority_guard_gate_id")!=GATE_ID or pol.get("scope_authority_guard_registry_id")!="FA3-AUTHORITY-CONTRACT-REGISTRY-001": findings.append(finding("SAGF-011","policy identity binding missing"))
    rows=regressions(root) if not findings else []
    if any(x["result"]!="PASS" for x in rows):findings.append(finding("SAGF-012","executable regressions failed"))
    report={"schema":"fa3.scope-authority-guard-gate-report.v1","gate_id":GATE_ID,"capability_count":CAPABILITY_COUNT,"authority_delta":0,"result":"PASS" if not findings else "FAIL","findings":findings,"regression_count":len(rows),"regressions":rows,"current_host_runtime_promotion_claim":False,"global_promotion_claim":False}
    out=root/"reports/scope-authority-guard-gate-report.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));args=ap.parse_args()
    report=gate(Path(args.root));print(json.dumps(report,indent=2,ensure_ascii=False));return 0 if report["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
