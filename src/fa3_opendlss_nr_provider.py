#!/usr/bin/env python3
"""Provider-scoped OpenDLSS-NR adapter helpers; no independent hardware authority."""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess
from pathlib import Path
from typing import Any

PROVIDER_ID="FA3-PROVIDER-OPENDLSS-NR-001"
PINNED_COMMIT="9d08f4184bbcb9d858e2fb7a7834ec0837a9d2f1"

class OpenDlssNrError(RuntimeError):
    def __init__(self,code:str,message:str):
        super().__init__(message); self.code=code

def _git_head(root:Path)->str:
    proc=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],text=True,capture_output=True,check=False)
    if proc.returncode!=0: raise OpenDlssNrError("ODNR-SOURCE-NOT-GIT",proc.stderr.strip() or "git rev-parse failed")
    return proc.stdout.strip()

def validate_source_root(root:Path)->dict[str,Any]:
    root=root.resolve()
    if not root.is_dir(): raise OpenDlssNrError("ODNR-SOURCE-MISSING",str(root))
    head=_git_head(root)
    if head!=PINNED_COMMIT: raise OpenDlssNrError("ODNR-SOURCE-PIN-MISMATCH",f"expected {PINNED_COMMIT}, got {head}")
    return {"provider_id":PROVIDER_ID,"source_root":str(root),"commit":head,"immutable_pin_match":True,
            "source_license_expected":"MIT","production_supply_chain_admission_implied":False}

def _safe_child(root:Path,relative:str)->Path:
    candidate=(root/relative).resolve()
    try: candidate.relative_to(root.resolve())
    except ValueError as exc: raise OpenDlssNrError("ODNR-MODEL-PATH-ESCAPE",relative) from exc
    return candidate

def validate_model_manifest(model_root:Path,verify_hashes:bool=True)->dict[str,Any]:
    model_root=model_root.resolve(); manifest_path=model_root/"manifest.json"
    if not manifest_path.is_file(): raise OpenDlssNrError("ODNR-MANIFEST-MISSING",str(manifest_path))
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")); stages=manifest.get("stages"); tensors=manifest.get("tensors")
    if not isinstance(stages,list) or not stages or not isinstance(tensors,list):
        raise OpenDlssNrError("ODNR-MANIFEST-INVALID","stages and tensors arrays are required")
    checked=[]
    for stage in stages:
        if not isinstance(stage,dict): raise OpenDlssNrError("ODNR-MANIFEST-INVALID","stage entries must be objects")
        rel=str(stage.get("file","")).strip(); expected_sha=str(stage.get("sha256","")).lower().strip(); expected_len=stage.get("packedByteLength")
        if not rel or len(expected_sha)!=64 or not isinstance(expected_len,int) or expected_len<0:
            raise OpenDlssNrError("ODNR-STAGE-METADATA-INVALID",rel or "<missing>")
        path=_safe_child(model_root,rel)
        if not path.is_file(): raise OpenDlssNrError("ODNR-STAGE-MISSING",rel)
        size=path.stat().st_size
        if size!=expected_len: raise OpenDlssNrError("ODNR-STAGE-SIZE-MISMATCH",rel)
        if verify_hashes:
            h=hashlib.sha256()
            with path.open("rb") as fh:
                for chunk in iter(lambda:fh.read(1024*1024),b""): h.update(chunk)
            if h.hexdigest()!=expected_sha: raise OpenDlssNrError("ODNR-STAGE-SHA256-MISMATCH",rel)
        checked.append({"file":rel,"bytes":size,"sha256_verified":bool(verify_hashes)})
    return {"provider_id":PROVIDER_ID,"manifest":str(manifest_path),"stage_count":len(checked),"tensor_count":len(tensors),
            "stage_integrity":checked,"model_license_or_output_rights_admitted":False,"model_registry_admission_implied":False}

def native_probe(source_root:Path)->dict[str,Any]:
    source=validate_source_root(source_root); is_windows=platform.system().lower()=="windows"; exe=source_root.resolve()/"build"/"dlss5vk.exe"
    return {**source,"execution_class":"HOST_NATIVE_VULKAN_PTX","platform":platform.system(),
            "upstream_native_platform_compatible":is_windows,"upstream_executable_present":exe.is_file(),
            "gpu_compatibility_discovered_here":False,"hardware_compatibility_source":"FA3_HARDWARE_DISCOVERY_PLUS_HRB_ONLY",
            "native_requirements_provider_scoped":True,"production_ready":False}

def run_parity(*,source_root:Path,model_root:Path,fixture_root:Path,hrb_lease_ref:str,supply_chain_admitted:bool,model_artifact_admitted:bool)->dict[str,Any]:
    if not hrb_lease_ref.strip(): raise OpenDlssNrError("ODNR-HRB-LEASE-MISSING","opaque HRB lease reference required")
    if supply_chain_admitted is not True: raise OpenDlssNrError("ODNR-SUPPLY-CHAIN-NOT-ADMITTED","source admission required")
    if model_artifact_admitted is not True: raise OpenDlssNrError("ODNR-MODEL-NOT-ADMITTED","model artifact admission required")
    probe=native_probe(source_root)
    if not probe["upstream_native_platform_compatible"]: raise OpenDlssNrError("ODNR-NATIVE-PLATFORM-INCOMPATIBLE",probe["platform"])
    if not probe["upstream_executable_present"]: raise OpenDlssNrError("ODNR-EXECUTABLE-MISSING","build/dlss5vk.exe")
    validate_model_manifest(model_root,True)
    if not fixture_root.resolve().is_dir(): raise OpenDlssNrError("ODNR-FIXTURE-MISSING",str(fixture_root))
    command=[str(source_root.resolve()/"build"/"dlss5vk.exe"),"parity","--model",str(model_root.resolve()),"--fixture",str(fixture_root.resolve())]
    proc=subprocess.run(command,text=True,capture_output=True,check=False)
    digest=hashlib.sha256((proc.stdout+"\n"+proc.stderr).encode()).hexdigest()
    result={"provider_id":PROVIDER_ID,"execution_class":"HOST_NATIVE_VULKAN_PTX","command_kind":"upstream-parity",
            "exit_code":proc.returncode,"output_sha256":digest,"hrb_lease_ref":hrb_lease_ref,
            "selected_provider_equal_executed_provider":True,"silent_fallback":False,
            "result":"PASS" if proc.returncode==0 else "BLOCKED"}
    if proc.returncode!=0: raise OpenDlssNrError("ODNR-PARITY-FAILED",json.dumps(result,sort_keys=True))
    return result

def main()->int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("probe"); p.add_argument("--source-root",required=True)
    m=sub.add_parser("verify-model"); m.add_argument("--model-root",required=True)
    args=parser.parse_args()
    try:
        result=native_probe(Path(args.source_root)) if args.command=="probe" else validate_model_manifest(Path(args.model_root),True)
        print(json.dumps(result,indent=2,ensure_ascii=False)); return 0
    except OpenDlssNrError as exc:
        print(json.dumps({"result":"BLOCKED","code":exc.code,"message":str(exc)},indent=2)); return 2

if __name__=="__main__": raise SystemExit(main())
