#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from fa3_convertx_adapter import (
    AdmissionDenied,
    ConversionRequest,
    machine_execution_admission,
    validate_current_host_receipt,
    validate_request,
    validate_runtime_contract,
)

PROVIDER_ID = "FA3-PROVIDER-CONVERTX-001"
PROFILE_ID = "FA3-FILE-CONVERSION-001"
TOOLS_ID = "FA3-TOOLS-FABRIC-001"
ALLOWLIST_ID = "FA3-CONVERTX-CONVERSION-ALLOWLIST-001"
CONFORMANCE_ID = "FA3-CONVERTX-RUNTIME-CONFORMANCE-001"
CURRENT_HOST_RECEIPT = Path("evidence/receipts/convertx-current-host.json")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def _expect_denied(fn: Callable[[], Any]) -> bool:
    try:
        fn()
    except AdmissionDenied:
        return True
    return False


def run_regressions() -> dict[str, Any]:
    allowlist = {
        "default_policy": "DENY",
        "candidate_pairs": [
            {"from": "image/png", "to": "image/jpeg", "state": "CANDIDATE"}
        ],
    }
    good = ConversionRequest("in.png", "image/png", "image/jpeg")
    runtime = {
        "non_root": True,
        "read_only_root": True,
        "cap_drop_all": True,
        "no_new_privileges": True,
        "seccomp": True,
        "resource_limits": True,
        "ephemeral_workspace": True,
        "host_mounts": "DENY",
        "outbound_network": "DENY",
        "image": "ghcr.io/c4illin/convertx@sha256:" + "a" * 64,
    }
    provider = {"status": "QUARANTINED", "machine_interface": {"machine_execution_enabled": False}}
    cases: list[tuple[str, bool]] = []
    cases.append(("unknown_pair_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "application/pdf"), allowlist))))
    cases.append(("arbitrary_converter_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "image/jpeg", converter_name="ImageMagick"), allowlist))))
    cases.append(("arbitrary_arguments_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "image/jpeg", provider_arguments=("--danger",)), allowlist))))
    cases.append(("xelatex_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "image/jpeg", converter_name="XeLaTeX"), allowlist))))
    cases.append(("latex_extension_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.tex", "image/png", "image/jpeg"), allowlist))))
    cases.append(("floating_image_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "image": "ghcr.io/c4illin/convertx:latest"}))))
    cases.append(("host_mount_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "host_mounts": ["/home:/home"]}))))
    cases.append(("unrestricted_egress_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "outbound_network": "ALLOW"}))))
    cases.append(("root_runtime_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "non_root": False}))))
    cases.append(("missing_limits_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "resource_limits": False}))))
    cases.append(("quarantined_machine_execution_denied", _expect_denied(lambda: machine_execution_admission(good, provider, allowlist, runtime, None))))
    approved = {"status": "APPROVED", "machine_interface": {"machine_execution_enabled": True}}
    cases.append(("missing_hrb_denied_for_machine_execution", _expect_denied(lambda: machine_execution_admission(good, approved, allowlist, runtime, None))))
    cases.append(("current_host_claim_without_receipt_denied", _expect_denied(lambda: validate_current_host_receipt({"status": "PASS"}))))
    passed = sum(1 for _, ok in cases if ok)
    return {"result": "PASS" if passed == len(cases) else "FAIL", "passed": passed, "total": len(cases), "cases": [{"name": n, "pass": ok} for n, ok in cases]}


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    required = {
        TOOLS_ID: root / "canonical/FA3-TOOLS-FABRIC-001.json",
        PROFILE_ID: root / "canonical/FA3-FILE-CONVERSION-001.json",
        PROVIDER_ID: root / "canonical/FA3-PROVIDER-CONVERTX-001.json",
        ALLOWLIST_ID: root / "canonical/FA3-CONVERTX-CONVERSION-ALLOWLIST-001.json",
        CONFORMANCE_ID: root / "canonical/FA3-CONVERTX-RUNTIME-CONFORMANCE-001.json",
    }
    docs: dict[str, dict[str, Any]] = {}
    for identity, path in required.items():
        if not path.exists():
            findings.append(finding("CONVERTX-MISSING", f"Required artifact missing: {path}"))
            continue
        try:
            docs[identity] = loadj(path)
        except Exception as exc:
            findings.append(finding("CONVERTX-JSON", f"Cannot parse {path}: {exc}"))
            continue
        if docs[identity].get("id") != identity:
            findings.append(finding("CONVERTX-ID", f"Identity mismatch in {path}"))

    tools = docs.get(TOOLS_ID, {})
    profile = docs.get(PROFILE_ID, {})
    provider = docs.get(PROVIDER_ID, {})
    allowlist = docs.get(ALLOWLIST_ID, {})
    conformance = docs.get(CONFORMANCE_ID, {})
    machine = provider.get("machine_interface", {})

    conversion_categories = [row for row in tools.get("categories", []) if row.get("id") == "CONVERSION"]
    if not conversion_categories or conversion_categories[0].get("canonical_execution_profile") != PROFILE_ID:
        findings.append(finding("CONVERTX-TOOLS-ROUTE", "Tools Conversion intent is not bound to the canonical conversion profile"))
    if tools.get("routing_contract", {}).get("direct_provider_bypass") is not False:
        findings.append(finding("CONVERTX-DIRECT-BYPASS", "Tools direct provider bypass must be disabled"))
    if profile.get("fail_closed") is not True or profile.get("request_contract", {}).get("arbitrary_cli_arguments_allowed") is not False:
        findings.append(finding("CONVERTX-PROFILE-POLICY", "Conversion profile is not fail-closed"))
    if profile.get("security", {}).get("xelatex") != "DENY":
        findings.append(finding("CONVERTX-XELATEX", "XeLaTeX must remain denied"))

    provider_status = provider.get("status")
    if provider_status == "QUARANTINED":
        if machine.get("machine_execution_enabled") is not False:
            findings.append(finding("CONVERTX-QUARANTINE-BYPASS", "Quarantined provider cannot enable machine execution"))
        if machine.get("fa3_adapter_execution_contract_materialized") is not False:
            findings.append(finding("CONVERTX-QUARANTINE-ADAPTER-CLAIM", "Quarantined provider must not claim a materialized production execution contract"))
    else:
        receipt_path = root / CURRENT_HOST_RECEIPT
        if machine.get("fa3_adapter_execution_contract_materialized") is not True:
            findings.append(finding("CONVERTX-ADAPTER-CONTRACT", "Promoted ConvertX requires a materialized FA3 execution contract"))
        if machine.get("machine_execution_enabled") is not True:
            findings.append(finding("CONVERTX-MACHINE-DISABLED", "Promoted ConvertX must explicitly enable the governed machine interface"))
        if not receipt_path.exists():
            findings.append(finding("CONVERTX-PROMOTION-EVIDENCE", "Non-quarantined ConvertX requires a real current-host receipt"))
        else:
            try:
                validate_current_host_receipt(loadj(receipt_path))
            except AdmissionDenied as exc:
                findings.append(finding("CONVERTX-PROMOTION-EVIDENCE", str(exc)))

    if machine.get("official_public_api_available") is not False:
        findings.append(finding("CONVERTX-API-CLAIM", "ConvertX must not be represented as having an official public API"))
    if provider.get("upstream", {}).get("production_tag_floating_allowed") is not False:
        findings.append(finding("CONVERTX-FLOATING-TAG", "Floating production tags must be forbidden"))
    if allowlist.get("default_policy") != "DENY" or allowlist.get("arbitrary_converter_arguments_allowed") is not False:
        findings.append(finding("CONVERTX-ALLOWLIST", "ConvertX conversion policy is not deny-by-default"))
    denied = allowlist.get("explicit_denials", [])
    if not any(row.get("converter_family") == "XeLaTeX" for row in denied):
        findings.append(finding("CONVERTX-XELATEX-ALLOWLIST", "XeLaTeX explicit denial is missing"))
    if conformance.get("ci_conformance", {}).get("current_host_claim_forbidden") is not True:
        findings.append(finding("CONVERTX-CI-HOST-CLAIM", "CI must not claim current-host execution"))
    regressions = run_regressions()
    if regressions["result"] != "PASS":
        findings.append(finding("CONVERTX-REGRESSION", "Built-in fail-closed regression set failed"))

    return {
        "result": "PASS" if not findings else "FAIL",
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "provider_status": provider_status or "UNKNOWN",
        "machine_execution_enabled": machine.get("machine_execution_enabled", False),
        "adapter_execution_contract_materialized": machine.get("fa3_adapter_execution_contract_materialized", False),
        "current_host_status": provider.get("current_host_status", "UNKNOWN"),
        "regressions": regressions,
        "findings": findings,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
