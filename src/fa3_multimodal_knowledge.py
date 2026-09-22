#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from typing import Any
FORBIDDEN={"binary","bytes","base64","raw_payload","inline_media"}
def _sha(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def normalize_projection(request:dict[str,Any])->dict[str,Any]:
    if any(k in request for k in FORBIDDEN):
        raise ValueError("binary media is forbidden in knowledge projection")
    artifact_ref=str(request.get("artifact_ref","")).strip()
    artifact_sha=str(request.get("artifact_sha256","")).strip().lower()
    media_type=str(request.get("media_type","")).lower()
    desc=request.get("derived_descriptors",[])
    if not artifact_ref or len(artifact_sha)!=64 or media_type not in {"image","video","audio"} or not isinstance(desc,list):
        raise ValueError("invalid multimodal projection request")
    derived=[]; edges=[]
    for i,row in enumerate(desc):
        if not isinstance(row,dict) or any(k in row for k in FORBIDDEN):
            raise ValueError("descriptor must be metadata-only object")
        locator=str(row.get("locator","")).strip()
        if not locator: raise ValueError("descriptor locator required")
        ref=f"FA3-MM-{media_type.upper()}-{_sha([artifact_ref,i,row])[:20].upper()}"
        item={"derived_ref":ref,"artifact_ref":artifact_ref,"artifact_sha256":artifact_sha,"media_type":media_type,"locator":locator}
        if media_type in {"video","audio"}:
            start=row.get("start_ms"); end=row.get("end_ms")
            if not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or end < start:
                raise ValueError("temporal media requires valid start_ms/end_ms")
            item["temporal_span"]={"start_ms":start,"end_ms":end}
        if "text" in row: item["derived_text"]=str(row["text"])
        if "bbox" in row: item["bbox"]=row["bbox"]
        derived.append(item)
        edges.append({"source_ref":artifact_ref,"source_sha256":artifact_sha,"locator":locator,"derived_ref":ref,"derivation":"MULTIMODAL_KNOWLEDGE_PROJECTION"})
    material={"artifact_ref":artifact_ref,"artifact_sha256":artifact_sha,"derived":derived}
    return {"schema":"fa3.multimodal-projection-receipt.v1","receipt_id":"FA3-MMREC-"+_sha(material)[:24].upper(),"artifact_ref":artifact_ref,"artifact_sha256":artifact_sha,"derived_refs":[x["derived_ref"] for x in derived],"provenance_edges":edges,"projections":derived,"status":"PASS","binary_payload_stored":False,"rebuildable":True}
