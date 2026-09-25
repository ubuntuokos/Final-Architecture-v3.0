#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, subprocess
from pathlib import Path
from typing import Any

PINNED_REVISION="1ea34ff48f87168174e12956e200b1d908b1c5ff"
PROVIDER_ID="FA3-PROVIDER-WAN22-001"
SUPPORTED_TASKS={"t2v-A14B","i2v-A14B","ti2v-5B","s2v-14B"}

class WanExecutionDenied(RuntimeError): pass

def loadj(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def run(cmd:list[str],**kwargs)->subprocess.CompletedProcess[str]:
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)
    if p.returncode:
        raise WanExecutionDenied(f"command failed rc={p.returncode}: {cmd[0]}")
    return p

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def select_nvidia_ordinal(uuid:str,bdf:str)->str:
    p=run(["nvidia-smi","--query-gpu=index,uuid,pci.bus_id","--format=csv,noheader,nounits"])
    matches=[]
    norm=lambda x:x.strip().lower().replace("00000000:","0000:")
    for line in p.stdout.splitlines():
        parts=[x.strip() for x in line.split(",")]
        if len(parts)!=3:continue
        if parts[1]==uuid and norm(parts[2])==norm(bdf):matches.append(parts[0])
    if len(matches)!=1:raise WanExecutionDenied("HRB accelerator UUID/BDF does not map to exactly one NVIDIA runtime ordinal")
    return matches[0]

def frame_num(ir:dict[str,Any],fps:int=24)->int:
    if isinstance(ir.get("frame_num"),int):
        n=int(ir["frame_num"])
    else:
        duration=float(ir.get("duration",5))
        n=max(5,int(round(duration*fps)))
    return n if (n-1)%4==0 else max(5,4*round((n-1)/4)+1)

def size_from_ir(ir:dict[str,Any])->str:
    if isinstance(ir.get("width"),int) and isinstance(ir.get("height"),int):
        return f"{ir['width']}*{ir['height']}"
    resolution=str(ir.get("resolution","720P")).upper()
    ratio=str(ir.get("ratio","16:9"))
    if resolution in {"720P","1280X720"} and ratio=="16:9":return "1280*720"
    if resolution in {"720P","720X1280"} and ratio=="9:16":return "720*1280"
    if resolution in {"480P","832X480"} and ratio=="16:9":return "832*480"
    raise WanExecutionDenied("Wan2.2 projection requires explicit supported width/height or supported resolution/ratio")

def references(ir:dict[str,Any],media_type:str)->list[str]:
    out=[]
    for ref in ir.get("references",[]):
        if isinstance(ref,dict) and ref.get("media_type")==media_type:
            p=ref.get("path") or ref.get("local_path")
            if isinstance(p,str) and p:out.append(p)
    return out

def validate_runtime(cfg:dict[str,Any])->tuple[Path,Path,Path,str]:
    if cfg.get("schema")!="fa3.wan22-runtime-config.v1":raise WanExecutionDenied("runtime config schema mismatch")
    if cfg.get("provider_id")!=PROVIDER_ID:raise WanExecutionDenied("runtime config provider mismatch")
    if cfg.get("runtime_kind")!="OFFICIAL_WAN22_CHECKOUT":raise WanExecutionDenied("only official Wan2.2 checkout is admitted by this wrapper revision")
    task=str(cfg.get("task",""))
    if task not in SUPPORTED_TASKS:raise WanExecutionDenied("unsupported Wan2.2 task")
    root=Path(str(cfg.get("source_root",""))).expanduser().resolve()
    python=Path(str(cfg.get("python",""))).expanduser().resolve()
    ckpt=Path(str(cfg.get("checkpoint_dir",""))).expanduser().resolve()
    if not (root/".git").is_dir() or not (root/"generate.py").is_file():raise WanExecutionDenied("official Wan2.2 source checkout missing")
    if not python.is_file() or not os.access(python,os.X_OK):raise WanExecutionDenied("isolated runtime Python missing")
    if not ckpt.is_dir():raise WanExecutionDenied("pre-admitted checkpoint directory missing")
    rev=run(["git","-C",str(root),"rev-parse","HEAD"]).stdout.strip()
    if rev!=PINNED_REVISION:raise WanExecutionDenied("Wan2.2 source revision mismatch")
    dirty=run(["git","-C",str(root),"status","--porcelain","--untracked-files=no"]).stdout.strip()
    if dirty:raise WanExecutionDenied("Wan2.2 tracked source tree is dirty")
    return root,python,ckpt,task

def execute(cfg_path:Path,ir_path:Path,output:Path)->dict[str,Any]:
    cfg=loadj(cfg_path);ir=loadj(ir_path)
    root,python,ckpt,task=validate_runtime(cfg)
    if ir.get("schema") not in {"fa3.video-generation-ir.v1","fa3.video-generation-ir.v2"}:raise WanExecutionDenied("VideoGenerationIR schema mismatch")
    prompt=ir.get("prompt") or ir.get("creative_prompt")
    if not isinstance(prompt,str) or not prompt.strip():raise WanExecutionDenied("prompt required")
    uuid=os.environ.get("FA3_ACCELERATOR_UUID","").strip();bdf=os.environ.get("FA3_ACCELERATOR_PCI_BDF","").strip()
    if not uuid or not bdf:raise WanExecutionDenied("HRB accelerator binding environment missing")
    ordinal=select_nvidia_ordinal(uuid,bdf)
    cmd=[str(python),str(root/"generate.py"),"--task",task,"--ckpt_dir",str(ckpt),"--save_file",str(output),"--prompt",prompt.strip(),"--size",size_from_ir(ir),"--frame_num",str(frame_num(ir)),"--base_seed",str(int(ir.get("seed",-1)))]
    images=references(ir,"image");audios=references(ir,"audio")
    if task in {"i2v-A14B","ti2v-5B"}:
        if not images:raise WanExecutionDenied("selected Wan task requires image reference")
        cmd += ["--image",images[0]]
    if task=="s2v-14B":
        if not images or not audios:raise WanExecutionDenied("selected Wan S2V task requires image and audio references")
        cmd += ["--image",images[0],"--audio",audios[0]]
    output.parent.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env["CUDA_VISIBLE_DEVICES"]=ordinal
    env["HF_HUB_OFFLINE"]="1";env["TRANSFORMERS_OFFLINE"]="1";env["PIP_NO_INDEX"]="1";env["WANDB_MODE"]="disabled"
    for k in list(env):
        if k.upper() in {"DASH_API_KEY","HF_TOKEN","HUGGING_FACE_HUB_TOKEN"}:env.pop(k,None)
    p=subprocess.run(cmd,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    if p.returncode!=0:raise WanExecutionDenied(f"Wan2.2 generation failed rc={p.returncode}")
    if not output.is_file() or output.stat().st_size<=0:raise WanExecutionDenied("Wan2.2 did not produce output artifact")
    return {
      "status":"SUCCEEDED","provider_id":PROVIDER_ID,"task":task,
      "source_revision":PINNED_REVISION,"artifact_path":str(output),
      "artifact_sha256":sha256_file(output),"hrb_lease_id":os.environ.get("FA3_HRB_LEASE_ID"),
      "accelerator_uuid":uuid,"accelerator_pci_bdf":bdf,"runtime_ordinal_is_identity":False,
      "network_model_fetch_performed":False,"prompt_extension_used":False
    }

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--runtime-config",required=True);ap.add_argument("--ir",required=True);ap.add_argument("--output",required=True)
    a=ap.parse_args()
    try:r=execute(Path(a.runtime_config),Path(a.ir),Path(a.output));print(json.dumps(r));return 0
    except Exception as exc:
        print(json.dumps({"status":"FAILED","provider_id":PROVIDER_ID,"error":str(exc)}))
        return 2
if __name__=="__main__":raise SystemExit(main())
