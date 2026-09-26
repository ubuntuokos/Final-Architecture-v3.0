#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from fa3_release_baseline import load_active_release_baseline


def derive(root: Path) -> dict:
    root=root.resolve()
    provider_dir=root/"canonical/providers"
    records=[]
    invalid=[]
    for p in sorted(provider_dir.glob("*.json")):
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            invalid.append({"path":str(p.relative_to(root)),"reason":f"PARSE_ERROR:{exc}"})
            continue
        pid=obj.get("id")
        if not isinstance(pid,str) or not pid.startswith("FA3-PROVIDER-"):
            invalid.append({"path":str(p.relative_to(root)),"reason":"INVALID_PROVIDER_ID"})
            continue
        records.append({"id":pid,"path":str(p.relative_to(root)),"status":obj.get("status") or obj.get("implementation_status")})
    return {
        "schema":"fa3.provider-count-report.v1",
        "policy_id":"FA3-PROVIDER-COUNT-POLICY-001",
        "capability_count":load_active_release_baseline(root).capability_count,
        "capability_count_fixed":True,
        "provider_count_fixed":False,
        "provider_count":len(records),
        "provider_ids":[r["id"] for r in records],
        "invalid_record_count":len(invalid),
        "invalid_records":invalid,
        "records":records
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--report")
    ns=ap.parse_args()
    root=Path(ns.root)
    report=derive(root)
    out=Path(ns.report) if ns.report else root/"reports/provider-count-report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["invalid_record_count"]==0 else 2

if __name__=="__main__":
    raise SystemExit(main())
