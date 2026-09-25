#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import uuid
from typing import Any

from fa3_caption_subtitle import (
    CaptionError,
    build_narration_plan,
    document_sha256,
    export_subtitle,
    parse_subtitle,
    revise_document,
    validate_document,
)

ACTION_IDS = (
    "caption.import",
    "caption.edit",
    "caption.sync",
    "caption.qc",
    "caption.export",
    "caption.translate",
    "caption.hardsub.recover",
    "caption.overlay.project",
    "caption.editorial.project",
    "narration.plan",
    "narration.synthesize",
    "narration.mix",
    "audio-description.plan",
)

NATIVE_ACTION_IDS = (
    "caption.import",
    "caption.edit",
    "caption.sync",
    "caption.qc",
    "caption.export",
    "caption.overlay.project",
    "caption.editorial.project",
    "narration.plan",
    "audio-description.plan",
)

def edit_cue(doc: dict[str, Any], cue_id: str, text: str, *, actor: str = "USER") -> dict[str, Any]:
    validate_document(doc)
    if not isinstance(text, str) or not text.strip():
        raise CaptionError("edited caption text must be non-empty")
    out = revise_document(doc, operation=f"EDIT_CUE:{cue_id}", actor=actor)
    found = False
    for track in out["tracks"]:
        for cue in track["cues"]:
            if cue.get("id") == cue_id:
                if "source_text" not in cue:
                    cue["source_text"] = cue["text"]
                cue["text"] = text.strip()
                cue["edited_by"] = actor
                found = True
                break
    if not found:
        raise CaptionError(f"unknown cue id: {cue_id}")
    validate_document(out)
    return out

def synchronize_document(doc: dict[str, Any], *, offset_ms: int = 0, drift_ppm: float = 0.0, actor: str = "USER") -> dict[str, Any]:
    validate_document(doc)
    if abs(float(drift_ppm)) > 100000:
        raise CaptionError("drift_ppm outside bounded range")
    out = revise_document(doc, operation=f"SYNC:offset={offset_ms}:drift_ppm={drift_ppm}", actor=actor)
    factor = 1.0 + float(drift_ppm) / 1_000_000.0
    for track in out["tracks"]:
        for cue in track["cues"]:
            for key in ("start_ms", "end_ms"):
                cue[key] = int(round(cue[key] * factor)) + int(offset_ms)
            if cue["start_ms"] < 0:
                raise CaptionError("synchronization would create negative caption time")
            for word in cue.get("words", []):
                word["start_ms"] = int(round(word["start_ms"] * factor)) + int(offset_ms)
                word["end_ms"] = int(round(word["end_ms"] * factor)) + int(offset_ms)
    validate_document(out)
    return out

def caption_quality_report(
    doc: dict[str, Any],
    *,
    max_chars_per_second: float = 20.0,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
    min_duration_ms: int = 500,
) -> dict[str, Any]:
    validate_document(doc)
    issues: list[dict[str, Any]] = []
    for track in doc["tracks"]:
        for cue in track["cues"]:
            duration_ms = cue["end_ms"] - cue["start_ms"]
            lines = cue["text"].splitlines() or [cue["text"]]
            cps = len(cue["text"].replace("\n", "")) / (duration_ms / 1000.0)
            if duration_ms < min_duration_ms:
                issues.append({"cue_id": cue["id"], "code": "CAPTION_TOO_SHORT", "value": duration_ms, "limit": min_duration_ms})
            if cps > max_chars_per_second:
                issues.append({"cue_id": cue["id"], "code": "READING_SPEED", "value": round(cps, 3), "limit": max_chars_per_second})
            if len(lines) > max_lines:
                issues.append({"cue_id": cue["id"], "code": "TOO_MANY_LINES", "value": len(lines), "limit": max_lines})
            if max((len(line) for line in lines), default=0) > max_chars_per_line:
                issues.append({"cue_id": cue["id"], "code": "LINE_TOO_LONG", "value": max(len(line) for line in lines), "limit": max_chars_per_line})
    return {
        "schema": "fa3.caption-quality-evidence.v1",
        "caption_document_sha256": document_sha256(doc),
        "status": "PASS" if not issues else "REVIEW_REQUIRED",
        "issues": issues,
        "limits": {
            "max_chars_per_second": max_chars_per_second,
            "max_chars_per_line": max_chars_per_line,
            "max_lines": max_lines,
            "min_duration_ms": min_duration_ms,
        },
    }

def build_hardsub_recovery_request(
    media_ref: str,
    *,
    language: str = "und",
    regions: list[dict[str, Any]] | None = None,
    provider_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not str(media_ref).strip():
        raise CaptionError("media_ref is required")
    return {
        "schema": "fa3.hardsub-recovery-request.v1",
        "request_id": str(uuid.uuid4()),
        "media_ref": media_ref,
        "language": language,
        "regions": regions or [],
        "provider_constraints": provider_constraints or {},
        "provider_selection_authority": "FA3-AUTH-MODEL-ROUTER-001",
        "direct_provider_selection": False,
        "runtime_status": "PENDING_ADMITTED_OCR_PROVIDER",
    }

def build_editorial_projection(doc: dict[str, Any], target: str) -> dict[str, Any]:
    validate_document(doc)
    key = target.strip().upper()
    allowed = {"KDENLIVE", "QUICKCLIP", "CREATIVE_STUDIO"}
    if key not in allowed:
        raise CaptionError(f"unsupported editorial target: {target}")
    return {
        "schema": "fa3.caption-editorial-projection.v1",
        "target": key,
        "caption_document_sha256": document_sha256(doc),
        "canonical_timeline_ir": "OpenTimelineIO",
        "editable_caption_semantics_required": True,
        "flattening_forbidden": True,
        "preferred_sidecars": ["ASS", "SRT", "VTT", "FA3 Caption JSON"],
    }

def build_browser_overlay_projection(doc: dict[str, Any]) -> dict[str, Any]:
    validate_document(doc)
    return {
        "schema": "fa3.caption-browser-overlay-projection.v1",
        "caption_document_sha256": document_sha256(doc),
        "presentation_only": True,
        "canonical_state": False,
        "supports_live_offset": True,
        "supports_style_projection": True,
        "supports_sentence_replay": True,
        "source_track_count": len(doc["tracks"]),
    }

def build_audio_description_gap_plan(
    doc: dict[str, Any],
    media_duration_ms: int,
    *,
    min_gap_ms: int = 1500,
    edge_guard_ms: int = 150,
) -> dict[str, Any]:
    validate_document(doc)
    if media_duration_ms <= 0 or min_gap_ms <= 0:
        raise CaptionError("media duration and minimum gap must be positive")
    occupied = sorted(
        (cue["start_ms"], cue["end_ms"])
        for track in doc["tracks"]
        for cue in track["cues"]
    )
    merged: list[list[int]] = []
    for start, end in occupied:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    gaps = []
    cursor = 0
    for start, end in merged:
        gap_start = cursor + (edge_guard_ms if cursor else 0)
        gap_end = start - edge_guard_ms
        if gap_end - gap_start >= min_gap_ms:
            gaps.append({"start_ms": gap_start, "end_ms": gap_end, "duration_ms": gap_end-gap_start})
        cursor = max(cursor, end)
    gap_start = cursor + (edge_guard_ms if cursor else 0)
    gap_end = media_duration_ms
    if gap_end-gap_start >= min_gap_ms:
        gaps.append({"start_ms": gap_start, "end_ms": gap_end, "duration_ms": gap_end-gap_start})
    return {
        "schema": "fa3.audio-description-gap-plan.v1",
        "caption_document_sha256": document_sha256(doc),
        "media_duration_ms": media_duration_ms,
        "min_gap_ms": min_gap_ms,
        "gaps": gaps,
        "generated_description_text": False,
        "human_review_required_before_synthesis": True,
    }

def build_uaf_request(action_id: str, arguments: dict[str, Any], *, principal_id: str, context_id: str) -> dict[str, Any]:
    if action_id not in ACTION_IDS:
        raise CaptionError(f"unknown caption/narration action: {action_id}")
    if not principal_id or not context_id:
        raise CaptionError("principal_id and context_id are required")
    return {
        "schema": "fa3.uaf.action-request.v1",
        "request_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "action_id": action_id,
        "arguments": copy.deepcopy(arguments),
        "principal": {"id": principal_id},
        "context": {"schema": "fa3.uaf.execution-context.v1", "context_id": context_id, "application": "FA3-CAPTION-SUBTITLE-001"},
        "provider_selection": "UAF_POLICY_BOUNDED",
        "direct_provider_bypass": False,
    }

def execute_native_action(action_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if action_id == "caption.import":
        doc = parse_subtitle(arguments["content"], arguments["format"], language=arguments.get("language", "und"), fps=float(arguments.get("fps", 25.0)))
        return {"status": "PASS", "artifact": doc, "evidence_refs": [document_sha256(doc)]}
    if action_id == "caption.edit":
        doc = edit_cue(arguments["document"], arguments["cue_id"], arguments["text"], actor=arguments.get("actor", "USER"))
        return {"status": "PASS", "artifact": doc, "evidence_refs": [document_sha256(doc)]}
    if action_id == "caption.sync":
        doc = synchronize_document(arguments["document"], offset_ms=int(arguments.get("offset_ms", 0)), drift_ppm=float(arguments.get("drift_ppm", 0.0)), actor=arguments.get("actor", "USER"))
        return {"status": "PASS", "artifact": doc, "evidence_refs": [document_sha256(doc)]}
    if action_id == "caption.qc":
        result = caption_quality_report(arguments["document"])
        return {"status": "PASS", "artifact": result, "evidence_refs": [result["caption_document_sha256"]]}
    if action_id == "caption.export":
        content = export_subtitle(arguments["document"], arguments["format"])
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return {"status": "PASS", "artifact": {"format": arguments["format"], "content": content, "sha256": digest}, "evidence_refs": [digest]}
    if action_id == "caption.overlay.project":
        result = build_browser_overlay_projection(arguments["document"])
        return {"status": "PASS", "artifact": result, "evidence_refs": [result["caption_document_sha256"]]}
    if action_id == "caption.editorial.project":
        result = build_editorial_projection(arguments["document"], arguments["target"])
        return {"status": "PASS", "artifact": result, "evidence_refs": [result["caption_document_sha256"]]}
    if action_id == "narration.plan":
        result = build_narration_plan(arguments["document"], voice_identity_ref=arguments.get("voice_identity_ref", "FA3-VOICE-DEFAULT"), speaker_voice_map=arguments.get("speaker_voice_map"), narration_mode=arguments.get("mode", "NARRATION"))
        return {"status": "PASS", "artifact": result, "evidence_refs": [result["caption_document_sha256"]]}
    if action_id == "audio-description.plan":
        result = build_audio_description_gap_plan(arguments["document"], int(arguments["media_duration_ms"]), min_gap_ms=int(arguments.get("min_gap_ms", 1500)))
        return {"status": "PASS", "artifact": result, "evidence_refs": [result["caption_document_sha256"]]}
    raise CaptionError(f"action requires a separately admitted external/provider runtime: {action_id}")
