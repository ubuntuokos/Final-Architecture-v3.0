#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, json, re
from pathlib import Path
from typing import Any
PROFILE="canonical/profiles/FA3-DISTRIBUTION-COMPLIANCE-001.json"
CONTRACT="canonical/contracts/FA3-DISTRIBUTION-COMPLIANCE-CONTRACTS-001.json"
REGISTRY="canonical/distribution-registry.json"
GATE_ID="FA3-GATE-DISTRIBUTION-COMPLIANCE-001"; GATESET_ID="FA3-DISTRIBUTION-COMPLIANCE-GATESET-001"
CLASSES=("FA3_NATIVE","EXTERNAL_REDISTRIBUTABLE","USER_LOCAL_EXTERNAL","REFERENCE_ONLY","BLOCKED")
SHA256=re.compile(r"^[0-9a-f]{64}$")
def loadj(path: Path) -> dict[str, Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError("top-level object required")
    return obj
def good_external_descriptor() -> dict[str, Any]:
    return {"artifact_id":"example.external.skill","origin":"EXTERNAL","source":{"repository":"example/project","commit":"1"*40},
      "hash_attestation":{"sha256":"a"*64},
      "license":{"snapshot_present":True,"spdx_expression":"MIT","source":"LICENSE","evidence_digest":"b"*64,
        "commercial_use":"ALLOW","redistribution":"ALLOW","modification":"ALLOW","source_distribution_required":False,
        "attribution_required":True,"notice_required":False,"patent_terms":"NONE_DECLARED","copyleft_scope":"NONE"},
      "distribution":{"class":"EXTERNAL_REDISTRIBUTABLE","product_bundle_allowed":True,
        "fa3_distribution_compatible":True,"decision_receipt":"dist:example:1"}}
def good_native_descriptor() -> dict[str, Any]:
    return {"artifact_id":"fa3.native.skill","origin":"FA3_NATIVE","hash_attestation":{"sha256":"c"*64},
      "distribution":{"class":"FA3_NATIVE","product_bundle_allowed":True,"fa3_distribution_compatible":True,
        "decision_receipt":"dist:native:1"}}
def classification_valid(d: dict[str, Any]) -> bool:
    dist=d.get("distribution",{}); cls=dist.get("class")
    if cls not in CLASSES or cls=="BLOCKED": return False
    if cls=="FA3_NATIVE":
        return d.get("origin")=="FA3_NATIVE" and bool(SHA256.fullmatch(str(d.get("hash_attestation",{}).get("sha256",""))))
    if cls in ("REFERENCE_ONLY","USER_LOCAL_EXTERNAL"): return dist.get("product_bundle_allowed") is False
    lic=d.get("license",{})
    required=("spdx_expression","source","evidence_digest","commercial_use","redistribution","modification",
      "source_distribution_required","attribution_required","notice_required","patent_terms","copyleft_scope")
    if any(k not in lic or lic[k] in (None,"","UNKNOWN") for k in required): return False
    return (lic.get("snapshot_present") is True and bool(SHA256.fullmatch(str(lic.get("evidence_digest",""))))
      and lic.get("commercial_use")=="ALLOW" and lic.get("redistribution")=="ALLOW"
      and dist.get("fa3_distribution_compatible") is True
      and bool(SHA256.fullmatch(str(d.get("hash_attestation",{}).get("sha256","")))))
def release_bundle_allowed(d: dict[str, Any]) -> bool:
    if not classification_valid(d): return False
    cls=d["distribution"]["class"]
    if cls=="FA3_NATIVE": return d["distribution"].get("product_bundle_allowed") is True
    if cls=="EXTERNAL_REDISTRIBUTABLE":
        return d["distribution"].get("product_bundle_allowed") is True and bool(d["distribution"].get("decision_receipt"))
    return False
def run_regressions() -> dict[str, Any]:
    e=good_external_descriptor(); n=good_native_descriptor()
    def mut(fn):
        x=copy.deepcopy(e); fn(x); return x
    checks=[release_bundle_allowed(e),release_bundle_allowed(n),
      not classification_valid(mut(lambda x:x["license"].update(commercial_use="DENY"))),
      not classification_valid(mut(lambda x:x["license"].update(redistribution="DENY"))),
      not classification_valid(mut(lambda x:x["license"].update(evidence_digest=""))),
      not classification_valid(mut(lambda x:x["license"].update(spdx_expression="UNKNOWN"))),
      not release_bundle_allowed(mut(lambda x:x["distribution"].update(decision_receipt=""))),
      not release_bundle_allowed({"artifact_id":"r","origin":"EXTERNAL","hash_attestation":{"sha256":"d"*64},
        "distribution":{"class":"REFERENCE_ONLY","product_bundle_allowed":False}}),
      not release_bundle_allowed({"artifact_id":"u","origin":"EXTERNAL","hash_attestation":{"sha256":"d"*64},
        "distribution":{"class":"USER_LOCAL_EXTERNAL","product_bundle_allowed":False}}),
      not classification_valid({"artifact_id":"b","origin":"EXTERNAL","distribution":{"class":"BLOCKED","product_bundle_allowed":False}})]
    cases=[{"case_id":f"DIST-{i:03d}","status":"PASS" if ok else "FAIL"} for i,ok in enumerate(checks,1)]
    return {"result":"PASS" if all(checks) else "FAIL","total":len(cases),"passed":sum(c["status"]=="PASS" for c in cases),"cases":cases}
def canonical_check(root: Path) -> list[str]:
    findings=[]; p=loadj(root/PROFILE); ct=loadj(root/CONTRACT); r=loadj(root/REGISTRY)
    if not (p.get("id")=="FA3-DISTRIBUTION-COMPLIANCE-001" and p.get("status")=="CANONICAL"
      and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==143):
        findings.append("distribution profile governance drift")
    if ct.get("distribution_classes")!=list(CLASSES): findings.append("distribution class contract drift")
    if r.get("id")!="FA3-DISTRIBUTION-REGISTRY-001": findings.append("distribution registry identity drift")
    for rec in r.get("records",[]):
        if rec.get("class") not in CLASSES: findings.append(f"invalid distribution class: {rec.get('subject_id')}")
        if rec.get("class") in ("REFERENCE_ONLY","USER_LOCAL_EXTERNAL","BLOCKED") and rec.get("release_bundle_status")!="EXCLUDED":
            findings.append(f"non-redistributable record included: {rec.get('subject_id')}")
    return findings
def gate(root: Path) -> dict[str, Any]:
    root=Path(root).resolve(); findings=canonical_check(root); regressions=run_regressions()
    result="PASS" if not findings and regressions["result"]=="PASS" else "FAIL"
    report={"schema":"fa3.distribution-compliance-gate-report.v1","gate_id":GATE_ID,"gateset_id":GATESET_ID,
      "result":result,"findings":findings,"regressions":regressions,"capability_count":143,"new_architectural_authority":False}
    out=root/"reports/distribution-compliance-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return report
def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args()
    report=gate(Path(a.root)); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
