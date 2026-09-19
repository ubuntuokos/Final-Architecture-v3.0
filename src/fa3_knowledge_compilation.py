#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from typing import Any

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def provenance_edge(source_ref:str,source_sha256:str,locator:str,derivation:str,derived_ref:str)->dict[str,Any]:
    if not all(isinstance(x,str) and x.strip() for x in (source_ref,source_sha256,locator,derivation,derived_ref)):
        raise ValueError("complete provenance edge required")
    if len(source_sha256)!=64 or any(c not in "0123456789abcdefABCDEF" for c in source_sha256):
        raise ValueError("source_sha256 must be hex sha256")
    material={"source_ref":source_ref,"source_sha256":source_sha256.lower(),"locator":locator,"derivation":derivation,"derived_ref":derived_ref}
    return {"edge_id":"FA3-PROV-"+_sha(material)[:24].upper(),**material}

def compile_projection(source:dict[str,Any],payload:dict[str,Any],provider_id:str)->dict[str,Any]:
    source_ref=str(source.get("source_ref","")).strip()
    source_sha=str(source.get("source_sha256","")).strip().lower()
    locator=str(source.get("locator","")).strip()
    if not source_ref or not locator or len(source_sha)!=64:
        raise ValueError("source_ref/source_sha256/locator required")
    if provider_id not in {"FA3-PROVIDER-OPENKB-001","FA3-NATIVE-KNOWLEDGE-COMPILER"}:
        raise ValueError("unadmitted compiler provider")
    kinds=("claims","entities","relations","concepts","temporal_assertions","contradictions")
    normalized={k:list(payload.get(k,[])) if isinstance(payload.get(k,[]),list) else [] for k in kinds}
    derived_refs=[]; edges=[]
    for kind in kinds:
        for idx,item in enumerate(normalized[kind]):
            if not isinstance(item,dict):
                raise ValueError(f"{kind} items must be objects")
            ref=f"FA3-KNOW-{kind.upper()}-{_sha([source_ref,kind,idx,item])[:20].upper()}"
            item["derived_ref"]=ref
            item["source_refs"]=[source_ref]
            edge=provenance_edge(source_ref,source_sha,locator,f"KNOWLEDGE_COMPILATION:{kind}",ref)
            item["provenance_edges"]=[edge["edge_id"]]
            derived_refs.append(ref); edges.append(edge)
    material={"source_ref":source_ref,"source_sha256":source_sha,"provider_id":provider_id,"derived_refs":derived_refs}
    return {"schema":"fa3.knowledge-compilation-receipt.v1","receipt_id":"FA3-KCOMP-"+_sha(material)[:24].upper(),"provider_id":provider_id,"source_refs":[source_ref],"source_hashes":[source_sha],"derived_refs":derived_refs,"provenance_edges":edges,"projections":normalized,"status":"PASS","derived":True,"rebuildable":True,"source_authority_unchanged":True}

def derive_from_journal_event(event:dict[str,Any],artifact:dict[str,Any])->dict[str,Any]:
    event_id=str(event.get("id") or event.get("event_id") or "").strip()
    artifact_ref=str(artifact.get("artifact_ref","")).strip()
    artifact_sha=str(artifact.get("artifact_sha256","")).strip().lower()
    locator=str(artifact.get("locator","")).strip()
    if not event_id or not artifact_ref or len(artifact_sha)!=64 or not locator:
        raise ValueError("journal event and authoritative artifact binding required")
    return {"schema":"fa3.knowledge-derivation-request.v1","journal_event_ref":event_id,"source_ref":artifact_ref,"source_sha256":artifact_sha,"locator":locator,"source_authority":"FA3-JOURNAL-001_AND_ORIGINAL_ARTIFACTS","derived_only":True,"writeback_to_source":"DENY"}
