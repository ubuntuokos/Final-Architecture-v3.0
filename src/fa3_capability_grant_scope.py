#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

APPROVAL_VALUES = {"NOT_REQUIRED_BY_POLICY", "REQUIRED", "SATISFIED"}


@dataclass(frozen=True)
class GrantDecision:
    allowed: bool
    reason: str


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_grant(grant: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    required = (
        "grant_id", "actor_identity", "operations", "resource_scope",
        "project_workspace_scope", "delegator_identity", "valid_from", "expires_at",
        "approval_binding", "budget_envelope", "provenance_refs",
    )
    for field in required:
        if field not in grant:
            findings.append("missing:" + field)
    for field in ("operations", "resource_scope", "project_workspace_scope"):
        value = grant.get(field)
        if not isinstance(value, list) or not value:
            findings.append(field + "_must_be_nonempty_allowlist")
    if grant.get("actor_inherits_full_delegator_authority") is True:
        findings.append("full_authority_inheritance_forbidden")
    approval = grant.get("approval_binding")
    if approval not in APPROVAL_VALUES:
        findings.append("invalid_approval_binding")
    try:
        if _parse_time(str(grant.get("valid_from"))) >= _parse_time(str(grant.get("expires_at"))):
            findings.append("invalid_time_window")
    except Exception:
        findings.append("invalid_time_format")
    budget = grant.get("budget_envelope")
    if not isinstance(budget, dict):
        findings.append("budget_envelope_must_be_object")
    else:
        for key, value in budget.items():
            if not isinstance(value, (int, float)) or value < 0:
                findings.append("invalid_budget:" + str(key))
    return findings


def authorize(
    grant: dict[str, Any],
    *,
    actor_identity: str,
    operation: str,
    resource: str,
    project_workspace: str,
    now: datetime,
    approval_satisfied: bool = False,
) -> GrantDecision:
    findings = validate_grant(grant)
    if findings:
        return GrantDecision(False, "invalid_grant:" + ",".join(findings))
    if actor_identity != grant["actor_identity"]:
        return GrantDecision(False, "actor_mismatch")
    if operation not in set(grant["operations"]):
        return GrantDecision(False, "operation_out_of_scope")
    if resource not in set(grant["resource_scope"]):
        return GrantDecision(False, "resource_out_of_scope")
    if project_workspace not in set(grant["project_workspace_scope"]):
        return GrantDecision(False, "project_workspace_out_of_scope")
    current = now.astimezone(timezone.utc)
    if current < _parse_time(grant["valid_from"]) or current >= _parse_time(grant["expires_at"]):
        return GrantDecision(False, "grant_not_active")
    if grant["approval_binding"] == "REQUIRED" and not approval_satisfied:
        return GrantDecision(False, "approval_required")
    return GrantDecision(True, "ALLOW")


def subgrant_is_subset(parent: dict[str, Any], child: dict[str, Any]) -> bool:
    return (
        set(child.get("operations", [])) <= set(parent.get("operations", []))
        and set(child.get("resource_scope", [])) <= set(parent.get("resource_scope", []))
        and set(child.get("project_workspace_scope", [])) <= set(parent.get("project_workspace_scope", []))
    )
