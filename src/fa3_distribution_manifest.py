#!/usr/bin/env python3
from __future__ import annotations
from typing import Any
def build_manifest(records:list[dict[str,Any]])->dict[str,Any]:
    included=[];excluded=[];notices=[]
    for r in records:
        row={"subject_id":r["subject_id"],"class":r["class"],"release_bundle_status":r["release_bundle_status"]}
        (included if r["release_bundle_status"]=="INCLUDED" else excluded).append(row)
        if r["release_bundle_status"]=="INCLUDED" and r.get("notice"):notices.append({"subject_id":r["subject_id"],"notice":r["notice"]})
    return {"schema":"fa3.distribution-manifest.v1","included":included,"excluded":excluded,"third_party_notices":notices,"included_external_count":sum(x["class"]=="EXTERNAL_REDISTRIBUTABLE" for x in included)}
