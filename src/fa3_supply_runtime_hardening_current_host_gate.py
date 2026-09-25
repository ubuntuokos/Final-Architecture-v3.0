#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count
from fa3_supply_runtime_hardening_gate import gate as parent_gate

CONF="canonical/FA3-SUPPLY-RUNTIME-HARDENING-CURRENT-HOST-CONFORMANCE-001.json"
GATE_RECORD="canonical/FA3-GATE-SUPPLY-RUNTIME-HARDENING-CURRENT-HOST-001.json"
SCS_RECEIPT="evidence/receipts/supply-chain-admission-current-host.json"
PROVIDER_RECEIPT="evidence/receipts/provider-runtime-current-host.json"
HRB_RECEIPT="evidence/receipts/hrb-composite-current-host.json"
HU_RECEIPT="evidence/receipts/hu-aqc-golden-corpus-current-host.json"
GATESET="FA3-SUPPLY-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"

def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def finding(code,msg,**kw):return {"code":code,"severity":"P0","message":msg,**kw}

def validate_scs(row:dict[str,Any])->list[dict[str,Any]]:
    fs=[]
    if row.get("schema")!="fa3.software-supply-chain-receipt.v1" or row.get("current_host_execution") is not True or row.get("synthetic") is not False:fs.append(finding("SRH-HOST-051","SCS receipt is not explicit real current-host execution"))
    if row.get("admission",{}).get("result")!="PASS" or row.get("admission",{}).get("admitted") is not True:fs.append(finding("SRH-HOST-052","SCS automated admission did not PASS"))
    lic=row.get("license",{})
    if lic.get("policy_result")!="PASS" or lic.get("declaration_matches_detection") is not True:fs.append(finding("SRH-HOST-053","SCS automated license policy did not PASS"))
    if row.get("artifact",{}).get("hash_scope") not in {"FILE_CONTENT","DETERMINISTIC_TREE_CONTENT"}:fs.append(finding("SRH-HOST-054","SCS artifact content hash scope missing"))
    return fs

def validate_provider(row:dict[str,Any])->list[dict[str,Any]]:
    fs=[]
    if row.get("schema")!="fa3.provider-runtime-current-host-receipt.v1" or row.get("status")!="CURRENT_HOST_PASS":fs.append(finding("SRH-HOST-071","provider runtime current-host receipt does not PASS"))
    if row.get("execution_class") not in {"VENV","OCI","HOST_NATIVE"}:fs.append(finding("SRH-HOST-072","provider runtime execution class invalid"))
    if row.get("synthetic") is not False or row.get("global_promotion_claim") is not False:fs.append(finding("SRH-HOST-073","provider runtime provenance/promotion boundary drift"))
    return fs

def validate_hrb(row:dict[str,Any])->list[dict[str,Any]]:
    fs=[]
    if row.get("schema")!="fa3.hrb-composite-current-host-receipt.v1" or row.get("status")!="CURRENT_HOST_CONTROL_PLANE_PASS":fs.append(finding("SRH-HOST-101","HRB composite current-host receipt does not PASS"))
    for k in ("overflow_refused","forged_parent_refused","parent_revocation_cascades"):
        if row.get(k) is not True:fs.append(finding("SRH-HOST-102","HRB composite negative/cascade proof missing",field=k))
    if row.get("test_only_ephemeral_hmac") is not True or row.get("hmac_secret_persisted") is not False:fs.append(finding("SRH-HOST-103","HRB current-host ephemeral integrity boundary drift"))
    if row.get("production_broker_promotion_claim") is not False or row.get("global_promotion_claim") is not False:fs.append(finding("SRH-HOST-104","control-plane receipt overclaims production/global promotion"))
    return fs

def validate_hu(row:dict[str,Any],profile:dict[str,Any])->list[dict[str,Any]]:
    fs=[];required=set(profile.get("golden_corpus",{}).get("categories",[]));observed=set(row.get("observed_categories",[]))
    if row.get("schema")!="fa3.hu-aqc-golden-corpus-current-host-receipt.v1" or row.get("status")!="CURRENT_HOST_PASS":fs.append(finding("SRH-HOST-201","HU golden-corpus current-host receipt does not PASS"))
    if not required or not required.issubset(observed):fs.append(finding("SRH-HOST-202","HU golden-corpus category coverage incomplete",missing=sorted(required-observed)))
    if row.get("sample_count",0)<len(required):fs.append(finding("SRH-HOST-203","HU golden corpus sample count below required category count"))
    if row.get("threshold_relaxation_performed") is not False:fs.append(finding("SRH-HOST-204","HU AQC threshold relaxation forbidden for closure"))
    if row.get("synthetic") is not False or row.get("global_promotion_claim") is not False:fs.append(finding("SRH-HOST-205","HU corpus evidence provenance/promotion boundary drift"))
    return fs

def gate(root:Path,*,require_evidence:bool=False)->dict[str,Any]:
    root=root.resolve();fs=[];count=module_active_capability_count(__file__)
    parent=parent_gate(root)
    if parent.get("result")!="PASS":fs.append(finding("SRH-HOST-001","parent hardening gate failed"))
    try:conf=loadj(root/CONF);gr=loadj(root/GATE_RECORD);hu_profile=loadj(root/"canonical/profiles/FA3-HU-AQC-001.json")
    except Exception as exc:
        return {"schema":"fa3.supply-runtime-hardening-current-host-gate-report.v1","gateset_id":GATESET,"result":"FAIL","status":"BLOCKED","findings":[finding("SRH-HOST-002","current-host materialization unreadable",error=repr(exc))]}
    if conf.get("current_host_gate")!=GATESET or conf.get("capability_count")!=count or conf.get("new_architectural_authorities")!=0 or conf.get("global_promotion_claim") is not False:fs.append(finding("SRH-HOST-003","current-host conformance invariant drift"))
    if gr.get("gateset_id")!=GATESET or gr.get("fail_closed") is not True or gr.get("global_promotion_claim") is not False:fs.append(finding("SRH-HOST-004","current-host gate record drift"))
    receipts={}
    for name,rel in (("scs",SCS_RECEIPT),("provider",PROVIDER_RECEIPT),("hrb",HRB_RECEIPT),("hu",HU_RECEIPT)):
        p=root/rel
        if p.is_file():
            try:receipts[name]=loadj(p)
            except Exception as exc:fs.append(finding("SRH-HOST-005","receipt unreadable",path=rel,error=repr(exc)))
    if "scs" in receipts:fs.extend(validate_scs(receipts["scs"]))
    if "provider" in receipts:fs.extend(validate_provider(receipts["provider"]))
    if "hrb" in receipts:fs.extend(validate_hrb(receipts["hrb"]))
    if "hu" in receipts:fs.extend(validate_hu(receipts["hu"],hu_profile))
    missing=[name for name in ("scs","provider","hrb","hu") if name not in receipts]
    if require_evidence and missing:fs.append(finding("SRH-HOST-006","required real current-host evidence missing",missing=missing))
    if fs:result,status="FAIL","BLOCKED"
    elif missing:result,status="PASS","PENDING_CURRENT_HOST"
    else:result,status="PASS","CURRENT_HOST_SCOPE_PASS"
    return {"schema":"fa3.supply-runtime-hardening-current-host-gate-report.v1","gate_id":"FA3-GATE-SUPPLY-RUNTIME-HARDENING-CURRENT-HOST-001","gateset_id":GATESET,"result":result,"status":status,"findings":fs,"missing_surfaces":missing,"surface_pass_count":4-len(missing),"capability_count":count,"new_capabilities":0,"new_architectural_authorities":0,"production_broker_promotion_claim":False,"global_promotion_claim":False}

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));p.add_argument("--require-evidence",action="store_true");p.add_argument("--report",default="reports/supply-runtime-hardening-current-host-gate-report.json");a=p.parse_args()
    root=Path(a.root).resolve();r=gate(root,require_evidence=a.require_evidence);out=root/a.report;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(json.dumps(r,indent=2,ensure_ascii=False));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
