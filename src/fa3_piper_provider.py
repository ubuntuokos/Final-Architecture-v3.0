#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, wave
from pathlib import Path
from typing import Any
PROVIDER_ID="FA3-PROVIDER-PIPER-001"
class PiperDenied(RuntimeError): pass
def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def execute_piper(req:dict[str,Any],output:Path)->dict[str,Any]:
    if req.get("language") not in {"hu","hu-HU","hu_HU"}: raise PiperDenied("Piper adapter is hu-HU only")
    if req.get("mode") not in {"plain","preset_voice"}: raise PiperDenied("Piper cloning is unsupported")
    if not req.get("license_and_rights_ref"): raise PiperDenied("license_and_rights_ref required")
    if req.get("device","cpu")!="cpu": raise PiperDenied("Piper FA3 adapter is CPU-only")
    exe=shutil.which("piper")
    if not exe: raise PiperDenied("piper executable not installed")
    root_raw=os.environ.get("FA3_PIPER_MODEL_ROOT","")
    if not root_raw: raise PiperDenied("FA3_PIPER_MODEL_ROOT is not configured")
    root=Path(root_raw).expanduser().resolve(); model_raw=str(req.get("model_path") or os.environ.get("FA3_PIPER_MODEL_PATH","")); model=Path(model_raw).expanduser().resolve()
    if not root.is_dir() or root not in model.parents: raise PiperDenied("model must be under FA3_PIPER_MODEL_ROOT")
    meta=model.with_suffix(model.suffix+".fa3.json")
    if not model.is_file() or not meta.is_file(): raise PiperDenied("model or FA3 metadata missing")
    m=json.loads(meta.read_text(encoding="utf-8"))
    if m.get("provider_id")!=PROVIDER_ID or m.get("language")!="hu-HU": raise PiperDenied("model metadata mismatch")
    expected=m.get("sha256")
    if not expected or sha256_file(model)!=expected: raise PiperDenied("model hash mismatch")
    output=output.expanduser().resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":os.environ.get("HOME","/tmp")}
    cp=subprocess.run([exe,"--model",str(model),"--output_file",str(output)],input=str(req.get("text","")),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120,check=False,env=env)
    if cp.returncode!=0: raise PiperDenied("piper execution failed: "+cp.stderr[-500:])
    with wave.open(str(output),"rb") as w: rate=w.getframerate(); channels=w.getnchannels(); frames=w.getnframes()
    if frames<=0 or channels!=1: raise PiperDenied("invalid Piper WAV output")
    return {"schema":"fa3.voice-synthesis-result.v1","request_id":req["request_id"],"provider_id":PROVIDER_ID,"audio_path":str(output),"audio_sha256":sha256_file(output),"sample_rate_hz":rate,"channels":channels,"voice_identity_ref":req.get("voice_identity_ref"),"language":"hu-HU","execution_evidence":{"device":"cpu","silent_fallback":False,"production_promotion_claim":False}}
