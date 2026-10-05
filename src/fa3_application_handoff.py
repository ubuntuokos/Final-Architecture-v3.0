#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

KINDS = {
    "OPERATION_REQUEST", "OPERATION_RESULT", "EVENT_NOTIFICATION", "ARTIFACT_HANDOFF",
    "INTERMEDIATE_RESULT", "CANCELLATION_REQUEST",
}


@dataclass(frozen=True)
class HandoffValidation:
    ok: bool
    findings: tuple[str, ...]


def validate_handoff(value: dict[str, Any]) -> HandoffValidation:
    findings: list[str] = []
    required = (
        "message_id", "kind", "source_application", "target_application", "correlation_id",
        "operation_ref", "work_context_ref", "capability_grant_ref", "provenance_refs",
    )
    for field in required:
        if field not in value:
            findings.append("missing:" + field)
    if value.get("kind") not in KINDS:
        findings.append("invalid_kind")
    if value.get("source_application") == value.get("target_application"):
        findings.append("self_handoff_requires_local_operation_path")
    if value.get("handoff_is_authorization") is True:
        findings.append("handoff_authorization_forbidden")
    if value.get("sender_expands_receiver_scope") is True:
        findings.append("receiver_scope_expansion_forbidden")
    if value.get("kind") == "ARTIFACT_HANDOFF":
        artifacts = value.get("artifact_refs")
        if not isinstance(artifacts, list) or not artifacts:
            findings.append("artifact_handoff_requires_artifact_refs")
        if value.get("provenance_preserved") is not True:
            findings.append("artifact_provenance_required")
    if value.get("kind") == "INTERMEDIATE_RESULT" and value.get("canonical_commit") is True:
        findings.append("intermediate_result_cannot_be_canonical_commit")
    return HandoffValidation(not findings, tuple(findings))


def can_dispatch_effect(value: dict[str, Any], *, grant_valid: bool, uaf_action_resolved: bool) -> bool:
    if not validate_handoff(value).ok:
        return False
    if value.get("kind") != "OPERATION_REQUEST":
        return False
    return grant_valid and uaf_action_resolved


def correlate(messages: list[dict[str, Any]], correlation_id: str) -> list[dict[str, Any]]:
    return [message for message in messages if message.get("correlation_id") == correlation_id]
