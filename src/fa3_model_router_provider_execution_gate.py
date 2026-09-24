#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from fa3_model_router_provider_execution import CredentialCandidate, ExecutionDenied, choose_credential, rebind_action, protocol_projection_status, execution_receipt

GATESET_ID="FA3-MODEL-ROUTER-PROVIDER-EXECUTION-GATESET-001"

def loadj(p: Path) -> dict[str, Any]:
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(f"object required: {p}")
    return v

def finding(code: str, message: str) -> dict[str, str]:
    return {"code":code,"severity":"P0","message":message}

def regressions() -> dict[str, Any]:
    good=[
      CredentialCandidate("FA3-PROVIDER-X-001","secretref:x/a","HEALTHY",True,2,0.2),
      CredentialCandidate("FA3-PROVIDER-X-001","secretref:x/b","QUOTA_LOW",True,0,0.8),
    ]
    checks=[]
    checks.append(("PEX-001", choose_credential(good,provider_id="FA3-PROVIDER-X-001").credential_ref=="secretref:x/a"))
    checks.append(("PEX-002", choose_credential(good,provider_id="FA3-PROVIDER-X-001",session_credential_ref="secretref:x/b").credential_ref=="secretref:x/b"))
    try:
        choose_credential([CredentialCandidate("FA3-PROVIDER-X-001","plaintext-key","HEALTHY",True)],provider_id="FA3-PROVIDER-X-001")
        checks.append(("PEX-003",False))
    except ExecutionDenied: checks.append(("PEX-003",True))
    checks.append(("PEX-004",rebind_action("RATE_LIMIT",True)=="INTRA_PROVIDER_REBIND"))
    checks.append(("PEX-005",rebind_action("RATE_LIMIT",False)=="MODEL_ROUTER_REEVALUATION_REQUIRED"))
    checks.append(("PEX-006",rebind_action("SECURITY_DENIED",True)=="FAIL_CLOSED"))
    checks.append(("PEX-007",protocol_projection_status(unsupported_fields=set(),security_relevant_fields={"pattern"})=="LOSSLESS"))
    checks.append(("PEX-008",protocol_projection_status(unsupported_fields={"pattern"},security_relevant_fields={"pattern"})=="UNSUPPORTED_FAIL_CLOSED"))
    checks.append(("PEX-009",protocol_projection_status(unsupported_fields={"maxLength"},security_relevant_fields=set())=="TRANSLATABLE_WITH_DECLARED_DEGRADATION"))
    receipt=execution_receipt(good[0],logical_route="chat-primary",physical_model="runtime-discovered",selection_reason="TEST")
    checks.append(("PEX-010","credential_ref_sha256" in receipt and "credential_ref" not in receipt and receipt["raw_credential_present"] is False))
    return {"result":"PASS" if all(v for _,v in checks) else "FAIL","total":len(checks),"passed":sum(v for _,v in checks),"cases":[{"case_id":k,"status":"PASS" if v else "FAIL"} for k,v in checks]}

def gate(root: Path) -> dict[str, Any]:
    f=[]
    router=loadj(root/"canonical/FA3-AUTH-MODEL-ROUTER-001.json")
    gateway=loadj(root/"canonical/profiles/FA3-LLM-GATEWAY-001.json")
    p=loadj(root/"canonical/profiles/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-001.json")
    proto=loadj(root/"canonical/profiles/FA3-LLM-PROTOCOL-COMPAT-001.json")
    enf=loadj(root/"canonical/model-router-provider-execution-enforcement.json")
    assessment=loadj(root/"canonical/assessments/FA3-ANTIGRAVITY-DERIVATION-ASSESSMENT-2026-09-24.json")
    decision=loadj(root/"canonical/decisions/FA3-DEC-ANTIGRAVITY-DERIVED-EXECUTION-MEDIATION-2026-09-24.json")
    if router.get("id")!="FA3-AUTH-MODEL-ROUTER-001" or router.get("data_plane",{}).get("single_routing_plane") is not True: f.append(finding("PEX-CANON-001","single Model Router authority drift"))
    if gateway.get("id")!="FA3-LLM-GATEWAY-001" or gateway.get("model_router_materialization",{}).get("role")!="REFERENCE_DATA_PLANE_ONLY": f.append(finding("PEX-CANON-002","LiteLLM data-plane boundary drift"))
    if p.get("parent_authority")!="FA3-AUTH-MODEL-ROUTER-001" or p.get("new_architectural_authority") is not False or p.get("capability_count")!=143: f.append(finding("PEX-CANON-003","provider execution profile governance drift"))
    if proto.get("parent_profile")!="FA3-LLM-GATEWAY-001" or proto.get("new_architectural_authority") is not False: f.append(finding("PEX-CANON-004","protocol compatibility boundary drift"))
    if enf.get("credential_policy",{}).get("raw_value_in_config") is not False or enf.get("credential_policy",{}).get("decision_fabric_secret_access") is not False: f.append(finding("PEX-SEC-001","credential secrecy boundary drift"))
    if enf.get("cross_provider_policy",{}).get("automatic_silent_transition") is not False: f.append(finding("PEX-ROUTE-001","silent cross-provider transition enabled"))
    if assessment.get("decision")!="REFERENCE_ONLY_CLEAN_ROOM_DERIVATION" or assessment.get("upstream_reference",{}).get("license")!="CC-BY-NC-SA-4.0": f.append(finding("PEX-LIC-001","clean-room license boundary missing"))
    if decision.get("capability_count")!=143 or decision.get("new_architectural_authority") is not False: f.append(finding("PEX-CANON-005","capability/authority accounting drift"))
    reg=regressions()
    if reg["result"]!="PASS": f.append(finding("PEX-REG-001","provider execution regression matrix failed"))
    return {"schema":"fa3.gate-report.v1","gate_id":GATESET_ID,"result":"PASS" if not f else "FAIL","findings":f,"regressions":reg,"current_host_claim":False}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--report")
    a=ap.parse_args()
    report=gate(Path(a.root))
    out=Path(a.report) if a.report else Path(a.root)/"reports/model-router-provider-execution-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
