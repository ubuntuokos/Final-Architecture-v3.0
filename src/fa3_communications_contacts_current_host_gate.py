#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-GATE-COMMUNICATIONS-CONTACTS-CURRENT-HOST-001"
RECEIPT = "evidence/receipts/communications-contacts-current-host.json"
REQUIRED = {"secret_broker","tls_stack","certificate_validation","network_stack","notification_integration","safe_attachment_pipeline","software_coexistence","hardware_safety","audit_evidence","protocol_adapter_capability"}
AI_REQUIRED = {"ai_policy_gate","model_router","provider_admission","hrb","tool_permission","prompt_injection_gate","context_isolation"}

def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    path = receipt_path or root / RECEIPT
    if not path.is_file():
        return {"schema":"fa3.communications-contacts-current-host-report.v1","gate_id":GATE_ID,"result":"PENDING_CURRENT_HOST","findings":[{"code":"CCCH-001","message":"physical current-host receipt missing"}],"runtime_promotion_claim":False}
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema":"fa3.communications-contacts-current-host-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":[{"code":"CCCH-002","message":str(exc)}],"runtime_promotion_claim":False}
    fs: list[dict[str, Any]] = []
    if receipt.get("physical_host") is not True or receipt.get("simulated") is not False:
        fs.append({"code":"CCCH-003","message":"receipt is not physical/non-simulated"})
    checks = receipt.get("checks", {})
    missing = sorted(x for x in REQUIRED if checks.get(x) is not True)
    if missing:
        fs.append({"code":"CCCH-004","message":"mandatory host checks missing","checks":missing})
    if receipt.get("ai_enabled") is True:
        ai_missing = sorted(x for x in AI_REQUIRED if checks.get(x) is not True)
        if ai_missing:
            fs.append({"code":"CCCH-005","message":"AI current-host checks missing","checks":ai_missing})
    if receipt.get("capability_count") != 175:
        fs.append({"code":"CCCH-006","message":"capability baseline drift"})
    if receipt.get("silent_fallback_observed") is not False:
        fs.append({"code":"CCCH-007","message":"silent fallback not explicitly disproven"})
    return {"schema":"fa3.communications-contacts-current-host-report.v1","gate_id":GATE_ID,"result":"PASS" if not fs else "FAIL","findings":fs,"runtime_promotion_claim":False,"physical_current_host_evidence":not fs}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--receipt")
    args = ap.parse_args()
    report = gate(Path(args.root), Path(args.receipt) if args.receipt else None)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
