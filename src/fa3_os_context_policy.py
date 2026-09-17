#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import uuid
from pathlib import Path
from typing import Any

from fa3_os_runtime import (
    JOURNAL_AUTHORITY,
    JOURNAL_SCHEMA,
    POLICY_ID,
    append_journal_event,
    canonical_json,
    extract_enrichment,
    read_journal_events,
    stable_digest,
    utc_now,
)

AUTH_SCHEMA = "fa3.gateway-authorization-receipt.v1"
AUTH_ISSUER = "central-mcp-gateway"
CONTEXT_READ_CAPABILITY = "FA3_OS_CONTEXT_READ"
ERASURE_SCHEMA = "fa3.os-selective-erasure-receipt.v1"
RETRIEVAL_SCHEMA = "fa3.os-context-retrieval-receipt.v1"
SUPPORTED_ERASURE_SCOPES = {
    "time_range",
    "project",
    "application",
    "source",
    "sensitivity_class",
    "artifact",
    "event_id",
}


class AuthorizationError(PermissionError):
    pass


def _parse_ts(value: str) -> dt.datetime:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def tombstoned_event_ids(journal_path: Path) -> set[str]:
    targets: set[str] = set()
    for event in read_journal_events(journal_path):
        if str(event.get("event_type", "")).upper() != "TOMBSTONE":
            continue
        target = str(event.get("target_event_id", "")).strip()
        if target:
            targets.add(target)
    return targets


def effective_events(journal_path: Path) -> list[dict[str, Any]]:
    tombstoned = tombstoned_event_ids(journal_path)
    rows: list[dict[str, Any]] = []
    for event in read_journal_events(journal_path):
        if str(event.get("event_type", "")).upper() == "TOMBSTONE":
            continue
        if str(event.get("id", "")) in tombstoned:
            continue
        rows.append(event)
    return rows


def _match_scope(event: dict[str, Any], scope: dict[str, Any]) -> bool:
    kind = str(scope.get("kind", "")).strip().lower()
    if kind not in SUPPORTED_ERASURE_SCOPES:
        raise ValueError(f"FA3-OS-ERASURE-001: unsupported erasure scope {kind!r}")
    value = scope.get("value")
    enrichment = extract_enrichment(event) or {}
    if kind == "event_id":
        return str(event.get("id", "")) == str(value)
    if kind == "project":
        return str(event.get("project_id", "")) == str(value)
    if kind == "application":
        return str(enrichment.get("application_id", "")) == str(value)
    if kind == "source":
        return str(event.get("source", "")) == str(value)
    if kind == "artifact":
        return str(enrichment.get("artifact_id", "")) == str(value)
    if kind == "sensitivity_class":
        needle = f"SENSITIVITY:{str(value).upper()}"
        return needle in {str(tag).upper() for tag in event.get("tags", [])}
    if kind == "time_range":
        if not isinstance(value, dict) or not value.get("start") or not value.get("end"):
            raise ValueError("FA3-OS-ERASURE-002: time_range requires start/end")
        stamp = _parse_ts(str(event.get("timestamp", "")))
        return _parse_ts(str(value["start"])) <= stamp <= _parse_ts(str(value["end"]))
    return False


def _tombstone_for(event: dict[str, Any], *, request_id: str, actor: str, reason: str, scope: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": JOURNAL_SCHEMA,
        "id": "FA3-EVT-" + str(uuid.uuid4()).upper(),
        "timestamp": utc_now(),
        "event_type": "TOMBSTONE",
        "domain": "AUDIT",
        "source": "FA3 OS",
        "project_id": "",
        "lifecycle": "SOFT_DELETED",
        "summary": "FA3 OS selective erasure tombstone",
        "details": canonical_json({
            "fa3_os_erasure": {
                "request_id": request_id,
                "actor": actor,
                "reason": reason,
                "policy_id": POLICY_ID,
                "scope": scope,
                "target_event_digest": stable_digest(event),
                "historical_event_rewrite": False,
            }
        }),
        "target_event_id": str(event.get("id", "")),
        "tags": ["FA3_OS", "SELECTIVE_ERASURE"],
        "integrity": "APPEND_ONLY",
    }


def selective_erase(
    journal_path: Path,
    *,
    scope: dict[str, Any],
    actor: str,
    reason: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    request_id = request_id or "FA3-OS-ERASE-" + str(uuid.uuid4()).upper()
    if not actor.strip() or not reason.strip():
        raise ValueError("FA3-OS-ERASURE-003: actor and reason are required")
    matched: list[dict[str, Any]] = []
    for event in effective_events(journal_path):
        if extract_enrichment(event) is None:
            continue
        if _match_scope(event, scope):
            matched.append(event)
    for event in matched:
        append_journal_event(journal_path, _tombstone_for(event, request_id=request_id, actor=actor, reason=reason, scope=scope))
    return {
        "schema": ERASURE_SCHEMA,
        "result": "PASS",
        "request_id": request_id,
        "policy_id": POLICY_ID,
        "ledger_authority": JOURNAL_AUTHORITY,
        "scope": scope,
        "matched_event_count": len(matched),
        "target_event_ids": [str(event.get("id", "")) for event in matched],
        "historical_event_rewrite": False,
        "append_only_tombstones": True,
    }


def validate_gateway_authorization(receipt: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise AuthorizationError("FA3-OS-AUTH-001: gateway receipt must be an object")
    required = {
        "schema": AUTH_SCHEMA,
        "issuer": AUTH_ISSUER,
        "decision": "ALLOW",
        "capability": CONTEXT_READ_CAPABILITY,
        "policy_id": POLICY_ID,
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise AuthorizationError(f"FA3-OS-AUTH-002: invalid {key}")
    for key in ("request_id", "actor", "purpose", "issued_at", "expires_at"):
        if not str(receipt.get(key, "")).strip():
            raise AuthorizationError(f"FA3-OS-AUTH-003: missing {key}")
    if receipt.get("gateway_runtime_admitted") is not True:
        raise AuthorizationError("FA3-OS-AUTH-004: gateway runtime is not admitted")
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    issued = _parse_ts(str(receipt["issued_at"]))
    expires = _parse_ts(str(receipt["expires_at"]))
    if issued > now + dt.timedelta(minutes=5):
        raise AuthorizationError("FA3-OS-AUTH-005: receipt issued in the future")
    if expires <= now or expires <= issued:
        raise AuthorizationError("FA3-OS-AUTH-006: receipt expired or invalid")
    scope = receipt.get("scope", {})
    if not isinstance(scope, dict):
        raise AuthorizationError("FA3-OS-AUTH-007: authorization scope must be an object")
    return receipt


def _event_allowed_by_scope(event: dict[str, Any], scope: dict[str, Any]) -> bool:
    enrichment = extract_enrichment(event) or {}
    projects = scope.get("project_ids")
    if isinstance(projects, list) and projects and str(event.get("project_id", "")) not in {str(v) for v in projects}:
        return False
    workstreams = scope.get("workstream_ids")
    if isinstance(workstreams, list) and workstreams and str(enrichment.get("workstream_id", "")) not in {str(v) for v in workstreams}:
        return False
    applications = scope.get("application_ids")
    if isinstance(applications, list) and applications and str(enrichment.get("application_id", "")) not in {str(v) for v in applications}:
        return False
    return True


def authorized_retrieve(
    journal_path: Path,
    *,
    authorization: dict[str, Any],
    text: str = "",
    project_id: str = "",
    workstream_id: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    authorization = validate_gateway_authorization(authorization)
    scope = authorization.get("scope", {})
    needle = text.lower().strip()
    rows: list[dict[str, Any]] = []
    for event in effective_events(journal_path):
        enrichment = extract_enrichment(event)
        if enrichment is None:
            continue
        if project_id and str(event.get("project_id", "")) != project_id:
            continue
        if workstream_id and str(enrichment.get("workstream_id", "")) != workstream_id:
            continue
        if not _event_allowed_by_scope(event, scope):
            continue
        if needle and needle not in canonical_json(event).lower():
            continue
        rows.append(event)
        if len(rows) >= max(1, min(int(limit), 500)):
            break

    source_refs = [str(event.get("id", "")) for event in rows]
    audit_event = {
        "schema": JOURNAL_SCHEMA,
        "id": "FA3-EVT-" + str(uuid.uuid4()).upper(),
        "timestamp": utc_now(),
        "event_type": "AUDIT",
        "domain": "AUDIT",
        "source": "FA3 OS",
        "project_id": project_id,
        "lifecycle": "AUTHORIZED_RETRIEVAL",
        "summary": "FA3 OS context retrieval authorized and audited",
        "details": canonical_json({
            "fa3_os_retrieval_audit": {
                "request_id": authorization["request_id"],
                "actor": authorization["actor"],
                "purpose": authorization["purpose"],
                "policy_id": POLICY_ID,
                "source_event_refs": source_refs,
                "timestamp": utc_now(),
                "gateway_issuer": authorization["issuer"],
                "capability": CONTEXT_READ_CAPABILITY,
            }
        }),
        "tags": ["FA3_OS", "CONTEXT_RETRIEVAL", "AUTHORIZED"],
        "integrity": "APPEND_ONLY",
    }
    append_journal_event(journal_path, audit_event)
    return {
        "schema": RETRIEVAL_SCHEMA,
        "result": "PASS",
        "request_id": authorization["request_id"],
        "policy_id": POLICY_ID,
        "ledger_authority": JOURNAL_AUTHORITY,
        "event_count": len(rows),
        "source_event_refs": source_refs,
        "audit_event_id": audit_event["id"],
        "events": rows,
    }
