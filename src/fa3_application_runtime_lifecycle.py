#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fa3_application_agent_adapter import application_ready_admission

TRANSITIONS = {
    "INSTALLED": {"CONFIGURING", "READY", "REMOVING"},
    "CONFIGURING": {"READY", "FAILED"},
    "READY": {"STARTING", "UPDATING", "REMOVING"},
    "STARTING": {"RUNNING", "FAILED"},
    "RUNNING": {"SUSPENDING", "STOPPING", "FAILED"},
    "SUSPENDING": {"SUSPENDED", "RUNNING", "FAILED"},
    "SUSPENDED": {"RESUMING", "STOPPING", "UPDATING", "REMOVING"},
    "RESUMING": {"RUNNING", "FAILED"},
    "STOPPING": {"STOPPED", "FAILED"},
    "STOPPED": {"STARTING", "UPDATING", "REMOVING"},
    "UPDATING": {"READY", "STOPPED", "ROLLBACK_PENDING", "FAILED"},
    "ROLLBACK_PENDING": {"ROLLING_BACK"},
    "ROLLING_BACK": {"READY", "STOPPED", "FAILED"},
    "REMOVING": {"REMOVED", "FAILED"},
    "FAILED": {"ROLLBACK_PENDING", "STOPPING", "REMOVING"},
}

@dataclass(frozen=True)
class LifecycleDecision:
    allowed: bool
    reason: str


def can_transition(current: str, requested: str) -> bool:
    return requested in TRANSITIONS.get(current, set())


def evaluate_transition(request: dict[str, Any], *, root: Path | None = None) -> LifecycleDecision:
    required = (
        "application_id", "current_state", "requested_state", "actor_identity",
        "operation_ref", "authorization_decision", "source_revision", "provenance_refs",
    )
    missing = [key for key in required if key not in request]
    if missing:
        return LifecycleDecision(False, "missing:" + ",".join(missing))
    if request["authorization_decision"] != "ALLOW":
        return LifecycleDecision(False, "authorization_required")
    if not str(request["operation_ref"]).startswith("application.lifecycle."):
        return LifecycleDecision(False, "typed_lifecycle_operation_required")
    if not can_transition(str(request["current_state"]), str(request["requested_state"])):
        return LifecycleDecision(False, "transition_not_allowed")
    if request["requested_state"] == "READY":
        communication = application_ready_admission(str(request["application_id"]), root=root)
        if not communication.allowed:
            return LifecycleDecision(False, "application_communication_admission_required:" + communication.reason)
    if request["requested_state"] == "SUSPENDED" and request.get("suspend_supported") is not True:
        return LifecycleDecision(False, "suspend_not_supported")
    if request["current_state"] == "SUSPENDED" and request["requested_state"] == "RESUMING":
        if request.get("runtime_resources_required") is True and request.get("fresh_resource_admission") is not True:
            return LifecycleDecision(False, "fresh_resource_admission_required")
    if request["current_state"] == "UPDATING" and request["requested_state"] in {"READY", "STOPPED"}:
        if request.get("update_evidence_pass") is not True:
            return LifecycleDecision(False, "update_evidence_required")
    return LifecycleDecision(True, "ALLOW")


def runtime_states() -> set[str]:
    return set(TRANSITIONS) | {state for targets in TRANSITIONS.values() for state in targets}
