#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

POLICY_PATH=Path("canonical/FA3-CURRENT-HOST-STRUCTURAL-CHANGE-POLICY-001.json")
DELTA_AUTHORITY_PATH=Path("canonical/FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001.json")
BASE_STATE_PATH=Path("canonical/FA3-CURRENT-HOST-BASE-STATE-001.json")
MANIFEST_PATH=Path("fa3-current-host/manifest.json")
CAP_RE=re.compile(r"^CAP-\d{3}$")
GLOBAL_PROOF_SURFACES={
 "canonical/current-host-capability-test-executors.json",
 "canonical/current-host-capability-test-qualifications.json",
 "canonical/current-host-capability-qualification-constituent-producers.json",
 "canonical/current-host-capability-proof-recipes.json",
 "canonical/FA3-CURRENT-HOST-STRUCTURAL-CHANGE-POLICY-001.json",
 "evidence/evidence-registry.json",
 "src/fa3_current_host_batch_planner.py",
 "src/fa3_current_host_batch_integrity.py",
 "src/fa3_current_host_closure_assertion.py",
 "src/fa3_current_host_evidence_audit.py",
 ".github/workflows/fa3-global-current-host-closure.yml",
}

def load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"JSON object required: {path}")
    return value

def cap_key(v:str):
    try:return (int(v.split("-",1)[1]),v)
    except Exception:return (10**9,v)

def infer_full_base_admitted(root:Path)->bool:
    base_path=root/BASE_STATE_PATH
    if base_path.is_file():
        base=load(base_path)
        return (
            base.get("schema")=="fa3.current-host-base-state.v1"
            and base.get("status")=="CURRENT_HOST_BASE_ADMITTED"
            and base.get("capability_count")==175
            and base.get("obligation_count")==525
            and isinstance(base.get("base_release_digest"),str)
            and len(base["base_release_digest"])==64
            and base.get("effective_host_digest")==base.get("base_release_digest")
        )
    active=load(root/MANIFEST_PATH).get("active_closure",{})
    return active.get("status") in {"ADMITTED_FULL_BASE","FULL_175_525_EXACT_HEAD_PASS_POST_MERGE_AUDITED"}

def affected(records:list[dict[str,Any]])->list[str]:
    out=set()
    for row in records:
        for key in ("affected_capability_ids","capability_ids"):
            raw=row.get(key,[])
            if isinstance(raw,list): out.update(x for x in raw if isinstance(x,str) and CAP_RE.fullmatch(x))
        for key in ("capability_subject","capability_id"):
            x=row.get(key)
            if isinstance(x,str) and CAP_RE.fullmatch(x): out.add(x)
    return sorted(out,key=cap_key)

def build_requalification_plan(root:Path, structural_report:dict[str,Any], *, projection_valid:bool,
                               main_in_lineage:bool, full_base_admitted:bool|None=None)->dict[str,Any]:
    root=root.resolve(); policy=load(root/POLICY_PATH); delta_authority=load(root/DELTA_AUTHORITY_PATH); findings=[]
    if structural_report.get("result")!="PASS": findings.append("STRUCTURAL_IMPACT_GATE_NOT_PASS")
    records=[]
    for rel in structural_report.get("impact_records",[]):
        try: records.append(load(root/rel))
        except Exception: findings.append(f"IMPACT_RECORD_UNAVAILABLE:{rel}")
    physical=[r for r in records if r.get("physical_requalification_required") is True]
    caps=affected(physical)
    changed=set(structural_report.get("changed_files",[]))
    explicit_full=any(
        "FULL" in str(r.get("physical_requalification_scope","")).upper()
        or "ACTIVE_175" in str(r.get("physical_requalification_scope","")).upper()
        or "525" in str(r.get("physical_requalification_scope","")).upper()
        or r.get("global_requalification_required") is True
        or r.get("proof_model_change") is True
        for r in physical
    )
    if physical and changed.intersection(GLOBAL_PROOF_SURFACES): explicit_full=True
    if full_base_admitted is None: full_base_admitted=infer_full_base_admitted(root)
    if findings: mode="BLOCKED"
    elif not physical: mode="NONE"
    elif explicit_full: mode="FULL"
    elif not full_base_admitted: mode="FULL"
    elif not caps:
        findings.append("SCOPED_REQUALIFICATION_SCOPE_UNDECLARED"); mode="BLOCKED"
    else:
        mandatory={
            x for x in delta_authority.get("mandatory_runtime_delta_capabilities",[])
            if isinstance(x,str) and CAP_RE.fullmatch(x)
        }
        caps=sorted(set(caps)|mandatory,key=cap_key)
        mode="SCOPED"
    ready=(not findings and mode in {"FULL","SCOPED"} and projection_valid and main_in_lineage)
    return {
      "schema":"fa3.current-host-requalification-plan.v1","policy_id":policy.get("id"),
      "result":"PASS" if not findings else "FAIL","mode":mode,
      "batch_id":"FULL-525" if mode=="FULL" else ("SCOPED" if mode=="SCOPED" else ""),
      "affected_capability_ids":caps if mode=="SCOPED" else [],
      "affected_capability_count":len(caps if mode=="SCOPED" else []),
      "projection_valid":projection_valid,"main_in_lineage":main_in_lineage,
      "full_base_admitted":bool(full_base_admitted),"physical_requalification_required":bool(physical),
      "global_or_proof_model_change":explicit_full,"execution_ready":ready,
      "historical_evidence_reused":False,"unchanged_base_evidence_relabelled":False,
      "capability_baseline":policy.get("capability_count"),
      "full_obligation_count":int(policy.get("capability_count",0))*3,
      "delta_policy":policy.get("delta_policy",{}),
      "delta_authority_id":delta_authority.get("id"),
      "mandatory_runtime_delta_capabilities":delta_authority.get("mandatory_runtime_delta_capabilities",[]),
      "findings":findings,
    }

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--structural-report",default="reports/current-host-structural-impact-gate-report.json")
    p.add_argument("--projection-valid",action="store_true"); p.add_argument("--main-in-lineage",action="store_true")
    p.add_argument("--full-base-admitted",choices=("auto","true","false"),default="auto")
    p.add_argument("--output",default="reports/current-host-requalification-plan.json")
    a=p.parse_args(); root=Path(a.root).resolve()
    base=None if a.full_base_admitted=="auto" else a.full_base_admitted=="true"
    r=build_requalification_plan(root,load(root/a.structural_report),projection_valid=a.projection_valid,
                                 main_in_lineage=a.main_in_lineage,full_base_admitted=base)
    out=root/a.output; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False,indent=2))
    gp=os.getenv("GITHUB_OUTPUT","")
    if gp:
        with open(gp,"a",encoding="utf-8") as f:
            f.write(f"mode={r['mode']}\n"); f.write(f"batch_id={r['batch_id']}\n")
            f.write(f"subjects={','.join(r['affected_capability_ids'])}\n")
            f.write(f"execute={'true' if r['execution_ready'] else 'false'}\n")
    return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
