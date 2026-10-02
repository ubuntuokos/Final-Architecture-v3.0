#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from fa3_shared_execution_security import execution_admitted, policy_subset, proof_allows_execution

CAPABILITY_COUNT = 175
PROFILE = "canonical/profiles/FA3-SHARED-EXECUTION-SECURITY-001.json"
CONTRACT = "canonical/contracts/FA3-SHARED-EXECUTION-SECURITY-CONTRACTS-001.json"
DECISION = "canonical/decisions/FA3-DEC-SHARED-EXECUTION-SECURITY-2026-10-02.json"
ASSESSMENT = "canonical/assessments/FA3-SHARED-EXECUTION-SECURITY-REUSE-ASSESSMENT-2026-10-02.json"
IMPACT = "canonical/FA3-SHARED-EXECUTION-SECURITY-CURRENT-HOST-IMPACT-001.json"
LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

def loadj(root, rel): return json.loads((root / rel).read_text(encoding="utf-8"))

def gate(root: Path):
    findings=[]
    p=loadj(root,PROFILE); c=loadj(root,CONTRACT); d=loadj(root,DECISION); a=loadj(root,ASSESSMENT); i=loadj(root,IMPACT); links=loadj(root,LINKS)
    required_auth={"FA3-AUTH-SECURITY-GOV-001","FA3-AUTH-MCP-GATEWAY-001","FA3-AUTH-HOST-RESOURCE-BROKER-001","FA3-AUTH-MODEL-ROUTER-001","FA3-SECRET-BROKER-001","FA3-AUTH-OBS-EVIDENCE-001"}
    checks=[
      (p.get("id")=="FA3-SHARED-EXECUTION-SECURITY-001","EXECSEC-001","profile missing/drifted"),
      (p.get("capability_count")==CAPABILITY_COUNT and p.get("new_capability") is False and p.get("new_architectural_authority") is False,"EXECSEC-002","baseline/authority drift"),
      (required_auth.issubset(set(p.get("authority_bindings",{}).values())),"EXECSEC-003","authority binding drift"),
      ("UNPROVEN_IS_NOT_PASS_WHEN_PROOF_REQUIRED" in p.get("invariants",[]),"EXECSEC-004","UNPROVEN fail-closed invariant missing"),
      (c.get("parent_profile")==p.get("id") and c.get("capability_count")==CAPABILITY_COUNT,"EXECSEC-005","contract/profile drift"),
      (d.get("authority_delta")==0 and d.get("upstream_runtime_dependency") is False and d.get("upstream_code_import") is False,"EXECSEC-006","decision admits upstream authority/runtime"),
      (a.get("published_main_commit")=="858498b1c3c81dffd65bb37c2266e53b3e973e06" and a.get("donor_registry_blob_sha")=="50580a9f3082161a3317383baa3e18879e98187e" and a.get("donor_registry_entry_count")==1357,"EXECSEC-007","reuse snapshot stale"),
      (i.get("classification")=="RUNTIME_REQUALIFICATION_REQUIRED" and i.get("current_host_runtime_promotion_claim") is False,"EXECSEC-008","current-host impact drift"),
      (any(x.get("donor_id")=="FA3-DONOR-NVIDIA-OPENSHELL-001" and x.get("usage_kind")=="ARCHITECTURE_PATTERN" and x.get("status")=="ACTIVE" for x in links.get("donor_usage_records",[])),"EXECSEC-009","OpenShell usage edge missing"),
      (policy_subset(["read"],["read","write"]) and not policy_subset(["read","network"],["read","write"]),"EXECSEC-010","policy subset regression"),
      (proof_allows_execution("PROVED",proof_required=True) and not proof_allows_execution("UNPROVEN",proof_required=True) and not proof_allows_execution("DENIED",proof_required=False),"EXECSEC-011","policy proof regression"),
      (execution_admitted(authorized_policy=["read"],requested_policy=["read"],proof_state="PROVED",proof_required=True,minimum_security_level="EXEC-SEC-L3",observed_security_level="EXEC-SEC-L4",authorization_valid=True,lease_valid=True,executable_digest_valid=True,enforcer_available=True),"EXECSEC-012","positive execution admission regression"),
      (not execution_admitted(authorized_policy=["read"],requested_policy=["read","network"],proof_state="PROVED",proof_required=True,minimum_security_level="EXEC-SEC-L3",observed_security_level="EXEC-SEC-L4",authorization_valid=True,lease_valid=True,executable_digest_valid=True,enforcer_available=True),"EXECSEC-013","policy expansion was admitted"),
    ]
    for ok,code,msg in checks:
        if not ok: findings.append({"code":code,"severity":"P0","message":msg})
    return {"schema":"fa3.shared-execution-security-gate-report.v1","gate_id":"FA3-SHARED-EXECUTION-SECURITY-GATESET-001","capability_count":CAPABILITY_COUNT,"authority_delta":0,"result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"current_host_runtime_promotion_claim":False}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=ap.parse_args()
    report=gate(Path(args.root).resolve()); out=Path(args.root)/"reports/shared-execution-security-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
