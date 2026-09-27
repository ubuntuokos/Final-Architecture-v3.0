#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from fa3_release_baseline import load_active_release_baseline
GATE_ID="FA3-BROWSER-CDP-PROVIDER-GATESET-001";PROVIDER_ID="FA3-PROVIDER-BROWSER-CDP-001"
def load(p):return json.loads(p.read_text())
def gate(root):
    root=root.resolve();baseline=load_active_release_baseline(root);f=[];required=["canonical/providers/FA3-PROVIDER-BROWSER-CDP-001.json","canonical/FA3-GATE-BROWSER-CDP-PROVIDER-001.json","canonical/browser-cdp-provider-enforcement.json","canonical/browser-cdp-current-host-enforcement.json","canonical/assessments/FA3-BROWSER-CDP-PROVIDER-DECISION-ASSESSMENT-2026-09-23.json","src/fa3_browser_cdp_provider.py","src/fa3_browser_cdp_current_host_gate.py","tests/test_browser_cdp_provider.py",".github/workflows/fa3-browser-cdp-provider.yml",".github/workflows/fa3-browser-cdp-current-host.yml","docs/browser-cdp-provider.md"]
    for rel in required:
        if not(root/rel).is_file():f.append({"code":"BCD-001","path":rel})
    if f:return{"schema":"fa3.browser-cdp-provider-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":f}
    p=load(root/"canonical/providers/FA3-PROVIDER-BROWSER-CDP-001.json");t=p.get("transport",{})
    if p.get("id")!=PROVIDER_ID or p.get("architectural_authority") is not False:f.append({"code":"BCD-002"})
    if p.get("new_capability") is not False or p.get("new_architectural_authority") is not False or p.get("capability_count")!=baseline.capability_count:f.append({"code":"BCD-003"})
    if p.get("activation_mode")!="OPTIONAL_DISABLED_BY_DEFAULT":f.append({"code":"BCD-004"})
    if t.get("protocol")!="CDP" or t.get("bind")!="LOOPBACK_ONLY" or t.get("remote_cdp")!="DENY" or t.get("accelerator_required") is not False:f.append({"code":"BCD-005"})
    s=(root/"src/fa3_browser_cdp_provider.py").read_text()
    for token in("--remote-debugging-address=127.0.0.1","CDP_LOOPBACK","BROWSER-CDP-REMOTE-DENIED","--disable-gpu"):
        if token not in s:f.append({"code":"BCD-006","token":token})
    if "--no-sandbox" in s or "shell=True" in s:f.append({"code":"BCD-007"})
    c=load(root/"canonical/browser-cdp-current-host-enforcement.json")
    if c.get("physical_browser_required") is not True or c.get("synthetic_current_host_pass")!="DENY" or c.get("loopback_cdp_required") is not True:f.append({"code":"BCD-008"})
    pol=load(root/"canonical/enforcement-policy.json")
    if GATE_ID not in pol.get("mandatory_reference_gates",[]):f.append({"code":"BCD-009","message":"global mandatory gate binding missing"})
    if pol.get("browser_cdp_provider_global_static_required") is not True or pol.get("browser_cdp_global_requirement") is not False:f.append({"code":"BCD-010","message":"global optional-provider policy invalid"})
    return{"schema":"fa3.browser-cdp-provider-gate-report.v1","gate_id":GATE_ID,"provider_id":PROVIDER_ID,"result":"PASS" if not f else "FAIL","findings":f,"capability_count":baseline.capability_count,"capability_delta":0,"authority_delta":0,"global_promotion_claim":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--report",default="reports/browser-cdp-provider-gate-report.json");a=ap.parse_args();root=Path(a.root);r=gate(root);out=root/a.report;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
