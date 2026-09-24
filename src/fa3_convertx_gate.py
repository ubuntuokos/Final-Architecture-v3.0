#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from fa3_convertx_adapter import (
    AdmissionDenied,
    ConversionRequest,
    candidate_validation_admission,
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
CONTRACT_ID = "FA3-CONVERTX-ADAPTER-CONTRACTS-001"
ASSESSMENT_ID = "FA3-TOOLS-FILE-CONVERSION-DECISION-ASSESSMENT-2026-09-24"
ACTION_IDS = {"file.convert.plan", "file.convert.execute", "file.convert.inspect"}
CURRENT_HOST_RECEIPT = Path("evidence/receipts/convertx-current-host.json")
EXECUTOR_PATH = Path("src/fa3_convertx_v018_http.py")


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
    candidate_allowlist = {
        "default_policy": "DENY",
        "candidate_pairs": [{
            "from": "image/png", "to": "image/jpeg", "state": "CANDIDATE",
            "provider_converter": "vips", "provider_target": "jpeg",
        }],
    }
    active_allowlist = {
        "default_policy": "DENY",
        "candidate_pairs": [{
            "from": "image/png", "to": "image/jpeg", "state": "ACTIVE",
            "provider_converter": "vips", "provider_target": "jpeg",
        }],
    }
    good = ConversionRequest(
        "in.png", "image/png", "image/jpeg",
        resource_admission_path="resource-admission.json",
    )
    runtime = {
        "non_root": True, "read_only_root": True, "cap_drop_all": True,
        "no_new_privileges": True, "seccomp": True, "resource_limits": True,
        "ephemeral_workspace": True, "host_mounts": "DENY",
        "outbound_network": "DENY",
        "image": "ghcr.io/c4illin/convertx@sha256:" + "a" * 64,
    }
    quarantined = {
        "status": "QUARANTINED",
        "machine_interface": {
            "machine_execution_enabled": False,
            "fa3_adapter_execution_contract_materialized": True,
            "fa3_candidate_executor_materialized": True,
            "candidate_validation_allowed_while_quarantined": True,
            "candidate_validation_is_production_routing": False,
        },
    }
    approved = {
        "status": "APPROVED",
        "machine_interface": {
            "machine_execution_enabled": True,
            "fa3_adapter_execution_contract_materialized": True,
            "fa3_candidate_executor_materialized": True,
        },
    }
    cases: list[tuple[str, bool]] = []
    cases.append(("unknown_pair_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "application/pdf"), candidate_allowlist))))
    cases.append(("arbitrary_converter_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "image/jpeg", converter_name="ImageMagick"), candidate_allowlist))))
    cases.append(("arbitrary_arguments_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "image/jpeg", provider_arguments=("--danger",)), candidate_allowlist))))
    cases.append(("xelatex_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.png", "image/png", "image/jpeg", converter_name="XeLaTeX"), candidate_allowlist))))
    cases.append(("latex_extension_denied", _expect_denied(lambda: validate_request(ConversionRequest("a.tex", "image/png", "image/jpeg"), candidate_allowlist))))
    cases.append(("floating_image_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "image": "ghcr.io/c4illin/convertx:latest"}))))
    cases.append(("host_mount_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "host_mounts": ["/home:/home"]}))))
    cases.append(("unrestricted_egress_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "outbound_network": "ALLOW"}))))
    cases.append(("root_runtime_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "non_root": False}))))
    cases.append(("missing_limits_denied", _expect_denied(lambda: validate_runtime_contract({**runtime, "resource_limits": False}))))
    cases.append(("candidate_validation_requires_explicit_intent", _expect_denied(lambda: candidate_validation_admission(good, quarantined, candidate_allowlist, runtime, explicit=False, resource_admission_verified=True))))
    cases.append(("unverified_resource_admission_denied", _expect_denied(lambda: candidate_validation_admission(good, quarantined, candidate_allowlist, runtime, explicit=True, resource_admission_verified=False))))
    cases.append(("candidate_validation_allowed_before_promotion", candidate_validation_admission(good, quarantined, candidate_allowlist, runtime, explicit=True, resource_admission_verified=True)["result"] == "ALLOW_CANDIDATE_VALIDATION"))
    cases.append(("candidate_pair_denied_for_production", _expect_denied(lambda: machine_execution_admission(good, approved, candidate_allowlist, runtime, {}, resource_admission_verified=True))))
    no_resource = ConversionRequest("in.png", "image/png", "image/jpeg")
    cases.append(("missing_resource_admission_denied_for_machine_execution", _expect_denied(lambda: machine_execution_admission(no_resource, approved, active_allowlist, runtime, None, resource_admission_verified=True))))
    cases.append(("current_host_claim_without_receipt_denied", _expect_denied(lambda: validate_current_host_receipt({"status": "PASS"}))))
    passed = sum(1 for _, ok in cases if ok)
    return {
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed, "total": len(cases),
        "cases": [{"name": n, "pass": ok} for n, ok in cases],
    }


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    required = {
        TOOLS_ID: root / "canonical/FA3-TOOLS-FABRIC-001.json",
        PROFILE_ID: root / "canonical/FA3-FILE-CONVERSION-001.json",
        PROVIDER_ID: root / "canonical/FA3-PROVIDER-CONVERTX-001.json",
        ALLOWLIST_ID: root / "canonical/FA3-CONVERTX-CONVERSION-ALLOWLIST-001.json",
        CONFORMANCE_ID: root / "canonical/FA3-CONVERTX-RUNTIME-CONFORMANCE-001.json",
        CONTRACT_ID: root / "canonical/contracts/FA3-CONVERTX-ADAPTER-CONTRACTS-001.json",
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
    contract = docs.get(CONTRACT_ID, {})
    machine = provider.get("machine_interface", {})

    conversion_categories = [row for row in tools.get("categories", []) if row.get("id") == "CONVERSION"]
    if not conversion_categories or conversion_categories[0].get("canonical_execution_profile") != PROFILE_ID:
        findings.append(finding("CONVERTX-TOOLS-ROUTE", "Tools Conversion intent is not bound to the canonical conversion profile"))
    routing = tools.get("routing_contract", {})
    if routing.get("direct_provider_bypass") is not False or routing.get("execution_fabric") != "FA3-UNIFIED-ACTION-FABRIC-001":
        findings.append(finding("CONVERTX-UAF-BOUNDARY", "Tools must enter conversion execution through UAF without direct provider bypass"))
    if tools.get("gui_contract", {}).get("route_id") != "create.tools" or tools.get("gui_contract", {}).get("direct_execution") is not False:
        findings.append(finding("CONVERTX-GUI-BOUNDARY", "Tools GUI must be a semantic-route draft-only non-execution surface"))

    if profile.get("fail_closed") is not True or profile.get("request_contract", {}).get("arbitrary_cli_arguments_allowed") is not False:
        findings.append(finding("CONVERTX-PROFILE-POLICY", "Conversion profile is not fail-closed"))
    if profile.get("security", {}).get("xelatex") != "DENY":
        findings.append(finding("CONVERTX-XELATEX", "XeLaTeX must remain denied"))
    if profile.get("execution_fabric") != "FA3-UNIFIED-ACTION-FABRIC-001" or not ACTION_IDS.issubset(set(profile.get("uaf_actions", []))):
        findings.append(finding("CONVERTX-PROFILE-UAF", "Conversion profile UAF action surface is incomplete"))
    if profile.get("routing", {}).get("policy") != "SPECIALIZED_PROVIDER_FIRST" or profile.get("decision_fabric", {}).get("provider_selection_authority") is not False:
        findings.append(finding("CONVERTX-ROUTING-AUTHORITY", "Provider selection must remain deterministic specialized-provider-first, not Decision Fabric authority"))

    if contract.get("upstream_reference", {}).get("release") != "v0.18.0":
        findings.append(finding("CONVERTX-CONTRACT-VERSION", "Adapter contract must remain pinned to upstream v0.18.0"))
    if contract.get("scope") != "CANDIDATE_VALIDATION_ONLY" or contract.get("production_routing") is not False:
        findings.append(finding("CONVERTX-CONTRACT-SCOPE", "v0.18.0 internal web-flow contract must remain candidate-only"))
    if contract.get("endpoint_policy", {}).get("base_url") != "LOOPBACK_ONLY":
        findings.append(finding("CONVERTX-CONTRACT-LOOPBACK", "ConvertX adapter contract must be loopback-only"))
    if contract.get("execution_boundary", {}).get("fabric") != "FA3-UNIFIED-ACTION-FABRIC-001" or contract.get("execution_boundary", {}).get("direct_agent_provider_bypass") is not False:
        findings.append(finding("CONVERTX-CONTRACT-UAF", "ConvertX adapter contract must remain behind UAF"))
    if not (root / EXECUTOR_PATH).exists():
        findings.append(finding("CONVERTX-EXECUTOR-MISSING", f"Candidate executor missing: {EXECUTOR_PATH}"))

    provider_status = provider.get("status")
    if provider_status == "QUARANTINED":
        if machine.get("machine_execution_enabled") is not False:
            findings.append(finding("CONVERTX-QUARANTINE-BYPASS", "Quarantined provider cannot enable production machine execution"))
        if machine.get("candidate_validation_allowed_while_quarantined") is not True:
            findings.append(finding("CONVERTX-CANDIDATE-VALIDATION", "Quarantined provider must expose an explicit candidate-validation path"))
        if machine.get("candidate_validation_is_production_routing") is not False:
            findings.append(finding("CONVERTX-CANDIDATE-PRODUCTION-BYPASS", "Candidate validation must not be production routing"))
        if machine.get("fa3_adapter_execution_contract_materialized") is not True or machine.get("fa3_candidate_executor_materialized") is not True:
            findings.append(finding("CONVERTX-CANDIDATE-MATERIALIZATION", "Candidate provider requires the pinned FA3 adapter and executor"))
    else:
        receipt_path = root / CURRENT_HOST_RECEIPT
        if machine.get("machine_execution_enabled") is not True:
            findings.append(finding("CONVERTX-MACHINE-DISABLED", "Promoted ConvertX must explicitly enable the governed machine interface"))
        if not receipt_path.exists():
            findings.append(finding("CONVERTX-PROMOTION-EVIDENCE", "Non-quarantined ConvertX requires a real current-host receipt"))
        else:
            try:
                validate_current_host_receipt(loadj(receipt_path))
            except AdmissionDenied as exc:
                findings.append(finding("CONVERTX-PROMOTION-EVIDENCE", str(exc)))

    if provider.get("distribution_class") != "USER_LOCAL_EXTERNAL" or provider.get("product_bundle_allowed") is not False:
        findings.append(finding("CONVERTX-DISTRIBUTION", "ConvertX must remain user-local external and excluded from the FA3 product bundle"))
    if provider.get("execution_boundary", {}).get("direct_gui_provider_bypass") is not False:
        findings.append(finding("CONVERTX-PROVIDER-UAF", "ConvertX provider cannot be directly invoked by GUI"))
    if provider.get("upstream", {}).get("production_tag_floating_allowed") is not False:
        findings.append(finding("CONVERTX-FLOATING-TAG", "Floating production tags must be forbidden"))
    if machine.get("official_public_api_available") is not False:
        findings.append(finding("CONVERTX-API-CLAIM", "ConvertX must not be represented as having an official public API"))

    if allowlist.get("default_policy") != "DENY" or allowlist.get("arbitrary_converter_arguments_allowed") is not False:
        findings.append(finding("CONVERTX-ALLOWLIST", "ConvertX conversion policy is not deny-by-default"))
    for row in allowlist.get("candidate_pairs", []):
        if row.get("state") not in {"CANDIDATE", "ACTIVE"} or not row.get("provider_converter") or not row.get("provider_target"):
            findings.append(finding("CONVERTX-PAIR-MAPPING", "Every ConvertX pair needs an explicit state and deterministic provider mapping"))
            break
    if not any(row.get("converter_family") == "XeLaTeX" for row in allowlist.get("explicit_denials", [])):
        findings.append(finding("CONVERTX-XELATEX-ALLOWLIST", "XeLaTeX explicit denial is missing"))

    resource = conformance.get("resource_admission", {})
    if conformance.get("ci_conformance", {}).get("current_host_claim_forbidden") is not True:
        findings.append(finding("CONVERTX-CI-HOST-CLAIM", "CI must not claim current-host execution"))
    if resource.get("current_authoritative_cpu_memory_verifier") != "HRB_NON_ACCELERATOR_AUTHORIZATION_UNMATERIALIZED":
        findings.append(finding("CONVERTX-RESOURCE-ADMISSION", "Current non-accelerator CPU/memory HRB blocker must remain explicit"))
    if resource.get("existing_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        findings.append(finding("CONVERTX-RESOURCE-AUTHORITY", "ConvertX must not create a parallel resource authority"))

    assessment_path = root / "canonical/assessments/FA3-TOOLS-FILE-CONVERSION-DECISION-ASSESSMENT-2026-09-24.json"
    if not assessment_path.is_file():
        findings.append(finding("CONVERTX-DECISION-ASSESSMENT", "Decision Fabric applicability assessment missing"))
    else:
        assessment = loadj(assessment_path)
        if assessment.get("assessment") != "OPTIONAL" or assessment.get("project_radar_checked") is not True:
            findings.append(finding("CONVERTX-DECISION-ASSESSMENT", "Decision Fabric assessment boundary invalid"))
        if not {TOOLS_ID, PROFILE_ID, PROVIDER_ID}.issubset(set(assessment.get("covered_ids", []))):
            findings.append(finding("CONVERTX-DECISION-COVERAGE", "Decision Fabric assessment does not cover Tools/File Conversion/ConvertX"))

    dist_path = root / "canonical/distribution-registry.json"
    if not dist_path.is_file():
        findings.append(finding("CONVERTX-DISTRIBUTION-REGISTRY", "Distribution registry missing"))
    else:
        matches = [row for row in loadj(dist_path).get("records", []) if row.get("subject_id") == PROVIDER_ID]
        if len(matches) != 1 or matches[0].get("class") != "USER_LOCAL_EXTERNAL" or matches[0].get("release_bundle_status") != "EXCLUDED":
            findings.append(finding("CONVERTX-DISTRIBUTION-REGISTRY", "ConvertX distribution registry entry invalid"))

    gui_path = root / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json"
    if not gui_path.is_file():
        findings.append(finding("CONVERTX-GUI-REGISTRY", "GUI surface registry missing"))
    else:
        routes = [row for row in loadj(gui_path).get("surfaces", []) if row.get("route_id") == "create.tools"]
        if len(routes) != 1 or routes[0].get("mutation") != "DRAFT_ONLY":
            findings.append(finding("CONVERTX-GUI-REGISTRY", "Tools semantic route must be uniquely registered as DRAFT_ONLY"))

    for action_id in ACTION_IDS:
        action_path = root / "canonical/actions" / f"{action_id}.json"
        if not action_path.is_file():
            findings.append(finding("CONVERTX-UAF-ACTION", f"Missing UAF action contract: {action_id}"))
            continue
        action = loadj(action_path)
        if action.get("schema") != "fa3.uaf.action-contract.v1" or action.get("id") != action_id:
            findings.append(finding("CONVERTX-UAF-ACTION", f"Invalid UAF action contract: {action_id}"))
    execute_path = root / "canonical/actions/file.convert.execute.json"
    if execute_path.is_file() and loadj(execute_path).get("resources", {}).get("hrb_required") is not True:
        findings.append(finding("CONVERTX-UAF-RESOURCE", "file.convert.execute must require HRB"))

    if (root / "apps/fa3-control-center/qml/ToolsOverlay.qml").exists():
        findings.append(finding("CONVERTX-GUI-LEGACY", "Legacy ToolsOverlay injection must not return"))

    regressions = run_regressions()
    if regressions["result"] != "PASS":
        findings.append(finding("CONVERTX-REGRESSION", "Built-in fail-closed regression set failed"))

    return {
        "result": "PASS" if not findings else "FAIL",
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "provider_status": provider_status or "UNKNOWN",
        "machine_execution_enabled": machine.get("machine_execution_enabled", False),
        "current_host_status": provider.get("current_host_status", "UNKNOWN"),
        "resource_admission_state": resource.get("current_authoritative_cpu_memory_verifier", "UNKNOWN"),
        "uaf_actions": sorted(ACTION_IDS),
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
