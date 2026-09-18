#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from fa3_mcp_gateway import Adapter, GatewayDenied
from fa3_os_context_policy import MCP_OS_ADAPTER_ID, MCP_OS_PROVIDER_ID, scoped_retrieve_events
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

    rows = scoped_retrieve_events(
        default_journal_path(),
        text=str(arguments.get("text", "")),
        project_id=str(arguments.get("project_id", "")),
        workstream_id=str(arguments.get("workstream_id", "")),
        limit=limit,
    )
    return {
        "event_count": len(rows),
        "source_event_refs": [str(row.get("id", "")) for row in rows],
        "events": rows,
        "authoritative_history": False,
        "ledger_authority": "FA3-JOURNAL-001",
    }


def create_adapters() -> tuple[Adapter, ...]:
    return (
        Adapter(
            adapter_id=MCP_OS_ADAPTER_ID,
            provider_id=MCP_OS_PROVIDER_ID,
            handler=_retrieve,
        ),
    )
