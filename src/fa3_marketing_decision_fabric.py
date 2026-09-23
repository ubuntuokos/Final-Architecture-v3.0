#!/usr/bin/env python3
"""Deterministic, bounded advisory decisions for FA3 marketing actions.

The module deliberately does not depend on a Jev runtime.  A separately admitted
advisory callable may reorder policy-eligible candidates, but it cannot add a
candidate, grant authority, or suppress the receipt.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable

SCHEMA = "fa3.marketing-decision-receipt.v1"
CONTEXT_SCHEMA = "fa3.marketing-context-envelope.v1"
OUTCOMES = {
    "CONTINUE", "RETRY", "REASSIGN", "ESCALATE",
    "STOP_SUCCESS", "STOP_BLOCKED", "STOP_FAILED",
}
KINDS = {
    "CONTEXT_SELECTION", "CANDIDATE_RANKING", "CLASSIFICATION",
    "RETRY_STOP_CONTINUE", "SEMANTIC_VALIDATION",
}
MAX_CANDIDATES = 128
MAX_CONTEXT_ITEMS = 32


class MarketingDecisionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DecisionRequest:
    decision_id: str
    kind: str
    scope: str
    candidates: tuple[dict[str, Any], ...]
    context: tuple[dict[str, Any], ...] = ()
    signals: dict[str, Any] = field(default_factory=dict)
    attempt: int = 0
    max_attempts: int = 0


def _digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _identifier(item: dict[str, Any], field_name: str = "id") -> str:
    value = str(item.get(field_name, "")).strip()
    if not value:
        raise MarketingDecisionError(
            "MDF-CANDIDATE-INVALID", f"{field_name} is required"
        )
    return value


def _bounded_unique(
    values: tuple[dict[str, Any], ...], maximum: int, label: str
) -> list[dict[str, Any]]:
    if not values:
        raise MarketingDecisionError(
            "MDF-CANDIDATE-SET-EMPTY", f"{label} must be non-empty"
        )
    if len(values) > maximum:
        raise MarketingDecisionError(
            "MDF-CANDIDATE-SET-UNBOUNDED",
            f"{label} exceeds the maximum of {maximum}",
        )
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, dict):
            raise MarketingDecisionError(
                "MDF-CANDIDATE-INVALID", f"{label} entries must be objects"
            )
        item = dict(raw)
        item_id = _identifier(item)
        if item_id in seen:
            raise MarketingDecisionError(
                "MDF-CANDIDATE-DUPLICATE", f"duplicate candidate: {item_id}"
            )
        seen.add(item_id)
        result.append(item)
    return result


def _number(item: dict[str, Any], name: str, default: float = 0.0) -> float:
    value = item.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MarketingDecisionError(
            "MDF-CANDIDATE-INVALID", f"{name} must be numeric"
        )
    return float(value)


def _policy_filter(item: dict[str, Any]) -> tuple[bool, str]:
    if item.get("eligible", True) is not True:
        return False, "policy-ineligible"
    if item.get("suppressed") is True:
        return False, "suppressed"
    if item.get("consent_required") is True and item.get("consent_valid") is not True:
        return False, "consent-missing-or-invalid"
    if item.get("evidence_valid", True) is not True:
        return False, "evidence-invalid"
    return True, "policy-eligible"


def _rank_key(item: dict[str, Any]) -> tuple[float, str]:
    score = (
        _number(item, "priority") * 1000.0
        + _number(item, "relevance") * 100.0
        - _number(item, "risk") * 100.0
        - _number(item, "cost")
    )
    return (-score, _identifier(item))


def _context_envelope(
    context: tuple[dict[str, Any], ...], scope: str
) -> dict[str, Any]:
    if not context:
        selected: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
    else:
        items = _bounded_unique(context, MAX_CANDIDATES, "context")
        ordered = sorted(items, key=_rank_key)
        selected = [
            {"ref": _identifier(item), "reason": "bounded-relevance-rank"}
            for item in ordered[:MAX_CONTEXT_ITEMS]
        ]
        rejected = [
            {"ref": _identifier(item), "reason": "context-budget"}
            for item in ordered[MAX_CONTEXT_ITEMS:]
        ]
    envelope = {
        "schema": CONTEXT_SCHEMA,
        "scope": scope,
        "selected": selected,
        "rejected": rejected,
    }
    envelope["digest"] = _digest(envelope)
    return envelope


def decide(
    request: DecisionRequest,
    advisory: Callable[[tuple[str, ...], dict[str, Any]], list[str]] | None = None,
) -> dict[str, Any]:
    if request.kind not in KINDS:
        raise MarketingDecisionError("MDF-KIND-INVALID", "unknown decision kind")
    if not request.decision_id.strip() or not request.scope.strip():
        raise MarketingDecisionError(
            "MDF-REQUEST-INVALID", "decision_id and scope are required"
        )
    candidates = _bounded_unique(request.candidates, MAX_CANDIDATES, "candidates")
    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for candidate in candidates:
        allowed, reason = _policy_filter(candidate)
        if allowed:
            eligible.append(candidate)
        else:
            rejected.append({"id": _identifier(candidate), "reason": reason})
    eligible.sort(key=_rank_key)

    implementation = "deterministic-policy-ranker"
    advisory_error: str | None = None
    if advisory is not None and eligible:
        allowed_ids = tuple(_identifier(item) for item in eligible)
        try:
            proposed = advisory(allowed_ids, dict(request.signals))
            if (
                not isinstance(proposed, list)
                or len(proposed) != len(allowed_ids)
                or len(set(proposed)) != len(proposed)
                or set(proposed) != set(allowed_ids)
            ):
                raise MarketingDecisionError(
                    "MDF-ADVISORY-EXPANSION",
                    "advisory result must be an exact permutation of eligible candidates",
                )
            by_id = {_identifier(item): item for item in eligible}
            eligible = [by_id[item_id] for item_id in proposed]
            implementation = "optional-advisory-rerank-after-deterministic-filter"
        except MarketingDecisionError:
            raise
        except Exception as exc:  # an advisory outage never becomes authority
            advisory_error = type(exc).__name__
            implementation = "deterministic-fallback-after-advisory-error"

    semantic_valid = request.signals.get("semantic_valid", True) is True
    if not semantic_valid:
        outcome = "RETRY" if request.attempt < request.max_attempts else "STOP_FAILED"
        reason = "semantic-validation-failed"
    elif request.signals.get("human_request") is True:
        outcome = "ESCALATE"
        reason = "human-request-required"
    elif request.signals.get("provider_unavailable") is True and eligible:
        outcome = "REASSIGN"
        reason = "provider-unavailable"
    elif not eligible:
        outcome = "STOP_BLOCKED"
        reason = "no-policy-eligible-candidate"
    elif request.signals.get("already_complete") is True:
        outcome = "STOP_SUCCESS"
        reason = "already-complete"
    else:
        outcome = "CONTINUE"
        reason = "policy-eligible-candidate-selected"
    if outcome not in OUTCOMES:  # defensive assertion for future edits
        raise MarketingDecisionError("MDF-OUTCOME-INVALID", outcome)

    selected = [_identifier(eligible[0])] if eligible and outcome in {
        "CONTINUE", "REASSIGN", "ESCALATE", "STOP_SUCCESS"
    } else []
    ranked = [_identifier(item) for item in eligible]
    receipt = {
        "schema": SCHEMA,
        "decision_id": request.decision_id,
        "kind": request.kind,
        "scope": request.scope,
        "input_digest": _digest({
            "candidates": candidates,
            "context": request.context,
            "signals": request.signals,
            "attempt": request.attempt,
            "max_attempts": request.max_attempts,
        }),
        "candidate_ids": [_identifier(item) for item in candidates],
        "eligible_ranked_ids": ranked,
        "selected_ids": selected,
        "rejected": rejected,
        "outcome": outcome,
        "reason": reason,
        "implementation": implementation,
        "advisory_provider_is_authority": False,
        "candidate_expansion": False,
        "context_envelope": _context_envelope(request.context, request.scope),
        "project_radar": {
            "status": outcome,
            "provenance_refs": list(request.signals.get("provenance_refs", [])),
            "evidence_refs": list(request.signals.get("evidence_refs", [])),
        },
    }
    if advisory_error:
        receipt["advisory_error_class"] = advisory_error
    receipt["receipt_digest"] = _digest(receipt)
    return receipt
