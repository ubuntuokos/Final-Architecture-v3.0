#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROVIDER_ID="FA3-PROVIDER-COSYVOICE-001"
PROFILE_ID="FA3-VOICE-001"
CONTRACT_ID="FA3-VOICE-CONTRACTS-001"
MODEL_ALLOWLIST_ID="FA3-COSYVOICE-MODEL-ALLOWLIST-001"
MODEL_ID="FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
MODEL_REVISION="29e01c4e8d000f4bcd70751be16fa94bf3d85a18"
UPSTREAM_COMMIT="074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc"
OFFICIAL_LANGUAGES={"zh","en","fr","es","ja","ko","it","ru","de"}
EXPERIMENTAL_LANGUAGES={"hu"}
SAMPLE_RATE=24000
CAPS=143

class PolicyDenied(RuntimeError): pass
class ModelTrustDenied(RuntimeError): pass
class HostAdmissionDenied(RuntimeError): pass

def now()->str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _load(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def load_allowlist(root:Path)->dict[str,Any]:
    return _load(root/"canonical/FA3-COSYVOICE-MODEL-ALLOWLIST-001.json")

def validate_language(req:dict[str,Any])->str:
    lang=str(req.get("language","")).strip().lower()
    if not lang:
        raise PolicyDenied("language is required")
    if lang in OFFICIAL_LANGUAGES:
        return "PRODUCTION_LANGUAGE_ELIGIBLE"
    if lang in EXPERIMENTAL_LANGUAGES:
        if req.get("experimental_language_ack") is not True:
            raise PolicyDenied("Hungarian is experimental for this upstream model and requires explicit acknowledgement")
        return "EXPERIMENTAL_LANGUAGE_NOT_PRODUCTION_PROMOTABLE"
    raise PolicyDenied(f"language not admitted by CosyVoice model policy: {lang}")

def validate_consent(req:dict[str,Any])->None:
    proof=req.get("consent_proof")
    if not isinstance(proof,dict):
        raise PolicyDenied("voice reference requires typed consent_proof")
    if proof.get("status")!="GRANTED" or proof.get("subject_authorized") is not True:
        raise PolicyDenied("voice consent is not GRANTED/authorized")
    scope=proof.get("scope")
    scopes={scope} if isinstance(scope,str) else set(scope or [])
    if "VOICE_SYNTHESIS" not in scopes:
        raise PolicyDenied("consent scope must include VOICE_SYNTHESIS")
    if not str(proof.get("provenance_ref","")).strip():
        raise PolicyDenied("consent provenance_ref is required")

def validate_reference_audio(req:dict[str,Any])->Path:
    p=Path(str(req.get("reference_audio_path",""))).expanduser()
    expected=str(req.get("reference_audio_sha256","")).lower()
    if not p.is_file() or len(expected)!=64:
        raise PolicyDenied("reference audio path/hash missing")
    actual=sha256_file(p.resolve())
    if actual!=expected:
        raise PolicyDenied("reference audio sha256 mismatch")
    return p.resolve()

def validate_request(root:Path, req:dict[str,Any])->dict[str,Any]:
    if req.get("schema")!="fa3.voice-synthesis-request.v1":
        raise PolicyDenied("request schema mismatch")
    for key in ("request_id","text","language","mode","model_id","voice_identity_ref"):
        if not str(req.get(key,"")).strip():
            raise PolicyDenied(f"missing required field: {key}")
    if len(str(req["text"]))>5000:
        raise PolicyDenied("text exceeds 5000-character provider bound")
    mode=req["mode"]
    if mode not in {"zero_shot","cross_lingual","instruct2"}:
        raise PolicyDenied("unsupported synthesis mode")
    if req.get("model_id")!=MODEL_ID:
        raise ModelTrustDenied("model identity not allowlisted")
    allow=load_allowlist(root)
    model=allow.get("models",{}).get(MODEL_ID)
    if not model or model.get("revision")!=MODEL_REVISION:
        raise ModelTrustDenied("canonical model revision drift")
    language_status=validate_language(req)
    validate_consent(req)
    ref=validate_reference_audio(req)
    prompt=str(req.get("prompt_text",""))
    instruct=str(req.get("instruct_text",""))
    if mode=="zero_shot" and not prompt.strip():
        raise PolicyDenied("zero_shot requires prompt_text")
    if len(prompt)>2000 or len(instruct)>1000:
        raise PolicyDenied("prompt/instruction provider bound exceeded")
    if mode=="instruct2" and not instruct.strip():
        raise PolicyDenied("instruct2 requires instruct_text")
    return {"language_status":language_status,"reference_audio":str(ref)}

def validate_source_checkout(repo_path:Path)->str:
    if not repo_path.is_dir():
        raise HostAdmissionDenied("CosyVoice source checkout missing")
    cp=subprocess.run(["git","-C",str(repo_path),"rev-parse","HEAD"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False,timeout=10)
    if cp.returncode!=0:
        raise HostAdmissionDenied("CosyVoice checkout is not a readable git repository")
    sha=cp.stdout.strip()
    if sha!=UPSTREAM_COMMIT:
        raise HostAdmissionDenied(f"CosyVoice source commit mismatch: {sha}")
    return sha

def validate_model_dir(root:Path, model_dir:Path)->dict[str,Any]:
    if not model_dir.is_dir():
        raise ModelTrustDenied("CosyVoice model directory missing")
    meta_path=model_dir/"FA3-MODEL-METADATA.json"
    if not meta_path.is_file():
        raise ModelTrustDenied("FA3 model metadata missing; use canonical bootstrap")
    meta=_load(meta_path)
    if meta.get("model_id")!=MODEL_ID or meta.get("revision")!=MODEL_REVISION:
        raise ModelTrustDenied("model metadata identity/revision mismatch")
    allow=load_allowlist(root)["models"][MODEL_ID]
    for rel,expected in allow.get("critical_artifacts",{}).items():
        p=model_dir/rel
        if not p.is_file() or sha256_file(p)!=expected:
            raise ModelTrustDenied(f"critical model artifact hash mismatch: {rel}")
    return meta

def validate_python310()->None:
    if sys.version_info[:2]!=(3,10):
        raise HostAdmissionDenied(f"CosyVoice provider requires Python 3.10, got {sys.version_info.major}.{sys.version_info.minor}")

def validate_sox()->str:
    p=shutil.which("sox")
    if not p:
        raise HostAdmissionDenied("SoX is required for FA3 CosyVoice current-host admission")
    return p

def validate_hrb_lease(device:str, lease_path:str|None)->dict[str,Any]|None:
    if device=="cpu":
        return None
    if not device.startswith("cuda:"):
        raise HostAdmissionDenied("device must be cpu or cuda:N")
    if not lease_path:
        raise HostAdmissionDenied("CUDA execution requires HRB lease")
    lease=_load(Path(lease_path).expanduser().resolve())
    if lease.get("schema")!="AcceleratorExecutionLease@1":
        raise HostAdmissionDenied("HRB lease schema mismatch")
    try:
        ordinal=int(device.split(":",1)[1])
    except Exception as exc:
        raise HostAdmissionDenied("invalid CUDA device ordinal") from exc
    if lease.get("device_ordinal")!=ordinal:
        raise HostAdmissionDenied("CUDA ordinal is not bound to HRB lease")
    if not str(lease.get("gpu_uuid","")).strip():
        raise HostAdmissionDenied("HRB lease gpu_uuid missing")
    expires=lease.get("expires_at")
    if expires:
        dt=datetime.fromisoformat(str(expires).replace("Z","+00:00"))
        if dt<=datetime.now(timezone.utc):
            raise HostAdmissionDenied("HRB lease expired")
    return lease

def prepare_device(device:str, lease:dict[str,Any]|None)->None:
    if device=="cpu":
        os.environ["CUDA_VISIBLE_DEVICES"]=""
    else:
        os.environ["CUDA_VISIBLE_DEVICES"]=str(lease["device_ordinal"])

def execute_synthesis(root:Path, req:dict[str,Any], repo_path:Path, model_dir:Path, output:Path, device:str="cpu", hrb_lease_path:str|None=None)->dict[str,Any]:
    validated=validate_request(root,req)
    validate_python310()
    sox=validate_sox()
    source_sha=validate_source_checkout(repo_path)
    model_meta=validate_model_dir(root,model_dir)
    lease=validate_hrb_lease(device,hrb_lease_path)
    prepare_device(device,lease)

    sys.path.insert(0,str(repo_path))
    sys.path.insert(0,str(repo_path/"third_party/Matcha-TTS"))
    try:
        import torch
        import torchaudio
        from cosyvoice.cli.cosyvoice import AutoModel
    except Exception as exc:
        raise HostAdmissionDenied(f"CosyVoice runtime import failed: {exc}") from exc

    cosy=AutoModel(model_dir=str(model_dir),load_trt=False,load_vllm=False,fp16=False)
    mode=req["mode"]
    ref=validated["reference_audio"]
    if mode=="zero_shot":
        iterator=cosy.inference_zero_shot(req["text"],req["prompt_text"],ref,stream=bool(req.get("streaming",False)))
    elif mode=="cross_lingual":
        iterator=cosy.inference_cross_lingual(req["text"],ref,stream=bool(req.get("streaming",False)))
    else:
        iterator=cosy.inference_instruct2(req["text"],req["instruct_text"],ref,stream=bool(req.get("streaming",False)))

    chunks=[]
    for item in iterator:
        speech=item.get("tts_speech")
        if speech is not None:
            chunks.append(speech.detach().cpu())
    if not chunks:
        raise RuntimeError("CosyVoice returned no audio chunks")
    speech=torch.cat(chunks,dim=1)
    output=output.expanduser().resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    torchaudio.save(str(output),speech,cosy.sample_rate)

    if cosy.sample_rate!=SAMPLE_RATE:
        raise RuntimeError(f"sample-rate contract mismatch: {cosy.sample_rate}")
    with wave.open(str(output),"rb") as w:
        if w.getframerate()!=SAMPLE_RATE or w.getnchannels()!=1 or w.getnframes()<=0:
            raise RuntimeError("output WAV contract mismatch")

    return {
        "schema":"fa3.voice-synthesis-result.v1",
        "request_id":req["request_id"],
        "provider_id":PROVIDER_ID,
        "profile_id":PROFILE_ID,
        "model_id":MODEL_ID,
        "model_revision":MODEL_REVISION,
        "audio_path":str(output),
        "audio_sha256":sha256_file(output),
        "sample_rate_hz":SAMPLE_RATE,
        "channels":1,
        "voice_identity_ref":req["voice_identity_ref"],
        "language":req["language"],
        "language_promotion_status":validated["language_status"],
        "execution_evidence":{
            "upstream_commit":source_sha,
            "model_revision":model_meta["revision"],
            "reference_audio_sha256":req["reference_audio_sha256"],
            "consent_provenance_ref":req["consent_proof"]["provenance_ref"],
            "device":device,
            "hrb_lease_id":None if lease is None else lease.get("lease_id"),
            "gpu_uuid":None if lease is None else lease.get("gpu_uuid"),
            "sox":sox,
            "streaming":bool(req.get("streaming",False))
        }
    }

def run_executable_conformance(root:Path)->dict[str,Any]:
    checks=[]
    def ok(cid,cond,detail=""):
        checks.append({"id":cid,"result":"PASS" if cond else "FAIL","detail":detail})
    allow=load_allowlist(root)
    provider=_load(root/"canonical/providers/FA3-PROVIDER-COSYVOICE-001.json")
    decision=_load(root/"canonical/decisions/FA3-DEC-COSYVOICE-2026-08-31.json")
    enf=_load(root/"canonical/cosyvoice-enforcement.json")
    runtime=_load(root/"canonical/FA3-COSYVOICE-RUNTIME-CONFORMANCE-001.json")
    ref=_load(root/"canonical/references/FA3-COSYVOICE-UPSTREAM-REFERENCE-2026-08-31.json")
    ok("COSY-001",CONTRACT_ID=="FA3-VOICE-CONTRACTS-001")
    ok("COSY-002",provider.get("architectural_authority") is False and provider.get("canonical_root") is False)
    ok("COSY-003",provider.get("capability_count")==CAPS and decision.get("capability_count_after")==CAPS and decision.get("new_capabilities")==0)
    ok("COSY-004",ref.get("repository_commit")==UPSTREAM_COMMIT)
    ok("COSY-005",allow["models"][MODEL_ID]["revision"]==MODEL_REVISION)
    ok("COSY-006",allow.get("arbitrary_local_checkpoint_paths_allowed") is False)
    ok("COSY-007",allow.get("network_fetch_default") is False)
    ok("COSY-008",any("Python 3.10" in r["requirement"] for r in enf["rules"]))
    ok("COSY-009",any("Conda" in r["requirement"] for r in enf["rules"]))
    ok("COSY-010",any("SoX" in r["requirement"] for r in enf["rules"]))
    ok("COSY-011",set(allow["models"][MODEL_ID]["official_languages"])==OFFICIAL_LANGUAGES)
    ok("COSY-012",allow["models"][MODEL_ID]["experimental_languages"]==["hu"])
    ok("COSY-013",any("consent" in r["requirement"].lower() for r in enf["rules"]))
    ok("COSY-014",any("sha256" in r["requirement"].lower() for r in enf["rules"]))
    ok("COSY-015",any("bounded" in r["requirement"].lower() for r in enf["rules"]))
    ok("COSY-016",any("Host Resource Broker" in r["requirement"] for r in enf["rules"]))
    ok("COSY-017",any("GPU execution target" in r["requirement"] for r in enf["rules"]))
    ok("COSY-018",allow["models"][MODEL_ID]["sample_rate_hz"]==SAMPLE_RATE)
    ok("COSY-019",any("Streaming" in r["requirement"] for r in enf["rules"]))
    ok("COSY-020",any("PASS evidence" in r["requirement"] for r in enf["rules"]))
    ok("COSY-021",provider.get("global_runtime_promotion_required_when_disabled") is False and runtime.get("production_promotion_claim") is False)
    passed=sum(c["result"]=="PASS" for c in checks)
    return {"schema":"fa3.cosyvoice-executable-conformance.v1","provider_id":PROVIDER_ID,"result":"PASS" if passed==len(checks) else "FAIL","passed":passed,"total":len(checks),"cases":checks}

def main()->int:
    ap=argparse.ArgumentParser(description="FA3 CosyVoice provider adapter")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--request")
    ap.add_argument("--cosyvoice-repo")
    ap.add_argument("--model-dir")
    ap.add_argument("--output")
    ap.add_argument("--device",default="cpu")
    ap.add_argument("--hrb-lease")
    ap.add_argument("--conformance",action="store_true")
    args=ap.parse_args()
    root=Path(args.root).resolve()
    if args.conformance:
        r=run_executable_conformance(root); print(json.dumps(r,indent=2)); return 0 if r["result"]=="PASS" else 2
    if not all((args.request,args.cosyvoice_repo,args.model_dir,args.output)):
        raise SystemExit("--request --cosyvoice-repo --model-dir --output are required for synthesis")
    req=_load(Path(args.request).expanduser().resolve())
    result=execute_synthesis(root,req,Path(args.cosyvoice_repo).expanduser().resolve(),Path(args.model_dir).expanduser().resolve(),Path(args.output),args.device,args.hrb_lease)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
