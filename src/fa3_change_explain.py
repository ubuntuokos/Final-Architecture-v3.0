#!/usr/bin/env python3
"""Deterministic explanations with an optional non-authoritative AI advisory."""
from __future__ import annotations

from typing import Any, Callable

from fa3_change_history import AI_MODES, ChangeHistoryError, redact


def explain(records: list[dict[str, Any]], impact: dict[str, Any], *,
            ai_mode: str = "OFF",
            router: Callable[[dict[str, Any]], str] | None = None) -> dict[str, Any]:
    if ai_mode not in AI_MODES:
        raise ChangeHistoryError("invalid AI mode")
    deterministic = {
        "truth_class": "DERIVED_FACT",
        "record_count": len(records),
        "objects": sorted({str(row.get("object_id")) for row in records}),
        "operations": sorted({str(row.get("operation")) for row in records}),
        "affected_ids": list(impact.get("affected_ids", [])),
        "invalidated_ids": list(impact.get("invalidated_ids", [])),
        "requalification_ids": list(impact.get("requalification_ids", [])),
        "risk_context": redact(impact.get("risk_context", {})),
    }
    result: dict[str, Any] = {
        "deterministic": deterministic,
        "ai_mode": ai_mode,
        "ai_invoked": False,
        "ai_output": None,
        "authoritative": False,
    }
    if ai_mode == "OFF":
        return result
    if router is None:
        if ai_mode == "ADVISORY":
            raise ChangeHistoryError("ADVISORY mode requires the canonical Model Router adapter")
        return result
    prompt = {
        "task": "Explain the already-established change facts without creating new facts or authority.",
        "deterministic_context": deterministic,
        "constraints": [
            "Output is AI_INFERENCE only",
            "Do not grant authority or approval",
            "Do not claim Current Host PASS",
            "Do not alter deterministic classifications",
        ],
    }
    output = router(prompt)
    result["ai_invoked"] = True
    result["ai_output"] = {
        "truth_class": "AI_INFERENCE",
        "text": str(output),
        "promotable_to_fact": False,
        "authoritative": False,
        "shadow_visible_to_operator": ai_mode == "ADVISORY",
    }
    return result
