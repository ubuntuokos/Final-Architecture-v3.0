#!/usr/bin/env python3
from __future__ import annotations
from copy import deepcopy
from typing import Any

HRB_AUTHORITY_ID="FA3-AUTH-HOST-RESOURCE-BROKER-001"
RESOURCE_ORDER=("CPU","RAM","NUMA","ACCELERATOR","VRAM","IO","NETWORK")
NUMERIC_RESOURCES=("cpu_threads","ram_bytes","vram_bytes","io_bytes_per_second","network_bytes_per_second")

class CompositeLeaseError(RuntimeError): pass

def _resources(row:dict[str,Any])->dict[str,int]:
    src=row.get("resources",{})
    out={}
    for k in NUMERIC_RESOURCES:
        v=src.get(k,0)
        if not isinstance(v,int) or v<0: raise CompositeLeaseError(f"invalid resource {k}")
        out[k]=v
    return out

def evaluate_reservation_plan(plan:dict[str,Any],capacity:dict[str,int])->dict[str,Any]:
    findings=[]
    if plan.get("schema")!="fa3.resource-reservation-plan.v1": findings.append("schema mismatch")
    if plan.get("authority_id")!=HRB_AUTHORITY_ID: findings.append("HRB authority mismatch")
    if plan.get("atomic_admission") is not True: findings.append("atomic admission required")
    if plan.get("hold_and_wait") is not False: findings.append("hold-and-wait forbidden")
    if tuple(plan.get("acquisition_order",[]))!=RESOURCE_ORDER: findings.append("canonical acquisition order required")
    workloads=plan.get("workloads",[])
    if not isinstance(workloads,list) or not workloads: findings.append("workloads missing"); workloads=[]
    byid={}
    try:
        for w in workloads:
            wid=w.get("id")
            if not wid or wid in byid: raise CompositeLeaseError("duplicate/missing workload id")
            byid[wid]=_resources(w)
    except CompositeLeaseError as e: findings.append(str(e))
    groups=plan.get("overlap_groups") or [[w.get("id")] for w in workloads]
    ceiling={k:0 for k in NUMERIC_RESOURCES}
    for group in groups:
        total={k:0 for k in NUMERIC_RESOURCES}
        if not isinstance(group,list) or not group: findings.append("invalid overlap group"); continue
        for wid in group:
            if wid not in byid: findings.append(f"unknown overlap workload {wid}"); continue
            for k,v in byid[wid].items(): total[k]+=v
        for k,v in total.items(): ceiling[k]=max(ceiling[k],v)
    for k,v in ceiling.items():
        cap=capacity.get(k,0)
        if not isinstance(cap,int) or cap<0 or v>cap: findings.append(f"insufficient {k}")
    accelerators=plan.get("accelerators",[])
    if not isinstance(accelerators,list): findings.append("accelerators malformed")
    else:
        for a in accelerators:
            if not a.get("stable_id"): findings.append("accelerator stable identity missing")
            if a.get("runtime_ordinal_is_identity") is not False: findings.append("runtime ordinal cannot be accelerator identity")
    return {"result":"PASS" if not findings else "FAIL","atomic_admitted":not findings,"reservation_ceiling":ceiling,"findings":findings}

def derive_child_lease(parent:dict[str,Any],request:dict[str,Any],*,issuer:str)->dict[str,Any]:
    if issuer!=HRB_AUTHORITY_ID: raise CompositeLeaseError("only HRB may derive a lease")
    if parent.get("state")!="ACTIVE": raise CompositeLeaseError("parent lease not active")
    if request.get("expires_at_utc","")>parent.get("expires_at_utc",""): raise CompositeLeaseError("child expiry exceeds parent")
    parent_res=_resources(parent); child_res=_resources(request)
    allocated=parent.get("child_allocated_resources",{})
    for k,v in child_res.items():
        if v+int(allocated.get(k,0))>parent_res[k]: raise CompositeLeaseError(f"child budget exceeds parent {k}")
    parent_acc={a.get("stable_id") for a in parent.get("accelerator_assignments",[])}
    for a in request.get("accelerator_assignments",[]):
        if a.get("stable_id") not in parent_acc: raise CompositeLeaseError("child accelerator outside parent")
    child={
      "schema":"FA3-HOST-RESOURCE-BROKER-001/DerivedExecutionLease@1",
      "issuer":HRB_AUTHORITY_ID,
      "parent_lease_id":parent.get("lease_id"),
      "parent_generation":parent.get("generation"),
      "lease_id":request.get("lease_id"),
      "generation":1,
      "state":"ISSUED",
      "resources":deepcopy(request.get("resources",{})),
      "accelerator_assignments":deepcopy(request.get("accelerator_assignments",[])),
      "issued_at_utc":request.get("issued_at_utc"),
      "expires_at_utc":request.get("expires_at_utc"),
      "scope":deepcopy(request.get("scope",{})),
      "revocation_cascades_from_parent":True,
      "may_mint_child_lease":False,
    }
    if not child["lease_id"]: raise CompositeLeaseError("child lease id missing")
    return child

def cascade_revocation(parent:dict[str,Any],children:list[dict[str,Any]])->list[dict[str,Any]]:
    if parent.get("state") not in {"REVOKING","EVICTING","EVICTED","QUARANTINED"}:
        raise CompositeLeaseError("parent is not revoking/terminal")
    out=[]
    for c in children:
        x=deepcopy(c)
        if x.get("parent_lease_id")!=parent.get("lease_id"): raise CompositeLeaseError("foreign child in cascade")
        if x.get("state") not in {"EVICTED","QUARANTINED"}: x["state"]="REVOKING"
        out.append(x)
    return out
