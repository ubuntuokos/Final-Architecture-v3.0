#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from typing import Any
from fa3_opendlss_nr_provider import PROVIDER_ID, OpenDlssNrError, run_parity

GATE_ID="FA3-NEURAL-RENDERING-CURRENT-HOST-GATESET-001"

def _receipt_admitted(path:str,label:str)->dict[str,Any]:
    p=Path(path)
    if not p.is_file(): raise OpenDlssNrError("ODNR-RECEIPT-MISSING",f"{label}: {p}")
    value=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(value,dict) or value.get("admitted") is not True: raise OpenDlssNrError("ODNR-RECEIPT-NOT-ADMITTED",label)
    return value

def gate(root:Path,provider_id:str="")->dict[str,Any]:
    provider_id=provider_id.strip()
    if not provider_id:
        return {"schema_id":"FA3-ENFORCEMENT-RESULT-001","schema_version":"1.0.0","gate":{"id":GATE_ID,"mode":"CURRENT_HOST_OPTIONAL_PROVIDER_NEGATIVE_PATH"},
                "result":"PASS","decision":{"reason_code":"OPTIONAL_PROVIDER_NOT_REQUESTED","promotion_effect":"NO_PROVIDER_RUNTIME_PROMOTION","exit_code":0},
                "provider_id":PROVIDER_ID,"provider_e2e_claim":False,"production_provider_admission":False,"global_promotion_claim":False}
    if provider_id!=PROVIDER_ID:
        return {"schema_id":"FA3-ENFORCEMENT-RESULT-001","schema_version":"1.0.0","gate":{"id":GATE_ID,"mode":"CURRENT_HOST_PROVIDER_E2E"},
                "result":"BLOCKED","decision":{"reason_code":"REQUESTED_PROVIDER_UNKNOWN","promotion_effect":"NONE","exit_code":2},
                "provider_id":provider_id,"provider_e2e_claim":False,"production_provider_admission":False,"global_promotion_claim":False}
    envs={"source_root":"FA3_NRENDER_SOURCE_ROOT","model_root":"FA3_NRENDER_MODEL_ROOT","fixture_root":"FA3_NRENDER_FIXTURE_ROOT",
          "hrb_receipt":"FA3_NRENDER_HRB_LEASE_RECEIPT","supply_receipt":"FA3_NRENDER_SUPPLY_CHAIN_RECEIPT","model_receipt":"FA3_NRENDER_MODEL_ADMISSION_RECEIPT"}
    values={k:os.environ.get(v,"").strip() for k,v in envs.items()}; missing=[envs[k] for k,v in values.items() if not v]
    if missing:
        return {"schema_id":"FA3-ENFORCEMENT-RESULT-001","schema_version":"1.0.0","gate":{"id":GATE_ID,"mode":"CURRENT_HOST_PROVIDER_E2E"},
                "result":"BLOCKED","decision":{"reason_code":"REQUIRED_CURRENT_HOST_INPUT_MISSING","promotion_effect":"NONE","exit_code":2},
                "missing":missing,"provider_id":PROVIDER_ID,"provider_e2e_claim":False,"production_provider_admission":False,"global_promotion_claim":False}
    try:
        hrb=_receipt_admitted(values["hrb_receipt"],"HRB"); _receipt_admitted(values["supply_receipt"],"supply-chain"); _receipt_admitted(values["model_receipt"],"model-artifact")
        lease_ref=str(hrb.get("lease_ref") or hrb.get("lease_id") or "").strip()
        if not lease_ref: raise OpenDlssNrError("ODNR-HRB-LEASE-MISSING","admitted HRB receipt lacks lease_ref/lease_id")
        parity=run_parity(source_root=Path(values["source_root"]),model_root=Path(values["model_root"]),fixture_root=Path(values["fixture_root"]),
                          hrb_lease_ref=lease_ref,supply_chain_admitted=True,model_artifact_admitted=True)
        return {"schema_id":"FA3-ENFORCEMENT-RESULT-001","schema_version":"1.0.0","gate":{"id":GATE_ID,"mode":"CURRENT_HOST_PROVIDER_E2E"},
                "result":"PASS","decision":{"reason_code":"PROVIDER_CURRENT_HOST_PARITY_E2E_PASS","promotion_effect":"CANDIDATE_EVIDENCE_ONLY_REQUIRES_SEPARATE_CANONICAL_PROMOTION","exit_code":0},
                "provider_id":PROVIDER_ID,"provider_e2e_claim":True,"production_provider_admission":False,"parity":parity,"global_promotion_claim":False}
    except (OpenDlssNrError,json.JSONDecodeError) as exc:
        return {"schema_id":"FA3-ENFORCEMENT-RESULT-001","schema_version":"1.0.0","gate":{"id":GATE_ID,"mode":"CURRENT_HOST_PROVIDER_E2E"},
                "result":"BLOCKED","decision":{"reason_code":getattr(exc,"code","INVALID_RECEIPT"),"promotion_effect":"NONE","exit_code":2},
                "message":str(exc),"provider_id":PROVIDER_ID,"provider_e2e_claim":False,"production_provider_admission":False,"global_promotion_claim":False}

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--provider-id",default=os.environ.get("FA3_NEURAL_RENDERING_REQUEST_PROVIDER",""))
    parser.add_argument("--output",default="reports/neural-rendering-current-host-report.json"); args=parser.parse_args()
    report=gate(Path(args.root),args.provider_id); out=Path(args.root).resolve()/args.output; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2,ensure_ascii=False))
    return int(report["decision"]["exit_code"])
if __name__=="__main__": raise SystemExit(main())
