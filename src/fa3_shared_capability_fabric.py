#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGISTRY_PATH = "canonical/FA3-SHARED-CAPABILITY-FABRIC-001.json"
CAP_RE = re.compile(r"^CAP-(\d{3})$")
STATES = {"ACTIVE", "VISIBLE_DISABLED", "HIDDEN", "DENIED", "UNAVAILABLE"}

@dataclass(frozen=True)
class SliceDecision:
    state: str
    reasons: tuple[str, ...]

def load_registry(root: Path) -> dict[str, Any]:
    return json.loads((Path(root) / REGISTRY_PATH).read_text(encoding="utf-8"))

def capability_id_valid(value: str, baseline: int = 175) -> bool:
    match = CAP_RE.fullmatch(str(value))
    return bool(match and 1 <= int(match.group(1)) <= baseline)

def slice_by_key(registry: dict[str, Any], key: str) -> dict[str, Any] | None:
    return next((item for item in registry.get("slices", []) if item.get("key") == key), None)

def resolve_slice(slice_record: dict[str, Any], context: dict[str, Any]) -> SliceDecision:
    key = slice_record.get("key")
    operation = context.get("operation")

    # Email compose/send is a universal shared surface across FA3 applications.
    if key == "email.management" and operation in {"email.send", "email.compose", "email.attach-context"}:
        if context.get("authority_allowed") is not True:
            return SliceDecision("DENIED", ("authority-denied",))
        if context.get("policy_allowed") is not True:
            return SliceDecision("DENIED", ("policy-denied",))
        if context.get("provider_available") is False:
            return SliceDecision("UNAVAILABLE", ("email-provider-unavailable",))
        if operation == "email.send" and context.get("explicit_send_intent") is not True:
            return SliceDecision("VISIBLE_DISABLED", ("explicit-send-intent-required",))
        return SliceDecision("ACTIVE", ())

    if not context.get("application_relevant", False):
        return SliceDecision("HIDDEN", ("not-applicable-to-application",))
    if not context.get("project_relevant", True):
        return SliceDecision("HIDDEN", ("not-applicable-to-project",))

    activation_class = slice_record.get("activation_class", "GENERAL")
    external_selected = context.get("external_service_selected") is True
    cost_context = context.get("cost_context") is True or external_selected

    if activation_class == "COST_CONTEXT" and not cost_context:
        return SliceDecision("HIDDEN", ("no-cost-context",))
    if activation_class == "EXTERNAL_SERVICE_CONTEXT" and not external_selected:
        return SliceDecision("HIDDEN", ("no-external-service-context",))

    if context.get("authority_allowed") is not True:
        return SliceDecision("DENIED", ("authority-denied",))
    if context.get("policy_allowed") is not True:
        return SliceDecision("DENIED", ("policy-denied",))
    if context.get("ai_required") is True and context.get("ai_policy_allowed") is not True:
        return SliceDecision("DENIED", ("ai-policy-denied",))
    if context.get("network_required") is True and context.get("network_allowed") is not True:
        return SliceDecision("DENIED", ("network-policy-denied",))
    if context.get("hardware_required") is True and context.get("hardware_allowed") is not True:
        return SliceDecision("DENIED", ("hardware-policy-denied",))
    if context.get("service_available") is False:
        return SliceDecision("UNAVAILABLE", ("service-unavailable",))

    reasons: list[str] = []
    if context.get("workflow_allowed") is not True:
        reasons.append("workflow-state-not-ready")
    if context.get("role_allowed") is not True:
        reasons.append("role-not-ready")
    if key == "purchase.order" and context.get("explicit_authorization") is not True:
        reasons.append("explicit-purchase-authorization-required")
    if context.get("approval_required") is True and context.get("approved") is not True:
        reasons.append("approval-required")
    if reasons:
        return SliceDecision("VISIBLE_DISABLED", tuple(reasons))
    return SliceDecision("ACTIVE", ())

def resolve(root: Path, slice_key: str, context: dict[str, Any]) -> SliceDecision:
    registry = load_registry(root)
    record = slice_by_key(registry, slice_key)
    if record is None:
        return SliceDecision("DENIED", ("unknown-shared-capability-slice",))
    return resolve_slice(record, context)
