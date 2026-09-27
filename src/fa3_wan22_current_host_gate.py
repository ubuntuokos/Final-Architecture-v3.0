#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN="1ea34ff48f87168174e12956e200b1d908b1c5ff"
PROVIDER="FA3-PROVIDER-WAN22-001"

def load(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def gate(root:Path, motion_receipt:Path, admission_receipt:Path)->dict:
    errors=[]
    if not admission_receipt.is_file():
        errors.append("Wan2.2 provider admission receipt missing"); adm={}
    else:
        adm=load(admission_receipt)
        if adm.get("schema")!="fa3.wan22-provider-admission-receipt.v1":errors.append("Wan2.2 admission schema mismatch")
        if adm.get("provider_id")!=PROVIDER or adm.get("status")!="PASS":errors.append("Wan2.2 provider admission not PASS")
        if adm.get("source_revision")!=PIN:errors.append("Wan2.2 source revision mismatch")
        if adm.get("license_decision")!="ALLOW":errors.append("Wan2.2 license decision not ALLOW")
        if adm.get("network_fetch_performed") is not False or adm.get("auto_install_performed") is not False:errors.append("Wan2.2 admission performed install/network fetch")
        if adm.get("current_host_runtime_execution_claim") is not False:errors.append("Wan2.2 admission incorrectly claims runtime execution")
    if not motion_receipt.is_file():
        errors.append("motion/video current-host receipt missing"); rec={}
    else:
        rec=load(motion_receipt)
        if rec.get("schema")!="fa3.motion-video-execution-receipt.v1" or rec.get("status")!="PASS":errors.append("motion/video receipt not PASS")
        if rec.get("provider_id")!=PROVIDER:errors.append("motion/video receipt provider is not Wan2.2")
        if rec.get("evidence_scope")!="REAL_PROVIDER_CURRENT_HOST":errors.append("real current-host evidence scope missing")
        if rec.get("synthetic_or_mock_provider") is not False:errors.append("synthetic/mock provider forbidden")
        if rec.get("cost_class")!="FREE_LOCAL":errors.append("Wan2.2 current-host path must be FREE_LOCAL")
        if rec.get("execution_topology")!="LOCAL":errors.append("Wan2.2 current-host path must be LOCAL")
        if rec.get("requires_accelerator") is not True:errors.append("Wan2.2 admitted current-host workload must be accelerator-bound")
        if not rec.get("hrb_receipt_sha256"):errors.append("Wan2.2 execution lacks HRB binding")
        native=rec.get("provider_native_result",{})
        if native.get("source_revision")!=PIN:errors.append("Wan2.2 native source revision mismatch")
        if native.get("network_model_fetch_performed") is not False:errors.append("Wan2.2 runtime performed network model fetch")
        if native.get("runtime_ordinal_is_identity") is not False:errors.append("runtime ordinal became canonical identity")
        if not rec.get("artifact_reference") or not rec.get("artifact_sha256"):errors.append("real video artifact identity missing")
    report={
      "schema":"fa3.wan22-current-host-gate-report.v1",
      "gate_id":"FA3-WAN22-CURRENT-HOST-GATESET-001",
      "result":"PASS" if not errors else "FAIL",
      "errors":errors,
      "provider_id":PROVIDER,
      "source_revision":PIN,
      "capability_count":143,
      "capability_delta":0,
      "authority_delta":0,
      "provider_current_host_e2e_claim":not errors,
      "global_promotion_claim":False
    }
    out=root/"reports/wan22-current-host-gate-report.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(ROOT));ap.add_argument("--motion-receipt",default="evidence/receipts/motion-video-current-host.json");ap.add_argument("--admission-receipt",default="evidence/receipts/wan22-provider-admission.json")
    a=ap.parse_args();root=Path(a.root).resolve();mr=Path(a.motion_receipt);ar=Path(a.admission_receipt);mr=mr if mr.is_absolute() else root/mr;ar=ar if ar.is_absolute() else root/ar
    r=gate(root,mr,ar);print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
