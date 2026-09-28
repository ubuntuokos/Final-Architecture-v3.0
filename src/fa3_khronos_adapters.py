#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess
from pathlib import Path
from typing import Any

REGISTRY = Path("canonical/FA3-KHRONOS-ADAPTER-REGISTRY-001.json")

def sdk_root() -> Path:
    base=os.environ.get("XDG_DATA_HOME")
    return Path(base).expanduser()/"fa3/khronos-sdk" if base else Path.home()/".local/share/fa3/khronos-sdk"

def load_registry(root: Path) -> dict[str,Any]:
    return json.loads((root/REGISTRY).read_text(encoding="utf-8"))

def source_state(root: Path) -> list[dict[str,Any]]:
    out=[]
    src=sdk_root()/"src"
    for row in load_registry(root).get("adapters",[]):
        name=str(row["project"]); p=src/name
        commit=None
        if (p/".git").is_dir():
            try:
                commit=subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],text=True,stderr=subprocess.DEVNULL).strip()
            except Exception:
                commit=None
        out.append({"adapter_id":row["id"],"project":name,"target":row["target"],"source_present":(p/".git").is_dir(),"commit":commit,"authority":False})
    return out

def projection(root: Path) -> dict[str,Any]:
    return {
      "schema":"fa3.khronos-adapter-projection.v1",
      "registry_id":"FA3-KHRONOS-ADAPTER-REGISTRY-001",
      "sdk_root":str(sdk_root()),
      "adapters":source_state(root),
      "host_resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
      "global_environment_mutation":False,
      "runtime_promotion_claim":False,
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ns=ap.parse_args()
    print(json.dumps(projection(Path(ns.root).resolve()),indent=2,sort_keys=True))
