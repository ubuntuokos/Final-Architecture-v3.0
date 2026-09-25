#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, subprocess
from pathlib import Path
from typing import Any

PINNED_REVISION="1ea34ff48f87168174e12956e200b1d908b1c5ff"
PROVIDER_ID="FA3-PROVIDER-WAN22-001"
MODEL_SECURITY_PROFILE="FA3-MODEL-ARTIFACT-SECURITY-001"
ROOT=Path(__file__).resolve().parents[1]

class AdmissionDenied(RuntimeError):pass

def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def run(cmd:list[str])->str:
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:raise AdmissionDenied("runtime identity command failed")
    return p.stdout.strip()

def validate_model_receipt(p:Path,cfg:dict[str,Any])->dict[str,Any]:
    r=loadj(p)
    if r.get("schema")!="fa3.model-artifact-admission-receipt.v1":raise AdmissionDenied("model artifact receipt schema mismatch")
    if r.get("authority")!=MODEL_SECURITY_PROFILE:raise AdmissionDenied("model artifact receipt authority mismatch")
    if r.get("status")!="PASS":raise AdmissionDenied("model artifact receipt not PASS")
    if r.get("provider_id")!=PROVIDER_ID:raise AdmissionDenied("model artifact receipt provider mismatch")
    if r.get("artifact_root")!=str(Path(cfg["checkpoint_dir"]).expanduser().resolve()):raise AdmissionDenied("model artifact root mismatch")
    if not isinstance(r.get("artifact_set_sha256"),str) or len(r["artifact_set_sha256"])!=64:raise AdmissionDenied("content-addressed model artifact identity missing")
    if r.get("license_decision")!="ALLOW":raise AdmissionDenied("model license decision not ALLOW")
    return r

def admit(cfg_path:Path,model_receipt_path:Path,out:Path)->dict[str,Any]:
    cfg=loadj(cfg_path)
    if cfg.get("schema")!="fa3.wan22-runtime-config.v1" or cfg.get("provider_id")!=PROVIDER_ID:raise AdmissionDenied("runtime config invalid")
    if cfg.get("runtime_kind")!="OFFICIAL_WAN22_CHECKOUT":raise AdmissionDenied("runtime kind not admitted")
    source=Path(cfg["source_root"]).expanduser().resolve();python=Path(cfg["python"]).expanduser().resolve();ckpt=Path(cfg["checkpoint_dir"]).expanduser().resolve()
    if not (source/".git").is_dir() or not python.is_file() or not ckpt.is_dir():raise AdmissionDenied("pre-provisioned runtime inputs missing")
    if run(["git","-C",str(source),"rev-parse","HEAD"])!=PINNED_REVISION:raise AdmissionDenied("upstream revision mismatch")
    if run(["git","-C",str(source),"status","--porcelain","--untracked-files=no"]):raise AdmissionDenied("tracked source tree dirty")
    model=validate_model_receipt(model_receipt_path,cfg)
    wrapper=(ROOT/"bin/fa3-wan22-provider-exec.py").resolve()
    receipt={
      "schema":"fa3.wan22-provider-admission-receipt.v1","provider_id":PROVIDER_ID,"status":"PASS",
      "synthetic_or_mock_provider":False,"source_revision":PINNED_REVISION,
      "source_root":str(source),"runtime_python":str(python),"checkpoint_dir":str(ckpt),
      "model_artifact_receipt_sha256":sha256_file(model_receipt_path),"model_artifact_set_sha256":model["artifact_set_sha256"],
      "license_decision":"ALLOW","network_fetch_performed":False,"auto_install_performed":False,
      "wrapper_sha256":sha256_file(wrapper),"current_host_runtime_execution_claim":False
    }
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    return receipt

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--runtime-config",required=True);ap.add_argument("--model-admission",required=True);ap.add_argument("--output",default="evidence/receipts/wan22-provider-admission.json")
    a=ap.parse_args()
    try:r=admit(Path(a.runtime_config),Path(a.model_admission),Path(a.output));print(json.dumps(r,indent=2));return 0
    except Exception as exc:print(json.dumps({"provider_id":PROVIDER_ID,"status":"FAIL","error":str(exc)},indent=2));return 2
if __name__=="__main__":raise SystemExit(main())
