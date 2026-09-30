#!/usr/bin/env python3
"""Provider-neutral FA3 Communications & Contacts policy core.

This module deliberately performs no SMTP/IMAP/CardDAV/provider I/O. It
materializes the shared context, permission and security boundary. Physical
execution stays behind UAF/provider admission and Current Host evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

SECURITY_GATE_CHAIN = (
    "IDENTITY",
    "AUTHENTICATION",
    "AUTHORIZATION",
    "CONTEXT_SCOPE",
    "LAYER_GUARD",
    "APPLICATION_BOUNDARY",
    "DATA_CLASSIFICATION_PRIVACY",
    "SECRET_BROKER",
    "COMMUNICATION_SECURITY",
    "ATTACHMENT_CONTENT_SECURITY",
    "ANTI_ABUSE_PHISHING",
    "AI_PERMISSION",
    "AI_CONTEXT_ISOLATION",
    "PROMPT_INJECTION_TOOL_USE",
    "MODEL_ROUTER_PROVIDER_ADMISSION",
    "HRB_RESOURCE",
    "PLUGIN_EXTENSION_SECURITY",
    "SOFTWARE_COEXISTENCE",
    "HARDWARE_SAFETY_ENVELOPE",
    "AUDIT_EVIDENCE",
    "CURRENT_HOST",
)

PERMISSION_DIMENSIONS = (
    "USER",
    "ROLE",
    "APPLICATION",
    "PROJECT_WORKSPACE",
    "WORKFLOW",
    "DATA_CLASSIFICATION",
    "COMMUNICATION",
)

EMBEDDED_FORBIDDEN = frozenset({
    "mailbox.enumerate.global",
    "contacts.enumerate.global",
    "account.configure",
    "provider.configure",
    "contact.export.global",
    "permission.admin",
    "mailbox.admin",
})

MUTATING_SEND_OPERATIONS = frozenset({"email.send", "email.reply", "email.forward"})

AI_OPERATIONS = frozenset({
    "AI.Mail.Summarize",
    "AI.Mail.DraftReply",
    "AI.Mail.Translate",
    "AI.Mail.Classify",
    "AI.Mail.ExtractTasks",
    "AI.Mail.ExtractContacts",
    "AI.Mail.Priority",
    "AI.Mail.PhishingAssist",
    "AI.Thread.Summarize",
    "AI.Contact.Deduplicate",
    "AI.Contact.Enrich",
    "AI.Search.Semantic",
})

HIGH_RISK_AGENT_OPERATIONS = frozenset({
    "email.send",
    "email.delete",
    "contact.export.global",
    "permission.admin",
    "mailbox.admin",
})


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "code": self.code, "detail": self.detail}


def _allowed_by_dimension(values: Iterable[str], operation: str) -> bool:
    allowed = set(values)
    return "*" in allowed or operation in allowed


def permission_intersection(
    permission_sets: Mapping[str, Iterable[str]], operation: str
) -> Decision:
    """Deny unless every mandatory dimension explicitly allows operation."""
    for dimension in PERMISSION_DIMENSIONS:
        values = permission_sets.get(dimension)
        if values is None:
            return Decision(False, "MISSING_PERMISSION_DIMENSION", dimension)
        if not _allowed_by_dimension(values, operation):
            return Decision(False, "PERMISSION_INTERSECTION_DENY", dimension)
    return Decision(True, "PERMISSION_INTERSECTION_PASS")


def gate_chain_decision(gate_results: Mapping[str, str]) -> Decision:
    """Every applicable communications security gate is fail-closed."""
    for gate in SECURITY_GATE_CHAIN:
        state = gate_results.get(gate)
        if state != "PASS":
            return Decision(False, "SECURITY_GATE_DENY", f"{gate}:{state or 'MISSING'}")
    return Decision(True, "SECURITY_GATE_CHAIN_PASS")


def ai_decision(request: Mapping[str, Any]) -> Decision:
    operation = str(request.get("ai_operation") or request.get("operation") or "")
    if operation not in AI_OPERATIONS:
        return Decision(False, "UNKNOWN_AI_OPERATION", operation)

    controls = request.get("ai_controls")
    if not isinstance(controls, Mapping):
        return Decision(False, "AI_CONTROLS_MISSING")
    for level in ("GLOBAL", "APPLICATION", "MODULE", "CAPABILITY", "OPERATION"):
        if controls.get(level) is not True:
            return Decision(False, "AI_DENY_WINS", level)

    if request.get("message_content_trust") != "UNTRUSTED":
        return Decision(False, "AI_MESSAGE_TRUST_CLASSIFICATION_REQUIRED")
    if request.get("prompt_injection_clear") is not True:
        return Decision(False, "PROMPT_INJECTION_GATE_DENY")
    if request.get("context_minimized") is not True:
        return Decision(False, "AI_CONTEXT_MINIMIZATION_REQUIRED")
    if request.get("secrets_removed") is not True:
        return Decision(False, "AI_SECRET_FILTER_REQUIRED")
    if request.get("pii_policy_pass") is not True:
        return Decision(False, "AI_PII_POLICY_DENY")
    if request.get("model_router_receipt") is not True:
        return Decision(False, "MODEL_ROUTER_RECEIPT_REQUIRED")
    if request.get("direct_provider_selection") is True:
        return Decision(False, "DIRECT_AI_PROVIDER_SELECTION_FORBIDDEN")
    if request.get("provider_switch_fallback") is True:
        return Decision(False, "SILENT_AI_FALLBACK_FORBIDDEN")
    if request.get("external_provider") is True:
        if request.get("provider_admitted") is not True:
            return Decision(False, "AI_PROVIDER_NOT_ADMITTED")
        if request.get("external_egress_allowed") is not True:
            return Decision(False, "AI_EXTERNAL_EGRESS_DENIED")

    return Decision(True, "AI_POLICY_PASS")


def authorize(request: Mapping[str, Any]) -> Decision:
    """Authorize a Communications action without executing it."""
    operation = str(request.get("operation") or "")
    if not operation:
        return Decision(False, "OPERATION_REQUIRED")

    mode = str(request.get("surface_mode") or "")
    if mode not in {"FULL", "EMBEDDED"}:
        return Decision(False, "SURFACE_MODE_INVALID", mode)

    if request.get("direct_provider_execution") is True:
        return Decision(False, "DIRECT_PROVIDER_BYPASS_FORBIDDEN")

    gate_result = gate_chain_decision(request.get("gate_results") or {})
    if not gate_result.allowed:
        return gate_result

    permission_result = permission_intersection(
        request.get("permission_sets") or {}, operation
    )
    if not permission_result.allowed:
        return permission_result

    if mode == "EMBEDDED" and operation in EMBEDDED_FORBIDDEN:
        return Decision(False, "EMBEDDED_GLOBAL_OPERATION_FORBIDDEN", operation)

    if operation in MUTATING_SEND_OPERATIONS:
        if request.get("explicit_send_intent") is not True:
            return Decision(False, "EXPLICIT_SEND_INTENT_REQUIRED")
        if request.get("dlp_decision") not in {"ALLOW", "WARN", "REQUIRE_APPROVAL"}:
            return Decision(False, "OUTBOUND_DLP_DENY")
        if request.get("recipient_policy_pass") is not True:
            return Decision(False, "RECIPIENT_POLICY_DENY")

    ai_operation = request.get("ai_operation")
    if ai_operation is not None:
        ai_result = ai_decision(request)
        if not ai_result.allowed:
            return ai_result

    return Decision(True, "COMMUNICATION_ACTION_AUTHORIZED")


def resource_visible(
    *,
    surface_mode: str,
    resource_contexts: Iterable[str],
    active_contexts: Iterable[str],
    permission_allowed: bool,
) -> bool:
    if not permission_allowed:
        return False
    if surface_mode == "FULL":
        return True
    if surface_mode != "EMBEDDED":
        return False
    return bool(set(resource_contexts) & set(active_contexts))


def attachment_disposition(scan: Mapping[str, Any]) -> str:
    """Return ALLOW/RESTRICT/QUARANTINE/DENY without opening the attachment."""
    if scan.get("malware_scan") == "MALICIOUS" or scan.get("dlp") == "BLOCK":
        return "DENY"

    mandatory = (
        "type_valid",
        "mime_match",
        "size_policy_pass",
        "archive_inspection_pass",
        "active_content_policy_pass",
        "safe_preview_ready",
    )
    if scan.get("malware_scan") != "CLEAN":
        return "QUARANTINE"
    if any(scan.get(field) is None for field in mandatory):
        return "QUARANTINE"
    if any(scan.get(field) is not True for field in mandatory):
        return "RESTRICT"
    if scan.get("dlp") in {"REQUIRE_APPROVAL", "REDACT", "WARN"}:
        return "RESTRICT"
    if scan.get("dlp") != "ALLOW":
        return "QUARANTINE"
    return "ALLOW"


def dlp_disposition(
    classes: Iterable[str],
    *,
    external_recipient: bool,
    approval_present: bool,
) -> str:
    classes = set(classes)
    if "CREDENTIAL" in classes or "SECRET" in classes:
        return "BLOCK"
    sensitive = bool(classes & {
        "PII", "FINANCIAL", "RESTRICTED_PROJECT",
        "CUSTOMER_CONFIDENTIAL", "PRODUCTION_CONFIDENTIAL",
    })
    if external_recipient and sensitive and not approval_present:
        return "REQUIRE_APPROVAL"
    if external_recipient and sensitive:
        return "WARN"
    return "ALLOW"


def ai_untrusted_envelope(message_text: str) -> dict[str, Any]:
    """Envelope external text as data. Never produce executable instructions."""
    return {
        "trust": "UNTRUSTED",
        "role": "external_message_data",
        "content": str(message_text),
        "may_override_system_policy": False,
        "may_authorize_tools": False,
    }


def agent_action_policy(operation: str, *, separately_authorized: bool) -> Decision:
    if operation in HIGH_RISK_AGENT_OPERATIONS and not separately_authorized:
        return Decision(False, "AGENT_HIGH_RISK_SEPARATE_AUTH_REQUIRED", operation)
    return Decision(True, "AGENT_ACTION_POLICY_PASS")
