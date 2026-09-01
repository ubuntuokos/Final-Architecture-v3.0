#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,platform,socket,subprocess,sys,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_model_manager_provider_adapter import (
    EVIDENCE_LEVEL,HF_PROVIDER_ID,LM_STUDIO_PROVIDER_ID,OLLAMA_PROVIDER_ID,
    RUNTIME_ID,find_binary,regression_check,safe_child_env,select_lmstudio_model,
    select_ollama_models,sha256_bytes,sha256_file,valid_revision,
)

MAX_HASH_FILE_BYTES=16*1024*1024
LM_IDENTIFIER="fa3-model-manager-e2e"

def utc_now()->str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def writej(path:Path,obj:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def run(argv:list[str],timeout:int=120,env:dict[str,str]|None=None)->subprocess.CompletedProcess[str]:
    return subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False,env=env)

def run_json_to_file(argv:list[str],output:Path,timeout:int,env:dict[str,str])->Any:
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",encoding="utf-8") as fh:
        p=subprocess.run(argv,text=True,stdout=fh,stderr=subprocess.PIPE,timeout=timeout,check=False,env=env)
    if p.returncode!=0:
        raise RuntimeError(f"{' '.join(argv[:3])} failed rc={p.returncode}: {p.stderr[-2000:]}")
    try:
        return json.loads(output.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"invalid JSON from {' '.join(argv[:3])}") from exc

def host_fingerprint()->dict[str,Any]:
    u=platform.uname()
    return {
        "system":u.system,"release":u.release,"machine":u.machine,
        "python":platform.python_version(),"cpu_count":os.cpu_count(),
        "hostname_sha256":sha256_bytes(u.node.encode("utf-8")),
    }

def no_proxy_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))

def http_json(url:str,payload:dict[str,Any]|None=None,timeout:int=120)->Any:
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(
        url,data=data,method="GET" if payload is None else "POST",
        headers={"Content-Type":"application/json","User-Agent":"FA3-Model-Manager-E2E/1"},
    )
    with no_proxy_opener().open(req,timeout=timeout) as resp:
        body=resp.read(8*1024*1024)
    return json.loads(body.decode("utf-8"))

def free_port()->int:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1",0))
        return int(s.getsockname()[1])

def hf_cache_candidates()->list[Path]:
    out:list[Path]=[]
    if os.environ.get("HF_HUB_CACHE"): out.append(Path(os.environ["HF_HUB_CACHE"]))
    if os.environ.get("HF_HOME"): out.append(Path(os.environ["HF_HOME"])/"hub")
    out += [
        Path("/ai-cache/huggingface/hub"),Path("/ai-cache/huggingface"),
        Path("/ai-cache/hf/hub"),Path("/ai-cache/hf"),Path("/ai-cache/hub"),
        Path.home()/".cache/huggingface/hub",
    ]
    unique=[]; seen=set()
    for path in out:
        try: p=path.expanduser().resolve()
        except Exception: continue
        if p.name!="hub" and (p/"hub").is_dir(): p=(p/"hub").resolve()
        if str(p) not in seen:
            seen.add(str(p)); unique.append(p)
    return unique

def choose_snapshot_file(snapshot:Path)->Path|None:
    for name in ("config.json","tokenizer_config.json","generation_config.json","README.md"):
        path=snapshot/name
        try:
            target=path.resolve()
            if path.exists() and target.is_file() and 0<target.stat().st_size<=MAX_HASH_FILE_BYTES:
                return path
        except OSError: pass
    try: children=sorted(snapshot.iterdir(),key=lambda p:p.name)
    except OSError: return None
    for path in children:
        try:
            target=path.resolve()
            if target.is_file() and 0<target.stat().st_size<=MAX_HASH_FILE_BYTES:
                return path
        except OSError: pass
    return None

def collect_hf()->dict[str,Any]:
    snapshots=[]
    for root in hf_cache_candidates():
        if not root.is_dir(): continue
        for model_dir in sorted(root.glob("models--*")):
            snap_root=model_dir/"snapshots"
            if not snap_root.is_dir(): continue
            encoded=model_dir.name[len("models--"):]
            parts=encoded.split("--",1)
            repo_id="/".join(parts) if len(parts)==2 else encoded.replace("--","/")
            for snap in sorted(snap_root.iterdir(),key=lambda p:p.name):
                if not snap.is_dir() or not valid_revision(snap.name): continue
                selected=choose_snapshot_file(snap)
                if selected is not None: snapshots.append((repo_id,snap.name,root,selected))
    if not snapshots:
        raise RuntimeError("no immutable Hugging Face model snapshot with hashable cached file found")
    snapshots.sort(key=lambda x:(x[0],x[1],x[3].name))
    repo_id,revision,root,selected=snapshots[0]
    target=selected.resolve()
    try:
        import huggingface_hub  # type: ignore
        hub_version=getattr(huggingface_hub,"__version__",None)
        hub_file=getattr(huggingface_hub,"__file__",None)
        hub_module_sha256=sha256_file(Path(hub_file).resolve()) if hub_file else None
    except Exception:
        hub_version=None; hub_module_sha256=None
    return {
        "provider_id":HF_PROVIDER_ID,"status":"PASS",
        "evidence_level":"CURRENT_HOST_SOURCE_CACHE_E2E_PASS",
        "repo_id":repo_id,"immutable_revision":revision,
        "cache_entry_relative_path":selected.relative_to(root).as_posix(),
        "cache_root_fingerprint":sha256_bytes(str(root).encode("utf-8")),
        "cache_root_class":"PERSISTENT_AI_CACHE" if str(root).startswith("/ai-cache") else "USER_CACHE",
        "cached_file_size":target.stat().st_size,"cached_file_sha256":sha256_file(target),
        "snapshot_entry_is_symlink":selected.is_symlink(),
        "huggingface_hub_version":hub_version,
        "huggingface_hub_module_sha256":hub_module_sha256,
        "network_fetch_performed":False,"floating_revision_used":False,
    }

def collect_lmstudio(runtime_dir:Path)->dict[str,Any]:
    lms=find_binary("lms")
    if lms is None: raise RuntimeError("LM Studio lms CLI not found")
    env=safe_child_env()
    version=run([str(lms),"--version"],30,env)
    if version.returncode!=0: raise RuntimeError("lms --version failed")
    rows=run_json_to_file([str(lms),"ls","--llm","--json"],runtime_dir/"lmstudio-models.json",180,env)
    model=select_lmstudio_model(rows)
    model_key=str(model["modelKey"]); model_size=int(model.get("sizeBytes") or 0)
    estimate=run([str(lms),"load",model_key,"--gpu","off","--context-length","512","--parallel","1","--local","--estimate-only","-y"],180,env)
    if estimate.returncode!=0:
        raise RuntimeError("LM Studio CPU resource estimate failed: "+estimate.stderr[-1500:])
    loaded=False
    try:
        load=run([str(lms),"load",model_key,"--gpu","off","--context-length","512","--parallel","1","--identifier",LM_IDENTIFIER,"--ttl","120","--local","-y"],600,env)
        if load.returncode!=0:
            raise RuntimeError("LM Studio CPU-only model load failed: "+(load.stderr or load.stdout)[-2000:])
        loaded=True
        ps=run_json_to_file([str(lms),"ps","--json"],runtime_dir/"lmstudio-ps.json",120,env)
        matches=[x for x in ps if isinstance(x,dict) and x.get("identifier")==LM_IDENTIFIER] if isinstance(ps,list) else []
        if len(matches)!=1: raise RuntimeError("LM Studio loaded-instance identity not found")
        chat=run([str(lms),"chat",LM_IDENTIFIER,"-p","Reply with the short token FA3_LM_STUDIO_E2E_PASS.","--ttl","30"],600,env)
        if chat.returncode!=0 or not chat.stdout.strip():
            raise RuntimeError("LM Studio one-shot inference failed")
        return {
            "provider_id":LM_STUDIO_PROVIDER_ID,"status":"PASS",
            "evidence_level":"CURRENT_HOST_RUNTIME_E2E_PASS",
            "lms_version":(version.stdout or version.stderr).strip(),
            "lms_binary_sha256":sha256_file(lms),
            "catalog_count":len(rows) if isinstance(rows,list) else None,
            "selected_model_key":model_key,"selected_model_size_bytes":model_size,
            "load_policy":{"local_only":True,"gpu_offload":"off","context_length":512,"parallel":1,"ttl_seconds":120},
            "loaded_instance":{"identifier":LM_IDENTIFIER,"model_key":matches[0].get("modelKey"),"device_identifier":matches[0].get("deviceIdentifier"),"status":matches[0].get("status")},
            "resource_estimate_stdout_sha256":sha256_bytes(estimate.stdout.encode("utf-8")),
            "inference_stdout_sha256":sha256_bytes(chat.stdout.encode("utf-8")),
            "inference_stdout_length":len(chat.stdout.strip()),
            "network_model_fetch_performed":False,"accelerator_execution_claimed":False,
        }
    finally:
        if loaded:
            unload=run([str(lms),"unload",LM_IDENTIFIER],180,env)
            if unload.returncode!=0: raise RuntimeError("LM Studio test model cleanup/unload failed")

def start_ollama_cpu(runtime_dir:Path):
    ollama=find_binary("ollama")
    if ollama is None: raise RuntimeError("Ollama binary not found")
    port=free_port(); base=f"http://127.0.0.1:{port}"
    env=safe_child_env()
    env.update({
        "OLLAMA_HOST":f"127.0.0.1:{port}","OLLAMA_KEEP_ALIVE":"0",
        "OLLAMA_MAX_LOADED_MODELS":"1","OLLAMA_NUM_PARALLEL":"1",
        "CUDA_VISIBLE_DEVICES":"","ROCR_VISIBLE_DEVICES":"",
        "HIP_VISIBLE_DEVICES":"","GPU_DEVICE_ORDINAL":"",
    })
    log_fh=(runtime_dir/"ollama-cpu.log").open("w",encoding="utf-8")
    proc=subprocess.Popen([str(ollama),"serve"],stdout=log_fh,stderr=subprocess.STDOUT,text=True,env=env,start_new_session=True)
    deadline=time.monotonic()+60; last=None
    while time.monotonic()<deadline:
        if proc.poll() is not None:
            log_fh.close()
            raise RuntimeError(f"ephemeral Ollama exited rc={proc.returncode}")
        try:
            http_json(base+"/api/version",timeout=5); log_fh.flush()
            return ollama,proc,base
        except Exception as exc:
            last=exc; time.sleep(0.5)
    log_fh.close()
    raise RuntimeError(f"ephemeral Ollama readiness timeout: {last}")

def collect_ollama(runtime_dir:Path)->dict[str,Any]:
    ollama,proc,base=start_ollama_cpu(runtime_dir)
    try:
        version=http_json(base+"/api/version",timeout=10)
        tags=http_json(base+"/api/tags",timeout=30)
        candidates=select_ollama_models(tags,limit=5)
        if not candidates: raise RuntimeError("no digest-addressed local Ollama model found")
        failures=[]
        for row in candidates:
            name=str(row.get("name") or row.get("model"))
            try:
                response=http_json(base+"/api/generate",{
                    "model":name,"prompt":"Reply briefly with FA3_OLLAMA_E2E_PASS.",
                    "stream":False,"keep_alive":"5m",
                    "options":{"num_ctx":512,"num_predict":8,"temperature":0},
                },timeout=600)
                text=str(response.get("response","")) if isinstance(response,dict) else ""
                if not text.strip(): raise RuntimeError("empty generate response")
                ps=http_json(base+"/api/ps",timeout=30)
                running=[x for x in (ps.get("models",[]) if isinstance(ps,dict) else []) if isinstance(x,dict) and (x.get("name")==name or x.get("model")==name)]
                if len(running)!=1: raise RuntimeError("running model not found in /api/ps")
                size_vram=running[0].get("size_vram")
                if size_vram is None or int(size_vram)!=0:
                    raise RuntimeError(f"CPU-only proof failed: size_vram={size_vram}")
                http_json(base+"/api/generate",{"model":name,"keep_alive":0},timeout=120)
                return {
                    "provider_id":OLLAMA_PROVIDER_ID,"status":"PASS",
                    "evidence_level":"CURRENT_HOST_RUNTIME_E2E_PASS",
                    "ollama_version":version.get("version") if isinstance(version,dict) else None,
                    "ollama_binary_sha256":sha256_file(ollama),"bind_host":"127.0.0.1",
                    "selected_model":name,"selected_model_digest":row.get("digest"),
                    "selected_model_size_bytes":row.get("size"),
                    "selected_model_details":row.get("details"),
                    "generate_response_sha256":sha256_bytes(text.encode("utf-8")),
                    "generate_response_length":len(text.strip()),"size_vram":int(size_vram),
                    "accelerator_visibility":"HIDDEN_FOR_CPU_SMOKE",
                    "network_model_pull_performed":False,"accelerator_execution_claimed":False,
                    "candidate_failures_before_success":failures,
                }
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")
                try: http_json(base+"/api/generate",{"model":name,"keep_alive":0},timeout=30)
                except Exception: pass
        raise RuntimeError("no local Ollama model completed CPU-only generate: "+" | ".join(failures[-3:]))
    finally:
        try: os.killpg(proc.pid,15)
        except ProcessLookupError: pass
        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            try: os.killpg(proc.pid,9)
            except ProcessLookupError: pass
            proc.wait(timeout=5)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(ROOT))
    args=ap.parse_args()
    root=Path(args.root).resolve()
    if platform.system()!="Linux" or platform.machine().lower() not in {"x86_64","amd64"}:
        raise RuntimeError("current-host evidence requires Linux x86_64")
    if hasattr(os,"geteuid") and os.geteuid()==0:
        raise RuntimeError("current-host evidence must not run as root")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir=root/"evidence/runtime/model-manager-current-host"/stamp
    runtime_dir.mkdir(parents=True,exist_ok=True)
    receipt_path=root/"evidence/receipts/model-manager-current-host.json"
    regressions=regression_check()
    if regressions.get("result")!="PASS": raise RuntimeError("provider adapter regression failed")
    receipt={
        "schema":"fa3.model-manager-current-host-receipt.v1","runtime_id":RUNTIME_ID,
        "status":"FAIL","evidence_level":"CURRENT_HOST_MODEL_PROVIDER_E2E_FAIL",
        "started_at":utc_now(),"host":host_fingerprint(),"adapter_regression":regressions,
        "execution_policy":{"local_artifacts_only":True,"network_download_or_pull":False,"cpu_first":True,"accelerator_execution_claimed":False,"accelerator_requires_hrb_for_separate_evidence":True},
        "providers":{},"new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":143,
    }
    try:
        receipt["providers"][HF_PROVIDER_ID]=collect_hf()
        receipt["providers"][LM_STUDIO_PROVIDER_ID]=collect_lmstudio(runtime_dir)
        receipt["providers"][OLLAMA_PROVIDER_ID]=collect_ollama(runtime_dir)
        receipt["status"]="PASS"; receipt["evidence_level"]=EVIDENCE_LEVEL
        receipt["completed_at"]=utc_now()
        receipt["promotion_effect"]="PROVIDER_SPECIFIC_CURRENT_HOST_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED"
        writej(receipt_path,receipt)
        writej(runtime_dir/"summary.json",{
            "runtime_id":RUNTIME_ID,"status":"PASS","evidence_level":EVIDENCE_LEVEL,
            "completed_at":receipt["completed_at"],
            "provider_statuses":{k:v.get("status") for k,v in receipt["providers"].items()},
            "receipt_sha256":sha256_file(receipt_path),
        })
        print(json.dumps(receipt,indent=2,ensure_ascii=False))
        return 0
    except Exception as exc:
        receipt["completed_at"]=utc_now()
        receipt["error_type"]=type(exc).__name__; receipt["error"]=str(exc)
        writej(receipt_path,receipt)
        print(json.dumps(receipt,indent=2,ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
