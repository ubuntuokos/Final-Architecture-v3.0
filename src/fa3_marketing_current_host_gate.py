#!/usr/bin/env python3
import argparse, json
from pathlib import Path

REQUIRED_PROVIDERS = {
    "FA3-PROVIDER-MAUTIC-001",
    "FA3-PROVIDER-TWENTY-001",
    "FA3-PROVIDER-LISTMONK-001",
}
REQUIRED_TESTS = {
    "rootless_podman",
    "immutable_image_lock",
    "loopback_only_public_bindings",
    "mautic_health",
    "mautic_hu_locale",
    "mautic_contact_roundtrip",
    "mautic_cron_commands",
    "twenty_health",
    "twenty_hu_signup",
    "twenty_api_key",
    "twenty_person_roundtrip",
    "listmonk_health",
    "listmonk_api_auth",
    "listmonk_hu_locale",
    "listmonk_subscriber_roundtrip",
    "listmonk_smtp_delivery",
    "smtp_egress_sink_only",
}

def evaluate(receipt):
    findings=[]
    if receipt.get("schema")!="fa3.marketing-current-host-evidence.v1":
        findings.append("schema")
    if receipt.get("execution_context")!="CURRENT_HOST_REAL_EXECUTION":
        findings.append("execution_context")
    if set(receipt.get("provider_ids",[]))!=REQUIRED_PROVIDERS:
        findings.append("provider_ids")
    results=receipt.get("tests",{})
    missing=REQUIRED_TESTS-set(results)
    if missing:
        findings.append("missing_tests:"+",".join(sorted(missing)))
    failed=[k for k in REQUIRED_TESTS if results.get(k,{}).get("status")!="PASS"]
    if failed:
        findings.append("failed_tests:"+",".join(sorted(failed)))
    if receipt.get("runtime_status")!="CURRENT_HOST_PRODUCTION_E2E_PASS":
        findings.append("runtime_status")
    if receipt.get("capability_count")!=143 or receipt.get("new_architectural_authorities")!=0:
        findings.append("architecture_invariants")
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",default="evidence/receipts/marketing-current-host.json")
    a=p.parse_args()
    path=Path(a.receipt)
    if not path.exists():
        print(json.dumps({"result":"FAIL","findings":["receipt_missing"]},indent=2))
        return 2
    report=evaluate(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
