#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path
from typing import Any

SHA256=re.compile(r"^[0-9a-f]{64}$")
REQUIRED_CHECKS=[
 "real_provider_request_pass","credential_authentication_enforced_pass","session_affinity_pass","intra_provider_rebind_pass",
 "cross_provider_silent_fallback_denied_pass","unadmitted_provider_denied_pass","unadmitted_credential_denied_pass",
 "protocol_lossless_or_declared_degradation_pass","security_relevant_schema_loss_denied_pass",
 "raw_secret_absent_from_logs_pass","raw_secret_absent_from_evidence_pass","rollback_pass",
]

def git_head(root: Path)->str: return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
def loadj(path: Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("object required")
    return value
def gate(root: Path, receipt_path: Path)->dict[str,Any]:
    findings=[]
    conf=loadj(root/"canonical/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-CONFORMANCE-001.json")
    if conf.get("global_promotion_claim") is not False or conf.get("capability_count")!=143: findings.append({"code":"PEXCH-001","message":"conformance governance drift"})
    if not receipt_path.is_file():
        findings.append({"code":"PEXCH-002","message":"real current-host receipt missing"})
        return {"schema":"fa3.gate-report.v1","gate_id":"FA3-GATE-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-001","result":"FAIL","findings":findings}
    r=loadj(receipt_path)
    if r.get("schema")!="fa3.model-router-provider-execution-current-host.v1" or r.get("result")!="PASS" or r.get("evidence_level")!="CURRENT_HOST_REAL_PROVIDER_EXECUTION_E2E_PASS": findings.append({"code":"PEXCH-003","message":"receipt scope/result mismatch"})
    if r.get("repository_head")!=git_head(root): findings.append({"code":"PEXCH-004","message":"receipt repository HEAD mismatch"})
    if r.get("synthetic_or_mock_provider") is not False or r.get("raw_secret_present") is not False or r.get("global_promotion_claim") is not False: findings.append({"code":"PEXCH-005","message":"synthetic/secret/global-promotion boundary violation"})
    for field in ("credential_ref_sha256","provider_current_host_admission_receipt_sha256","secret_projection_receipt_sha256"):
        if SHA256.fullmatch(str(r.get(field,""))) is None: findings.append({"code":"PEXCH-006","message":"digest binding missing","field":field})
    checks=r.get("checks",{})
    missing=[name for name in REQUIRED_CHECKS if checks.get(name) is not True]
    if missing: findings.append({"code":"PEXCH-007","message":"required evidence matrix incomplete","missing":missing})
    return {"schema":"fa3.gate-report.v1","gate_id":"FA3-GATE-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-001","result":"PASS" if not findings else "FAIL","findings":findings,"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--receipt",required=True); a=ap.parse_args()
    report=gate(Path(a.root).resolve(),Path(a.receipt).resolve()); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
