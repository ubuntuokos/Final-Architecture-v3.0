#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from typing import Any
from fa3_model_manager_provider_adapter import EVIDENCE_LEVEL,HF_PROVIDER_ID,LM_STUDIO_PROVIDER_ID,OLLAMA_PROVIDER_ID,PROVIDER_IDS,RUNTIME_ID

RECEIPT="evidence/receipts/model-manager-current-host.json"
GATE_ID="FA3-GATE-MODEL-MANAGER-CURRENT-HOST-001"

def loadj(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def digest64(value:Any)->bool: return isinstance(value,str) and re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}",value) is not None

def gate(root:Path)->dict[str,Any]:
    path=root/RECEIPT; fs=[]
    if not path.is_file():
        fs.append(finding("MODEL-MGR-HOST-001","current-host Model Manager provider receipt missing")); receipt={}
    else:
        try: receipt=loadj(path)
        except Exception as exc:
            receipt={}; fs.append(finding("MODEL-MGR-HOST-002","current-host receipt unreadable",error=repr(exc)))
    if receipt:
        if receipt.get("runtime_id")!=RUNTIME_ID or receipt.get("status")!="PASS" or receipt.get("evidence_level")!=EVIDENCE_LEVEL:
            fs.append(finding("MODEL-MGR-HOST-003","combined provider production PASS identity/evidence level missing"))
        policy=receipt.get("execution_policy",{})
        if not (policy.get("local_artifacts_only") is True and policy.get("network_download_or_pull") is False and policy.get("cpu_first") is True and policy.get("accelerator_execution_claimed") is False and policy.get("accelerator_requires_hrb_for_separate_evidence") is True):
            fs.append(finding("MODEL-MGR-HOST-004","current-host execution policy drift"))
        providers=receipt.get("providers",{})
        if set(providers)!=set(PROVIDER_IDS):
            fs.append(finding("MODEL-MGR-HOST-005","provider evidence set incomplete",present=sorted(providers)))
        hf=providers.get(HF_PROVIDER_ID,{})
        if not (hf.get("status")=="PASS" and hf.get("evidence_level")=="CURRENT_HOST_SOURCE_CACHE_E2E_PASS" and re.fullmatch(r"[0-9a-f]{40,64}",str(hf.get("immutable_revision",""))) and digest64(hf.get("cached_file_sha256")) and int(hf.get("cached_file_size",0))>0 and hf.get("network_fetch_performed") is False and hf.get("floating_revision_used") is False):
            fs.append(finding("MODEL-MGR-HOST-006","Hugging Face immutable cache/content evidence incomplete"))
        lm=providers.get(LM_STUDIO_PROVIDER_ID,{})
        lp=lm.get("load_policy",{})
        if not (lm.get("status")=="PASS" and lm.get("evidence_level")=="CURRENT_HOST_RUNTIME_E2E_PASS" and digest64(lm.get("lms_binary_sha256")) and int(lm.get("catalog_count",0))>0 and bool(lm.get("selected_model_key")) and lp.get("local_only") is True and lp.get("gpu_offload")=="off" and int(lm.get("inference_stdout_length",0))>0 and digest64(lm.get("inference_stdout_sha256")) and lm.get("network_model_fetch_performed") is False and lm.get("accelerator_execution_claimed") is False):
            fs.append(finding("MODEL-MGR-HOST-007","LM Studio real CPU-only load/inference evidence incomplete"))
        oll=providers.get(OLLAMA_PROVIDER_ID,{})
        if not (oll.get("status")=="PASS" and oll.get("evidence_level")=="CURRENT_HOST_RUNTIME_E2E_PASS" and digest64(oll.get("ollama_binary_sha256")) and oll.get("bind_host")=="127.0.0.1" and digest64(oll.get("selected_model_digest")) and int(oll.get("generate_response_length",0))>0 and digest64(oll.get("generate_response_sha256")) and int(oll.get("size_vram",-1))==0 and oll.get("network_model_pull_performed") is False and oll.get("accelerator_execution_claimed") is False):
            fs.append(finding("MODEL-MGR-HOST-008","Ollama real loopback CPU-only generation evidence incomplete"))
        if receipt.get("new_capabilities")!=0 or receipt.get("new_architectural_authorities")!=0 or receipt.get("capability_count_after")!=143:
            fs.append(finding("MODEL-MGR-HOST-009","capability/authority invariant drift"))
    report={"schema":"fa3.model-manager-current-host-gate-report.v1","gate_id":GATE_ID,"runtime_id":RUNTIME_ID,"provider_ids":PROVIDER_IDS,"result":"PASS" if not fs else "FAIL","evidence_level":receipt.get("evidence_level") if receipt else None,"findings":fs,"promotion_effect":"PROVIDER_SPECIFIC_CURRENT_HOST_EVIDENCE_ONLY_ACCELERATOR_AND_GLOBAL_PROMOTION_SEPARATE"}
    out=root/"reports/model-manager-current-host-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    report=gate(Path(args.root).resolve())
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
