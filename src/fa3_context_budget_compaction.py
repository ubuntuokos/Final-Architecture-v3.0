#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any

CONTEXT_CLASSES = {"PROTECTED", "ACTIVE", "SUMMARIZABLE", "ARCHIVABLE", "RETRIEVABLE"}
REMOVAL_ORDER = {"ARCHIVABLE": 0, "RETRIEVABLE": 1, "SUMMARIZABLE": 2}

class ContextBudgetError(ValueError):
    pass

def _strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)

def validate_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(segments, list):
        raise ContextBudgetError("segments must be list")
    seen: set[str] = set()
    result = []
    for row in segments:
        if not isinstance(row, dict):
            raise ContextBudgetError("context segment must be object")
        segment_id = str(row.get("segment_id", "")).strip()
        provenance_ref = str(row.get("provenance_ref", "")).strip()
        classification = row.get("classification")
        token_count = row.get("token_count")
        if not segment_id or segment_id in seen:
            raise ContextBudgetError("context segment identity invalid or duplicate")
        if not provenance_ref:
            raise ContextBudgetError("context provenance reference required")
        if classification not in CONTEXT_CLASSES:
            raise ContextBudgetError("context classification invalid")
        if not _strict_int(token_count) or token_count < 0:
            raise ContextBudgetError("context token count invalid")
        seen.add(segment_id)
        result.append({
            "segment_id": segment_id,
            "classification": classification,
            "token_count": token_count,
            "provenance_ref": provenance_ref,
            "ordinal": row.get("ordinal", len(result)),
        })
    return result

def context_state_digest(segments: list[dict[str, Any]]) -> str:
    checked = validate_segments(segments)
    canonical = json.dumps(checked, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def plan_context_compaction(
    segments: list[dict[str, Any]],
    *,
    max_context_tokens: int,
    target_context_tokens: int,
    min_headroom_tokens: int,
    min_growth_tokens: int,
    last_compaction_total_tokens: int | None = None,
) -> dict[str, Any]:
    checked = validate_segments(segments)
    for name, value in (
        ("max_context_tokens", max_context_tokens),
        ("target_context_tokens", target_context_tokens),
        ("min_headroom_tokens", min_headroom_tokens),
        ("min_growth_tokens", min_growth_tokens),
    ):
        if not _strict_int(value) or value < 0:
            raise ContextBudgetError(f"{name} invalid")
    if max_context_tokens <= 0 or target_context_tokens > max_context_tokens:
        raise ContextBudgetError("context budget ordering invalid")
    if min_headroom_tokens > max_context_tokens:
        raise ContextBudgetError("headroom exceeds context budget")
    if last_compaction_total_tokens is not None and (
        not _strict_int(last_compaction_total_tokens) or last_compaction_total_tokens < 0
    ):
        raise ContextBudgetError("last compaction total invalid")

    total = sum(row["token_count"] for row in checked)
    soft_trigger = max_context_tokens - min_headroom_tokens
    base = {
        "schema": "fa3.context-compaction-plan.v1",
        "source_state_sha256": context_state_digest(checked),
        "source_total_tokens": total,
        "max_context_tokens": max_context_tokens,
        "target_context_tokens": target_context_tokens,
        "min_headroom_tokens": min_headroom_tokens,
        "min_growth_tokens": min_growth_tokens,
        "source_history_mutated": False,
        "provenance_preserved": True,
        "authority": False,
    }
    if total <= soft_trigger:
        return {**base, "status": "NOOP_HEADROOM_SUFFICIENT", "selected_segment_ids": [], "projected_total_tokens": total}
    if (
        last_compaction_total_tokens is not None
        and total <= max_context_tokens
        and total - last_compaction_total_tokens < min_growth_tokens
    ):
        return {**base, "status": "DEFER_ANTI_THRASH", "selected_segment_ids": [], "projected_total_tokens": total}

    candidates = [row for row in checked if row["classification"] in REMOVAL_ORDER]
    candidates.sort(key=lambda row: (REMOVAL_ORDER[row["classification"]], int(row.get("ordinal", 0)), row["segment_id"]))
    selected = []
    projected = total
    for row in candidates:
        if projected <= target_context_tokens:
            break
        selected.append(row)
        projected -= row["token_count"]

    if projected > max_context_tokens:
        return {
            **base,
            "status": "FAIL_CLOSED_RESELECTION_REQUIRED",
            "selected_segment_ids": [row["segment_id"] for row in selected],
            "projected_total_tokens": projected,
            "protected_or_active_tokens": sum(row["token_count"] for row in checked if row["classification"] in {"PROTECTED", "ACTIVE"}),
        }

    return {
        **base,
        "status": "COMPACTION_REQUIRED",
        "selected_segment_ids": [row["segment_id"] for row in selected],
        "selected_provenance_refs": [row["provenance_ref"] for row in selected],
        "projected_total_tokens": projected,
        "retrieval_backreferences_required": bool(selected),
        "silent_context_drop": False,
    }

def compaction_receipt(plan: dict[str, Any], *, summary_artifact_ref: str | None = None) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema") != "fa3.context-compaction-plan.v1":
        raise ContextBudgetError("compaction plan required")
    if plan.get("status") != "COMPACTION_REQUIRED":
        raise ContextBudgetError("receipt only valid for required compaction")
    if summary_artifact_ref is not None and not str(summary_artifact_ref).strip():
        raise ContextBudgetError("summary artifact reference invalid")
    return {
        "schema": "fa3.context-compaction-receipt.v1",
        "source_state_sha256": plan["source_state_sha256"],
        "selected_segment_ids": list(plan["selected_segment_ids"]),
        "selected_provenance_refs": list(plan.get("selected_provenance_refs", [])),
        "summary_artifact_ref": summary_artifact_ref,
        "source_history_mutated": False,
        "provenance_preserved": True,
        "retrieval_backreferences_required": bool(plan.get("retrieval_backreferences_required")),
        "authority": False,
    }
