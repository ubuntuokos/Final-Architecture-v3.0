#!/usr/bin/env python3
"""Impact and evidence-currentness reasoning for CHIF."""
from __future__ import annotations

from typing import Any, Iterable

from fa3_change_graph import reachable
from fa3_change_history import validate_edge


def evidence_currentness(evidence: dict[str, Any], current_identity: dict[str, str]) -> dict[str, Any]:
    observed = evidence.get("subject_identity") or {}
    stale_fields = sorted(
        key for key, value in current_identity.items()
        if observed.get(key) not in (None, value)
    )
    return {
        "current": not stale_fields,
        "stale_fields": stale_fields,
        "requires_requalification": bool(stale_fields),
        "reason": "IDENTITY_DRIFT" if stale_fields else "IDENTITY_MATCH",
    }


def change_risk_context(subject_ids: Iterable[str], edges: list[dict[str, Any]],
                        evidence_states: Iterable[dict[str, Any]] = (),
                        scope_states: Iterable[str] = ()) -> dict[str, Any]:
    for edge in edges:
        validate_edge(edge)
    subjects = sorted(set(subject_ids))
    affected = reachable(edges, subjects, {"AFFECTS", "DEPENDS_ON", "INVALIDATES", "REQUALIFIES"})
    invalidated = sorted({
        e["target_id"] for e in edges
        if e["relation"] == "INVALIDATES" and e["source_id"] in set(subjects + affected)
    })
    requalification = sorted({
        e["target_id"] for e in edges
        if e["relation"] == "REQUALIFIES" and e["source_id"] in set(subjects + affected)
    })
    stale_evidence = sum(1 for state in evidence_states if state.get("current") is False)
    scope_states = list(scope_states)
    out_of_scope = sum(1 for state in scope_states if state == "OUT_OF_SCOPE")
    justification = sum(1 for state in scope_states if state == "JUSTIFICATION_REQUIRED")
    score = min(100, len(affected) * 3 + len(invalidated) * 8 + len(requalification) * 8
                + stale_evidence * 12 + out_of_scope * 20 + justification * 8)
    return {
        "subject_ids": subjects,
        "affected_ids": affected,
        "invalidated_ids": invalidated,
        "requalification_ids": requalification,
        "risk_context": {
            "deterministic_score": score,
            "stale_evidence_count": stale_evidence,
            "out_of_scope_count": out_of_scope,
            "justification_required_count": justification,
            "authoritative_decision": False,
        },
    }
