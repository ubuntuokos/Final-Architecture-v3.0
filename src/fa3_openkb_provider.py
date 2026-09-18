#!/usr/bin/env python3
from __future__ import annotations
import hashlib,subprocess
from pathlib import Path
from typing import Any,Callable
PROVIDER_ID="FA3-PROVIDER-OPENKB-001"
UPSTREAM_COMMIT="ff54396e575ee6feb0113b631a34caa082b441cc"
class OpenKBProvider:
    def __init__(self,allowed_roots:tuple[Path,...],derived_root:Path,runner:Callable[...,Any]|None=None):
        self.allowed_roots=tuple(p.resolve() for p in allowed_roots); self.derived_root=derived_root.resolve(); self.runner=runner
        if not self.allowed_roots or not self.derived_root.is_absolute(): raise ValueError("absolute roots required")
    def _source(self,value:Any)->Path:
        p=Path(str(value)).expanduser().resolve()
        if not p.is_file() or not any(p==r or r in p.parents for r in self.allowed_roots): raise ValueError("source outside admitted local roots")
        return p
    def compile(self,arguments:dict[str,Any])->dict[str,Any]:
        source=self._source(arguments.get("source")); workspace=(self.derived_root/str(arguments.get("workspace_id","default"))).resolve()
        if self.derived_root not in workspace.parents and workspace!=self.derived_root: raise ValueError("derived workspace escape")
        workspace.mkdir(parents=True,exist_ok=True); digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if self.runner is not None: result=self.runner(source=source,workspace=workspace)
        else:
            proc=subprocess.run(["openkb","add",str(source)],cwd=workspace,text=True,capture_output=True,timeout=900,shell=False)
            if proc.returncode!=0: raise RuntimeError("OpenKB compilation failed")
            result={"stdout_tail":proc.stdout[-2000:]}
        return {"provider_id":PROVIDER_ID,"source_ref":str(source),"source_sha256":digest,"derived_root":str(workspace),"result":result,"source_authority":False,"derived":True,"rebuildable":True,"global_promotion_claim":False}
