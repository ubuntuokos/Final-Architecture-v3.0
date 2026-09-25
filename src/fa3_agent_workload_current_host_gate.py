#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_agent_workload_gate import gate as static_gate

PROFILE="FA3-AGENT-WORKLOAD-RUNTIME-001"
CONFORMANCE="FA3-AGENT-WORKLOAD-RUNTIME-CURRENT-HOST-CONFORMANCE-001"
GATESET="FA3-AGENT-WORKLOAD-RUNTIME-CURRENT-HOST-GATESET-001"
NATIVE="FA3-PROVIDER-AGENT-RUNNER-NATIVE-001"
LEVEL="CURRENT_HOST_PRODUCTION_E2E_PASS"
WORKLOAD="fa3-agent-workload-native-current-host"
LABELS=["self-hosted","linux","x64","fa3-current-host"]

def loadj(p: Path) -> dict[str, Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError("object required")
    return x

def finding(code: str,msg: str,**kw: Any)->dict[str,Any]:
    return {"code":code,"severity":"P0","message":msg,**kw}

def validate_materialization(root: Path) -> list[dict[str,Any]]:
    fs=[]
    conf=loadj(root/"canonical/FA3-AGENT-WORKLOAD-RUNTIME-CURRENT-HOST-CONFORMANCE-001.json")
    gate=loadj(root/"canonical/FA3-GATE-AGENT-WORKLOAD-RUNTIME-CURRENT-HOST-001.json")
    wf=(root/".github/workflows/fa3-agent-workload-runtime-current-host.yml").read_text(encoding="utf-8")
    if conf.get("id")!=CONFORMANCE or conf.get("status")!="PENDING_CURRENT_HOST" or conf.get("production_admitted") is not False:
        fs.append(finding("AWR-HOST-001","current-host conformance must remain pending before evidence"))
    if conf.get("required_runner_labels")!=LABELS or gate.get("required_runner_labels")!=LABELS or gate.get("current_host_evidence_required") is not True:
        fs.append(finding("AWR-HOST-002","current-host runner/evidence contract drift"))
    for token in ["workflow_dispatch:","runs-on: [self-hosted, linux, x64, fa3-current-host]","FA3_CURRENT_HOST_EXECUTION_CONTEXT: REAL_SELF_HOSTED_FA3_CURRENT_HOST","--resource-admission-receipt"]:
        if token not in wf: fs.append(finding("AWR-HOST-003","workflow current-host boundary token missing",token=token))
    if "runs-on: ubuntu-latest" not in wf:
        fs.append(finding("AWR-HOST-004","reference regression job missing"))
    return fs

def validate_receipt(receipt: dict[str,Any])->list[dict[str,Any]]:
    fs=[]
    if receipt.get("schema")!="fa3.agent-workload-runtime-current-host-receipt.v1" or receipt.get("profile_id")!=PROFILE or receipt.get("provider_id")!=NATIVE:
        fs.append(finding("AWR-HOST-010","receipt identity mismatch"))
    if receipt.get("status")!="PASS" or receipt.get("evidence_level")!=LEVEL or receipt.get("synthetic") is not False:
        fs.append(finding("AWR-HOST-011","real current-host PASS semantics missing"))
    if receipt.get("execution_context")!="REAL_SELF_HOSTED_FA3_CURRENT_HOST" or receipt.get("runner_labels")!=LABELS:
        fs.append(finding("AWR-HOST-012","self-hosted execution context/labels mismatch"))
    ra=receipt.get("resource_admission",{})
    if ra.get("authority")!="FA3-AUTH-HOST-RESOURCE-BROKER-001" or ra.get("result")!="PASS" or ra.get("workload_id")!=WORKLOAD or not str(ra.get("authorization_id") or "").strip() or not str(ra.get("receipt_sha256") or "").strip() or ra.get("fresh_scope_bound_required") is not True:
        fs.append(finding("AWR-HOST-013","fresh scope-bound HRB admission evidence missing"))
    tests=receipt.get("tests",{})
    if tests.get("static_gate")!="PASS" or tests.get("non_root_execution")!="PASS" or tests.get("cleanup")!="PASS" or tests.get("cgroup_v2_systemd_scope",{}).get("status")!="PASS" or tests.get("real_process_pause_resume",{}).get("status")!="PASS":
        fs.append(finding("AWR-HOST-014","native runner real-execution test incomplete"))
    if receipt.get("admitted_provider_ids")!=[NATIVE] or receipt.get("provider_subclaims")!={"podman":"NOT_TESTED","google_ax":"NOT_TESTED"}:
        fs.append(finding("AWR-HOST-015","provider admission scope expanded"))
    required_nonclaims={"GLOBAL_FA3_PROMOTION","GOOGLE_AX_PRODUCTION_ADMISSION","PODMAN_PRODUCTION_ADMISSION","PROCESS_CHECKPOINT_SUPPORT","VM_CHECKPOINT_SUPPORT"}
    if not required_nonclaims.issubset(set(receipt.get("non_claims",[]))) or receipt.get("global_promotion_claim") is not False:
        fs.append(finding("AWR-HOST-016","non-claim/global promotion boundary missing"))
    if receipt.get("errors") not in ([],None):
        fs.append(finding("AWR-HOST-017","collector reported errors",errors=receipt.get("errors")))
    return fs

def gate(root: Path, receipt_path: Path|None=None, *, require_evidence: bool=True)->dict[str,Any]:
    root=root.resolve(); fs=validate_materialization(root)
    parent=static_gate(root)
    if parent.get("result")!="PASS": fs.append(finding("AWR-HOST-000","parent static workload gate failed"))
    path=receipt_path or root/"evidence/receipts/agent-workload-runtime-current-host.json"
    if require_evidence:
        try: fs.extend(validate_receipt(loadj(path)))
        except Exception as exc: fs.append(finding("AWR-HOST-018","current-host receipt missing or unreadable",error=repr(exc)))
    report={"schema":"fa3.agent-workload-runtime-current-host-gate-report.v1","gate_id":GATESET,"result":"PASS" if not fs else "BLOCKED","findings":fs,
            "evidence_level":LEVEL if require_evidence and not fs else None,"evidence_required":require_evidence,
            "promotion_effect":"NATIVE_PROVIDER_HOST_SCOPED_ONLY_GLOBAL_PROMOTION_UNCHANGED","global_promotion_claim":False}
    out=root/"reports/agent-workload-runtime-current-host-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--receipt"); ap.add_argument("--static-only",action="store_true"); a=ap.parse_args()
    p=Path(a.receipt).resolve() if a.receipt else None
    r=gate(Path(a.root),p,require_evidence=not a.static_only); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
