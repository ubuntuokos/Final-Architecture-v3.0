#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from typing import Any

from fa3_agent_runtime_semantics import RuntimeSemanticsError, validate_reasoning_intent

PROTOCOLS = {"OPENAI", "ANTHROPIC", "GEMINI"}
SCHEMA_METADATA_KEYS = {"$schema", "$id", "title", "description", "default", "examples", "$comment"}
SUBSCHEMA_MAP_KEYS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
SUBSCHEMA_LIST_KEYS = {"oneOf", "anyOf", "allOf", "prefixItems"}
SUBSCHEMA_SINGLE_KEYS = {
    "items", "contains", "not", "if", "then", "else", "propertyNames",
    "additionalProperties", "unevaluatedProperties",
}
DEFAULT_SECURITY_SCHEMA_KEYS = {
    "type", "properties", "required", "enum", "const", "pattern",
    "minLength", "maxLength", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties",
    "additionalProperties", "unevaluatedProperties",
    "oneOf", "anyOf", "allOf", "not", "dependentRequired", "dependentSchemas",
}
SAFE_TOOL_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


class ProtocolCompatibilityError(ValueError):
    pass


def _strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def checked_reasoning_intent(intent: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_reasoning_intent(intent)
    except RuntimeSemanticsError as exc:
        raise ProtocolCompatibilityError(str(exc)) from exc


def project_reasoning_intent(intent: dict[str, Any], protocol: str) -> dict[str, Any]:
    checked = checked_reasoning_intent(intent)
    if protocol not in PROTOCOLS:
        raise ProtocolCompatibilityError("unsupported LLM protocol")
    projection_modes = {
        "OPENAI": "OPENAI_REASONING_EFFORT_OR_BUDGET_PROJECTION",
        "ANTHROPIC": "ANTHROPIC_THINKING_BUDGET_PROJECTION",
        "GEMINI": "GEMINI_THINKING_CONFIG_PROJECTION",
    }
    return {
        "schema": "fa3.reasoning-protocol-projection.v1",
        "protocol": protocol,
        "projection_mode": projection_modes[protocol],
        "canonical_intent": checked,
        "provider_or_model_selection_authority": False,
        "adapter_may_increase_reasoning": False,
        "silent_budget_clamp": False,
    }


def normalize_tool_call_id(raw_id: str) -> dict[str, Any]:
    if not isinstance(raw_id, str) or not raw_id:
        raise ProtocolCompatibilityError("tool call id required")
    digest = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()
    if SAFE_TOOL_ID.fullmatch(raw_id):
        normalized = raw_id
        transformed = False
    else:
        normalized = "fa3tc-" + digest[:32]
        transformed = True
    return {
        "schema": "fa3.tool-call-id-projection.v1",
        "canonical_id": normalized,
        "source_id_sha256": digest,
        "transformed": transformed,
        "reversible_via_receipt_mapping": True,
    }


def _collect_schema_keywords(value: Any, out: set[str]) -> None:
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        if key in SCHEMA_METADATA_KEYS or key.startswith("x-"):
            continue
        out.add(str(key))
        if key in SUBSCHEMA_MAP_KEYS:
            if isinstance(child, dict):
                for subschema in child.values():
                    _collect_schema_keywords(subschema, out)
            continue
        if key in SUBSCHEMA_LIST_KEYS:
            if isinstance(child, list):
                for subschema in child:
                    _collect_schema_keywords(subschema, out)
            continue
        if key in SUBSCHEMA_SINGLE_KEYS:
            _collect_schema_keywords(child, out)
            continue
        if isinstance(child, dict):
            _collect_schema_keywords(child, out)


def tool_schema_projection(
    schema: dict[str, Any],
    *,
    supported_keywords: set[str],
    security_relevant_keywords: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        raise ProtocolCompatibilityError("tool schema must be object")
    observed: set[str] = set()
    _collect_schema_keywords(schema, observed)
    unsupported = observed - set(supported_keywords)
    security = set(security_relevant_keywords or DEFAULT_SECURITY_SCHEMA_KEYS)
    security_loss = sorted(unsupported & security)
    if security_loss:
        status = "UNSUPPORTED_FAIL_CLOSED"
    elif unsupported:
        status = "TRANSLATABLE_WITH_DECLARED_DEGRADATION"
    else:
        status = "LOSSLESS"
    return {
        "schema": "fa3.tool-schema-compatibility-receipt.v1",
        "status": status,
        "observed_keywords": sorted(observed),
        "unsupported_keywords": sorted(unsupported),
        "security_relevant_loss": security_loss,
        "silent_drop": False,
    }


def validate_stream_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(events, list) or not events:
        raise ProtocolCompatibilityError("stream event list required")
    allowed = {"START", "DELTA", "TOOL_CALL", "TOOL_RESULT", "HEARTBEAT", "ERROR", "DONE"}
    terminal_seen = False
    started = False
    for idx, event in enumerate(events):
        if not isinstance(event, dict) or event.get("type") not in allowed:
            raise ProtocolCompatibilityError(f"invalid stream event at {idx}")
        kind = event["type"]
        if terminal_seen:
            raise ProtocolCompatibilityError("event after terminal stream state")
        if kind == "START":
            if started:
                raise ProtocolCompatibilityError("duplicate stream START")
            started = True
        elif not started and kind != "HEARTBEAT":
            raise ProtocolCompatibilityError("stream payload before START")
        if kind in {"ERROR", "DONE"}:
            terminal_seen = True
    if not terminal_seen:
        raise ProtocolCompatibilityError("stream must terminate explicitly")
    return {
        "schema": "fa3.streaming-projection-receipt.v1",
        "ordered": True,
        "terminal_explicit": True,
        "heartbeat_transport_only": True,
        "provider_routing_authority": False,
    }


def normalize_provider_error(status: int, *, error_type: str, error_code: str) -> dict[str, Any]:
    if not _strict_int(status) or status < 100 or status > 599:
        raise ProtocolCompatibilityError("invalid HTTP status")
    if 200 <= status < 300:
        raise ProtocolCompatibilityError("provider error cannot be normalized as success")
    return {
        "schema": "fa3.provider-error-envelope.v1",
        "http_status": status,
        "error_type": str(error_type or "unspecified"),
        "error_code": str(error_code or "unspecified"),
        "success": False,
        "upstream_status_preserved": True,
    }


def validate_multimodal_payload(
    parts: list[dict[str, Any]],
    *,
    max_inline_bytes: int,
    max_parts: int,
) -> dict[str, Any]:
    if not _strict_int(max_inline_bytes) or max_inline_bytes < 0:
        raise ProtocolCompatibilityError("invalid max_inline_bytes")
    if not _strict_int(max_parts) or max_parts <= 0:
        raise ProtocolCompatibilityError("invalid max_parts")
    if not isinstance(parts, list) or len(parts) > max_parts:
        raise ProtocolCompatibilityError("multimodal part count exceeds bound")
    inline_total = 0
    for part in parts:
        if not isinstance(part, dict) or part.get("kind") not in {"TEXT", "INLINE_MEDIA", "ARTIFACT_REF"}:
            raise ProtocolCompatibilityError("invalid multimodal part")
        if part["kind"] == "INLINE_MEDIA":
            size = part.get("size_bytes")
            if not _strict_int(size) or size < 0:
                raise ProtocolCompatibilityError("inline media size required")
            inline_total += size
        if part["kind"] == "ARTIFACT_REF" and not str(part.get("artifact_ref", "")).strip():
            raise ProtocolCompatibilityError("artifact reference required")
    if inline_total > max_inline_bytes:
        raise ProtocolCompatibilityError("inline multimodal payload exceeds bound")
    return {
        "schema": "fa3.multimodal-projection-receipt.v1",
        "part_count": len(parts),
        "inline_bytes": inline_total,
        "max_inline_bytes": max_inline_bytes,
        "artifact_reference_supported": True,
        "bounded": True,
    }


def canonical_usage_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolCompatibilityError("usage metadata must be object")
    allowed = {"input_tokens", "output_tokens", "reasoning_tokens", "cached_input_tokens"}
    result: dict[str, int] = {}
    for key in allowed:
        if key in value:
            count = value[key]
            if not _strict_int(count) or count < 0:
                raise ProtocolCompatibilityError(f"invalid usage count: {key}")
            result[key] = count
    return {
        "schema": "fa3.llm-usage-metadata.v1",
        "usage": result,
        "provider_specific_fields_ignored_for_accounting": True,
    }
