#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")
STATES = (
    "DISCOVERED", "UPSTREAM_IDENTITY_VERIFIED", "QUARANTINED", "BUILD_VERIFIED",
    "STAGING_QUALIFIED", "CURRENT_HOST_EXECUTED", "CURRENT_HOST_QUALIFIED",
    "ACCEPTANCE_PASS", "PROMOTION_AUTHORIZED", "PRODUCTION_PROMOTED",
)
NEXT_STATE = {left: right for left, right in zip(STATES, STATES[1:])}
RISK_APPROVALS = {"AUTO": 0, "REVIEW": 1, "CRITICAL": 2}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def validate_identity(identity: dict[str, Any]) -> dict[str, Any]:
    required = ("selected_version", "source_commit", "source_sha256", "artifact_sha256", "sbom_sha256", "provenance_sha256")
    missing = [key for key in required if not identity.get(key)]
    bad: list[str] = []
    if identity.get("source_commit") and not (isinstance(identity["source_commit"], str) and COMMIT_RE.fullmatch(identity["source_commit"])):
        bad.append("source_commit")
    for key in ("source_sha256", "artifact_sha256", "sbom_sha256", "provenance_sha256"):
        if identity.get(key) and not _sha(identity[key]):
            bad.append(key)
    return {"result": "PASS" if not missing and not bad else "FAIL", "missing": missing, "invalid": bad}


def transition(current: str, target: str) -> str:
    if current not in NEXT_STATE or NEXT_STATE[current] != target:
        raise ValueError(f"illegal qualification transition: {current} -> {target}")
    return target


def staging_receipt(identity: dict[str, Any], tests_passed: bool) -> dict[str, Any]:
    ident = validate_identity(identity)
    qualified = ident["result"] == "PASS" and tests_passed
    return {
        "schema": "fa3.dependency-staging-receipt.v1",
        "state": "STAGING_QUALIFIED" if qualified else "BUILD_VERIFIED",
        "result": "PASS" if qualified else "FAIL",
        "identity": identity,
        "evidence_class": "STAGING_QUALIFICATION",
        "production_authority": False,
        "may_claim_current_host": False,
        "may_promote": False,
        "production_ssot_write": False,
    }


def authorize_promotion(qualification: dict[str, Any], risk_tier: str, approvals: list[str]) -> dict[str, Any]:
    required_approvals = RISK_APPROVALS.get(risk_tier)
    errors: list[str] = []
    if required_approvals is None:
        errors.append("unknown_risk_tier")
    if qualification.get("state") != "ACCEPTANCE_PASS":
        errors.append("acceptance_pass_required")
    if qualification.get("current_host_qualified") is not True:
        errors.append("current_host_qualified_required")
    if not isinstance(qualification.get("host_attestation_sha256"), str) or not _sha(qualification.get("host_attestation_sha256")):
        errors.append("host_attestation_sha256_required")
    if validate_identity(qualification.get("identity", {}))["result"] != "PASS":
        errors.append("immutable_identity_incomplete")
    if required_approvals is not None and len(set(approvals)) < required_approvals:
        errors.append("insufficient_approvals")
    return {
        "schema": "fa3.dependency-promotion-authorization.v1",
        "result": "PASS" if not errors else "FAIL",
        "state": "PROMOTION_AUTHORIZED" if not errors else qualification.get("state"),
        "risk_tier": risk_tier,
        "errors": errors,
        "production_authority": not errors,
    }
