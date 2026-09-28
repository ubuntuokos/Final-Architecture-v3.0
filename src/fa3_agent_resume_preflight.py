"""Non-authoritative resume preflight for existing Temporal/Agent Workload.

Only authentic Journal/Temporal lineage and current existing admissions may
authorize resumed work. This module returns a plan, never runs or replays tools.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Callable

class ResumeDenied(ValueError):
    pass

def event_digest(event: dict[str, Any]) -> str:
    """Hash the complete event record except its own terminal digest."""
    data = {key: value for key, value in event.items() if key != "event_sha256"}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")).hexdigest()

def assess_resume(
    session_id: str, events: list[dict[str, Any]],
    requested: list[dict[str, Any]], *,
    verify_authenticated_ledger: Callable[[str, str], bool],
    expected_terminal_digest: str, attempted_retries: int,
    max_retries: int, max_tool_calls: int,
) -> dict[str, Any]:
    """Verify a committed hash chain before producing side-effect-safe guidance.

    The authentication callback MUST bind to existing Temporal/Journal/Evidence,
    not a value supplied by the agent. Any unverifiable ledger fails closed.
    No pending approval is inferred from a successful model result.
    """
    if not isinstance(session_id, str) or not session_id.strip():
        raise ResumeDenied("durable session required")
    if not isinstance(events, list) or not events:
        raise ResumeDenied("authenticated committed events required")
    if any(type(v) is not int or v < 0 for v in
           (attempted_retries, max_retries, max_tool_calls)):
        raise ResumeDenied("invalid retry or tool budget")
    if not isinstance(requested, list):
        raise ResumeDenied("pending work must be a list")
    previous = "0" * 64
    committed: dict[str, dict[str, Any]] = {}
    approvals: set[str] = set()
    ids = set()
    for position, e in enumerate(events, 1):
        if not isinstance(e, dict) or (e.get("session_id") != session_id or
            e.get("sequence") != position or type(e.get("sequence")) is not int or
            not isinstance(e.get("event_id"), str) or not e["event_id"] or
            e["event_id"] in ids):
            raise ResumeDenied("event session, order or identity invalid")
        ids.add(e["event_id"])
        if (e.get("previous_sha256") != previous or
                e.get("event_sha256") != event_digest(e)):
            raise ResumeDenied("committed event hash chain invalid")
        kind = e.get("event_type")
        if kind == "EXTERNAL_EFFECT_COMMITTED":
            key = e.get("effect_key")
            receipt = e.get("evidence_ref")
            if not isinstance(key, str) or not key or not isinstance(receipt, str) or not receipt:
                raise ResumeDenied("committed effect missing idempotency or evidence ref")
            if key in committed:
                raise ResumeDenied("duplicate external effect in committed lineage")
            committed[key] = e
        elif kind == "APPROVAL_PENDING":
            key = e.get("effect_key")
            if not isinstance(key, str) or not key:
                raise ResumeDenied("approval has no effect identity")
            approvals.add(key)
        elif kind == "APPROVAL_RESOLVED":
            key = e.get("effect_key")
            if key not in approvals or e.get("decision") not in {"APPROVE", "DENY"}:
                raise ResumeDenied("approval resolution has no matching pending request")
            approvals.remove(key)
        elif kind not in {"SESSION_STARTED", "CHECKPOINT", "MODEL_CALL", "TOOL_RESULT"}:
            raise ResumeDenied("unsupported replay event kind")
        previous = e["event_sha256"]
    if previous != expected_terminal_digest:
        raise ResumeDenied("terminal checkpoint changed")
    if not callable(verify_authenticated_ledger):
        raise ResumeDenied("authenticating ledger validator required")
    try:
        authenticated = verify_authenticated_ledger(session_id, previous)
    except Exception as exc:
        raise ResumeDenied("ledger authentication unavailable") from exc
    if authenticated is not True:
        raise ResumeDenied("untrusted or stale committed ledger")
    if len(requested) > max_tool_calls:
        raise ResumeDenied("requested tool work exceeds existing budget")
    seen = set()
    plan = []
    for row in requested:
        if not isinstance(row, dict):
            raise ResumeDenied("requested effect must be structured")
        key = row.get("effect_key")
        if not isinstance(key, str) or not key or key in seen:
            raise ResumeDenied("invalid or duplicate requested effect key")
        seen.add(key)
        if key in committed:
            state = "VERIFY_EXISTING_EFFECT_NO_REEXECUTION"
        elif key in approvals:
            state = "PAUSED_AWAITING_EXISTING_APPROVAL"
        elif attempted_retries >= max_retries:
            state = "ESCALATE_RETRY_BUDGET_EXHAUSTED"
        else:
            state = "REQUIRE_FRESH_SECURITY_UAF_HRB_AND_MODEL_ROUTE_ADMISSION"
        plan.append({"effect_key": key, "state": state,
                     "execution_performed": False, "effect_authorization": False})
    return {
        "schema": "fa3.agent-resume-preflight.v1",
        "session_id": session_id,
        "terminal_digest": previous,
        "effects": plan,
        "attempted_retries": attempted_retries,
        "remaining_retry_budget": max(0, max_retries - attempted_retries),
        "status": "REVIEW_AND_EXISTING_TEMPORAL_ADMISSION_REQUIRED",
        "durable_authority": "EXISTING_TEMPORAL_ONLY",
        "canonical_evidence_authority": "FA3-AUTH-OBS-EVIDENCE-001",
        "authority": False, "execution_performed": False,
    }
