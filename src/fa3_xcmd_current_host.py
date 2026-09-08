#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-XCMD-001"
CONTRACT_ID = "FA3-XCMD-RUNTIME-ADMISSION-CONTRACTS-001"
CONFORMANCE_ID = "FA3-XCMD-RUNTIME-CONFORMANCE-001"
GATE_ID = "FA3-GATE-XCMD-CURRENT-HOST-001"
DECISION_ID = "FA3-DEC-XCMD-CURRENT-HOST-2026-09-08"
REFERENCE_ID = "FA3-XCMD-RUNTIME-UPSTREAM-REFERENCE-2026-09-08"
CAPABILITY_COUNT = 143
CAPABILITY = "CAP-008"
TAG = "v0.10.0"
COMMIT = "bf3f49aa388f7a1a7bcdcb9e7fd326e0f996b694"
TREE = "0458ecf558690f16bde0c396f322aa9a5658cb14"
PASS_STATUS = "CURRENT_HOST_PRODUCTION_E2E_PASS"
RUNNER_LABELS = {"self-hosted", "linux", "x64", "fa3-current-host"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def static_check(root: Path) -> dict[str, Any]:
    required = {
        "provider": root / "canonical/providers/FA3-PROVIDER-XCMD-001.json",
        "parent_enforcement": root / "canonical/xcmd-enforcement.json",
        "contract": root / "canonical/contracts/FA3-XCMD-RUNTIME-ADMISSION-CONTRACTS-001.json",
        "reference": root / "canonical/references/FA3-XCMD-RUNTIME-UPSTREAM-REFERENCE-2026-09-08.json",
        "conformance": root / "canonical/FA3-XCMD-RUNTIME-CONFORMANCE-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-XCMD-CURRENT-HOST-2026-09-08.json",
        "enforcement": root / "canonical/xcmd-current-host-enforcement.json",
        "gate": root / "canonical/FA3-GATE-XCMD-CURRENT-HOST-001.json",
    }
    findings: list[str] = []
    for name, path in required.items():
        if not path.exists():
            findings.append(f"missing:{name}:{path.relative_to(root)}")
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider = load(required["provider"])
    parent = load(required["parent_enforcement"])
    contract = load(required["contract"])
    reference = load(required["reference"])
    conformance = load(required["conformance"])
    decision = load(required["decision"])
    enforcement = load(required["enforcement"])
    gate = load(required["gate"])

    checks = {
        "provider_non_authoritative": provider.get("architectural_authority") is False and provider.get("new_capability") is False,
        "capability_count": all(x.get("capability_count", x.get("capability_count_after")) == CAPABILITY_COUNT for x in (provider, contract, conformance, enforcement, gate)) and decision.get("capability_count_after") == CAPABILITY_COUNT,
        "provider_pending": provider.get("current_host_activation_status") == "PENDING_REAL_CURRENT_HOST_E2E" and provider.get("current_host_runtime_evidence") == "NOT_CLAIMED",
        "parent_child_gate": GATE_ID in parent.get("child_gates", []),
        "contract_identity": contract.get("id") == CONTRACT_ID and contract.get("capability_projection") == [CAPABILITY],
        "reference_identity": reference.get("id") == REFERENCE_ID and reference.get("latest_stable_release_observed", {}).get("tag") == TAG,
        "reference_commit": reference.get("latest_stable_release_observed", {}).get("commit") == COMMIT and SHA40.fullmatch(COMMIT) is not None,
        "reference_tree": reference.get("latest_stable_release_observed", {}).get("tree") == TREE and SHA40.fullmatch(TREE) is not None,
        "floating_denied": reference.get("fa3_disposition", {}).get("floating_x_allowed_as_runtime_identity") is False,
        "remote_eval_denied": reference.get("fa3_disposition", {}).get("direct_remote_eval_allowed") is False,
        "self_update_denied": reference.get("fa3_disposition", {}).get("self_update_allowed") is False,
        "conformance_pending": conformance.get("status") == "PENDING_REAL_CURRENT_HOST_E2E" and conformance.get("current_host_production_claim") is False,
        "decision_pending": decision.get("status") == "CANONICAL_PENDING_CURRENT_HOST" and decision.get("current_host_production_claim") is False,
        "gate_fail_closed": gate.get("id") == GATE_ID and gate.get("fail_closed") is True,
        "ci_fixture_no_pass": contract.get("evidence", {}).get("ci_fixture_can_claim_current_host_pass") is False,
    }
    for key, ok in checks.items():
        if not ok:
            findings.append(f"check_failed:{key}")
    return {"result": "PASS" if not findings else "FAIL", "checks": checks, "findings": findings}


def receipt_valid(receipt: dict[str, Any], *, require_real_runner: bool = True) -> bool:
    if receipt.get("schema") != "fa3.xcmd-current-host-receipt.v1":
        return False
    if receipt.get("provider_id") != PROVIDER_ID or receipt.get("gate_id") != GATE_ID:
        return False
    if receipt.get("candidate", {}).get("tag") != TAG:
        return False
    if receipt.get("candidate", {}).get("commit") != COMMIT or receipt.get("candidate", {}).get("tree") != TREE:
        return False
    if receipt.get("caller", {}).get("identity") in (None, "") or receipt.get("request_id") in (None, "") or receipt.get("workspace_id") in (None, ""):
        return False
    if receipt.get("capability_scope") != [CAPABILITY]:
        return False
    if receipt.get("policy", {}).get("authorization_authority") != "FA3-AUTH-SECURITY-GOV-001":
        return False
    if receipt.get("policy", {}).get("tool_mediation_authority") != "FA3-AUTH-MCP-GATEWAY-001":
        return False
    if receipt.get("execution", {}).get("root_execution") is not False:
        return False
    if receipt.get("execution", {}).get("direct_remote_eval") is not False:
        return False
    if receipt.get("execution", {}).get("self_update") is not False:
        return False
    if receipt.get("execution", {}).get("host_shell_startup_unchanged") is not True:
        return False
    if receipt.get("execution", {}).get("resident_provider_processes_after") != 0:
        return False
    if receipt.get("source", {}).get("commit_revalidated") is not True or receipt.get("source", {}).get("tree_revalidated") is not True:
        return False
    if receipt.get("ci_fixture") is True and receipt.get("result_status") == PASS_STATUS:
        return False
    if require_real_runner:
        labels = set(receipt.get("runner", {}).get("labels", []))
        if not RUNNER_LABELS.issubset(labels):
            return False
        if receipt.get("ci_fixture") is not False:
            return False
    return receipt.get("result_status") == PASS_STATUS


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["static", "verify"])
    p.add_argument("--root", default=".")
    p.add_argument("--receipt", default="evidence/receipts/xcmd-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    if a.mode == "static":
        out = static_check(root)
    else:
        rp = root / a.receipt
        if not rp.exists():
            out = {"result": "FAIL", "findings": [f"missing_receipt:{a.receipt}"]}
        else:
            r = load(rp)
            out = {"result": "PASS" if receipt_valid(r) else "FAIL", "receipt_status": r.get("result_status")}
    print(json.dumps(out, indent=2))
    return 0 if out["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
