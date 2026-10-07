"""Fail-closed CFA3 factual readback continuity guard.

This guard is authority-neutral. It validates whether a task that depends on
prior work has completed factual readback, re-analysis, contradiction handling,
current-state verification and scope guarding before continuation.

ALLOW_CONTINUATION is only a governance preflight result. It never grants
security, effect, workflow, model, resource, merge or release authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

POLICY_ID = "CFA3-FACTUAL-READBACK-CONTINUITY-POLICY-001"

_ALLOWED_DECISIONS = {
    "ALLOW_CONTINUATION",
    "BLOCKER_STOP",
    "NEW_TASK_NO_READBACK_REQUIRED",
}

_REQUIRED_FIELDS = (
    "task_id",
    "prior_state_required",
    "source_refs",
    "readback_complete",
    "reanalysis_complete",
    "current_state_verified",
    "contradictions",
    "unknown_facts",
    "scope_guard_passed",
)

_REQUIRED_TRUE_FOR_CONTINUATION = (
    "readback_complete",
    "reanalysis_complete",
    "current_state_verified",
    "scope_guard_passed",
)


def _stop(reason: str, *, missing: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": "cfa3.factual-readback-guard-result.v1",
        "policy_id": POLICY_ID,
        "decision": "BLOCKER_STOP",
        "pass": False,
        "reason": reason,
        "missing": missing or [],
        "effect_authority_granted": False,
    }


def _is_nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) > 0
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def evaluate_readback(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one factual-readback record.

    Memory or prior AI statements may occur in provenance metadata, but they do
    not satisfy source_refs on their own. Callers must provide factual source
    references that were actually re-read or re-queried.
    """
    if not isinstance(record, Mapping):
        return _stop("RECORD_MUST_BE_MAPPING")

    missing = [field for field in _REQUIRED_FIELDS if field not in record]
    if missing:
        return _stop("MISSING_REQUIRED_FIELDS", missing=missing)

    task_id = record["task_id"]
    if not isinstance(task_id, str) or not task_id.strip():
        return _stop("INVALID_TASK_ID")

    prior_state_required = record["prior_state_required"]
    if prior_state_required is not True and prior_state_required is not False:
        return _stop("INVALID_PRIOR_STATE_REQUIRED")

    for field in ("readback_complete", "reanalysis_complete", "current_state_verified", "scope_guard_passed"):
        value = record[field]
        if value is not True and value is not False:
            return _stop(f"INVALID_BOOLEAN:{field}")

    contradictions = record["contradictions"]
    unknown_facts = record["unknown_facts"]
    if not isinstance(contradictions, list):
        return _stop("CONTRADICTIONS_MUST_BE_LIST")
    if not isinstance(unknown_facts, list):
        return _stop("UNKNOWN_FACTS_MUST_BE_LIST")

    if prior_state_required is False:
        return {
            "schema": "cfa3.factual-readback-guard-result.v1",
            "policy_id": POLICY_ID,
            "decision": "NEW_TASK_NO_READBACK_REQUIRED",
            "pass": True,
            "reason": "SELF_CONTAINED_NEW_TASK",
            "effect_authority_granted": False,
        }

    if not _is_nonempty_string_list(record["source_refs"]):
        return _stop("FACTUAL_SOURCE_REFS_REQUIRED")

    incomplete = [field for field in _REQUIRED_TRUE_FOR_CONTINUATION if record[field] is not True]
    if incomplete:
        return _stop("READBACK_OR_VERIFICATION_INCOMPLETE", missing=incomplete)

    unresolved_contradictions = [
        item for item in contradictions
        if not isinstance(item, Mapping) or item.get("resolved") is not True
    ]
    if unresolved_contradictions:
        return _stop("UNRESOLVED_CONTRADICTION")

    if unknown_facts:
        return _stop("UNKNOWN_FACTS_REMAIN")

    return {
        "schema": "cfa3.factual-readback-guard-result.v1",
        "policy_id": POLICY_ID,
        "decision": "ALLOW_CONTINUATION",
        "pass": True,
        "reason": "FACTUAL_READBACK_REANALYSIS_AND_VERIFICATION_PASS",
        "effect_authority_granted": False,
    }


def gate(record: Mapping[str, Any]) -> dict[str, Any]:
    return evaluate_readback(record)
