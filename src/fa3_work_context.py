#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REFERENCE_FIELDS = (
    "organization_ref", "production_ref", "goal_ref", "project_ref", "workstream_ref",
    "milestone_ref", "task_ref", "workspace_ref", "workflow_ref", "actor_ref", "agent_ref",
    "budget_ref",
)
COLLECTION_FIELDS = ("asset_refs", "artifact_refs", "approval_refs")


@dataclass(frozen=True)
class ContextValidation:
    ok: bool
    findings: tuple[str, ...]


def validate_work_context(value: dict[str, Any]) -> ContextValidation:
    findings: list[str] = []
    for field in ("context_id", "application_id", "project_workspace_scope", "provenance_refs"):
        if field not in value:
            findings.append("missing:" + field)
    if not isinstance(value.get("provenance_refs"), list):
        findings.append("provenance_refs_must_be_list")
    for field in REFERENCE_FIELDS:
        ref = value.get(field)
        if ref is not None and (not isinstance(ref, str) or not ref):
            findings.append("invalid_reference:" + field)
    for field in COLLECTION_FIELDS:
        refs = value.get(field, [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            findings.append("invalid_reference_collection:" + field)
    if value.get("owns_project_truth") is True or value.get("owns_task_truth") is True:
        findings.append("shadow_work_authority_forbidden")
    if value.get("agent_scope_expansion") is True:
        findings.append("agent_scope_expansion_forbidden")
    return ContextValidation(not findings, tuple(findings))


def project_for_application(context: dict[str, Any], allowed_fields: set[str]) -> dict[str, Any]:
    result = {
        "context_id": context["context_id"],
        "application_id": context["application_id"],
        "project_workspace_scope": context["project_workspace_scope"],
        "provenance_refs": list(context.get("provenance_refs", [])),
    }
    for field in REFERENCE_FIELDS + COLLECTION_FIELDS:
        if field in allowed_fields and field in context:
            result[field] = context[field]
    return result


def to_os_event_enrichment(context: dict[str, Any], *, action: str, subject_kind: str, subject_ref: str) -> dict[str, Any]:
    validation = validate_work_context(context)
    if not validation.ok:
        raise ValueError(",".join(validation.findings))
    return {
        "schema_version": "1.0.0",
        "action": action,
        "subject": {"kind": subject_kind, "reference": subject_ref},
        "application_id": context["application_id"],
        "workstream_id": context.get("workstream_ref"),
        "workflow_reference": context.get("workflow_ref"),
        "capture_policy_id": "FA3-OS-POLICY-001",
        "provenance": {"source_class": "FA3_NATIVE", "source_reference": context["context_id"]},
        "confidence": 1.0,
        "tags": ["work-context"],
    }
