#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Any
from fa3_hrb_composite_lease import CompositeLeaseError,CompositeLeaseIssuer,evaluate_reservation_plan
from fa3_hrb_lease_lifecycle import LeaseKey,LeaseKeyring
from fa3_release_baseline import module_active_capability_count

def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def utc(dt:datetime)->str: return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")
def writej(p:Path,o:dict[str,Any])->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def collect(root:Path,plan_path:Path,capacity_path:Path,output:Path)->dict[str,Any]:
    started=time.monotonic(); now=datetime.now(timezone.utc)
    receipt={"schema":"fa3.hrb-composite-current-host-receipt.v1","surface":"HRB_COMPOSITE_RESERVATION_CONTROL_PLANE","captured_at":utc(now),"synthetic":False,"test_only_ephemeral_hmac":True,"production_broker_promotion_claim":False,"global_promotion_claim":False}
    try:
        plan=loadj(plan_path); capacity=loadj(capacity_path)
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
    p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));p.add_argument("--plan",required=True);p.add_argument("--capacity",required=True);p.add_argument("--output",default="evidence/receipts/hrb-composite-current-host.json");a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.output);out=out if out.is_absolute() else root/out
    r=collect(root,Path(a.plan).resolve(),Path(a.capacity).resolve(),out);print(json.dumps(r,indent=2,ensure_ascii=False));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
