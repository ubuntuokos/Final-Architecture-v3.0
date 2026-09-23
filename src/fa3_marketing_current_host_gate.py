#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_PROVIDERS = {
    "FA3-PROVIDER-MAUTIC-001",
    "FA3-PROVIDER-TWENTY-001",
    "FA3-PROVIDER-LISTMONK-001",
}
REQUIRED_LABELS = {"self-hosted", "linux", "x64", "fa3-current-host"}
REQUIRED_TESTS = {
    "rootless_podman",
    "immutable_image_lock",
    "loopback_only_public_bindings",
    "secret_broker_opaque_lease",
    "uaf_no_direct_provider_bypass",
    "decision_receipt_bound_to_candidate_set",
    "mautic_health_and_campaign_projection",
    "twenty_health_and_contact_roundtrip",
    "listmonk_health_and_newsletter_roundtrip",
    "consent_missing_blocks_dispatch",
    "suppression_blocks_dispatch",
    "approval_missing_blocks_launch",
    "smtp_egress_sink_only",
    "delivery_receipt_reconciliation",
    "restart_recovery",
}


def evaluate(receipt: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    if receipt.get("schema") != "fa3.marketing-current-host-evidence.v2":
        findings.append("schema")
    if receipt.get("execution_context") != "CURRENT_HOST_REAL_EXECUTION":
        findings.append("execution_context")
    if receipt.get("evidence_level") != "CURRENT_HOST_PRODUCTION_E2E_PASS":
        findings.append("evidence_level")
    if receipt.get("synthetic") is not False:
        findings.append("synthetic")
    if set(receipt.get("runner_labels", [])) != REQUIRED_LABELS:
        findings.append("runner_labels")
    if set(receipt.get("provider_ids", [])) != REQUIRED_PROVIDERS:
        findings.append("provider_ids")
    tests = receipt.get("tests", {})
    if not isinstance(tests, dict):
        findings.append("tests")
        tests = {}
    missing = REQUIRED_TESTS - set(tests)
    if missing:
        findings.append("missing_tests:" + ",".join(sorted(missing)))
    failed = sorted(name for name in REQUIRED_TESTS if tests.get(name, {}).get("status") != "PASS")
    if failed:
        findings.append("failed_tests:" + ",".join(failed))
    if receipt.get("runtime_status") != "CURRENT_HOST_PRODUCTION_E2E_PASS":
        findings.append("runtime_status")
    if receipt.get("secret_values_collected") is not False:
        findings.append("secret_values_collected")
    if receipt.get("capability_count") != 143 or receipt.get("new_architectural_authorities") != 0:
        findings.append("architecture_invariants")
    if receipt.get("current_host_commit_sha") in (None, "", "UNKNOWN"):
        findings.append("current_host_commit_sha")
    return {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "gate": {"id": "FA3-MARKETING-CURRENT-HOST-GATESET-001", "mode": "CURRENT_HOST_RUNTIME"},
        "result": "PASS" if not findings else "BLOCKED",
        "findings": findings,
        "promotion_effect": "MARKETING_PROVIDER_RUNTIME_ADMITTED" if not findings else "NO_PROMOTION",
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt", default="evidence/receipts/marketing-current-host.json")
    args = parser.parse_args()
    path = Path(args.receipt)
    if not path.is_absolute():
        path = Path(args.root) / path
    if not path.is_file():
        report = {"result": "BLOCKED", "findings": ["receipt_missing"], "global_promotion_claim": False}
    else:
        report = evaluate(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
