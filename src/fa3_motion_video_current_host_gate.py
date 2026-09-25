#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

GATE_ID="FA3-MOTION-VIDEO-CURRENT-HOST-GATESET-001"

def load(path:Path):return json.loads(path.read_text(encoding="utf-8"))

def gate(root:Path,receipt_path:Path)->dict:
    errors=[]
    policy=load(root/"canonical/motion-video-runtime-enforcement.json")
    runtime=load(root/"canonical/FA3-MOTION-VIDEO-RUNTIME-ADMISSION-001.json")
    repl=load(root/"canonical/h3-replacement-enforcement.json")
    if not policy.get("fail_closed"):errors.append("runtime enforcement must fail closed")
    if runtime.get("active") is not True:errors.append("replacement runtime surface must be active")
    if repl.get("mandatory") is not True:errors.append("H3 replacement policy must be mandatory")
    if not receipt_path.is_file():
        errors.append("current-host receipt missing")
        receipt={}
    else:
        receipt=load(receipt_path)
        if receipt.get("schema")!="fa3.motion-video-execution-receipt.v1":errors.append("receipt schema mismatch")
        if receipt.get("status")!="PASS":errors.append("receipt status is not PASS")
        if receipt.get("evidence_scope")!="REAL_PROVIDER_CURRENT_HOST":errors.append("real current-host scope missing")
        if receipt.get("synthetic_or_mock_provider") is not False:errors.append("synthetic/mock provider evidence forbidden")
        if receipt.get("silent_fallback_used") is not False:errors.append("silent fallback detected")
        if receipt.get("raw_secret_present") is not False:errors.append("raw secret leakage detected")
        if not receipt.get("artifact_reference"):errors.append("artifact reference missing")
        if not receipt.get("selection_receipt_sha256"):errors.append("selection binding missing")
        if not receipt.get("provider_manifest_sha256"):errors.append("manifest binding missing")
        if not receipt.get("video_generation_ir_sha256"):errors.append("IR binding missing")
        if receipt.get("execution_topology")=="LOCAL" and receipt.get("requires_accelerator") is True and not receipt.get("hrb_receipt_sha256"):
            errors.append("local accelerator execution lacks HRB binding")
    report={
      "schema":"fa3.motion-video-current-host-gate-report.v1",
      "gate_id":GATE_ID,
      "result":"PASS" if not errors else "FAIL",
      "errors":errors,
      "provider_id":receipt.get("provider_id"),
      "cost_class":receipt.get("cost_class"),
      "transport":receipt.get("transport"),
      "artifact_reference":receipt.get("artifact_reference"),
      "capability_count":143,
      "capability_delta":0,
      "authority_delta":0,
      "global_promotion_claim":False
    }
    out=root/"reports/motion-video-current-host-gate-report.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--receipt",default="evidence/receipts/motion-video-current-host.json")
    args=ap.parse_args(); root=Path(args.root); rp=Path(args.receipt); rp=rp if rp.is_absolute() else root/rp
    report=gate(root,rp); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
