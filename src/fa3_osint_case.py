#!/usr/bin/env python3
"""Case-bound CAP-053 request and typed observation preparation.

Structural validation only. Existing FA3 Security/MCP authority must verify
approval receipts and execute separately admitted providers; no code here
starts a process, accesses a network, or grants permission.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from fa3_osint_arsenal_catalog import safe_source_url

SCOPE_CLASSES = frozenset({"OWNED_ASSET", "AUTHORIZED_SUBJECT", "PUBLIC_AGGREGATE"})
RESTRICTED = frozenset({
    "red-team-offensive", "data-breach", "people-identity", "image-facial",
    "dark-web", "iot-devices", "hardware-hacking", "vpn-privacy",
    "bug-bounty", "search-dorking", "crypto-blockchain",
})
NO_RUNTIME = {
    "authority": False,
    "provider_admitted": False,
    "runtime_execution_allowed": False,
    "automatic_provider_admission": False,
    "automatic_model_selection": False,
    "current_host_pass_claim": False,
}


class CaseContractError(ValueError):
    pass


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaseContractError("missing/invalid " + name)
    return value.strip()


def _timestamp(value: Any, name: str) -> datetime:
    raw = _string(value, name)
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaseContractError("invalid " + name) from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise CaseContractError("timezone required for " + name)
    return timestamp


def validate_case_request(request: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema") != "fa3.osint-investigation-request.v1":
        raise CaseContractError("unexpected request schema")
    case_id = _string(request.get("case_id"), "case_id")
    purpose = _string(request.get("purpose"), "purpose")
    scope = request.get("scope_class")
    if scope not in SCOPE_CLASSES:
        raise CaseContractError("unknown scope_class")
    expiry = _timestamp(request.get("expires_at"), "expires_at")
    present = now or datetime.now(timezone.utc)
    if present.tzinfo is None or present.utcoffset() is None:
        raise CaseContractError("timezone required for current time")
    if expiry <= present:
        raise CaseContractError("case request has expired")
    allowed = request.get("target_scope")
    if not isinstance(allowed, list) or not allowed or not all(
        isinstance(item, str) and item.strip() for item in allowed
    ):
        raise CaseContractError("nonempty explicit target_scope required")
    requested_classes = request.get("data_classes", [])
    if not isinstance(requested_classes, list) or not all(isinstance(x, str) for x in requested_classes):
        raise CaseContractError("invalid data_classes")
    if scope == "PUBLIC_AGGREGATE" and set(requested_classes) & {
        "PERSON_IDENTIFIERS", "FACE_IDENTIFICATION", "BREACH_CREDENTIALS"
    }:
        raise CaseContractError("personal/sensitive lookup prohibited for public aggregate scope")
    if scope == "AUTHORIZED_SUBJECT":
        _string(request.get("authorization_reference"), "authorization_reference")
        _string(request.get("human_approval_reference"), "human_approval_reference")
    if scope == "OWNED_ASSET":
        _string(request.get("ownership_reference"), "ownership_reference")
    policy_ref = _string(request.get("security_policy_receipt_ref"), "security_policy_receipt_ref")
    # This function cannot authenticate these externally issued references.
    # The Security/MCP authority MUST do so again before any provider call.
    return {
        "schema": "fa3.osint-request-preflight.v1",
        "case_id": case_id,
        "purpose": purpose,
        "scope_class": scope,
        "explicit_target_scope": allowed,
        "security_policy_receipt_ref": policy_ref,
        "result": "PENDING_INDEPENDENT_SECURITY_AUTHORITY_VERIFICATION",
        "verification_performed": False,
        **NO_RUNTIME,
    }


def candidate_disposition(record: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Classify metadata for an independent admission review, never admit."""
    tool_id = _string(record.get("id"), "tool.id")
    findings = []
    if record.get("status") != "DISCOVERED_METADATA_ONLY":
        findings.append("UNEXPECTED_METADATA_STATUS")
    if record.get("review_class") == "RESTRICTED_REVIEW" or record.get("category") in RESTRICTED:
        findings.append("SENSITIVE_CATEGORY_REQUIRES_SPECIAL_SEPARATE_REVIEW")
    if record.get("url_status") != "UNVERIFIED_EXTERNAL_LINK" or not safe_source_url(record.get("url")):
        findings.append("SOURCE_URL_UNRESOLVED_OR_INVALID")
    for key in (
        "independent_license_verified", "upstream_source_pinned",
        "supply_chain_review_pass", "privacy_and_terms_review_pass",
        "host_coexistence_review_pass", "network_egress_review_pass",
    ):
        if review.get(key) is not True:
            findings.append("MISSING_REVIEW:" + key)
    return {
        "schema": "fa3.osint-candidate-admission-precheck.v1",
        "tool_id": tool_id,
        "result": "BLOCKED" if findings else "PENDING_SEPARATE_PROVIDER_ADMISSION",
        "findings": findings,
        "review_evidence_is_authenticated": False,
        **NO_RUNTIME,
    }


def observation_projection(
    request: dict[str, Any], record: dict[str, Any], *,
    artifact: bytes, collected_at: str,
    extracted_fields: dict[str, Any], uncertainty: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Project untrusted collection results without modifying original evidence.

    The returned payload MUST be submitted through the existing FA3 Evidence
    authority; it does not become an evidence receipt itself.
    """
    preflight = validate_case_request(request, now=now)
    if not isinstance(artifact, bytes) or not artifact:
        raise CaseContractError("nonempty original artifact bytes required")
    if not isinstance(extracted_fields, dict):
        raise CaseContractError("structured extracted_fields required")
    if any(k in extracted_fields for k in ("ai_summary", "ai_confidence", "inferred_identity")):
        raise CaseContractError("AI interpretations must use a separate, attributed observation")
    if not isinstance(uncertainty, str) or not uncertainty.strip():
        raise CaseContractError("uncertainty statement required")
    observed = _timestamp(collected_at, "collected_at")
    if observed > (now or datetime.now(timezone.utc)):
        raise CaseContractError("observation timestamp cannot be future")
    tool_id = _string(record.get("id"), "tool.id")
    source = safe_source_url(record.get("url"))
    if not source:
        raise CaseContractError("unverified source reference cannot create an observation")
    if record.get("status") != "DISCOVERED_METADATA_ONLY":
        raise CaseContractError("unknown source metadata status")
    return {
        "schema": "fa3.osint-investigation-observation.v1",
        "case_id": preflight["case_id"],
        "scope_class": preflight["scope_class"],
        "source_tool_id": tool_id,
        "source_url": source,
        "source_positions": list(record.get("source_positions", [])),
        "collected_at": observed.isoformat(),
        "original_artifact_sha256": hashlib.sha256(artifact).hexdigest(),
        "extracted_fields": extracted_fields,
        "uncertainty": uncertainty.strip(),
        "interpretations_are_separate": True,
        "target_evidence_contract": "FA3-EVIDENCE-ENVELOPE-001",
        "result": "UNTRUSTED_OBSERVATION_PENDING_EVIDENCE_AUTHORITY",
        **NO_RUNTIME,
    }


def maigret_reference_plan(request: dict[str, Any], username: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Non-executable mapping to the existing CAP-053 Maigret reference."""
    preflight = validate_case_request(request, now=now)
    if preflight["scope_class"] != "AUTHORIZED_SUBJECT":
        raise CaseContractError("username lookup requires AUTHORIZED_SUBJECT scope")
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", username):
        raise CaseContractError("invalid username")
    if username not in preflight["explicit_target_scope"]:
        raise CaseContractError("username outside case scope")
    return {
        "schema": "fa3.osint-provider-plan.v1",
        "provider": "soxoj/maigret",
        "capability": "CAP-053",
        "upstream_commit": "b6642744988e7e6c2d21f75db60ec3093019ba25",
        "case_id": preflight["case_id"],
        "username": username,
        "result": "NON_EXECUTABLE_PLAN_PENDING_ADMISSION_AND_SCOPE_VERIFICATION",
        "shell_command": None,
        "network_request": None,
        **NO_RUNTIME,
    }
