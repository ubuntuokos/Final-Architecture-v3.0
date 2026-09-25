#!/usr/bin/env python3
from __future__ import annotations
from copy import deepcopy
from typing import Any
from fa3_hrb_lease_lifecycle import LeaseKeyring

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


def _scope_subset(parent:Any,child:Any)->bool:
    if isinstance(parent,dict):
        return isinstance(child,dict) and all(k in parent and _scope_subset(parent[k],v) for k,v in child.items())
    if isinstance(parent,list):
        if isinstance(child,list): return all(v in parent for v in child)
        return child in parent
    return parent==child

def evaluate_reservation_plan(plan:dict[str,Any],capacity:dict[str,int])->dict[str,Any]:
    findings=[]
    if plan.get("schema")!="fa3.resource-reservation-plan.v1": findings.append("schema mismatch")
    if plan.get("authority_id")!=HRB_AUTHORITY_ID: findings.append("HRB authority mismatch")
    if plan.get("atomic_admission") is not True: findings.append("atomic admission required")
    if plan.get("hold_and_wait") is not False: findings.append("hold-and-wait forbidden")
    if tuple(plan.get("acquisition_order",[]))!=RESOURCE_ORDER: findings.append("canonical acquisition order required")
    queue=plan.get("queue_policy",{})
    if not isinstance(queue,dict) or not isinstance(queue.get("max_waiters"),int) or queue.get("max_waiters",0)<1: findings.append("bounded queue max_waiters required")
    if not isinstance(queue,dict) or not isinstance(queue.get("deadline_seconds"),(int,float)) or queue.get("deadline_seconds",0)<=0: findings.append("positive queue deadline required")
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

def derive_child_lease(parent:dict[str,Any],request:dict[str,Any],*,keyring:LeaseKeyring,allocated_resources:dict[str,int]|None=None)->dict[str,Any]:
    try:
        keyring.verify(parent)
    except Exception as exc:
        raise CompositeLeaseError("parent lease is not authenticated by the HRB internal lease keyring") from exc
    if parent.get("issuer")!=HRB_AUTHORITY_ID: raise CompositeLeaseError("parent issuer is not HRB")
    if parent.get("state")!="ACTIVE": raise CompositeLeaseError("parent lease not active")
    if request.get("expires_at_utc","")>parent.get("expires_at_utc",""): raise CompositeLeaseError("child expiry exceeds parent")
    parent_scope=parent.get("scope",{})
    child_scope=request.get("scope",{})
    if not _scope_subset(parent_scope,child_scope): raise CompositeLeaseError("child scope exceeds parent scope")
    parent_res=_resources(parent); child_res=_resources(request)
    allocated=allocated_resources if allocated_resources is not None else parent.get("child_allocated_resources",{})
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
    child["authentication"]=keyring.sign(child)
    return child

def cascade_revocation(parent:dict[str,Any],children:list[dict[str,Any]],*,keyring:LeaseKeyring)->list[dict[str,Any]]:
    try:
        keyring.verify(parent)
    except Exception as exc:
        raise CompositeLeaseError("parent lease authentication invalid") from exc
    if parent.get("state") not in {"REVOKING","EVICTING","EVICTED","QUARANTINED"}:
        raise CompositeLeaseError("parent is not revoking/terminal")
    out=[]
    for c in children:
        try:
            keyring.verify(c)
        except Exception as exc:
            raise CompositeLeaseError("derived child authentication invalid") from exc
        x=deepcopy(c)
        if x.get("parent_lease_id")!=parent.get("lease_id"): raise CompositeLeaseError("foreign child in cascade")
        if x.get("state") not in {"EVICTED","QUARANTINED"}: x["state"]="REVOKING"
        x["authentication"]=keyring.sign(x)
        out.append(x)
    return out


class CompositeLeaseIssuer:
    """Stateful HRB-side derived-lease allocator.

    The object must be constructed inside the HRB trust boundary with the existing
    ephemeral LeaseKeyring. Providers never receive the keyring and therefore
    cannot mint or mutate authenticated derived leases.
    """
    def __init__(self,keyring:LeaseKeyring):
        self._keyring=keyring
        self._parents:dict[str,dict[str,Any]]={}
        self._children:dict[str,dict[str,dict[str,Any]]]={}
        self._allocated:dict[str,dict[str,int]]={}

    def register_parent(self,parent:dict[str,Any])->None:
        try:self._keyring.verify(parent)
        except Exception as exc: raise CompositeLeaseError("parent lease authentication invalid") from exc
        if parent.get("issuer")!=HRB_AUTHORITY_ID or parent.get("state")!="ACTIVE":
            raise CompositeLeaseError("only an authenticated ACTIVE HRB parent may be registered")
        pid=str(parent.get("lease_id",""))
        if not pid: raise CompositeLeaseError("parent lease id missing")
        self._parents[pid]=deepcopy(parent)
        self._children.setdefault(pid,{})
        self._allocated.setdefault(pid,{k:0 for k in NUMERIC_RESOURCES})

    def derive(self,parent_id:str,request:dict[str,Any])->dict[str,Any]:
        if parent_id not in self._parents: raise CompositeLeaseError("parent not registered")
        parent=deepcopy(self._parents[parent_id])
        child=derive_child_lease(parent,request,keyring=self._keyring,allocated_resources=deepcopy(self._allocated[parent_id]))
        cid=str(child["lease_id"])
        if cid in self._children[parent_id]: raise CompositeLeaseError("duplicate child lease id")
        for k,v in _resources(child).items(): self._allocated[parent_id][k]+=v
        self._children[parent_id][cid]=deepcopy(child)
        return deepcopy(child)

    def release(self,parent_id:str,child_id:str)->dict[str,Any]:
        child=self._children.get(parent_id,{}).get(child_id)
        if child is None: raise CompositeLeaseError("child lease not found")
        try:self._keyring.verify(child)
        except Exception as exc: raise CompositeLeaseError("child lease authentication invalid") from exc
        if child.get("state") not in {"EVICTED","QUARANTINED"}:
            child=deepcopy(child); child["state"]="EVICTED"; child["authentication"]=self._keyring.sign(child)
        for k,v in _resources(child).items(): self._allocated[parent_id][k]=max(0,self._allocated[parent_id][k]-v)
        self._children[parent_id].pop(child_id,None)
        return deepcopy(child)

    def revoke_parent(self,parent_id:str)->list[dict[str,Any]]:
        parent=deepcopy(self._parents.get(parent_id) or {})
        if not parent: raise CompositeLeaseError("parent not registered")
        parent["state"]="REVOKING"; parent["authentication"]=self._keyring.sign(parent)
        children=list(self._children[parent_id].values())
        cascaded=cascade_revocation(parent,children,keyring=self._keyring)
        self._parents[parent_id]=parent
        self._children[parent_id]={str(c["lease_id"]):deepcopy(c) for c in cascaded}
        return deepcopy(cascaded)

    def allocation(self,parent_id:str)->dict[str,int]:
        if parent_id not in self._allocated: raise CompositeLeaseError("parent not registered")
        return deepcopy(self._allocated[parent_id])
