#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-SCS-001"
CONTRACT_ID = "FA3-HUMAN-CREDENTIAL-VAULT-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-VAULTWARDEN-001"
DECISION_ID = "FA3-DEC-VAULTWARDEN-HARDENING-2026-09-12"
REFERENCE_ID = "FA3-VAULTWARDEN-UPSTREAM-REFERENCE-2026-09-12"
GATE_ID = "FA3-VAULTWARDEN-GATESET-001"
ADMISSION_ID = "FA3-VAULTWARDEN-RUNTIME-ADMISSION-001"
CONFORMANCE_ID = "FA3-VAULTWARDEN-RUNTIME-CONFORMANCE-001"
RELEASE_ID = "FA3-RELEASE-PROJECTION-VAULTWARDEN-2026-09-12"
CAPABILITY_COUNT = 143
RELEASE = "1.37.2"
TAG_SHA = "f92e640ef5d96c0ec69ced35e419fef3a4711a2f"
COMMIT = "46d71107f5094460dd5ecbe1dbac6e6c71e5189a"
LICENSE = "AGPL-3.0-only"

P0_INVARIANTS = [
    "VAULTWARDEN_HUMAN_VAULT_NOT_RUNTIME_SECRET_BROKER",
    "VAULTWARDEN_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
    "VAULTWARDEN_CAPABILITY_AND_AUTHORITY_COUNT_INVARIANT",
    "VAULTWARDEN_IMMUTABLE_UPSTREAM_PIN_REQUIRED",
    "VAULTWARDEN_AGPL_LICENSE_PROVENANCE_REQUIRED",
    "VAULTWARDEN_SECRETREF_BOUNDARY_REQUIRED",
    "VAULTWARDEN_SECRET_VALUES_FORBIDDEN_IN_GENERAL_CONFIG",
    "VAULTWARDEN_ADMIN_SURFACE_DISABLED_BY_DEFAULT",
    "VAULTWARDEN_CLOSED_ENROLLMENT_BY_DEFAULT",
    "VAULTWARDEN_SECURE_TRANSPORT_AND_TLS_BOUNDARY_REQUIRED",
    "VAULTWARDEN_STRICT_SERVICE_EXPOSURE_REQUIRED",
    "VAULTWARDEN_SENSITIVE_TELEMETRY_REDACTION_REQUIRED",
    "VAULTWARDEN_LEAST_PRIVILEGE_NON_ROOT_REQUIRED",
    "VAULTWARDEN_MINIMAL_READONLY_MOUNTS_REQUIRED",
    "VAULTWARDEN_DENY_BY_DEFAULT_EGRESS_REQUIRED",
    "VAULTWARDEN_SSRF_RESISTANT_OUTBOUND_ACCESS_REQUIRED",
    "VAULTWARDEN_COMPLETE_STATE_BACKUP_INVENTORY_REQUIRED",
    "VAULTWARDEN_RESTORE_DRILL_EVIDENCE_REQUIRED",
    "VAULTWARDEN_PROVIDER_CLIENT_COMPATIBILITY_EVIDENCE_REQUIRED",
    "VAULTWARDEN_FLOATING_LATEST_TAG_FORBIDDEN_FOR_PRODUCTION",
    "VAULTWARDEN_PRODUCTION_IMAGE_DIGEST_REQUIRED",
    "VAULTWARDEN_UNSCOPED_WORKLOAD_VAULT_ACCESS_FORBIDDEN",
    "VAULTWARDEN_CURRENT_HOST_E2E_REQUIRED_FOR_RUNTIME_PROMOTION",
]

PATHS = {
    "profile": "canonical/profiles/FA3-SCS-001.json",
    "contract": "canonical/contracts/FA3-HUMAN-CREDENTIAL-VAULT-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-VAULTWARDEN-001.json",
    "decision": "canonical/decisions/FA3-DEC-VAULTWARDEN-HARDENING-2026-09-12.json",
    "reference": "canonical/references/FA3-VAULTWARDEN-UPSTREAM-REFERENCE-2026-09-12.json",
    "enforcement": "canonical/vaultwarden-enforcement.json",
    "admission": "canonical/vaultwarden-runtime-admission.json",
    "conformance": "canonical/FA3-VAULTWARDEN-RUNTIME-CONFORMANCE-001.json",
    "gate": "canonical/FA3-GATE-VAULTWARDEN-001.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-VAULTWARDEN-2026-09-12.json",
    "evidence": "evidence/reference/vaultwarden-reference-pass.json",
}

POLICY = {
    "human_vault_runtime_secret_broker_separated": True,
    "secret_ref_boundary_required": True,
    "secret_values_as_general_configuration": False,
    "admin_surface_enabled_by_default": False,
    "closed_enrollment_by_default": True,
    "secure_transport_required": True,
    "tls_or_equivalent_secure_termination_boundary_required": True,
    "strict_hostname_service_exposure_required": True,
    "sensitive_telemetry_redaction_required": True,
    "least_privilege_non_root_required": True,
    "minimal_mount_surface_required": True,
    "readonly_mount_where_possible": True,
    "deny_by_default_network_egress": True,
    "ssrf_resistant_outbound_validation_required": True,
    "backup_component_inventory_required": True,
    "restore_drill_evidence_required": True,
    "client_compatibility_evidence_required": True,
    "floating_container_tag_allowed_for_production": False,
    "immutable_provider_version_required": True,
    "image_digest_required_for_production": True,
    "direct_unscoped_workload_vault_access": False,
    "machine_secret_minting_or_lease_authority": False,
    "current_host_e2e_required_for_runtime_promotion": True,
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hardening_policy_valid(policy: dict[str, Any]) -> bool:
    return all(policy.get(k) is v for k, v in POLICY.items())


def runtime_promotion_valid(*, current_host_e2e: bool, immutable_image_digest: bool,
                            compatibility_matrix: bool, restore_drill: bool,
                            secure_transport: bool, isolation_pass: bool,
                            synthetic: bool) -> bool:
    return bool(current_host_e2e and immutable_image_digest and compatibility_matrix
                and restore_drill and secure_transport and isolation_pass and not synthetic)


def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def walk(obj: Any, source: str, field: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = f"{field}.{key}" if field else key
                if isinstance(value, str) and value == PROVIDER_ID and (
                    key == "authority" or key.endswith("_authority")
                ):
                    findings.append({"source": source, "field": here})
                walk(value, source, here)
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                walk(value, source, f"{field}[{i}]")

    for path in sorted((root / "canonical").rglob("*.json")):
        try:
            walk(loadj(path), str(path.relative_to(root)))
        except Exception as exc:
            findings.append({"source": str(path.relative_to(root)), "error": str(exc)})
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def reference_check(root: Path) -> dict[str, Any]:
    root = Path(root)
    findings: list[str] = []
    missing = [name for name, rel in PATHS.items() if not (root / rel).is_file()]
    if missing:
        return {"result": "FAIL", "findings": [f"missing:{x}" for x in missing]}

    p = {name: loadj(root / rel) for name, rel in PATHS.items()}
    profile, contract, provider = p["profile"], p["contract"], p["provider"]
    decision, ref, enf = p["decision"], p["reference"], p["enforcement"]
    admission, conf, gate = p["admission"], p["conformance"], p["gate"]
    release, evidence = p["release"], p["evidence"]

    if not (profile.get("id") == PROFILE_ID and profile.get("capability_count") == CAPABILITY_COUNT
            and profile.get("new_capability") is False
            and profile.get("new_architectural_authority") is False):
        findings.append("profile")

    upstream = provider.get("upstream", {})
    auth = provider.get("authority_boundaries", {})
    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("parent_profile") == PROFILE_ID
        and provider.get("provider_role") == "OPTIONAL_HUMAN_CREDENTIAL_VAULT_PROVIDER_AND_SECURITY_HARDENING_PATTERN_SOURCE"
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("contracts") == [CONTRACT_ID]
        and provider.get("runtime_activation_status") == "NOT_ADMITTED_PENDING_CURRENT_HOST"
        and upstream.get("release") == RELEASE
        and upstream.get("tag_object_sha") == TAG_SHA
        and upstream.get("release_commit") == COMMIT
        and upstream.get("license") == LICENSE
        and upstream.get("tag_signature_verified") is True
        and auth.get("machine_secrets") == "EXISTING_FA3_SECRETS_AUTHORITY_ONLY"
        and auth.get("runtime_secret_broker") == "EXISTING_FA3_SECRETS_AUTHORITY_ONLY"
        and hardening_policy_valid(provider.get("hardening_policy", {}))
        and provider.get("promotion", {}).get("production_runtime_promoted") is False
    ):
        findings.append("provider")

    required_contracts = {
        "CredentialReference", "CredentialAccessRequest", "CredentialAuditEvent",
        "CredentialBackupEvidence", "CredentialRestoreEvidence",
        "CredentialProviderCompatibilityEvidence",
    }
    if not (
        contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True
        and contract.get("capability_count") == CAPABILITY_COUNT
        and required_contracts.issubset(set(contract.get("contracts", [])))
        and contract.get("semantic_boundaries", {}).get("machine_secret_broker")
        == "OUT_OF_SCOPE_EXISTING_FA3_SECRETS_AUTHORITY_ONLY"
    ):
        findings.append("contract")

    if not (
        decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append("decision")

    stable, disp = ref.get("stable_reference", {}), ref.get("fa3_disposition", {})
    if not (
        ref.get("id") == REFERENCE_ID and stable.get("release") == RELEASE
        and stable.get("tag_object_sha") == TAG_SHA and stable.get("commit_sha") == COMMIT
        and stable.get("tag_signature_verified") is True
        and ref.get("license", {}).get("spdx") == LICENSE
        and ref.get("license", {}).get("network_copyleft") is True
        and disp.get("provider_is_machine_secret_broker") is False
        and disp.get("floating_latest_container_tag_allowed_for_production") is False
        and disp.get("immutable_container_digest_required_for_production") is True
        and disp.get("client_compatibility_evidence_required_for_production") is True
        and disp.get("restore_drill_required_for_recovery_pass") is True
        and disp.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append("reference")

    if not (
        enf.get("gate_id") == GATE_ID and enf.get("fail_closed") is True
        and enf.get("mandatory_rule_count") == len(P0_INVARIANTS)
        and enf.get("p0_invariants") == P0_INVARIANTS
        and enf.get("stable_reference_release") == RELEASE
        and enf.get("stable_reference_commit") == COMMIT
    ):
        findings.append("enforcement")

    pin = admission.get("immutable_runtime_pin", {})
    required = {
        "IMMUTABLE_CONTAINER_DIGEST", "PROVIDER_CLIENT_COMPATIBILITY_MATRIX_PASS",
        "RESTORE_DRILL_AND_LOGIN_PASS", "CURRENT_HOST_PRODUCTION_E2E_RECEIPT_PASS",
    }
    if not (
        admission.get("id") == ADMISSION_ID and admission.get("status") == "NOT_ADMITTED"
        and admission.get("fail_closed") is True and admission.get("disabled_state_global_blocker") is False
        and pin.get("release") == RELEASE and pin.get("release_commit") == COMMIT
        and pin.get("container_digest") is None
        and required.issubset(set(admission.get("activation_requires", [])))
        and admission.get("production_runtime_promoted") is False
    ):
        findings.append("admission")

    if not (
        conf.get("id") == CONFORMANCE_ID and conf.get("status") == "NOT_EXECUTED"
        and conf.get("synthetic_evidence_allowed_for_promotion") is False
        and conf.get("current_host_receipt") is None
        and conf.get("production_runtime_promoted") is False
    ):
        findings.append("conformance")

    if not (
        gate.get("id") == "FA3-GATE-VAULTWARDEN-001" and gate.get("gateset_id") == GATE_ID
        and gate.get("fail_closed") is True and gate.get("rule_count") == len(P0_INVARIANTS)
        and gate.get("current_host_runtime_required_for_reference_pass") is False
        and gate.get("current_host_runtime_required_for_runtime_promotion") is True
    ):
        findings.append("gate")

    if not (
        release.get("id") == RELEASE_ID
        and release.get("projection_semantics") == "NO_BASELINE_SEMANTIC_CHANGE_IMPLEMENTATION_PROJECTION_UPDATE"
        and release.get("new_capabilities") == 0
        and release.get("new_architectural_authorities") == 0
        and release.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append("release")

    if not (
        evidence.get("status") == "PASS" and evidence.get("rules_checked") == len(P0_INVARIANTS)
        and evidence.get("current_host_runtime_evidence") is False
        and evidence.get("immutable_container_digest_evidence") is False
        and evidence.get("production_runtime_promoted") is False
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append("evidence")

    authority = scan_canonical_authority_assignments(root)
    if authority["result"] != "PASS":
        findings.append("authority-assignment")

    return {
        "result": "PASS" if not findings else "FAIL",
        "rules_checked": len(P0_INVARIANTS),
        "authority_scan": authority,
        "findings": findings,
    }


def run_regressions() -> dict[str, Any]:
    cases = []
    for key, expected in POLICY.items():
        bad = dict(POLICY)
        bad[key] = not expected
        cases.append({
            "case": key,
            "result": "PASS" if hardening_policy_valid(POLICY) and not hardening_policy_valid(bad) else "FAIL",
        })
    complete = runtime_promotion_valid(
        current_host_e2e=True, immutable_image_digest=True, compatibility_matrix=True,
        restore_drill=True, secure_transport=True, isolation_pass=True, synthetic=False)
    no_digest = not runtime_promotion_valid(
        current_host_e2e=True, immutable_image_digest=False, compatibility_matrix=True,
        restore_drill=True, secure_transport=True, isolation_pass=True, synthetic=False)
    synthetic = not runtime_promotion_valid(
        current_host_e2e=True, immutable_image_digest=True, compatibility_matrix=True,
        restore_drill=True, secure_transport=True, isolation_pass=True, synthetic=True)
    cases.append({"case": "production_promotion_complete_real_evidence",
                  "result": "PASS" if complete and no_digest and synthetic else "FAIL"})
    return {
        "result": "PASS" if all(c["result"] == "PASS" for c in cases) else "FAIL",
        "passed": sum(c["result"] == "PASS" for c in cases),
        "total": len(cases),
        "cases": cases,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    reference, regressions = reference_check(root), run_regressions()
    result = "PASS" if reference["result"] == regressions["result"] == "PASS" else "FAIL"
    print(json.dumps({
        "schema": "fa3.vaultwarden-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "reference": reference,
        "regressions": regressions,
        "production_runtime_promoted": False,
        "result": result,
    }, indent=2, sort_keys=True))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
