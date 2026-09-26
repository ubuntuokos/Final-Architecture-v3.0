#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fa3_release_baseline import load_active_release_baseline

def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def build(root: Path) -> dict:
    root=root.resolve()
    baseline=load_active_release_baseline(root)
    footprints={}
    fp_dir=root/"canonical/coexistence/footprints"
    if fp_dir.is_dir():
        for path in sorted(fp_dir.glob("*.json")):
            try:
                row=_load(path)
            except Exception:
                continue
            cid=row.get("component_id")
            if isinstance(cid,str):
                footprints[cid]=(path,row)

    entries=[]
    provider_dir=root/"canonical/providers"
    for path in sorted(provider_dir.glob("*.json")):
        row=_load(path)
        cid=row.get("id")
        if not isinstance(cid,str) or not cid.startswith("FA3-PROVIDER-"):
            continue
        fp=footprints.get(cid)
        if fp is None:
            footprint_status="PENDING_FOOTPRINT"
            coexistence_status="STATIC_AUDIT_PENDING"
            footprint_path=None
        else:
            footprint_status="MATERIALIZED"
            footprint_path=fp[0].relative_to(root).as_posix()
            ev=fp[1].get("evidence",{})
            static=ev.get("static_status")
            host=ev.get("current_host_status")
            if static=="FAIL" or host=="FAIL":
                coexistence_status="STATIC_AUDIT_FAIL"
            elif static=="PASS" and host=="PASS":
                coexistence_status="CURRENT_HOST_PASS"
            elif static=="PASS":
                coexistence_status="STATIC_AUDIT_PASS_CURRENT_HOST_PENDING"
            else:
                coexistence_status="STATIC_AUDIT_PENDING"
        entries.append({
            "component_id":cid,
            "record_path":path.relative_to(root).as_posix(),
            "record_status":row.get("status") or row.get("implementation_status"),
            "footprint_status":footprint_status,
            "footprint_path":footprint_path,
            "coexistence_status":coexistence_status,
        })

    all_fp=all(x["footprint_status"]=="MATERIALIZED" for x in entries)
    all_host=bool(entries) and all(x["coexistence_status"]=="CURRENT_HOST_PASS" for x in entries)
    static_pass=sum(x["coexistence_status"] in {"STATIC_AUDIT_PASS_CURRENT_HOST_PENDING","CURRENT_HOST_PASS"} for x in entries)
    static_pending=sum(x["coexistence_status"]=="STATIC_AUDIT_PENDING" for x in entries)
    static_fail=sum(x["coexistence_status"]=="STATIC_AUDIT_FAIL" for x in entries)
    return {
        "schema":"fa3.coexistence-inventory.v1",
        "capability_count":baseline.capability_count,
        "provider_count":len(entries),
        "entries":entries,
        "static_audit_summary":{"pass":static_pass,"pending":static_pending,"fail":static_fail},
        "closure":{
            "all_providers_inventoried":True,
            "all_footprints_materialized":all_fp,
            "all_current_host_proven":all_host,
        },
        "truth_boundary":{
            "inventory_presence_implies_coexistence_pass":False,
            "footprint_materialization_implies_current_host_pass":False,
            "current_host_pass_requires_physical_evidence":True,
        },
    }

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--report")
    ns=ap.parse_args()
    root=Path(ns.root)
    report=build(root)
    out=Path(ns.report) if ns.report else root/"reports/coexistence-inventory.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "provider_count":report["provider_count"],
        "footprints_materialized":sum(x["footprint_status"]=="MATERIALIZED" for x in report["entries"]),
        "pending_footprints":sum(x["footprint_status"]=="PENDING_FOOTPRINT" for x in report["entries"]),
        "static_audit_summary":report["static_audit_summary"],
        "all_current_host_proven":report["closure"]["all_current_host_proven"],
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
