#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
from typing import Any
CLASSES={"FA3_NATIVE","EXTERNAL_REDISTRIBUTABLE","USER_LOCAL_EXTERNAL","REFERENCE_ONLY","BLOCKED"}
SCOPES=("canonical/providers","canonical/references","canonical/third-party")
def load(path:Path)->dict[str,Any]:
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise ValueError(f"object required: {path}")
    return x
def distribution_of(row:dict[str,Any])->dict[str,Any]:
    d=row.get("distribution")
    if isinstance(d,dict):return d
    cls=row.get("distribution_class")
    return {"class":cls,"release_bundle_status":"INCLUDED" if row.get("product_bundle_allowed") is True else "EXCLUDED"}
def canonical_registration(row:dict[str,Any],registry:dict[str,Any])->list[str]:
    d=distribution_of(row);sid=row.get("id") or row.get("subject_id")
    if not sid:return ["canonical external record id missing"]
    matches=[r for r in registry.get("records",[]) if r.get("subject_id")==sid]
    if len(matches)!=1:return [f"distribution registry requires exactly one matching record for {sid}"]
    reg=matches[0];errors=[]
    if reg.get("class")!=d.get("class"):errors.append(f"distribution registry class mismatch for {sid}")
    status=d.get("release_bundle_status")
    if status not in ("INCLUDED","EXCLUDED"):
        status="INCLUDED" if (d.get("product_bundle_allowed") is True or row.get("product_bundle_allowed") is True) else "EXCLUDED"
    if reg.get("release_bundle_status")!=status:errors.append(f"distribution registry bundle-status mismatch for {sid}")
    return errors
def validate_record(row:dict[str,Any])->list[str]:
    d=distribution_of(row);cls=d.get("class");errors=[]
    if cls not in CLASSES:return ["distribution class missing or invalid"]
    included=d.get("release_bundle_status")=="INCLUDED" or d.get("product_bundle_allowed") is True
    if cls in {"REFERENCE_ONLY","USER_LOCAL_EXTERNAL","BLOCKED"} and included:errors.append(f"{cls} may not enter product bundle")
    if cls=="EXTERNAL_REDISTRIBUTABLE":
        if not (d.get("compatibility_attestation_ref") or d.get("classification_basis")):
            errors.append("EXTERNAL_REDISTRIBUTABLE requires compatibility attestation reference or classification basis")
        if included and not (d.get("distribution_decision_receipt") or d.get("inclusion_requires_distribution_decision_receipt")):
            errors.append("included EXTERNAL_REDISTRIBUTABLE requires distribution decision receipt")
    return errors
def added_json(root:Path,base_ref:str)->list[str]:
    p=subprocess.run(["git","diff","--name-status",base_ref,"HEAD","--",*SCOPES],cwd=root,text=True,capture_output=True,check=False)
    if p.returncode!=0:raise RuntimeError(p.stderr.strip() or "git diff failed")
    out=[]
    for line in p.stdout.splitlines():
        parts=line.split("\t")
        if len(parts)==2 and parts[0]=="A" and parts[1].endswith(".json"):out.append(parts[1])
    return out
def gate(root:Path,base_ref:str)->dict[str,Any]:
    root=Path(root).resolve();findings=[];registry=load(root/"canonical/distribution-registry.json")
    for rel in added_json(root,base_ref):
        try:
            row=load(root/rel);errors=validate_record(row)
            if not errors:errors.extend(canonical_registration(row,registry))
        except Exception as exc:errors=[str(exc)]
        if errors:findings.append({"code":"DIST-ADOPTION-001","path":rel,"errors":errors})
    return {"schema":"fa3.distribution-adoption-gate-report.v1","gate_id":"FA3-DISTRIBUTION-ADOPTION-GATE-001",
      "result":"PASS" if not findings else "FAIL","base_ref":base_ref,"findings":findings,"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--base-ref",required=True)
    ap.add_argument("--report",default="reports/distribution-adoption-gate-report.json");a=ap.parse_args()
    report=gate(Path(a.root),a.base_ref);out=Path(a.root)/a.report;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
