#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from fa3_mcp_gateway import Adapter, GatewayDenied
from fa3_os_context_policy import (
    MCP_OS_ADAPTER_ID,
    MCP_OS_PROVIDER_ID,
    record_mcp_gateway_retrieval_audit,
    scoped_retrieve_events,
)
from fa3_os_runtime import default_journal_path

_ALLOWED_ARGUMENTS = {"text", "project_id", "workstream_id", "limit"}


def _retrieve(arguments: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(arguments) - _ALLOWED_ARGUMENTS)
    if unknown:
        raise GatewayDenied("INVALID_SCHEMA", "Unsupported FA3 OS retrieval arguments: " + ", ".join(unknown))
    try:
        limit = int(arguments.get("limit", 100))
    except (TypeError, ValueError) as exc:
        raise GatewayDenied("INVALID_SCHEMA", "Retrieval limit must be an integer") from exc
    if limit < 1 or limit > 500:
        raise GatewayDenied("INVALID_SCHEMA", "Retrieval limit must be between 1 and 500")

    if not str(arguments.get("project_id", "")).strip() and not str(arguments.get("workstream_id", "")).strip():
        raise GatewayDenied("POLICY_SCOPE_MISMATCH", "Agent retrieval requires project_id or workstream_id scope")

    rows = scoped_retrieve_events(
        default_journal_path(),
        text=str(arguments.get("text", "")),
        project_id=str(arguments.get("project_id", "")),
        workstream_id=str(arguments.get("workstream_id", "")),
        limit=limit,
    )
    projected = [
        {
            "id": str(row.get("id", "")),
            "timestamp": row.get("timestamp"),
            "domain": row.get("domain"),
            "source": row.get("source"),
            "lifecycle": row.get("lifecycle"),
            "summary": row.get("summary"),
            "project_id": row.get("project_id"),
            "tags": row.get("tags", []),
        }
        for row in rows
    ]
    return {
        "event_count": len(projected),
        "source_event_refs": [row["id"] for row in projected],
        "events": projected,
        "authoritative_history": False,
        "ledger_authority": "FA3-JOURNAL-001",
        "projection_mode": "MINIMIZED_AGENT_CONTEXT",
    }


def _audit_retrieval(request: dict[str, Any], receipt: dict[str, Any]) -> None:
    decision = request.get("policy_decision") if isinstance(request.get("policy_decision"), dict) else {}
    arguments = request.get("arguments") if isinstance(request.get("arguments"), dict) else {}
    audit = record_mcp_gateway_retrieval_audit(
        default_journal_path(),
        gateway_receipt=receipt,
        purpose=str(decision.get("purpose", "agent context retrieval")),
        project_id=str(arguments.get("project_id", "")),
    )
    result = receipt.get("result")
    if isinstance(result, dict):
        result["audit_event_id"] = audit["audit_event_id"]


def create_adapters() -> tuple[Adapter, ...]:
    return (
        Adapter(
            adapter_id=MCP_OS_ADAPTER_ID,
            provider_id=MCP_OS_PROVIDER_ID,
            handler=_retrieve,
            receipt_handler=_audit_retrieval,
        ),
    )
