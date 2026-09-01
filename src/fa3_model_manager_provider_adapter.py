#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, shutil
from pathlib import Path
from typing import Any

RUNTIME_ID="FA3-MODEL-MANAGER-RUNTIME-CONFORMANCE-001"
GATE_ID="FA3-GATE-MODEL-MANAGER-CURRENT-HOST-001"
HF_PROVIDER_ID="FA3-PROVIDER-HF-MODEL-STORE-001"
LM_STUDIO_PROVIDER_ID="FA3-PROVIDER-LM-STUDIO-MODEL-001"
OLLAMA_PROVIDER_ID="FA3-PROVIDER-OLLAMA-MODEL-001"
PROVIDER_IDS=[HF_PROVIDER_ID,LM_STUDIO_PROVIDER_ID,OLLAMA_PROVIDER_ID]
EVIDENCE_LEVEL="CURRENT_HOST_MODEL_PROVIDER_E2E_PASS"
_SECRET_MARKERS=("TOKEN","SECRET","PASSWORD","PASSWD","API_KEY","PRIVATE_KEY","ACCESS_KEY")
_PROXY_KEYS={"HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"}

def sha256_bytes(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda:fh.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def safe_child_env(base:dict[str,str]|None=None)->dict[str,str]:
    source=dict(os.environ if base is None else base)
    keep={"PATH","HOME","USER","LOGNAME","SHELL","LANG","LC_ALL","LC_CTYPE","XDG_RUNTIME_DIR","XDG_CONFIG_HOME","XDG_CACHE_HOME","XDG_DATA_HOME","DISPLAY","WAYLAND_DISPLAY","DBUS_SESSION_BUS_ADDRESS","LMSTUDIO_HOME","OLLAMA_MODELS"}
    out={}
    for key,value in source.items():
        if not value: continue
        upper=key.upper()
        if key in _PROXY_KEYS or any(marker in upper for marker in _SECRET_MARKERS): continue
        if key in keep or key.startswith("LMS_"): out[key]=value
    return out

def find_binary(name:str,extra:list[Path]|None=None)->Path|None:
    hit=shutil.which(name); candidates=[]
    if hit: candidates.append(Path(hit))
    home=Path.home()
    defaults={"lms":[home/".lmstudio/bin/lms",home/".local/bin/lms",Path("/usr/local/bin/lms"),Path("/usr/bin/lms")],"ollama":[home/".local/bin/ollama",Path("/usr/local/bin/ollama"),Path("/usr/bin/ollama")]}
    candidates.extend(defaults.get(name,[]))
    if extra: candidates.extend(extra)
    seen=set()
    for path in candidates:
        try: resolved=path.expanduser().resolve()
        except Exception: continue
        if str(resolved) in seen: continue
        seen.add(str(resolved))
        if resolved.is_file() and os.access(resolved,os.X_OK): return resolved
    return None

def valid_revision(value:Any)->bool:
    return isinstance(value,str) and re.fullmatch(r"[0-9a-f]{40,64}",value) is not None

def select_lmstudio_model(rows:Any)->dict[str,Any]:
    if not isinstance(rows,list): raise ValueError("lms ls --json did not return a list")
    candidates=[]
    for row in rows:
        if not isinstance(row,dict): continue
        key=row.get("modelKey")
        if not isinstance(key,str) or not key or row.get("type") not in {None,"llm"}: continue
        try: size=int(row.get("sizeBytes") or 0)
        except Exception: size=0
        candidates.append((0 if size>0 else 1,size if size>0 else 2**63,key,row))
    if not candidates: raise ValueError("no local LM Studio LLM model found")
    candidates.sort(key=lambda x:(x[0],x[1],x[2]))
    return candidates[0][3]

def select_ollama_models(tags:Any,limit:int=5)->list[dict[str,Any]]:
    rows=tags.get("models",[]) if isinstance(tags,dict) else []
    candidates=[]
    for row in rows:
        if not isinstance(row,dict): continue
        name=row.get("name") or row.get("model"); digest=row.get("digest")
        if not isinstance(name,str) or not name: continue
        if not isinstance(digest,str) or re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}",digest) is None: continue
        try: size=int(row.get("size") or 0)
        except Exception: size=0
        candidates.append((0 if size>0 else 1,size if size>0 else 2**63,name,row))
    candidates.sort(key=lambda x:(x[0],x[1],x[2]))
    return [x[3] for x in candidates[:limit]]

def regression_check()->dict[str,Any]:
    cases={}
    cases["immutable_revision_accept"]=valid_revision("a"*40)
    cases["floating_revision_reject"]=not valid_revision("latest")
    cases["lm_smallest_selection"]=select_lmstudio_model([{"modelKey":"large","type":"llm","sizeBytes":20},{"modelKey":"small","type":"llm","sizeBytes":10}])["modelKey"]=="small"
    cases["ollama_digest_selection"]=select_ollama_models({"models":[{"name":"bad","digest":"latest","size":1},{"name":"ok","digest":"b"*64,"size":2}]})[0]["name"]=="ok"
    env=safe_child_env({"PATH":"/usr/bin","HOME":"/tmp","HF_TOKEN":"secret","OPENAI_API_KEY":"secret","HTTPS_PROXY":"http://proxy","XDG_RUNTIME_DIR":"/run/user/1000","OLLAMA_MODELS":"/models"})
    cases["secret_proxy_env_removed"]="HF_TOKEN" not in env and "OPENAI_API_KEY" not in env and "HTTPS_PROXY" not in env
    cases["runtime_paths_preserved"]=env.get("XDG_RUNTIME_DIR")=="/run/user/1000" and env.get("OLLAMA_MODELS")=="/models"
    return {"schema":"fa3.model-manager-provider-adapter-regression.v1","result":"PASS" if all(cases.values()) else "FAIL","passed":sum(cases.values()),"total":len(cases),"cases":cases}

if __name__=="__main__": print(json.dumps(regression_check(),indent=2))
