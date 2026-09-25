#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fa3_supply_chain_admission import sha256_file,sha256_tree
from fa3_upstream_patchset import evaluate_patchset

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-repository",required=True)
    p.add_argument("--upstream-commit",required=True)
    p.add_argument("--patched-commit",required=True)
    p.add_argument("--patch-series",required=True)
    p.add_argument("--patched-tree",required=True)
    p.add_argument("--dependency-lock",required=True)
    p.add_argument("--supply-chain-receipt",required=True)
    p.add_argument("--reason",required=True)
    p.add_argument("--review-by",required=True)
    p.add_argument("--upstream-issue-ref",action="append",default=[])
    p.add_argument("--output",required=True)
    a=p.parse_args()
    receipt_path=Path(a.supply_chain_receipt).resolve()
    receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema")!="fa3.software-supply-chain-receipt.v1" or receipt.get("admission",{}).get("result")!="PASS":
        raise SystemExit("PATCHED_VENDOR requires an admitted SoftwareSupplyChainReceipt")
    lic=receipt.get("license",{})
    record={
      "schema":"fa3.upstream-patch-set.v1",
      "disposition":"PATCHED_VENDOR",
      "upstream_repository":a.upstream_repository,
      "upstream_commit":a.upstream_commit,
      "patched_commit":a.patched_commit,
      "patch_series_sha256":sha256_tree(Path(a.patch_series)),
      "patched_tree_sha256":sha256_tree(Path(a.patched_tree)),
      "dependency_lock_sha256":sha256_file(Path(a.dependency_lock)),
      "reason":a.reason,
      "upstream_issue_refs":list(a.upstream_issue_ref),
      "security_disposition":"PASS",
      "supply_chain_receipt_status":"PASS",
      "supply_chain_receipt_sha256":sha256_file(receipt_path),
      "review_by":a.review_by,
      "license_disposition":{
        "commercial_compatible":lic.get("commercial_compatible") is True,
        "redistribution_compatible":lic.get("redistribution_compatible") is True,
        "conflicts":list(lic.get("conflicts",[])),
        "declared_expression":lic.get("declared_expression"),
        "detected_expressions":lic.get("detected_expressions",[])
      }
    }
    result=evaluate_patchset(record)
    record["evaluation"]=result
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(record,indent=2,ensure_ascii=False))
    return 0 if result["result"]=="PASS" and result["runtime_admitted"] and result["distribution_admitted"] else 2
if __name__=="__main__":raise SystemExit(main())
