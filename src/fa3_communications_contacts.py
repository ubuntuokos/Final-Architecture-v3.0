#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable

PROFILE_ID = "FA3-COMMUNICATIONS-CONTACTS-SHARED-001"

BASE_GATES = {
    "identity", "authentication", "authorization", "context_scope", "layer_guard",
    "application_boundary", "data_classification", "privacy", "secret_broker",
    "communication_security", "audit_evidence", "software_coexistence",
    "hardware_safety", "current_host",
}
AI_GATES = {
    "ai_permission", "ai_context_isolation", "prompt_injection", "context_minimization",
    "secret_filter", "pii_filter", "model_router", "provider_admission", "hrb",
    "tool_permission", "output_validation",
}
PERMISSIONS = {
    "mail.read": "mail.read", "mail.compose": "mail.compose", "mail.send": "mail.send",
    "mail.forward": "mail.forward", "mail.assign": "mail.assign", "mail.note": "mail.note",
    "contact.read": "contacts.read", "contact.write": "contacts.write",
    "contact.export": "contacts.export", "contacts.export_all": "contacts.export_all",
    "mail.read_all": "mail.read_all", "mail.delete": "mail.delete",
    "mailbox.admin": "mailbox.admin", "permissions.admin": "permissions.admin",
    "ai.mail.summarize": "ai.mail.summarize",
    "ai.mail.draft_reply": "ai.mail.draft_reply",
    "ai.contact.deduplicate": "ai.contact.deduplicate",
}
EMBEDDED_FORBIDDEN = {"mailbox.admin", "permissions.admin", "contacts.export_all", "mail.read_all"}
AI_OPERATIONS = {x for x in PERMISSIONS if x.startswith("ai.")}
EGRESS_OPERATIONS = {"mail.send", "mail.forward", "contact.export", "contacts.export_all"}
HIGH_RISK = {"mail.send", "mail.delete", "contact.export", "contacts.export_all", "mailbox.admin", "permissions.admin"}

@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    effective_permissions: tuple[str, ...]
    missing_gates: tuple[str, ...] = ()
    reason: str = ""

def _intersection(groups: Iterable[Iterable[str]]) -> set[str]:
    rows = [set(g) for g in groups]
    if not rows:
        return set()
    out = rows[0].copy()
    for row in rows[1:]:
        out &= row
    return out

def authorize(request: dict[str, Any]) -> Decision:
    operation = str(request.get("operation") or "")
    surface = str(request.get("surface_mode") or "")
    if operation not in PERMISSIONS and operation not in EMBEDDED_FORBIDDEN:
        return Decision(False, "UNKNOWN_OPERATION", ())
    if surface not in {"FULL", "EMBEDDED"}:
        return Decision(False, "UNKNOWN_SURFACE_MODE", ())
    if surface == "EMBEDDED" and operation in EMBEDDED_FORBIDDEN:
        return Decision(False, "EMBEDDED_OPERATION_FORBIDDEN", ())
    if surface == "EMBEDDED" and not request.get("context_ids"):
        return Decision(False, "EMBEDDED_CONTEXT_REQUIRED", ())

    effective = _intersection([
        request.get("user_permissions", []), request.get("role_permissions", []),
        request.get("application_permissions", []), request.get("context_permissions", []),
        request.get("data_permissions", []),
    ])
    permission = PERMISSIONS.get(operation)
    if permission and permission not in effective:
        return Decision(False, "PERMISSION_INTERSECTION_DENY", tuple(sorted(effective)))

    required = set(BASE_GATES)
    if request.get("has_attachment"):
        required.add("attachment_security")
    if request.get("external_message"):
        required.add("anti_phishing")
    if operation in EGRESS_OPERATIONS:
        required.add("dlp")
    if operation in HIGH_RISK:
        required.add("explicit_approval")
    if operation in {"mail.send", "mail.forward"}:
        required.add("provider_admission")
    if operation in AI_OPERATIONS:
        required |= AI_GATES
        policy = request.get("ai_policy", {})
        for level in ("global", "application", "module", "capability", "operation"):
            if policy.get(level) is not True:
                return Decision(False, "AI_DISABLED_OR_NOT_EXPLICITLY_ENABLED", tuple(sorted(effective)), reason=level)
        if request.get("external_message") is not True and request.get("input_classification") not in {"LOCAL_TRUSTED", "LOCAL_UNTRUSTED"}:
            return Decision(False, "AI_INPUT_CLASSIFICATION_REQUIRED", tuple(sorted(effective)))
        if request.get("external_message") is True and request.get("message_content_as_system_instruction") is True:
            return Decision(False, "UNTRUSTED_CONTENT_AUTHORITY_ESCALATION_DENIED", tuple(sorted(effective)))
        requested = request.get("requested_provider")
        selected = request.get("selected_provider")
        if requested and selected and requested != selected:
            return Decision(False, "SILENT_PROVIDER_FALLBACK_DENIED", tuple(sorted(effective)))

    gates = request.get("security_gates", {})
    missing = tuple(sorted(g for g in required if gates.get(g) is not True))
    if missing:
        return Decision(False, "SECURITY_GATE_DENY", tuple(sorted(effective)), missing)
    return Decision(True, "ALLOW", tuple(sorted(effective)))

def embedded_projection(*, visible_items: Iterable[str], allowed_items: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(visible_items) & set(allowed_items)))

def reference_cases() -> dict[str, bool]:
    p = {
        "mail.read", "mail.compose", "mail.send", "mail.forward", "mail.assign", "mail.note",
        "contacts.read", "contacts.write", "contacts.export", "ai.mail.summarize",
        "ai.mail.draft_reply", "ai.contact.deduplicate",
    }
    gates = {g: True for g in BASE_GATES | {"dlp", "explicit_approval", "provider_admission", "attachment_security", "anti_phishing"} | AI_GATES}
    base = dict(surface_mode="FULL", operation="mail.send", user_permissions=p, role_permissions=p,
                application_permissions=p, context_permissions=p, data_permissions=p, security_gates=gates)
    embedded = dict(base, surface_mode="EMBEDDED", operation="mail.read", context_ids=["project:A"])
    ai = dict(base, operation="ai.mail.summarize", external_message=True,
              input_classification="EXTERNAL_UNTRUSTED",
              ai_policy={x: True for x in ("global", "application", "module", "capability", "operation")},
              requested_provider="provider:a", selected_provider="provider:a")
    return {
        "full_send_allowed": authorize(base).allowed,
        "embedded_context_allowed": authorize(embedded).allowed,
        "embedded_missing_context_denied": not authorize({**embedded, "context_ids": []}).allowed,
        "permission_union_forbidden": not authorize({**embedded, "role_permissions": []}).allowed,
        "ai_explicit_allowed": authorize(ai).allowed,
        "ai_disabled_denied": not authorize({**ai, "ai_policy": {}}).allowed,
        "prompt_injection_authority_denied": not authorize({**ai, "message_content_as_system_instruction": True}).allowed,
        "silent_provider_fallback_denied": not authorize({**ai, "selected_provider": "provider:b"}).allowed,
        "missing_gate_denied": not authorize({**base, "security_gates": {}}).allowed,
    }
