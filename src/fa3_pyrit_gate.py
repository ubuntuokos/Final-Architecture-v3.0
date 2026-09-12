#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-AI-SEC-VALIDATION-001"
CONTRACT_ID = "FA3-AI-SECURITY-VALIDATION-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-PYRIT-001"
DECISION_ID = "FA3-DEC-PYRIT-2026-09-12"
REFERENCE_ID = "FA3-PYRIT-UPSTREAM-REFERENCE-2026-09-12"
GATE_ID = "FA3-PYRIT-GATESET-001"
ADMISSION_ID = "FA3-PYRIT-RUNTIME-ADMISSION-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v1.1.0"
REFERENCE_COMMIT = "d0524f0714840519b826eb770687ca1d4f46a761"
MANDATORY_CONSTRAINT = (
    "PyRIT SHALL NOT become an FA3 orchestration, policy, identity, authorization, "
    "MCP/capability-gateway, canonical-memory, model-registry, model-routing, "
    "host-resource/GPU-placement, evidence/provenance, secrets, network-egress, "
    "artifact-trust or promotion authority."
)

P0_INVARIANTS = [
    "PYRIT_EXISTING_AISEC_CONTRACT_ONLY",
    "PYRIT_PROVIDER_NOT_AUTHORITY",
    "PYRIT_IMMUTABLE_STABLE_PIN",
    "PYRIT_PERMISSIVE_MIT_LICENSE_REQUIRED",
    "PYRIT_EXPLICIT_TARGET_ALLOWLIST_REQUIRED",
    "PYRIT_DENY_BY_DEFAULT_EGRESS_REQUIRED",
    "PYRIT_SECRET_ISOLATION_REQUIRED",
    "PYRIT_ARBITRARY_MCP_AND_HOST_SHELL_FORBIDDEN",
    "PYRIT_PROVIDER_LOCAL_MEMORY_ONLY",
    "PYRIT_CANONICAL_EVIDENCE_PROJECTION_REQUIRED",
    "PYRIT_MODEL_ROUTING_VIA_EXISTING_FA3_AUTHORITY",
    "PYRIT_DIRECT_GPU_DEVICE_PLACEMENT_FORBIDDEN",
    "PYRIT_TEST_DATA_AND_RESOURCE_ISOLATION_REQUIRED",
    "PYRIT_IMMUTABLE_RUN_IDENTITY_AND_PROVENANCE_REQUIRED",
    "PYRIT_UNDETERMINED_SCORE_CANNOT_PASS",
    "PYRIT_CURRENT_HOST_E2E_REQUIRED_FOR_RUNTIME_PROMOTION",
]

PATHS = {
    "profile": "canonical/profiles/FA3-AI-SEC-VALIDATION-001.json",
    "contract": "canonical/contracts/FA3-AI-SECURITY-VALIDATION-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-PYRIT-001.json",
    "decision": "canonical/decisions/FA3-DEC-PYRIT-2026-09-12.json",
    "reference": "canonical/references/FA3-PYRIT-UPSTREAM-REFERENCE-2026-09-12.json",
    "enforcement": "canonical/pyrit-enforcement.json",
    "admission": "canonical/pyrit-runtime-admission.json",
    "evidence": "evidence/reference/pyrit-reference-pass.json",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def execution_policy_valid(policy: dict[str, Any]) -> bool:
    return bool(
        policy.get("explicit_target_allowlist_required") is True
        and policy.get("deny_by_default_network_egress") is True
        and policy.get("secret_environment_passthrough") is False
        and policy.get("arbitrary_host_shell") is False
        and policy.get("arbitrary_mcp_capability_access") is False
        and policy.get("canonical_memory_write") is False
        and policy.get("provider_local_operational_memory_only") is True
        and policy.get("test_data_separation_required") is True
        and policy.get("resource_limits_required") is True
        and policy.get("immutable_run_identity_required") is True
        and policy.get("evidence_projection_required") is True
        and policy.get("direct_gpu_or_device_placement") is False
        and policy.get("model_execution_via_existing_fa3_router") is True
        and policy.get("undetermined_score_is_security_pass") is False
    )


def score_status_valid(status: str, security_pass: bool) -> bool:
    if status == "UNDETERMINED":
        return not security_pass
    return status in {"PASS", "FAIL"} and (not security_pass or status == "PASS")


def runtime_promotion_valid(*, current_host_e2e: bool, synthetic: bool,
                            immutable_runtime_pin: bool, isolation_pass: bool) -> bool:
    return bool(current_host_e2e and not synthetic and immutable_runtime_pin and isolation_pass)


def provider_shape_valid(provider: dict[str, Any]) -> bool:
    auth = provider.get("authority_boundaries", {})
    required_auth = {
        "identity": "EXISTING_FA3_IDENTITY_AUTHORITY_ONLY",
        "authorization_policy": "FA3-AUTH-SECURITY-GOV-001",
        "mcp_tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
        "model_routing": "FA3-AUTH-MODEL-ROUTER-001",
        "host_resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
        "memory": "EXISTING_FA3_MEMORY_AUTHORITY_ONLY",
        "secrets": "EXISTING_FA3_SECRETS_AUTHORITY_ONLY",
        "network_egress": "EXISTING_FA3_NETWORK_EGRESS_AUTHORITY_ONLY",
        "artifact_trust": "FA3-REG-ARTIFACT-MODEL-001",
        "registry": "FA3-REGISTRY-001",
        "promotion": "EXISTING_FA3_PROMOTION_AUTHORITY_ONLY",
    }
    upstream = provider.get("upstream", {})
    return bool(
        provider.get("id") == PROVIDER_ID
        and provider.get("parent_profile") == PROFILE_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("runtime_activation_status") == "NOT_ADMITTED_PENDING_CURRENT_HOST"
        and provider.get("contracts") == [CONTRACT_ID]
        and provider.get("upstream_reference") == REFERENCE_ID
        and upstream.get("repository") == "microsoft/PyRIT"
        and upstream.get("release") == REFERENCE_RELEASE
        and upstream.get("release_commit") == REFERENCE_COMMIT
        and upstream.get("license") == "MIT"
        and auth == required_auth
        and provider.get("normative_constraint") == MANDATORY_CONSTRAINT
        and execution_policy_valid(provider.get("execution_policy", {}))
    )


def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0

    def walk(obj: Any, path: str, source: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = f"{path}.{key}" if path else key
                if isinstance(value, str) and value == PROVIDER_ID and (
                    key == "authority" or key.endswith("_authority")
                ):
                    findings.append(finding(
                        "PYRIT-AUTH-001",
                        "PyRIT assigned prohibited canonical authority",
                        source=source,
                        field=here,
                    ))
                walk(value, here, source)
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                walk(value, f"{path}[{idx}]", source)

    for path in sorted((root / "canonical").rglob("*.json")):
        scanned += 1
        try:
            walk(loadj(path), "", str(path.relative_to(root)))
        except Exception as exc:
            findings.append(finding(
                "PYRIT-AUTH-002",
                "Unreadable canonical JSON",
                source=str(path.relative_to(root)),
                error=str(exc),
            ))
    return {
        "result": "PASS" if not findings else "FAIL",
        "scanned_canonical_json_files": scanned,
        "findings": findings,
    }


def reference_check(root: Path) -> dict[str, Any]:
    root = Path(root)
    findings: list[dict[str, Any]] = []
    for name, rel in PATHS.items():
        if not (root / rel).is_file():
            findings.append(finding("PYRIT-REF-001", f"Missing required PyRIT artifact: {name}", path=rel))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile = loadj(root / PATHS["profile"])
    contract = loadj(root / PATHS["contract"])
    provider = loadj(root / PATHS["provider"])
    decision = loadj(root / PATHS["decision"])
    reference = loadj(root / PATHS["reference"])
    enforcement = loadj(root / PATHS["enforcement"])
    admission = loadj(root / PATHS["admission"])
    evidence = loadj(root / PATHS["evidence"])

    if not provider_shape_valid(provider):
        findings.append(finding("PYRIT-REF-002", "PyRIT provider boundary or execution-policy drift"))

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and PROVIDER_ID in profile.get("providers", [])
        and CONTRACT_ID in profile.get("contracts", [])
    ):
        findings.append(finding("PYRIT-REF-003", "AI security profile binding drift"))

    contracts = set(contract.get("contracts", []))
    required_contracts = {
        "AdversarialSecurityEvidence",
        "PromptSecurityAssessment",
        "SecurityRegressionEvidence",
    }
    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("provider_neutral") is True
        and contract.get("capability_count") == CAPABILITY_COUNT
        and required_contracts.issubset(contracts)
    ):
        findings.append(finding("PYRIT-REF-004", "Provider-neutral AI security contract closure drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("profile_id") == PROFILE_ID
        and decision.get("contract_id") == CONTRACT_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("mandatory_constraint") == MANDATORY_CONSTRAINT
    ):
        findings.append(finding("PYRIT-REF-005", "PyRIT canonical decision drift"))

    stable = reference.get("stable_reference", {})
    disposition = reference.get("fa3_disposition", {})
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("provider_id") == PROVIDER_ID
        and reference.get("repository") == "microsoft/PyRIT"
        and stable.get("release") == REFERENCE_RELEASE
        and stable.get("commit_sha") == REFERENCE_COMMIT
        and reference.get("license", {}).get("spdx") == "MIT"
        and reference.get("license", {}).get("permissive") is True
        and disposition.get("floating_main_allowed_as_promotion_evidence") is False
        and disposition.get("provider_memory_is_canonical_memory") is False
        and disposition.get("direct_gpu_placement_allowed") is False
        and disposition.get("undetermined_score_may_count_as_security_pass") is False
        and disposition.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(finding("PYRIT-REF-006", "PyRIT immutable upstream/license disposition drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("profile_id") == PROFILE_ID
        and enforcement.get("contract_id") == CONTRACT_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("stable_reference_release") == REFERENCE_RELEASE
        and enforcement.get("stable_reference_commit") == REFERENCE_COMMIT
        and enforcement.get("mandatory_rule_count") == len(P0_INVARIANTS)
        and enforcement.get("p0_invariants") == P0_INVARIANTS
        and enforcement.get("runtime_activation_requires_current_host_conformance") is True
    ):
        findings.append(finding("PYRIT-REF-007", "PyRIT enforcement record drift"))

    pin = admission.get("immutable_runtime_pin", {})
    required_activation = {
        "EXPLICIT_TARGET_ALLOWLIST",
        "DENY_BY_DEFAULT_NETWORK_EGRESS",
        "UNSCOPED_SECRET_ENVIRONMENT_NOT_PASSED",
        "ARBITRARY_MCP_CAPABILITY_ACCESS_FORBIDDEN",
        "ARBITRARY_HOST_SHELL_FORBIDDEN",
        "CANONICAL_MEMORY_WRITE_FORBIDDEN",
        "MODEL_EXECUTION_VIA_EXISTING_FA3_MODEL_ROUTER",
        "DIRECT_GPU_OR_DEVICE_PLACEMENT_FORBIDDEN",
        "CURRENT_HOST_PRODUCTION_E2E_RECEIPT_PASS",
    }
    if not (
        admission.get("id") == ADMISSION_ID
        and admission.get("provider_id") == PROVIDER_ID
        and admission.get("status") == "NOT_ADMITTED"
        and admission.get("fail_closed") is True
        and admission.get("current_host_evidence_required") is True
        and pin.get("release") == REFERENCE_RELEASE
        and pin.get("release_commit") == REFERENCE_COMMIT
        and required_activation.issubset(set(admission.get("activation_requires", [])))
    ):
        findings.append(finding("PYRIT-REF-008", "PyRIT runtime admission boundary drift"))

    if not (
        evidence.get("schema") == "fa3.pyrit-reference-evidence.v1"
        and evidence.get("provider_id") == PROVIDER_ID
        and evidence.get("gate_id") == GATE_ID
        and evidence.get("status") == "PASS"
        and evidence.get("rules_checked") == len(P0_INVARIANTS)
        and evidence.get("current_host_runtime_evidence") is False
        and evidence.get("production_runtime_promoted") is False
        and evidence.get("new_capabilities") == 0
        and evidence.get("new_architectural_authorities") == 0
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("PYRIT-REF-009", "PyRIT reference evidence scope drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    provider_good = {
        "explicit_target_allowlist_required": True,
        "deny_by_default_network_egress": True,
        "secret_environment_passthrough": False,
        "arbitrary_host_shell": False,
        "arbitrary_mcp_capability_access": False,
        "canonical_memory_write": False,
        "provider_local_operational_memory_only": True,
        "test_data_separation_required": True,
        "resource_limits_required": True,
        "immutable_run_identity_required": True,
        "evidence_projection_required": True,
        "direct_gpu_or_device_placement": False,
        "model_execution_via_existing_fa3_router": True,
        "undetermined_score_is_security_pass": False,
    }
    cases = [
        ("PYRIT-REG-001", "secure execution policy",
         execution_policy_valid(provider_good),
         not execution_policy_valid({**provider_good, "explicit_target_allowlist_required": False})),
        ("PYRIT-REG-002", "deny unrestricted egress",
         execution_policy_valid(provider_good),
         not execution_policy_valid({**provider_good, "deny_by_default_network_egress": False})),
        ("PYRIT-REG-003", "deny secrets passthrough",
         execution_policy_valid(provider_good),
         not execution_policy_valid({**provider_good, "secret_environment_passthrough": True})),
        ("PYRIT-REG-004", "deny MCP and shell authority",
         execution_policy_valid(provider_good),
         not execution_policy_valid({**provider_good, "arbitrary_host_shell": True})),
        ("PYRIT-REG-005", "provider-local memory only",
         execution_policy_valid(provider_good),
         not execution_policy_valid({**provider_good, "canonical_memory_write": True})),
        ("PYRIT-REG-006", "router owns model execution and device placement",
         execution_policy_valid(provider_good),
         not execution_policy_valid({**provider_good, "direct_gpu_or_device_placement": True})),
        ("PYRIT-REG-007", "undetermined score cannot pass",
         score_status_valid("UNDETERMINED", False),
         not score_status_valid("UNDETERMINED", True)),
        ("PYRIT-REG-008", "current-host runtime promotion",
         runtime_promotion_valid(current_host_e2e=True, synthetic=False, immutable_runtime_pin=True, isolation_pass=True),
         not runtime_promotion_valid(current_host_e2e=False, synthetic=True, immutable_runtime_pin=True, isolation_pass=True)),
    ]
    rendered = [
        {
            "id": code,
            "name": name,
            "positive_case": positive,
            "negative_case": negative,
            "status": "PASS" if positive and negative else "FAIL",
        }
        for code, name, positive, negative in cases
    ]
    return {
        "result": "PASS" if all(case["status"] == "PASS" for case in rendered) else "FAIL",
        "passed": sum(case["status"] == "PASS" for case in rendered),
        "total": len(rendered),
        "cases": rendered,
    }


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_check(root)
    regressions = run_regressions()
    authority = scan_canonical_authority_assignments(root)
    findings = list(reference.get("findings", [])) + list(authority.get("findings", []))
    if regressions["result"] != "PASS":
        findings.append(finding("PYRIT-REG-FAIL", "PyRIT executable regression suite failed"))

    report = {
        "schema": "fa3.pyrit-gate-report.v1",
        "gate_set_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "reference_status": reference["result"],
        "authority_scan_status": authority["result"],
        "scanned_canonical_json_files": authority["scanned_canonical_json_files"],
        "regressions": regressions,
        "findings": findings,
        "current_host_runtime_promoted": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
    }
    out = root / "reports/pyrit-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[1]
    result = gate(here)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["result"] == "PASS" else 2)
