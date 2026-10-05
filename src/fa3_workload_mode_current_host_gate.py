#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
GATE_ID="FA3-WORKLOAD-MODE-CURRENT-HOST-GATESET-001"
def gate(receipt_path:Path,expected_source_sha:str|None=None)->dict:
    findings=[]
    if not receipt_path.is_file(): return {"gate_id":GATE_ID,"result":"FAIL","findings":[{"code":"WMCH-000","message":"receipt missing"}],"global_promotion_claim":False}
    try:r=json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception as exc:return {"gate_id":GATE_ID,"result":"FAIL","findings":[{"code":"WMCH-001","message":str(exc)}],"global_promotion_claim":False}
    if r.get("schema")!="fa3.workload-mode-current-host-receipt.v1":findings.append({"code":"WMCH-002","message":"schema mismatch"})
    if r.get("result")!="PASS":findings.append({"code":"WMCH-003","message":"collector did not pass"})
    if r.get("capability_count")!=175:findings.append({"code":"WMCH-004","message":"capability baseline drift"})
    if expected_source_sha and r.get("source_sha")!=expected_source_sha:findings.append({"code":"WMCH-005","message":"source SHA mismatch"})
    if r.get("global_promotion_claim") is not False:findings.append({"code":"WMCH-006","message":"scoped receipt overclaims global promotion"})
    status=r.get("status",{})
    if status.get("fa3_state")!="CONNECTED" or status.get("authority")!="FA3_HRB":findings.append({"code":"WMCH-007","message":"FA3/HRB handshake missing"})
    if r.get("systemd_cgroup_resource_mutation_proven") is not False:findings.append({"code":"WMCH-008","message":"unexecuted resource mutation proof overclaimed"})
    if r.get("vendor_gpu_telemetry_proven") is not False:findings.append({"code":"WMCH-009","message":"unexecuted GPU telemetry proof overclaimed"})
    return {"schema":"fa3.workload-mode-current-host-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not findings else "FAIL","findings":findings,"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--receipt",required=True);ap.add_argument("--expected-source-sha");ap.add_argument("--json",action="store_true");ns=ap.parse_args()
    r=gate(Path(ns.receipt),ns.expected_source_sha);print(json.dumps(r,indent=2,sort_keys=True) if ns.json else f"{GATE_ID}: {r['result']}");return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
