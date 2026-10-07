#!/usr/bin/env python3
from __future__ import annotations
from fa3_release_baseline import module_active_capability_count

import json
import re
from pathlib import Path
from typing import Any

GATE_ID = "FA3-GATE-OPENMODELDB-PROVIDER-001"
PROVIDER_ID = "FA3-PROVIDER-OPENMODELDB-001"
PROFILE_ID = "FA3-MODEL-MANAGER-001"
REGISTRY_ID = "FA3-MODEL-REGISTRY-001"
SECURITY_PROFILE_ID = "FA3-MODEL-ARTIFACT-SECURITY-001"
SECURITY_GATE_ID = "FA3-GATE-MODEL-ARTIFACT-SECURITY-001"
DECISION_ID = "FA3-DEC-OPENMODELDB-PROVIDER-2026-09-13"
REFERENCE_ID = "FA3-OPENMODELDB-UPSTREAM-REFERENCE-2026-09-13"
UPSTREAM_COMMIT = "782aac088bd83dd3fc438a42eb0c3868dc559110"
CAPABILITY_COUNT = module_active_capability_count(__file__)
EVIDENCE_PATH = "evidence/reference/openmodeldb-provider-ci-2026-09-13.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def resource_admission(
    *,
    expected_sha256: str,
    observed_sha256: str,
    license_id: str | None,
    format_name: str,
    security_admitted: bool,
    mediated: bool,
    lineage_known: bool,
    runtime_verified: bool,
    runtime_evidence: str | None,
) -> bool:
    dangerous = format_name.lower() in {"pth", "pt", "ckpt", "pickle", "pkl"}
    return bool(
        _sha256(expected_sha256)
        and _sha256(observed_sha256)
        and expected_sha256.lower() == observed_sha256.lower()
        and license_id not in {None, "", "UNKNOWN"}
        and mediated
        and lineage_known
        and (not dangerous or security_admitted)
        and runtime_verified
        and runtime_evidence
    )


def run_regressions() -> dict[str, Any]:
    good = {
        "expected_sha256": "a" * 64,
        "observed_sha256": "a" * 64,
        "license_id": "MIT",
        "format_name": "safetensors",
        "security_admitted": True,
        "mediated": True,
        "lineage_known": True,
        "runtime_verified": True,
        "runtime_evidence": "EVID-RUNTIME-1",
    }
    cases = [
        ("BASELINE_VALID_RESOURCE", resource_admission(**good)),
        ("CHECKSUM_MISMATCH_BLOCKED", not resource_admission(**{**good, "observed_sha256": "b" * 64})),
        ("UNKNOWN_LICENSE_BLOCKED", not resource_admission(**{**good, "license_id": "UNKNOWN"})),
        ("UNMEDIATED_IMPORT_BLOCKED", not resource_admission(**{**good, "mediated": False})),
        ("DANGEROUS_SERIALIZATION_UNADMITTED_BLOCKED", not resource_admission(**{**good, "format_name": "pth", "security_admitted": False})),
        ("UNKNOWN_LINEAGE_BLOCKED", not resource_admission(**{**good, "lineage_known": False})),
        ("UNKNOWN_RUNTIME_COMPATIBILITY_BLOCKED", not resource_admission(**{**good, "runtime_verified": False})),
        ("MISSING_RUNTIME_EVIDENCE_BLOCKED", not resource_admission(**{**good, "runtime_evidence": None})),
    ]
    rows = [{"case": name, "status": "PASS" if ok else "FAIL"} for name, ok in cases]
    passed = sum(row["status"] == "PASS" for row in rows)
    return {
        "schema": "fa3.openmodeldb-provider-regression-report.v1",
        "result": "PASS" if passed == len(rows) else "FAIL",
        "passed": passed,
        "total": len(rows),
        "cases": rows,
    }


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-OPENMODELDB-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-OPENMODELDB-PROVIDER-2026-09-13.json",
        "reference": root / "canonical/references/FA3-OPENMODELDB-UPSTREAM-REFERENCE-2026-09-13.json",
        "enforcement": root / "canonical/openmodeldb-provider-enforcement.json",
        "profile": root / "canonical/profiles/FA3-MODEL-MANAGER-001.json",
        "model_manager_enforcement": root / "canonical/model-manager-v2-enforcement.json",
        "evidence": root / EVIDENCE_PATH,
    }
    for key, path in paths.items():
        if not path.is_file():
            findings.append(_finding("OPENMODELDB-REF-001", "Missing required OpenModelDB materialization artifact", artifact=key, path=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider = _load(paths["provider"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    enforcement = _load(paths["enforcement"])
    profile = _load(paths["profile"])
    model_manager_enforcement = _load(paths["model_manager_enforcement"])
    evidence = _load(paths["evidence"])

    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("parent_profile") == PROFILE_ID
        and provider.get("upstream_repository") == "OpenModelDB/open-model-database"
        and provider.get("upstream_commit") == UPSTREAM_COMMIT
        and provider.get("architectural_authority") is False
        and provider.get("artifact_trust_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(_finding("OPENMODELDB-REF-010", "Provider identity, pin or authority boundary drift"))

    resource_contract = provider.get("resource_metadata_contract", {})
    required_resource_fields = {"platform", "type", "size", "sha256", "urls"}
    if not (
        required_resource_fields.issubset(set(resource_contract.get("provider_resource_fields", [])))
        and resource_contract.get("provider_declared_sha256") == "REQUIRED_AND_MUST_MATCH_DOWNLOADED_BYTES"
        and provider.get("fa3_usage_policy", {}).get("unknown_license") == "BLOCK_PROMOTION"
        and provider.get("fa3_usage_policy", {}).get("direct_runtime_provider_download_bypass") == "FORBIDDEN"
    ):
        findings.append(_finding("OPENMODELDB-REF-011", "Checksum, license or mediated-acquisition policy drift"))

    security = provider.get("security_binding", {})
    if not (
        security.get("profile_id") == SECURITY_PROFILE_ID
        and security.get("required_gate_id") == SECURITY_GATE_ID
        and security.get("all_acquisition_import_paths_mediated") is True
        and security.get("catalog_pass_is_artifact_security_pass") is False
        and security.get("checksum_pass_is_runtime_compatibility_pass") is False
    ):
        findings.append(_finding("OPENMODELDB-REF-012", "Model Artifact Security binding drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(_finding("OPENMODELDB-REF-013", "Canonical OpenModelDB decision drift"))

    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("repository") == "OpenModelDB/open-model-database"
        and reference.get("commit") == UPSTREAM_COMMIT
        and reference.get("floating_latest_allowed_as_production_evidence") is False
        and reference.get("verified_upstream_facts", {}).get("resource_schema_contains_sha256") is True
        and reference.get("verified_upstream_facts", {}).get("model_license_field_can_be_optional") is True
    ):
        findings.append(_finding("OPENMODELDB-REF-014", "Upstream reference pin/schema drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("security_gate_id") == SECURITY_GATE_ID
        and enforcement.get("current_host_runtime_promotion_claim") is False
        and len(enforcement.get("mandatory_rules", [])) == 10
    ):
        findings.append(_finding("OPENMODELDB-REF-015", "OpenModelDB enforcement drift"))

    if not (
        PROVIDER_ID in profile.get("providers", [])
        and profile.get("provider_roles", {}).get("openmodeldb") == "SPECIALIZED_OPTIONAL_UPSCALING_RESTORATION_DISCOVERY_METADATA_AND_ACQUISITION_SOURCE_PROVIDER"
        and profile.get("security_extension", {}).get("mandatory_before_promotion") is True
        and profile.get("security_extension", {}).get("all_acquisition_import_paths_mediated") is True
        and profile.get("security_extension", {}).get("runtime_provider_direct_download_bypass") == "FORBIDDEN"
    ):
        findings.append(_finding("OPENMODELDB-REF-016", "Model Manager profile/security integration drift"))

    if PROVIDER_ID not in model_manager_enforcement.get("provider_ids", []):
        findings.append(_finding("OPENMODELDB-REF-017", "Model Manager v2 enforcement provider binding missing"))

    if not (
        evidence.get("gate_id") == GATE_ID
        and evidence.get("status") in {"PENDING_CI", "PASS"}
        and evidence.get("upstream_commit") == UPSTREAM_COMMIT
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("OPENMODELDB-REF-018", "Reference evidence contract drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    ok = reference["result"] == regressions["result"] == "PASS"
    return {
        "schema": "fa3.openmodeldb-provider-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "regressions": regressions,
        "current_host_runtime_promotion_claim": False,
        "promotion_effect": "STATIC_PROVIDER_ADMISSION_PASS_DOES_NOT_CLAIM_MODEL_ARTIFACT_OR_CURRENT_HOST_RUNTIME_PROMOTION",
    }
