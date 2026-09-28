#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count

PROFILE_ID="FA3-CREATIVE-OPERATIONS-DASHBOARD-001"
CONTRACT_ID="FA3-CREATIVE-OPERATIONS-DASHBOARD-CONTRACTS-001"
GATE_ID="FA3-CREATIVE-OPERATIONS-DASHBOARD-GATESET-001"
DECISION_ID="FA3-DEC-CREATIVE-OPERATIONS-DASHBOARD-NATIVE-2026-09-26"
CAPABILITY_ID="CAP-057"
CAPABILITY_COUNT=module_active_capability_count(__file__)

def _load(p): return json.loads(p.read_text(encoding="utf-8"))
def gate(root: Path):
    profile=_load(root/"canonical/profiles/FA3-CREATIVE-OPERATIONS-DASHBOARD-001.json")
    contract=_load(root/"canonical/contracts/FA3-CREATIVE-OPERATIONS-DASHBOARD-CONTRACTS-001.json")
    action=(root/"deployment/creative-operations-dashboard/bin/fa3-creative-ops-action").read_text(encoding="utf-8")
    findings=[]
    if not (profile.get("id")==PROFILE_ID and profile.get("provider_ids")==[] and profile.get("capability_count")==CAPABILITY_COUNT and profile.get("capability_projection")==[CAPABILITY_ID] and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False):
        findings.append("profile-drift")
    if not (contract.get("id")==CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("external_runtime_dependency") is False and contract.get("capability_count")==CAPABILITY_COUNT and contract.get("capability_projection")==[CAPABILITY_ID]):
        findings.append("contract-drift")
    for token in ("open_loopback_url","ALLOW_ENUMERATED_UNITS_ONLY","FORBIDDEN"):
        if token not in (action + json.dumps(contract)): findings.append("action-boundary-drift:"+token)
    return {"schema":"fa3.creative-operations-dashboard-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"contract_id":CONTRACT_ID,"capability_id":CAPABILITY_ID,"capability_count":CAPABILITY_COUNT,"result":"PASS" if not findings else "FAIL","findings":findings,"current_host_runtime_promotion_claim":False}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--output"); a=ap.parse_args()
    r=gate(Path(a.root).resolve())
    if a.output: Path(a.output).write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,indent=2)); raise SystemExit(0 if r["result"]=="PASS" else 2)
if __name__=="__main__": main()
