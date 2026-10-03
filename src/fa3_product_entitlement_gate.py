#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import json
from pathlib import Path
from fa3_product_entitlement import validate

def gate(root:Path)->dict:
    findings=validate(root)
    return {
      "schema":"fa3.product-entitlement-gate-report.v1",
      "gate_id":"FA3-GATE-PRODUCT-ENTITLEMENT-001",
      "result":"PASS" if not findings else "FAIL",
      "capability_baseline":175,
      "capability_delta":0,
      "authority_delta":0,
      "runtime_promotion_claim":False,
      "findings":findings
    }

def main()->int:
    root=Path(__file__).resolve().parents[1]
    report=gate(root)
    out=root/"reports/product-entitlement-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
