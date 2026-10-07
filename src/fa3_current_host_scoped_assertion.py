#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from typing import Any

def load(path:Path)->dict[str,Any]:
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise AssertionError(f"JSON object required: {path}")
    return x

def assert_scoped_requalification(root:Path,subjects:list[str])->dict[str,Any]:
    root=root.resolve(); expected=sorted(set(subjects))
    if not expected or len(expected)!=len(subjects): raise AssertionError("non-empty unique scoped subjects required")
    obligations=len(expected)*3
    p=load(root/"reports/current-host-capability-qualification-constituent-orchestrator.json")
    e=load(root/"reports/current-host-capability-test-orchestrator.json")
    b=load(root/"reports/current-host-capability-test-bundle-assembler.json")
    a=load(root/"reports/current-host-capability-attestation-producer.json")
    h=load(root/"reports/current-host-capability-handoff.json")
    assert p["orchestrator_integrity"]=="PASS" and sorted(p["requested_subjects"])==expected
    assert p["selected_producer_count"]==obligations and p["constituents_materialized"]==obligations
    assert e["orchestrator_integrity"]=="PASS" and sorted(e["requested_subjects"])==expected
    assert e["selected_executor_count"]==obligations and e["results_materialized"]==obligations
    assert b["assembler_integrity"]=="PASS" and b["bundles_materialized"]==len(expected)
    assert sorted(b["materialized_capability_ids"])==expected
    assert a["producer_integrity"]=="PASS" and a["attestations_materialized"]==len(expected)
    assert sorted(a["materialized_capability_ids"])==expected
    assert h["handoff_integrity"]=="PASS" and h["receipts_materialized"]==len(expected)
    assert sorted(h["materialized_capability_ids"])==expected
    for row in (p,e,b,a,h): assert row["global_promotion_claim"] is False
    result={"schema":"fa3.current-host-scoped-requalification-report.v1","result":"PASS","mode":"SCOPED",
            "affected_capability_ids":expected,"affected_capability_count":len(expected),
            "obligation_count":obligations,"positive_negative_rollback_per_capability":True,
            "historical_base_evidence_relabelled":False,"global_promotion_claim":False,
            "receipts_materialized":h["receipts_materialized"]}
    out=root/"reports/current-host-scoped-requalification.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--subjects",default=os.getenv("FA3_CURRENT_HOST_SUBJECTS","")); args=ap.parse_args()
    subjects=[x for x in args.subjects.split(",") if x]
    print(json.dumps(assert_scoped_requalification(Path(args.root),subjects),ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
