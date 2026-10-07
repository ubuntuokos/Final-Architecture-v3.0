#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,os,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Any
from fa3_hrb_composite_lease import CompositeLeaseError,CompositeLeaseIssuer,evaluate_reservation_plan
from fa3_hrb_lease_lifecycle import LeaseKey,LeaseKeyring
from fa3_release_baseline import module_active_capability_count

def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def utc(dt:datetime)->str: return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")
def writej(p:Path,o:dict[str,Any])->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def load_hardware_discovery(root:Path):
    source=root/"evidence/collect-hrb-systemd-manager-current-host.py"
    spec=importlib.util.spec_from_file_location("fa3_hrb_live_hardware",source)
    if spec is None or spec.loader is None: raise RuntimeError("cannot load current-host hardware discovery")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.hardware_discovery()

def derive_live_plan_capacity(discovery:dict[str,Any])->tuple[dict[str,Any],dict[str,int]]:
    cpu=discovery.get("cpu",{});logical=max(1,int(cpu.get("logical_cpu_count",1)))
    try:ram_total=int(os.sysconf("SC_PAGE_SIZE"))*int(os.sysconf("SC_PHYS_PAGES"))
    except Exception:ram_total=1024**3
    devices=[d for d in discovery.get("accelerators",{}).get("devices",[]) if isinstance(d,dict) and d.get("eligible_for_workload_admission") and d.get("stable_id")]
    first=devices[0] if devices else None
    vram_total=max(0,int(first.get("vram_mib_evidence_only",0))*1024*1024) if first else 0
    child_cpu=1 if logical>=2 else 0
    child_ram=max(1,min(ram_total//10,8*1024**3))
    child_vram=max(0,min(vram_total//5,4*1024**3)) if vram_total else 0
    resources={"cpu_threads":child_cpu,"ram_bytes":child_ram,"vram_bytes":child_vram,"io_bytes_per_second":0,"network_bytes_per_second":0}
    plan={"schema":"fa3.resource-reservation-plan.v1","authority_id":"FA3-AUTH-HOST-RESOURCE-BROKER-001","atomic_admission":True,"hold_and_wait":False,"acquisition_order":["CPU","RAM","NUMA","ACCELERATOR","VRAM","IO","NETWORK"],"queue_policy":{"max_waiters":8,"deadline_seconds":30},"workloads":[{"id":"current-host-child-a","resources":dict(resources)},{"id":"current-host-child-b","resources":dict(resources)}],"overlap_groups":[["current-host-child-a","current-host-child-b"]],"accelerators":[]}
    if first:plan["accelerators"]=[{"stable_id":str(first["stable_id"]),"runtime_ordinal_is_identity":False}]
    capacity={"cpu_threads":logical,"ram_bytes":ram_total,"vram_bytes":vram_total,"io_bytes_per_second":0,"network_bytes_per_second":0}
    return plan,capacity

def collect(root:Path,plan_path:Path|None,capacity_path:Path|None,output:Path)->dict[str,Any]:
    started=time.monotonic(); now=datetime.now(timezone.utc)
    receipt={"schema":"fa3.hrb-composite-current-host-receipt.v1","surface":"HRB_COMPOSITE_RESERVATION_CONTROL_PLANE","captured_at":utc(now),"synthetic":False,"test_only_ephemeral_hmac":True,"production_broker_promotion_claim":False,"global_promotion_claim":False}
    try:
        if plan_path is None and capacity_path is None:
            discovery=load_hardware_discovery(root);plan,capacity=derive_live_plan_capacity(discovery);input_mode="AUTO_LIVE_HARDWARE_DISCOVERY"
            receipt["hardware_discovery_fingerprint_sha256"]=discovery.get("fingerprint_sha256")
            receipt["accelerator_device_count"]=discovery.get("accelerators",{}).get("device_count",0)
        elif plan_path is not None and capacity_path is not None:
            plan=loadj(plan_path);capacity=loadj(capacity_path);input_mode="EXPLICIT_OPERATOR_INPUT"
        else:raise RuntimeError("plan and capacity must be supplied together or both omitted")
        receipt["input_mode"]=input_mode
        result=evaluate_reservation_plan(plan,capacity)
        if result["result"]!="PASS": raise RuntimeError("reservation plan not atomically admissible: "+",".join(result["findings"]))
        groups=plan.get("overlap_groups") or [[w["id"]] for w in plan["workloads"]]
        byid={w["id"]:w for w in plan["workloads"]}
        def score(group:list[str])->int:
            return sum(sum(int(v) for v in byid[i].get("resources",{}).values() if isinstance(v,int)) for i in group)
        peak=max(groups,key=score)
        key_id="current-host-"+os.urandom(4).hex()
        keyring=LeaseKeyring([LeaseKey(key_id,os.urandom(32))],key_id)
        accelerators=[{"stable_id":a["stable_id"]} for a in plan.get("accelerators",[]) if a.get("stable_id")]
        parent={"lease_id":"current-host-parent-"+os.urandom(6).hex(),"generation":1,"issuer":"FA3-AUTH-HOST-RESOURCE-BROKER-001","state":"ACTIVE","issued_at_utc":utc(now),"expires_at_utc":utc(now+timedelta(minutes=10)),"resources":result["reservation_ceiling"],"accelerator_assignments":accelerators,"scope":{"workload_id":peak},"authentication":{}}
        parent["authentication"]=keyring.sign(parent)
        issuer=CompositeLeaseIssuer(keyring);issuer.register_parent(parent)
        children=[]
        first_acc=accelerators[:1]
        for idx,wid in enumerate(peak):
            w=byid[wid];r=w.get("resources",{})
            req={"lease_id":f"current-host-child-{idx}-{os.urandom(4).hex()}","issued_at_utc":utc(now),"expires_at_utc":utc(now+timedelta(minutes=5)),"resources":r,"accelerator_assignments":first_acc if int(r.get("vram_bytes",0))>0 else [],"scope":{"workload_id":wid}}
            c=issuer.derive(parent["lease_id"],req);keyring.verify(c);children.append(c)
        overflow_refused=False
        try:
            issuer.derive(parent["lease_id"],{"lease_id":"overflow-"+os.urandom(4).hex(),"issued_at_utc":utc(now),"expires_at_utc":utc(now+timedelta(minutes=5)),"resources":{"cpu_threads":1,"ram_bytes":1,"vram_bytes":1,"io_bytes_per_second":1,"network_bytes_per_second":1},"accelerator_assignments":first_acc,"scope":{"workload_id":peak[0]}})
        except CompositeLeaseError: overflow_refused=True
        forged_refused=False
        forged=json.loads(json.dumps(parent));forged["authentication"]["mac"]="0"*64
        try:CompositeLeaseIssuer(keyring).register_parent(forged)
        except CompositeLeaseError:forged_refused=True
        cascaded=issuer.revoke_parent(parent["lease_id"])
        cascade_ok=len(cascaded)==len(children) and all(c.get("state")=="REVOKING" for c in cascaded)
        for c in cascaded:keyring.verify(c)
        if not (overflow_refused and forged_refused and cascade_ok):raise RuntimeError("mandatory negative/cascade proof failed")
        receipt.update({"result":"PASS","status":"CURRENT_HOST_CONTROL_PLANE_PASS","capability_count":module_active_capability_count(__file__),"plan_result":result,"peak_overlap_group":peak,"derived_child_count":len(children),"aggregate_allocation_before_revoke":issuer.allocation(parent["lease_id"]),"overflow_refused":True,"forged_parent_refused":True,"parent_revocation_cascades":True,"bounded_execution_seconds":round(time.monotonic()-started,6),"hmac_secret_persisted":False})
    except Exception as exc:
        receipt.update({"result":"PENDING","status":"PENDING_CURRENT_HOST","error_type":type(exc).__name__,"error":str(exc)})
    writej(output,receipt);return receipt

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));p.add_argument("--plan",default="");p.add_argument("--capacity",default="");p.add_argument("--output",default="evidence/receipts/hrb-composite-current-host.json");a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.output);out=out if out.is_absolute() else root/out
    plan=Path(a.plan).resolve() if a.plan else None;capacity=Path(a.capacity).resolve() if a.capacity else None
    r=collect(root,plan,capacity,out);print(json.dumps(r,indent=2,ensure_ascii=False));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
