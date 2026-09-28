#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_authenticated_approval import (
    REQUIREMENTS,
    RECEIPT_SCHEMA,
    GRANT_SCHEMA,
    SECURITY_AUTHORITY,
    TRUST_PROFILE,
)
from fa3_release_baseline import module_active_capability_count

POLICY = "canonical/authenticated-approval-enforcement.json"
CAPABILITY_COUNT = module_active_capability_count(__file__)


def _load(root: Path) -> dict[str, Any]:
    return json.loads((root / POLICY).read_text(encoding="utf-8"))


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def evaluate(root: Path) -> dict[str, Any]:
    policy = _load(root)
    rules = set(policy.get("invariants", []))
    checks = [
        _check("baseline", policy.get("capability_count") == CAPABILITY_COUNT == 175, "active capability baseline remains 175"),
        _check("zero-delta", policy.get("new_capabilities") == 0 and policy.get("new_architectural_authorities") == 0, "no capability/authority delta"),
        _check("identity-authority-separation", policy.get("identity_trust_profile") == TRUST_PROFILE and policy.get("authorization_authority") == SECURITY_AUTHORITY, "PKI identity and Security Governance authorization remain separate"),
        _check("boolean-fields-rejected", "BOOLEAN_SIGNED_APPROVED_INDEPENDENT_FIELDS_ARE_NOT_AUTHORITY_EVIDENCE" in rules, "boolean approval fields are not authority evidence"),
        _check("certificate-not-authorization", "CERTIFICATE_ISSUANCE_DOES_NOT_GRANT_APPROVAL_ROLE" in rules, "certificate issuance does not grant role"),
        _check("security-role-grant", "SECURITY_GOVERNANCE_SIGNED_ROLE_GRANT_REQUIRED" in rules, "signed Security Governance role grant required"),
        _check("model-designation-scope", "MODEL_ROUTER_DESIGNATION_ROLE_GRANTS_REQUIRE_DISTINCT_SCOPE_AND_ROLE" in rules, "native model approval scope and role separate from release promotion"),
        _check("content-binding", "PAYLOAD_SHA256_MUST_MATCH_CANONICAL_PAYLOAD" in rules and "RECEIPT_SIGNATURE_MUST_VERIFY_OVER_CANONICAL_CONTENT" in rules, "payload digest and receipt signature bind content"),
        _check("source-binding", "SOURCE_COMMIT_MUST_MATCH_CURRENT_REPOSITORY_HEAD" in rules, "receipt is exact-source-bound"),
        _check("freshness", "RECEIPT_AND_ROLE_GRANT_MUST_BE_FRESH" in rules, "receipt and role grant freshness required"),
        _check("single-use", "PROMOTION_APPROVAL_RECEIPTS_ARE_SINGLE_USE" in rules and "PROMOTION_CONSUMPTION_LEDGER_IS_FAIL_CLOSED" in rules, "promotion approval replay protection required"),
        _check("independence", "INDEPENDENT_REVIEWER_IDENTITY_MUST_DIFFER_FROM_PRODUCER_IDENTITY" in rules, "independence derives from authenticated identities"),
        _check("human-promoter", "HUMAN_PROMOTION_REQUIRES_HUMAN_IDENTITY_CLASS" in rules, "human promotion requires human identity class"),
        _check("receipt-schema", RECEIPT_SCHEMA == "fa3.authenticated-approval-receipt.v2", "authenticated receipt schema v2"),
        _check("grant-schema", GRANT_SCHEMA == "fa3.authorization-role-grant.v1", "role grant schema v1"),
        _check("acceptance-surfaces", set(REQUIREMENTS) == {"host-fingerprint.json","source-exclusion-receipt.json","release-integrity.json","independent-review.json","human-promotion-receipt.json"}, "all trust-sensitive acceptance receipts covered"),
    ]
    passed = all(x["status"] == "PASS" for x in checks)
    return {
        "schema": "fa3.authenticated-approval-gate-report.v1",
        "gate_id": "FA3-GATE-AUTHENTICATED-APPROVAL-001",
        "result": "PASS" if passed else "FAIL",
        "current_host_runtime_promotion_claim": False,
        "summary": {"passed": sum(x["status"] == "PASS" for x in checks), "total": len(checks)},
        "checks": checks,
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    path = root / "reports/authenticated-approval-gate-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
