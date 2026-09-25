#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fa3_provider_runtime import validate_runtime_environment
from fa3_supply_chain_admission import sha256_file

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--plan",required=True)
    p.add_argument("--supply-chain-receipt",required=True)
    p.add_argument("--output",default=".fa3-current-host/runtime/provider-runtime-bound.json")
    a=p.parse_args()
    plan_path=Path(a.plan).resolve();receipt_path=Path(a.supply_chain_receipt).resolve();out=Path(a.output)
    plan=json.loads(plan_path.read_text(encoding="utf-8"))
    receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema")!="fa3.software-supply-chain-receipt.v1" or receipt.get("current_host_execution") is not True or receipt.get("admission",{}).get("result")!="PASS":
        raise SystemExit("SCS receipt is not an admitted current-host receipt")
    bound=json.loads(json.dumps(plan))
    bound.pop("template_only",None)
    bound["supply_chain_receipt_status"]="PASS"
    bound["supply_chain_receipt_sha256"]=sha256_file(receipt_path)
    result=validate_runtime_environment(bound)
    if result["result"]!="PASS":
        raise SystemExit("bound provider runtime plan invalid: "+",".join(result["findings"]))
    if not out.is_absolute():out=Path.cwd()/out
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(bound,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"result":"PASS","output":str(out),"supply_chain_receipt_sha256":bound["supply_chain_receipt_sha256"]},indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
