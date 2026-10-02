#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_shared_execution_security import (
    DENIED, PROVED, UNPROVEN, credential_projection_valid,
    execution_admitted, prove_policy,
)

PROFILE = "canonical/profiles/FA3-SHARED-EXECUTION-SECURITY-001.json"
CONTRACT = "canonical/contracts/FA3-SHARED-EXECUTION-SECURITY-CONTRACTS-001.json"
ASSESSMENT = "canonical/assessments/FA3-SHARED-EXECUTION-SECURITY-REUSE-ASSESSMENT-2026-10-02.json"
DECISION = "canonical/decisions/FA3-DEC-SHARED-EXECUTION-SECURITY-2026-10-02.json"
IMPACT = "canonical/FA3-SHARED-EXECUTION-SECURITY-CURRENT-HOST-IMPACT-001.json"
ENFORCEMENT = "canonical/shared-execution-security-enforcement.json"
LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
CAPABILITY_COUNT = 175
GATE_ID = "FA3-SHARED-EXECUTION-SECURITY-GATESET-001"

def loadj(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))

def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}

def regressions() -> list[dict[str, Any]]:
    boundary={"filesystem":["workspace:rw"],"network":["github.com"],"process":["python"],"mcp":["read_file"],"credentials":["github:lease"]}
    good={k:list(v) for k,v in boundary.items()}
    too_wide={**good,"network":["github.com","example.com"]}
    rows=[]
    def add(name: str, ok: bool): rows.append({"name":name,"result":"PASS" if ok else "FAIL"})
    add("policy-contained", prove_policy(good,boundary)==PROVED)
    add("policy-expansion-denied", prove_policy(too_wide,boundary)==DENIED)
    add("unsupported-proof-unproven", prove_policy(good,boundary,supported=False)==UNPROVEN)
    base=dict(proof_state=PROVED,proof_required=True,executable_digest_matches=True,policy_revision_matches=True,
              approval_valid=True,resource_leases_valid=True,secret_leases_valid=True,
              actual_assurance="EXEC-SEC-L4",minimum_assurance="EXEC-SEC-L3",enforcer_alive=True)
    add("execution-positive", execution_admitted(**base))
    add("unproven-denied", not execution_admitted(**{**base,"proof_state":UNPROVEN}))
    add("digest-change-denied", not execution_admitted(**{**base,"executable_digest_matches":False}))
    add("enforcer-loss-denied", not execution_admitted(**{**base,"enforcer_alive":False}))
    add("secret-projection-positive", credential_projection_valid(raw_secret_exposed=False,endpoint_bound=True,operation_bound=True,lease_valid=True))
    add("raw-secret-denied", not credential_projection_valid(raw_secret_exposed=True,endpoint_bound=True,operation_bound=True,lease_valid=True))
    return rows

def gate(root: Path) -> dict[str, Any]:
    fs=[]
    try:
        p=loadj(root,PROFILE); c=loadj(root,CONTRACT); a=loadj(root,ASSESSMENT)
        d=loadj(root,DECISION); i=loadj(root,IMPACT); e=loadj(root,ENFORCEMENT); links=loadj(root,LINKS)
    except Exception as exc:
        fs.append(finding("EXECSEC-000",f"materialization unreadable: {exc!r}"))
        return report(root,fs,[])
    if not (p.get("id")=="FA3-SHARED-EXECUTION-SECURITY-001" and p.get("canonical_root") is False and
            p.get("provider_neutral") is True and p.get("shared_component") is True and
            p.get("new_capability") is False and p.get("new_architectural_authority") is False and
            p.get("capability_count")==CAPABILITY_COUNT):
        fs.append(finding("EXECSEC-001","profile baseline/placement drift"))
    auth=p.get("authority_bindings",{})
    required={
        "security_policy":"FA3-AUTH-SECURITY-GOV-001",
        "tool_mediation":"FA3-AUTH-MCP-GATEWAY-001",
        "host_resources":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "model_routing":"FA3-AUTH-MODEL-ROUTER-001",
        "secrets":"FA3-SECRET-BROKER-001",
        "evidence":"FA3-AUTH-OBS-EVIDENCE-001",
    }
    if any(auth.get(k)!=v for k,v in required.items()):
        fs.append(finding("EXECSEC-002","authority binding drift"))
    if c.get("parent_profile")!=p.get("id") or c.get("capability_count")!=CAPABILITY_COUNT:
        fs.append(finding("EXECSEC-003","contract/profile binding drift"))
    semantics=c.get("required_semantics",{})
    if semantics.get("policy_relation")!="EFFECTIVE_POLICY_SUBSET_OF_AUTHORIZED_BOUNDARY" or semantics.get("proof_required_unproven_action")!="DENY":
        fs.append(finding("EXECSEC-004","policy proof semantics weakened"))
    if a.get("result")!="PASS" or a.get("donor_planning_snapshot",{}).get("donor_registry_entry_count")!=1354:
        fs.append(finding("EXECSEC-005","reuse assessment snapshot invalid"))
    if a.get("shared_capability_placement",{}).get("disposition")!="SHARED":
        fs.append(finding("EXECSEC-006","shared placement missing"))
    if d.get("new_architectural_authorities")!=0 or d.get("openshell_runtime_admitted") is not False:
        fs.append(finding("EXECSEC-007","decision admits authority/runtime"))
    if i.get("classification")!="RUNTIME_REQUALIFICATION_REQUIRED" or i.get("physical_current_host_pass_claimed") is not False:
        fs.append(finding("EXECSEC-008","Current Host impact overclaim"))
    if e.get("fail_closed") is not True or e.get("capability_count")!=CAPABILITY_COUNT:
        fs.append(finding("EXECSEC-009","enforcement baseline drift"))
    usage=[x for x in links.get("donor_usage_records",[]) if x.get("id")=="FA3-USAGE-NVIDIA-OPENSHELL-EXECUTION-SECURITY-001"]
    if len(usage)!=1 or usage[0].get("donor_id")!="FA3-DONOR-NVIDIA-OPENSHELL-001" or usage[0].get("usage_kind")!="ARCHITECTURE_PATTERN":
        fs.append(finding("EXECSEC-010","OpenShell usage edge missing or invalid"))
    rows=regressions()
    if any(x["result"]!="PASS" for x in rows): fs.append(finding("EXECSEC-011","execution-security regressions failed"))
    return report(root,fs,rows)

def report(root: Path, findings: list[dict[str,Any]], rows: list[dict[str,Any]]) -> dict[str,Any]:
    r={"schema":"fa3.shared-execution-security-gate-report.v1","gate_id":GATE_ID,
       "capability_count":CAPABILITY_COUNT,"authority_delta":0,
       "result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),
       "findings":findings,"regressions":rows,"current_host_runtime_promotion_claim":False}
    out=root/"reports/shared-execution-security-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return r

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args()
    r=gate(Path(a.root)); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
