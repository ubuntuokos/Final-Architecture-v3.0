#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LIFECYCLE = {
    "DECLARED", "VALIDATING", "READY", "RUNNING", "WAITING_APPROVAL",
    "SUSPENDED", "COMPLETED", "FAILED", "PROMOTION_CANDIDATE", "ARCHIVED",
}
PROMOTION_TARGETS = {"BLUEPRINT_TEMPLATE", "PLUGIN", "EXTENSION", "APPLICATION"}


@dataclass(frozen=True)
class CapsuleValidation:
    ok: bool
    findings: tuple[str, ...]


def validate_capsule(spec: dict[str, Any]) -> CapsuleValidation:
    findings: list[str] = []
    required = (
        "capsule_id", "application_id", "objective", "blueprint_ref", "workload_task_ref",
        "workspace_ref", "capability_grant_ref", "work_context_ref", "lifecycle_state",
        "provenance_refs",
    )
    for field in required:
        if field not in spec:
            findings.append("missing:" + field)
    if spec.get("lifecycle_state") not in LIFECYCLE:
        findings.append("invalid_lifecycle_state")
    for forbidden in (
        "owns_application_authority", "owns_project_truth", "owns_task_truth",
        "owns_permission_authority", "owns_durable_workflow_authority",
    ):
        if spec.get(forbidden) is True:
            findings.append("forbidden_authority:" + forbidden)
    if spec.get("capability_scope_expansion") is True:
        findings.append("capability_scope_expansion_forbidden")
    if spec.get("direct_tool_bypass") is True:
        findings.append("direct_tool_bypass_forbidden")
    if spec.get("embedded_secret_values") is True:
        findings.append("embedded_secret_values_forbidden")
    return CapsuleValidation(not findings, tuple(findings))


def speculative_result_can_commit(*, approval_satisfied: bool, uaf_authorized: bool,
                                  canonical_target_authorized: bool) -> bool:
    return approval_satisfied and uaf_authorized and canonical_target_authorized


def promotion_eligible(review: dict[str, bool], target: str) -> bool:
    required = {
        "functional_reuse", "security", "license_rights", "capability_compatibility",
        "gui_compatibility", "application_compatibility_propagation", "test_and_rollback",
    }
    return target in PROMOTION_TARGETS and all(review.get(key) is True for key in required)
