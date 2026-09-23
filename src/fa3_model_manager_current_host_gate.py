#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from typing import Any
from fa3_model_manager_provider_adapter import EVIDENCE_LEVEL,HF_PROVIDER_ID,LM_STUDIO_PROVIDER_ID,OLLAMA_PROVIDER_ID,PROVIDER_IDS,RUNTIME_ID

RECEIPT="evidence/receipts/model-manager-current-host.json"
GATE_ID="FA3-GATE-MODEL-MANAGER-CURRENT-HOST-001"
SERVING_PROVIDER_IDS={LM_STUDIO_PROVIDER_ID,OLLAMA_PROVIDER_ID}

def loadj(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def digest64(value:Any)->bool: return isinstance(value,str) and re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}",value) is not None

def validate_hf(item:dict[str,Any])->bool:
    return (
        item.get("status")=="PASS"
        and item.get("evidence_level")=="CURRENT_HOST_SOURCE_CACHE_E2E_PASS"
        and re.fullmatch(r"[0-9a-f]{40,64}",str(item.get("immutable_revision",""))) is not None
        and digest64(item.get("cached_file_sha256"))
        and int(item.get("cached_file_size",0))>0
        and item.get("network_fetch_performed") is False
        and item.get("floating_revision_used") is False
    )

def validate_lm(item:dict[str,Any])->bool:
    lp=item.get("load_policy",{})
    return (
        item.get("status")=="PASS"
        and item.get("evidence_level")=="CURRENT_HOST_RUNTIME_E2E_PASS"
        and digest64(item.get("lms_binary_sha256"))
        and int(item.get("catalog_count",0))>0
        and bool(item.get("selected_model_key"))
        and lp.get("local_only") is True
        and lp.get("gpu_offload")=="off"
        and int(item.get("inference_stdout_length",0))>0
        and digest64(item.get("inference_stdout_sha256"))
        and item.get("network_model_fetch_performed") is False
        and item.get("accelerator_execution_claimed") is False
    )

def validate_ollama(item:dict[str,Any])->bool:
    return (
        item.get("status")=="PASS"
        and item.get("evidence_level")=="CURRENT_HOST_RUNTIME_E2E_PASS"
        and digest64(item.get("ollama_binary_sha256"))
        and item.get("bind_host")=="127.0.0.1"
        and digest64(item.get("selected_model_digest"))
        and int(item.get("generate_response_length",0))>0
        and digest64(item.get("generate_response_sha256"))
        and int(item.get("size_vram",-1))==0
        and item.get("network_model_pull_performed") is False
        and item.get("accelerator_execution_claimed") is False
    )

def valid_unavailable(item:dict[str,Any],provider_id:str)->bool:
    return (
        item.get("provider_id")==provider_id
        and item.get("status")=="UNAVAILABLE_OR_FAILED"
        and item.get("evidence_level")=="CURRENT_HOST_PROVIDER_NOT_ADMITTED"
        and item.get("production_admission_claim") is False
        and digest64(item.get("error_fingerprint_sha256"))
        and bool(item.get("error_type"))
    )

def gate(root:Path)->dict[str,Any]:
    path=root/RECEIPT; fs=[]
    if not path.is_file():
        fs.append(finding("MODEL-MGR-HOST-001","current-host Model Manager provider receipt missing")); receipt={}
    else:
        try: receipt=loadj(path)
        except Exception as exc:
            receipt={}; fs.append(finding("MODEL-MGR-HOST-002","current-host receipt unreadable",error=repr(exc)))
    if receipt:
        if receipt.get("schema")!="fa3.model-manager-current-host-receipt.v2" or receipt.get("runtime_id")!=RUNTIME_ID:
            fs.append(finding("MODEL-MGR-HOST-003","provider receipt identity/schema mismatch"))
        policy=receipt.get("execution_policy",{})
        if not (
            policy.get("local_artifacts_only") is True
            and policy.get("network_download_or_pull") is False
            and policy.get("cpu_first") is True
            and policy.get("accelerator_execution_claimed") is False
            and policy.get("accelerator_requires_hrb_for_separate_evidence") is True
            and policy.get("optional_provider_absence_blocks_other_provider_admission") is False
        ):
            fs.append(finding("MODEL-MGR-HOST-004","current-host execution policy drift"))

        providers=receipt.get("providers",{})
        if set(providers)!=set(PROVIDER_IDS):
            fs.append(finding("MODEL-MGR-HOST-005","provider observation set incomplete",present=sorted(providers)))

        validators={
            HF_PROVIDER_ID:validate_hf,
            LM_STUDIO_PROVIDER_ID:validate_lm,
            OLLAMA_PROVIDER_ID:validate_ollama,
        }
        admitted=[]
        for provider_id in PROVIDER_IDS:
            item=providers.get(provider_id,{})
            if item.get("status")=="PASS":
                if not validators[provider_id](item):
                    fs.append(finding("MODEL-MGR-HOST-006","provider claims PASS without complete provider-specific evidence",provider_id=provider_id))
                else:
                    admitted.append(provider_id)
            elif not valid_unavailable(item,provider_id):
                fs.append(finding("MODEL-MGR-HOST-007","provider non-PASS state is not explicit fail-closed evidence",provider_id=provider_id))

        serving=sorted(SERVING_PROVIDER_IDS.intersection(admitted))
        if receipt.get("status")=="PASS":
            if receipt.get("evidence_level")!=EVIDENCE_LEVEL:
                fs.append(finding("MODEL-MGR-HOST-008","overall PASS evidence level mismatch"))
            if not serving:
                fs.append(finding("MODEL-MGR-HOST-009","overall PASS requires at least one real local serving runtime"))
        else:
            fs.append(finding("MODEL-MGR-HOST-010","current-host Model Manager has no admitted local serving runtime"))

        if sorted(receipt.get("admitted_provider_ids",[]))!=sorted(admitted):
            fs.append(finding("MODEL-MGR-HOST-011","admitted_provider_ids do not match validated provider evidence"))
        if sorted(receipt.get("serving_provider_ids",[]))!=serving:
            fs.append(finding("MODEL-MGR-HOST-012","serving_provider_ids do not match validated serving evidence"))
        unavailable=sorted(pid for pid in PROVIDER_IDS if pid not in admitted)
        if sorted(receipt.get("unavailable_provider_ids",[]))!=unavailable:
            fs.append(finding("MODEL-MGR-HOST-013","unavailable_provider_ids mismatch"))
        expected_coverage="COMPLETE" if not unavailable else "PARTIAL"
        if receipt.get("provider_coverage")!=expected_coverage:
            fs.append(finding("MODEL-MGR-HOST-014","provider coverage classification mismatch"))
        if receipt.get("combined_pass_semantics")!="AT_LEAST_ONE_REAL_LOCAL_SERVING_RUNTIME_PASS":
            fs.append(finding("MODEL-MGR-HOST-015","combined PASS semantics are not provider-neutral"))
        if receipt.get("new_capabilities")!=0 or receipt.get("new_architectural_authorities")!=0 or receipt.get("capability_count_after")!=143:
            fs.append(finding("MODEL-MGR-HOST-016","capability/authority invariant drift"))

    report={
        "schema":"fa3.model-manager-current-host-gate-report.v2",
        "gate_id":GATE_ID,
        "runtime_id":RUNTIME_ID,
        "provider_ids":PROVIDER_IDS,
        "serving_provider_ids":sorted(SERVING_PROVIDER_IDS),
        "result":"PASS" if not fs else "FAIL",
        "evidence_level":receipt.get("evidence_level") if receipt else None,
        "findings":fs,
        "promotion_effect":"PER_PROVIDER_CURRENT_HOST_EVIDENCE_ONLY_OPTIONAL_PROVIDER_ABSENCE_DOES_NOT_BLOCK_OTHER_ADMITTED_PROVIDERS",
    }
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
