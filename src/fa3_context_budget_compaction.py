#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any

CONTEXT_CLASSES = {"PROTECTED", "ACTIVE", "SUMMARIZABLE", "ARCHIVABLE", "RETRIEVABLE"}
REMOVAL_ORDER = {"ARCHIVABLE": 0, "RETRIEVABLE": 1, "SUMMARIZABLE": 2}
ACTION_BY_CLASS = {
    "ARCHIVABLE": "ARCHIVE_CANDIDATE",
    "RETRIEVABLE": "RETRIEVAL_BACKREFERENCE",
    "SUMMARIZABLE": "SUMMARIZATION_CANDIDATE",
}


class ContextBudgetError(ValueError):
    pass


def _strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


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


def _checkpoint_lineage(
    source_state_sha256: str,
    checkpoint_id: str | None,
    parent_checkpoint_id: str | None,
) -> dict[str, Any]:
    checkpoint = str(checkpoint_id or f"ctx:{source_state_sha256[:24]}").strip()
    parent = str(parent_checkpoint_id).strip() if parent_checkpoint_id is not None else None
    if not checkpoint:
        raise ContextBudgetError("checkpoint id invalid")
    if parent == checkpoint:
        raise ContextBudgetError("checkpoint cannot parent itself")
    return {
        "checkpoint_id": checkpoint,
        "parent_checkpoint_id": parent,
        "source_state_sha256": source_state_sha256,
    }


def plan_context_compaction(
    segments: list[dict[str, Any]],
    *,
    max_context_tokens: int,
    target_context_tokens: int,
    min_headroom_tokens: int,
    min_growth_tokens: int,
    last_compaction_total_tokens: int | None = None,
    tool_schema_overhead_tokens: int = 0,
    multimodal_overhead_tokens: int = 0,
    reserved_output_tokens: int = 0,
    hysteresis_tokens: int = 0,
    now_seconds: float | None = None,
    last_compaction_at_seconds: float | None = None,
    cooldown_seconds: float = 0.0,
    checkpoint_id: str | None = None,
    parent_checkpoint_id: str | None = None,
) -> dict[str, Any]:
    checked = validate_segments(segments)
    for name, value in (
        ("max_context_tokens", max_context_tokens),
        ("target_context_tokens", target_context_tokens),
        ("min_headroom_tokens", min_headroom_tokens),
        ("min_growth_tokens", min_growth_tokens),
        ("tool_schema_overhead_tokens", tool_schema_overhead_tokens),
        ("multimodal_overhead_tokens", multimodal_overhead_tokens),
        ("reserved_output_tokens", reserved_output_tokens),
        ("hysteresis_tokens", hysteresis_tokens),
    ):
        if not _strict_int(value) or value < 0:
            raise ContextBudgetError(f"{name} invalid")
    if max_context_tokens <= 0 or target_context_tokens > max_context_tokens:
        raise ContextBudgetError("context budget ordering invalid")
    if reserved_output_tokens >= max_context_tokens:
        raise ContextBudgetError("reserved output consumes complete context budget")
    effective_context_limit = max_context_tokens - reserved_output_tokens
    if min_headroom_tokens > effective_context_limit:
        raise ContextBudgetError("headroom exceeds effective context budget")
    if hysteresis_tokens > effective_context_limit:
        raise ContextBudgetError("hysteresis exceeds effective context budget")
    if last_compaction_total_tokens is not None and (
        not _strict_int(last_compaction_total_tokens) or last_compaction_total_tokens < 0
    ):
        raise ContextBudgetError("last compaction total invalid")
    if not _nonnegative_number(cooldown_seconds):
        raise ContextBudgetError("cooldown invalid")
    if last_compaction_at_seconds is not None:
        if not _nonnegative_number(last_compaction_at_seconds) or not _nonnegative_number(now_seconds):
            raise ContextBudgetError("cooldown timestamps invalid")
        if float(now_seconds) < float(last_compaction_at_seconds):
            raise ContextBudgetError("cooldown time moved backwards")
    elif now_seconds is not None and not _nonnegative_number(now_seconds):
        raise ContextBudgetError("now_seconds invalid")

    segment_tokens = sum(row["token_count"] for row in checked)
    overhead_tokens = tool_schema_overhead_tokens + multimodal_overhead_tokens
    total = segment_tokens + overhead_tokens
    soft_trigger = effective_context_limit - min_headroom_tokens
    effective_target = min(target_context_tokens, max(0, soft_trigger - hysteresis_tokens))
    state_digest = context_state_digest(checked)
    lineage = _checkpoint_lineage(state_digest, checkpoint_id, parent_checkpoint_id)

    base = {
        "schema": "fa3.context-compaction-plan.v2",
        "source_state_sha256": state_digest,
        "source_total_tokens": total,
        "segment_tokens": segment_tokens,
        "tool_schema_overhead_tokens": tool_schema_overhead_tokens,
        "multimodal_overhead_tokens": multimodal_overhead_tokens,
        "overhead_tokens": overhead_tokens,
        "reserved_output_tokens": reserved_output_tokens,
        "max_context_tokens": max_context_tokens,
        "effective_context_limit": effective_context_limit,
        "target_context_tokens": target_context_tokens,
        "effective_target_tokens": effective_target,
        "min_headroom_tokens": min_headroom_tokens,
        "min_growth_tokens": min_growth_tokens,
        "hysteresis_tokens": hysteresis_tokens,
        "cooldown_seconds": float(cooldown_seconds),
        "checkpoint_lineage": lineage,
        "source_history_mutated": False,
        "provenance_preserved": True,
        "authority": False,
    }
    if total <= soft_trigger:
        return {
            **base,
            "status": "NOOP_HEADROOM_SUFFICIENT",
            "selected_segment_ids": [],
            "selected_actions": [],
            "projected_total_tokens": total,
        }

    hard_overflow = total > effective_context_limit
    if last_compaction_at_seconds is not None and float(cooldown_seconds) > 0:
        elapsed = float(now_seconds) - float(last_compaction_at_seconds)
        if elapsed < float(cooldown_seconds) and not hard_overflow:
            return {
                **base,
                "status": "DEFER_COOLDOWN",
                "cooldown_remaining_seconds": float(cooldown_seconds) - elapsed,
                "selected_segment_ids": [],
                "selected_actions": [],
                "projected_total_tokens": total,
            }

    if (
        last_compaction_total_tokens is not None
        and not hard_overflow
        and total - last_compaction_total_tokens < min_growth_tokens
    ):
        return {
            **base,
            "status": "DEFER_ANTI_THRASH",
            "selected_segment_ids": [],
            "selected_actions": [],
            "projected_total_tokens": total,
        }

    candidates = [row for row in checked if row["classification"] in REMOVAL_ORDER]
    candidates.sort(
        key=lambda row: (
            REMOVAL_ORDER[row["classification"]],
            int(row.get("ordinal", 0)),
            row["segment_id"],
        )
    )
    selected = []
    projected = total
    for row in candidates:
        if projected <= effective_target:
            break
        selected.append(row)
        projected -= row["token_count"]

    actions = [
        {
            "segment_id": row["segment_id"],
            "classification": row["classification"],
            "action": ACTION_BY_CLASS[row["classification"]],
            "provenance_ref": row["provenance_ref"],
        }
        for row in selected
    ]
    if projected > effective_context_limit:
        return {
            **base,
            "status": "FAIL_CLOSED_RESELECTION_REQUIRED",
            "selected_segment_ids": [row["segment_id"] for row in selected],
            "selected_actions": actions,
            "projected_total_tokens": projected,
            "protected_or_active_tokens": sum(
                row["token_count"]
                for row in checked
                if row["classification"] in {"PROTECTED", "ACTIVE"}
            ),
            "noncompactable_overhead_tokens": overhead_tokens,
        }

    return {
        **base,
        "status": "COMPACTION_REQUIRED",
        "selected_segment_ids": [row["segment_id"] for row in selected],
        "selected_provenance_refs": [row["provenance_ref"] for row in selected],
        "selected_actions": actions,
        "projected_total_tokens": projected,
        "target_reached": projected <= effective_target,
        "summarization_required": any(row["classification"] == "SUMMARIZABLE" for row in selected),
        "archive_candidate_present": any(row["classification"] == "ARCHIVABLE" for row in selected),
        "retrieval_backreferences_required": bool(selected),
        "silent_context_drop": False,
    }


def compaction_receipt(
    plan: dict[str, Any],
    *,
    summary_artifact_ref: str | None = None,
) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema") not in {
        "fa3.context-compaction-plan.v1",
        "fa3.context-compaction-plan.v2",
    }:
        raise ContextBudgetError("compaction plan required")
    if plan.get("status") != "COMPACTION_REQUIRED":
        raise ContextBudgetError("receipt only valid for required compaction")
    if summary_artifact_ref is not None and not str(summary_artifact_ref).strip():
        raise ContextBudgetError("summary artifact reference invalid")
    if plan.get("summarization_required") and not summary_artifact_ref:
        raise ContextBudgetError("summary artifact required for summarization candidate")
    return {
        "schema": "fa3.context-compaction-receipt.v2",
        "source_state_sha256": plan["source_state_sha256"],
        "checkpoint_lineage": dict(plan.get("checkpoint_lineage", {})),
        "selected_segment_ids": list(plan["selected_segment_ids"]),
        "selected_provenance_refs": list(plan.get("selected_provenance_refs", [])),
        "selected_actions": list(plan.get("selected_actions", [])),
        "summary_artifact_ref": summary_artifact_ref,
        "tool_schema_overhead_tokens": int(plan.get("tool_schema_overhead_tokens", 0)),
        "multimodal_overhead_tokens": int(plan.get("multimodal_overhead_tokens", 0)),
        "reserved_output_tokens": int(plan.get("reserved_output_tokens", 0)),
        "hysteresis_tokens": int(plan.get("hysteresis_tokens", 0)),
        "cooldown_seconds": float(plan.get("cooldown_seconds", 0.0)),
        "source_history_mutated": False,
        "provenance_preserved": True,
        "retrieval_backreferences_required": bool(plan.get("retrieval_backreferences_required")),
        "authority": False,
    }
