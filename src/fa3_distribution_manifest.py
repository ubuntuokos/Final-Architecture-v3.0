#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

def build_manifest(records:list[dict[str,Any]])->dict[str,Any]:
    included=[];excluded=[];notices=[]
    for r in records:
        row={"subject_id":r["subject_id"],"class":r["class"],"release_bundle_status":r["release_bundle_status"]}
        (included if r["release_bundle_status"]=="INCLUDED" else excluded).append(row)
        if r["release_bundle_status"]=="INCLUDED" and r.get("notice"):
            notices.append({"subject_id":r["subject_id"],"notice":r["notice"]})
    return {"schema":"fa3.distribution-manifest.v1","included":included,"excluded":excluded,
      "third_party_notices":notices,"included_external_count":sum(x["class"]=="EXTERNAL_REDISTRIBUTABLE" for x in included)}

def canonical_manifest(registry:dict[str,Any])->dict[str,Any]:
    body=build_manifest(registry.get("records",[]))
    return {"schema":body["schema"],"id":"FA3-DISTRIBUTION-MANIFEST-001","status":"CANONICAL",
      "registry_id":registry.get("id"),"included":body["included"],"excluded":body["excluded"],
      "third_party_notices":body["third_party_notices"],"included_external_count":body["included_external_count"],
      "generation_semantics":"DERIVED_FROM_CANONICAL_DISTRIBUTION_REGISTRY",
      "release_bundle_inclusion_requires_receipt":True}

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry",default="canonical/distribution-registry.json")
    ap.add_argument("--output",default="canonical/distribution-manifest.json")
    ap.add_argument("--check",action="store_true")
    a=ap.parse_args()
    registry=json.loads(Path(a.registry).read_text(encoding="utf-8"))
    expected=canonical_manifest(registry)
    out=Path(a.output)
    if a.check:
        actual=json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None
        ok=actual==expected
        print(json.dumps({"result":"PASS" if ok else "FAIL","output":str(out)},indent=2))
        return 0 if ok else 2
    out.write_text(json.dumps(expected,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"result":"PASS","output":str(out)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
