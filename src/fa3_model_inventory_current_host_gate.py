#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count
from fa3_model_inventory_current_host_adapter import CANONICAL_STORE_ID, CONFORMANCE_ID, EVIDENCE_LEVEL, GATE_ID, PROVIDER_IDS
from fa3_model_manager_provider_adapter import sha256_file

RECEIPT="evidence/receipts/model-inventory-current-host.json"
DECISION_ID="FA3-DEC-MODEL-MANAGER-INVENTORY-CURRENT-HOST-2026-09-05"
ENFORCEMENT_PATH="canonical/model-manager-inventory-current-host-enforcement.json"
CONFORMANCE_PATH="canonical/FA3-MODEL-INVENTORY-CURRENT-HOST-CONFORMANCE-001.json"
CAPABILITY_COUNT=module_active_capability_count(__file__)

def loadj(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding="utf-8"))
def finding(code:str,message:str,**extra:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":message,**extra}
def digest64(v:Any)->bool: return isinstance(v,str) and re.fullmatch(r"[0-9a-f]{64}",v) is not None

def reference_check(root:Path)->dict[str,Any]:
    fs=[]
    paths={
      "conformance":root/CONFORMANCE_PATH,
      "enforcement":root/ENFORCEMENT_PATH,
      "decision":root/"canonical/decisions"/f"{DECISION_ID}.json",
      "contract":root/"canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json",
    }
    for name,path in paths.items():
        if not path.is_file(): fs.append(finding("MODEL-INV-REF-001","required canonical artifact missing",artifact=name,path=str(path.relative_to(root))))
    if fs: return {"result":"FAIL","findings":fs}
    conf,enf,dec,contract=[loadj(paths[k]) for k in ("conformance","enforcement","decision","contract")]
    if not (conf.get("id")==CONFORMANCE_ID and conf.get("provider_ids")==PROVIDER_IDS and conf.get("canonical_store_id")==CANONICAL_STORE_ID and conf.get("required_evidence_level")==EVIDENCE_LEVEL and conf.get("capability_count")==CAPABILITY_COUNT):
        fs.append(finding("MODEL-INV-REF-010","current-host inventory conformance drift"))
    if not (enf.get("gate_id")==GATE_ID and enf.get("provider_ids")==PROVIDER_IDS and enf.get("canonical_store_id")==CANONICAL_STORE_ID and enf.get("fail_closed") is True and enf.get("read_only_required") is True):
        fs.append(finding("MODEL-INV-REF-011","inventory enforcement drift"))
    if not (dec.get("id")==DECISION_ID and dec.get("provider_ids")==PROVIDER_IDS and dec.get("canonical_store_id")==CANONICAL_STORE_ID and dec.get("capability_count_after")==CAPABILITY_COUNT):
        fs.append(finding("MODEL-INV-REF-012","inventory decision drift"))
    if not ("ReadOnlyProviderInventoryScan" in contract.get("contracts",[]) and contract.get("current_host_inventory_contract",{}).get("canonical_artifact_store")):
        fs.append(finding("MODEL-INV-REF-014","Model Manager inventory contract extension missing"))
    return {"result":"PASS" if not fs else "FAIL","findings":fs}

def gate(root:Path)->dict[str,Any]:
    fs=[]; ref=reference_check(root)
    if ref["result"]!="PASS": fs.extend(ref["findings"])
    path=root/RECEIPT; receipt={}
    if not path.is_file(): fs.append(finding("MODEL-INV-HOST-001","current-host cross-provider inventory receipt missing"))
    else:
        try: receipt=loadj(path)
        except Exception as exc: fs.append(finding("MODEL-INV-HOST-002","current-host inventory receipt unreadable",error=repr(exc)))
    if receipt:
        if not (receipt.get("conformance_id")==CONFORMANCE_ID and receipt.get("gate_id")==GATE_ID and receipt.get("status")=="PASS" and receipt.get("evidence_level")==EVIDENCE_LEVEL):
            fs.append(finding("MODEL-INV-HOST-003","receipt identity/evidence level missing"))
        policy=receipt.get("execution_policy",{})
        if not (policy.get("read_only_provider_discovery") is True and policy.get("model_store_mutation") is False and policy.get("network_access") is False and policy.get("canonical_admission") is False and policy.get("absolute_model_store_paths_emitted") is False):
            fs.append(finding("MODEL-INV-HOST-004","read-only execution policy drift"))
        if receipt.get("provider_ids")!=PROVIDER_IDS or receipt.get("canonical_store_id")!=CANONICAL_STORE_ID:
            fs.append(finding("MODEL-INV-HOST-005","inventory source set mismatch"))
        store=receipt.get("canonical_store",{}); rep=store.get("representative",{})
        if not (store.get("status")=="PASS" and int(store.get("entry_count",0))>0 and digest64(store.get("inventory_manifest_sha256")) and int(rep.get("size_bytes",0))>0 and digest64(rep.get("sha256")) and store.get("path_disclosure")=="ABSOLUTE_PATHS_NOT_EMITTED"):
            fs.append(finding("MODEL-INV-HOST-006","canonical model-store read-only evidence incomplete"))
        cross=receipt.get("cross_provider",{}); inv_rel=cross.get("inventory_file"); inv_path=root/str(inv_rel) if isinstance(inv_rel,str) else None
        if not (int(cross.get("available_provider_count",0))>=1 and digest64(cross.get("inventory_snapshot_sha256")) and digest64(cross.get("inventory_file_sha256")) and inv_path is not None and inv_path.is_file() and sha256_file(inv_path)==cross.get("inventory_file_sha256")):
            fs.append(finding("MODEL-INV-HOST-007","cross-provider inventory evidence incomplete"))
        if not (receipt.get("canonical_store_before_after_equal") is True and receipt.get("model_store_mutation_detected") is False and receipt.get("network_access_performed") is False):
            fs.append(finding("MODEL-INV-HOST-008","read-only/no-network proof failed"))
        if receipt.get("new_capabilities")!=0 or receipt.get("new_architectural_authorities")!=0 or receipt.get("capability_count_after")!=CAPABILITY_COUNT:
            fs.append(finding("MODEL-INV-HOST-009","capability/authority invariant drift"))
    report={"schema":"fa3.model-inventory-current-host-gate-report.v2","gate_id":GATE_ID,"conformance_id":CONFORMANCE_ID,"canonical_store_id":CANONICAL_STORE_ID,"provider_ids":PROVIDER_IDS,"result":"PASS" if not fs else "FAIL","reference":ref,"findings":fs,"promotion_effect":"CURRENT_HOST_READ_ONLY_INVENTORY_PASS_DOES_NOT_GRANT_ROUTING_RUNTIME_OR_GLOBAL_PROMOTION"}
    out=root/"reports/model-inventory-current-host-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=ap.parse_args()
    report=gate(Path(args.root).resolve()); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
