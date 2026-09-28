"""Task-scoped projection over existing FA3 Context Selection.

The real Security authority must authenticate grants via the injected verifier
before any context item is sent to Decision Fabric or a downstream consumer.
This module neither issues grants nor stores canonical memories.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Callable

from fa3_context_selection import ContextSelector, verify_projection

class TaskContextDenied(ValueError):
    pass

def _ids(value: Any, label: str) -> set[str]:
    if (not isinstance(value, list) or not value or
            not all(isinstance(v, str) and v.strip() == v and v for v in value) or
            len(value) != len(set(value))):
        raise TaskContextDenied(label + " must contain unique, non-empty IDs")
    return set(value)

def project_task_context(
    values: list[dict[str, Any]], *,
    task_id: str, requested_ids: list[str], grant: dict[str, Any],
    verify_security_grant: Callable[[dict[str, Any], str, frozenset[str]], bool],
    selector: ContextSelector | None = None, target_active: int | None = None,
) -> dict[str, Any]:
    """Require an externally authenticated, task-exact grant before ranking.

    A caller-supplied JSON grant is never authenticated by its own fields.
    verify_security_grant MUST be a trusted backend binding to existing Security.
    """
    if not isinstance(task_id, str) or not task_id.strip():
        raise TaskContextDenied("task identity required")
    requested = _ids(requested_ids, "requested_ids")
    if not isinstance(grant, dict) or grant.get("task_id") != task_id:
        raise TaskContextDenied("grant is missing or bound to a different task")
    allowed = _ids(grant.get("allowed_item_ids"), "grant.allowed_item_ids")
    if not requested.issubset(allowed):
        raise TaskContextDenied("requested context is outside grant scope")
    if not callable(verify_security_grant):
        raise TaskContextDenied("Security grant verifier required")
    try:
        verified = verify_security_grant(grant, task_id, frozenset(requested))
    except Exception as exc:
        raise TaskContextDenied("Security grant verification failed") from exc
    if verified is not True:
        raise TaskContextDenied("grant not authenticated by existing Security")
    if not isinstance(values, list):
        raise TaskContextDenied("context source must be a list")
    ids = [v.get("id") for v in values if isinstance(v, dict)]
    if len(ids) != len(values) or len(ids) != len(set(ids)):
        raise TaskContextDenied("invalid or repeated source context IDs")
    if not requested.issubset(ids):
        raise TaskContextDenied("requested context item missing")
    # Permission-before-relevance: unauthorized bytes, metadata and protected
    # items never reach the Decision Fabric's candidate construction.
    subset = [v for v in values if v["id"] in requested]
    projected = (selector or ContextSelector()).project(
        subset, target_active=target_active, rollout="ADVISORY"
    )
    verify_projection(projected)
    footprint = [{"id": row["id"], "source_sha256": row["source_sha256"]}
                 for row in projected["items"]]
    scope_hash = hashlib.sha256(json.dumps(
        {"task_id": task_id, "sources": sorted(footprint, key=lambda x: x["id"])},
        sort_keys=True, separators=(",", ":",
        )).encode("utf-8")).hexdigest()
    return {
        "schema": "fa3.task-context-projection.v1",
        "task_id": task_id,
        "projection": projected,
        "source_scope_digest_sha256": scope_hash,
        "permission_before_relevance": True,
        "canonical_source_unchanged": True,
        "authorization_receipt_claim": False,
        "authority": False,
    }

def restore_task_context(value: dict[str, Any], *, item_id: str) -> dict[str, Any]:
    """Restore only a hidden item already in the authorized task projection."""
    if value.get("schema") != "fa3.task-context-projection.v1":
        raise TaskContextDenied("task projection required")
    projection = value.get("projection")
    if not isinstance(projection, dict):
        raise TaskContextDenied("missing task projection")
    verify_projection(projection)
    if item_id not in {row.get("id") for row in projection.get("items", [])}:
        raise TaskContextDenied("item not present in authorized projection")
    ContextSelector.restore(projection, item_id)
    verify_projection(projection)
    return value
