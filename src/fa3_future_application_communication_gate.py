#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from fa3_application_agent_adapter import ApplicationCommunicationError, validate_application_entry, validate_relationship
GATE_ID="FA3-FUTURE-APPLICATION-COMMUNICATION-GATESET-001"; CONTRACT_ID="FA3-FUTURE-APPLICATION-COMMUNICATION-CONTRACTS-001"; DECISION_ID="FA3-DEC-FUTURE-APPLICATION-COMMUNICATION-2026-10-06"; BASELINE_ID="FA3-FUTURE-APPLICATION-COMMUNICATION-BASELINE-20261006"; REGISTRY_ID="FA3-APPLICATION-COMMUNICATION-READINESS-REGISTRY-001"; ADAPTER_ID="FA3-SHARED-APPLICATION-AGENT-ADAPTER-001"

def _load(root: Path, rel: str) -> dict[str, Any]:
    value=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(rel)
    return value

def gate(root: Path) -> dict[str, Any]:
    root=Path(root).resolve(); findings=[]
    paths={"contract":"canonical/contracts/FA3-FUTURE-APPLICATION-COMMUNICATION-CONTRACTS-001.json","decision":"canonical/decisions/FA3-DEC-FUTURE-APPLICATION-COMMUNICATION-2026-10-06.json","baseline":"canonical/FA3-FUTURE-APPLICATION-COMMUNICATION-BASELINE-20261006.json","registry":"canonical/FA3-APPLICATION-COMMUNICATION-READINESS-REGISTRY-001.json","lifecycle":"canonical/FA3-APP-LIFECYCLE-001.json","runtime_lifecycle":"canonical/contracts/FA3-APPLICATION-RUNTIME-LIFECYCLE-CONTRACTS-001.json","consumers":"canonical/FA3-APPLICATION-WORK-CAPABILITY-CONSUMER-RECONCILIATION-001.json","gate_record":"canonical/FA3-GATE-FUTURE-APPLICATION-COMMUNICATION-001.json","gate_registry":"canonical/FA3-GATE-REGISTRY-001.json","policy":"canonical/enforcement-policy.json","current_host":"canonical/current-host-impact/FA3-CH-IMPACT-FUTURE-APPLICATION-COMMUNICATION-20261006.json"}
    docs={}
    for key,rel in paths.items():
        try: docs[key]=_load(root,rel)
        except Exception as exc: findings.append({"code":"FAC-GATE-001","detail":f"{key}:{exc}"})
    if findings: return {"schema":"fa3.future-application-communication-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings,"capability_count":175,"current_host_runtime_promotion_claim":False}
    contract,decision,baseline,registry=docs["contract"],docs["decision"],docs["baseline"],docs["registry"]
    if contract.get("id")!=CONTRACT_ID or contract.get("capability_count")!=175 or contract.get("new_capability") is not False or contract.get("new_architectural_authority") is not False: findings.append({"code":"FAC-GATE-002","detail":"contract identity/baseline drift"})
    if decision.get("id")!=DECISION_ID or decision.get("status")!="CANONICAL_OWNER_APPROVED": findings.append({"code":"FAC-GATE-003","detail":"decision missing"})
    if baseline.get("id")!=BASELINE_ID or baseline.get("effective_main_sha")!="b483b8b3e4e05f3bf003b32517bd0655c07cd633": findings.append({"code":"FAC-GATE-004","detail":"policy epoch baseline drift"})
    if registry.get("id")!=REGISTRY_ID or registry.get("shared_adapter_id")!=ADAPTER_ID: findings.append({"code":"FAC-GATE-005","detail":"readiness registry drift"})
    current_ids={row.get("application_id") for row in docs["consumers"].get("consumers",[]) if isinstance(row,dict) and row.get("application_id")}
    future_ids=current_ids-set(baseline.get("grandfathered_application_ids") or [])
    entries=[row for row in registry.get("applications",[]) if isinstance(row,dict)]; entry_ids=[row.get("application_id") for row in entries]
    if len(entry_ids)!=len(set(entry_ids)): findings.append({"code":"FAC-GATE-006","detail":"duplicate readiness application entry"})
    if set(entry_ids)!=future_ids: findings.append({"code":"FAC-GATE-007","detail":"future application readiness coverage mismatch"})
    for entry in entries:
        try: validate_application_entry(entry)
        except ApplicationCommunicationError as exc: findings.append({"code":"FAC-GATE-008","detail":f"{entry.get('application_id')}:{exc.code}"})
    for relationship in registry.get("relationships",[]):
        try: validate_relationship(relationship)
        except ApplicationCommunicationError as exc: findings.append({"code":"FAC-GATE-009","detail":exc.code})
    life=docs["lifecycle"].get("future_application_communication",{})
    if life.get("contract_id")!=CONTRACT_ID or life.get("application_ready_requires_self_communication_admission_pass") is not True or life.get("fail_closed") is not True: findings.append({"code":"FAC-GATE-010","detail":"provisioning lifecycle binding missing"})
    runtime=docs["runtime_lifecycle"].get("application_ready_communication_admission",{})
    if runtime.get("contract_id")!=CONTRACT_ID or runtime.get("shared_application_agent_adapter_required")!=ADAPTER_ID or runtime.get("missing_or_unknown")!="DENY": findings.append({"code":"FAC-GATE-011","detail":"runtime lifecycle binding missing"})
    if docs["gate_record"].get("enforcement_id")!=GATE_ID or docs["gate_record"].get("entrypoint")!="src/fa3_future_application_communication_gate.py::gate": findings.append({"code":"FAC-GATE-012","detail":"gate record drift"})
    if GATE_ID not in docs["gate_registry"].get("mandatory_reference_gates",[]): findings.append({"code":"FAC-GATE-013","detail":"canonical gate registry membership missing"})
    if docs["policy"].get("mandatory_reference_gates")!=docs["gate_registry"].get("mandatory_reference_gates"): findings.append({"code":"FAC-GATE-014","detail":"enforcement mirror drift"})
    if docs["policy"].get("future_application_communication_gate_id")!=GATE_ID: findings.append({"code":"FAC-GATE-015","detail":"global enforcement binding missing"})
    ch=docs["current_host"]
    if ch.get("status")!="RECONCILED" or ch.get("physical_current_host_pass_claimed") is not False or ch.get("physical_requalification_required") is not True: findings.append({"code":"FAC-GATE-016","detail":"Current Host impact record invalid"})
    return {"schema":"fa3.future-application-communication-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not findings else "FAIL","capability_count":175,"capability_delta":0,"authority_delta":0,"future_application_ids":sorted(future_ids),"qualified_relationship_count":len(registry.get("relationships",[])),"findings":findings,"current_host_runtime_promotion_claim":False}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=p.parse_args(); r=gate(Path(a.root)); print(json.dumps(r,indent=2,ensure_ascii=False)); raise SystemExit(0 if r["result"]=="PASS" else 2)
