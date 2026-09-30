#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

DESCRIPTOR_SCHEMA = "fa3.license-rights-descriptor.v1"
RELEASE_SCHEMA = "fa3.release-license-compliance-receipt.v1"
SUBJECT_TYPES = {
    "CODE", "DOCUMENTATION", "MODEL", "DATASET", "ASSET", "FONT",
    "SDK", "CODEC", "PROVIDER", "SERVICE", "TEMPLATE",
}
DISPOSITIONS = {
    "ALLOW", "ALLOW_WITH_OBLIGATIONS", "REVIEW_REQUIRED",
    "REFERENCE_ONLY", "DENY",
}
RELEASE_DISPOSITIONS = {"ALLOW", "ALLOW_WITH_OBLIGATIONS"}
UNKNOWN_MARKERS = {"", "UNKNOWN", "NOASSERTION", "NONE", "UNCLASSIFIED"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unknown(value: Any) -> bool:
    return not _nonempty(value) or str(value).strip().upper() in UNKNOWN_MARKERS


def evaluate_descriptor(descriptor: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []

    if descriptor.get("schema") != DESCRIPTOR_SCHEMA:
        findings.append("descriptor schema mismatch")

    subject = descriptor.get("subject", {})
    if not _nonempty(subject.get("id")):
        findings.append("subject id missing")
    if subject.get("type") not in SUBJECT_TYPES:
        findings.append("subject type invalid")

    source = descriptor.get("source", {})
    if not _nonempty(source.get("locator")):
        findings.append("source locator missing")
    if not (_nonempty(source.get("revision")) or _nonempty(source.get("sha256"))):
        findings.append("immutable source revision or sha256 missing")

    lic = descriptor.get("license", {})
    for field in ("declared", "concluded", "effective"):
        if _unknown(lic.get(field)):
            findings.append(f"{field} license unknown")
    detected = lic.get("detected")
    if not isinstance(detected, list) or not detected:
        findings.append("detected license evidence missing")
    elif any(_unknown(x) for x in detected):
        findings.append("detected license contains unknown value")

    rights = descriptor.get("rights", {})
    for field in ("modification_allowed", "redistribution_allowed", "commercial_use_allowed"):
        if not isinstance(rights.get(field), bool):
            findings.append(f"{field} must be explicit boolean")

    obligations = descriptor.get("obligations", {})
    for field in ("attribution_required", "source_offer_required", "entitlement_required"):
        if not isinstance(obligations.get(field), bool):
            findings.append(f"{field} must be explicit boolean")

    unresolved = obligations.get("unresolved", [])
    if not isinstance(unresolved, list):
        findings.append("unresolved obligations malformed")
        unresolved = []
    if unresolved:
        findings.append("unresolved rights obligations")

    if obligations.get("entitlement_required") is True and not _nonempty(obligations.get("entitlement_reference")):
        findings.append("required commercial entitlement reference missing")

    if descriptor.get("raw_secret_material_present") is True:
        findings.append("raw secret material forbidden in rights descriptor")

    disposition = descriptor.get("disposition")
    if disposition not in DISPOSITIONS:
        findings.append("rights disposition invalid")

    evidence = descriptor.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(_nonempty(x) for x in evidence):
        findings.append("rights evidence missing")

    valid = not findings
    admitted = (
        valid
        and disposition in RELEASE_DISPOSITIONS
        and rights.get("redistribution_allowed") is True
        and rights.get("commercial_use_allowed") is True
    )
    return {
        "result": "PASS" if valid else "FAIL",
        "descriptor_valid": valid,
        "admitted_for_release": admitted,
        "disposition": disposition,
        "findings": findings,
        "policy_id": policy.get("id"),
    }


def evaluate_release_receipt(receipt: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []

    if receipt.get("schema") != RELEASE_SCHEMA:
        findings.append("release receipt schema mismatch")

    audit = receipt.get("repository_audit", {})
    if audit.get("status") != "PASS":
        findings.append("repository rights audit not PASS")

    sbom = receipt.get("sbom", {})
    if sbom.get("spdx_status") != "GENERATED":
        findings.append("SPDX SBOM missing")
    if sbom.get("cyclonedx_status") != "GENERATED":
        findings.append("CycloneDX SBOM missing")

    notices = receipt.get("notices", {})
    if notices.get("third_party_notice_status") != "GENERATED":
        findings.append("third-party notice missing")

    obligations = receipt.get("obligations", {})
    for field in (
        "attribution_resolved",
        "source_offer_resolved",
        "entitlements_resolved",
    ):
        if obligations.get(field) is not True:
            findings.append(f"{field} is not resolved")

    counts = receipt.get("counts", {})
    for field in ("unknown_license_count", "unresolved_conflict_count"):
        if counts.get(field) != 0:
            findings.append(f"{field} must be zero")

    passed = not findings
    return {
        "result": "PASS" if passed else "FAIL",
        "release_eligible": passed,
        "findings": findings,
        "policy_id": policy.get("id"),
    }
