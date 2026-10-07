#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ENTITY_KINDS = {
    "GOAL", "PROGRAM", "PRODUCTION", "PROJECT", "WORKSTREAM", "MILESTONE",
    "TASK", "CHECK_IN", "RISK", "BLOCKER", "DECISION_REQUEST", "ACTIVITY",
}
CHECKIN_STATUS = {
    "ON_TRACK", "AT_RISK", "BLOCKED", "WAITING_APPROVAL", "OVERDUE", "COMPLETE",
}
ALLOWED_PARENTS = {
    "PROGRAM": {"GOAL"},
    "PRODUCTION": {"GOAL", "PROGRAM"},
    "PROJECT": {"GOAL", "PROGRAM", "PRODUCTION"},
    "WORKSTREAM": {"PROJECT", "PRODUCTION"},
    "MILESTONE": {"PROJECT", "WORKSTREAM"},
    "TASK": {"PROJECT", "WORKSTREAM", "MILESTONE"},
    "CHECK_IN": {"GOAL", "PROGRAM", "PRODUCTION", "PROJECT", "WORKSTREAM", "MILESTONE", "TASK"},
    "RISK": {"GOAL", "PROGRAM", "PRODUCTION", "PROJECT", "WORKSTREAM", "MILESTONE", "TASK"},
    "BLOCKER": {"PROJECT", "WORKSTREAM", "MILESTONE", "TASK"},
    "DECISION_REQUEST": {"GOAL", "PROGRAM", "PRODUCTION", "PROJECT", "WORKSTREAM", "MILESTONE", "TASK"},
    "ACTIVITY": {"GOAL", "PROGRAM", "PRODUCTION", "PROJECT", "WORKSTREAM", "MILESTONE", "TASK"},
}

@dataclass(frozen=True)
class Validation:
    ok: bool
    findings: tuple[str, ...]


def validate_entity(entity: dict[str, Any], parent: dict[str, Any] | None = None) -> Validation:
    findings: list[str] = []
    for field in ("canonical_id", "kind", "title", "state", "project_workspace_scope", "provenance_refs"):
        if field not in entity:
            findings.append("missing:" + field)
    kind = entity.get("kind")
    if kind not in ENTITY_KINDS:
        findings.append("invalid_kind")
    if entity.get("provider_owns_canonical_identity") is True:
        findings.append("provider_canonical_identity_forbidden")
    if parent is not None:
        parent_kind = parent.get("kind")
        allowed = ALLOWED_PARENTS.get(str(kind), set())
        if parent_kind not in allowed:
            findings.append("invalid_parent_relation")
        if entity.get("parent_ref") != parent.get("canonical_id"):
            findings.append("parent_ref_mismatch")
    return Validation(not findings, tuple(findings))


def validate_check_in(value: dict[str, Any]) -> Validation:
    findings: list[str] = []
    required = (
        "canonical_check_in_id", "subject_ref", "status", "completed_since_last",
        "next_actions", "blockers", "risks", "decisions_needed", "actor_identity",
        "timestamp", "provenance_refs",
    )
    for field in required:
        if field not in value:
            findings.append("missing:" + field)
    if value.get("status") not in CHECKIN_STATUS:
        findings.append("invalid_status")
    if value.get("ai_summary_is_source_truth") is True:
        findings.append("ai_summary_cannot_replace_source")
    return Validation(not findings, tuple(findings))


def canonical_path(*, goal: str | None = None, program: str | None = None,
                   production: str | None = None, project: str | None = None,
                   workstream: str | None = None, milestone: str | None = None,
                   task: str | None = None) -> list[str]:
    ordered = [goal, program, production, project, workstream, milestone, task]
    return [value for value in ordered if value]
