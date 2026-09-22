#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from typing import Any,Callable
PROVIDER_ID="FA3-PROVIDER-CONDB-001"
UPSTREAM_COMMIT="62da030426b3eee96a77b464e7007cdf8530c42e"
class ConDBProvider:
    def __init__(self,cache_root:Path,db_factory:Callable[[str],Any]|None=None):
        self.cache_root=cache_root.resolve(); self.db_factory=db_factory
        if not self.cache_root.is_absolute(): raise ValueError("absolute cache_root required")
    def _db_path(self,cache_id:str)->Path:
        safe="".join(ch for ch in cache_id if ch.isalnum() or ch in "-_")[:80] or "default"; p=(self.cache_root/(safe+".sqlite")).resolve()
        if self.cache_root not in p.parents: raise ValueError("cache path escape")
        self.cache_root.mkdir(parents=True,exist_ok=True); return p
    def ingest_tree(self,arguments:dict[str,Any])->dict[str,Any]:
        tree=arguments.get("tree"); cache_id=str(arguments.get("cache_id","default"))
        if not isinstance(tree,dict): raise ValueError("tree must be object")
        path=self._db_path(cache_id); factory=self.db_factory
        if factory is None:
            import contextdb
            factory=contextdb.open
        db=factory(str(path))
        try: tree_id=db.store(tree,format="document")
        finally:
            close=getattr(db,"close",None)
            if close: close()
        return {"provider_id":PROVIDER_ID,"cache_id":cache_id,"tree_id":tree_id,"cache_path":str(path),"derived":True,"rebuildable":True,"durable_authority":False,"global_promotion_claim":False}
    def projection_receipt(self,cache_id:str,tree_id:str,source_refs:list[str])->dict[str,Any]:
        return {"schema":"fa3.condb-cache-receipt.v1","provider_id":PROVIDER_ID,"cache_id":cache_id,"tree_id":tree_id,"source_refs":list(source_refs),"derived":True,"rebuildable":True,"authority":"NONE","global_promotion_claim":False}
