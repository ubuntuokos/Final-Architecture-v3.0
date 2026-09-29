"""S2 metadata-only stream binding, subordinate to existing FA3 file.convert.inspect.

No codec, source file, host execution, model, authorization or proof occurs here.
Authenticated inspector/stem receipts are verified by existing FA3 authorities later.
"""
from __future__ import annotations
import re
from typing import Any
from fa3_selective_import_preview import preflight_preview

SCHEMA = "fa3.selective-source-stream-inventory.v1"
REF = re.compile(r"^ref:[A-Za-z0-9][A-Za-z0-9_.-]{0,247}$")
TYPES = {"audio", "video", "subtitle"}
STEMS = {"UNKNOWN", "SPEECH", "SINGING", "VOCALS", "INSTRUMENTAL",
         "MUSIC", "AMBIENCE", "SFX", "AMBIENCE_AND_SFX"}
SPECIAL = {("AUDIO", "SPEECH_OR_SINGING_SEPARATE"),
           ("AUDIO", "INSTRUMENTAL_ONLY"), ("AUDIO", "AMBIENCE_AND_SFX"),
           ("VIDEO", "MUSIC_OR_INSTRUMENTAL_ONLY"),
           ("VIDEO", "AMBIENCE_AND_SFX_ONLY")}
AUDIO_LEAVES = SPECIAL | {("AUDIO", "FULL_AUDIO"),
                           ("AUDIO", "TRANSCRIPT_ONLY"),
                           ("AUDIO", "DENOISED_SPEECH"),
                           ("VIDEO", "FULL_AUDIO_ONLY"),
                           ("VIDEO", "TRANSCRIPT_ONLY")}

def valid_int(v: Any, minimum: int = 0) -> bool:
    return type(v) is int and v >= minimum

def inspect_binding(request: dict, inventory: dict, choices: list[dict] | None = None) -> dict:
    """Return bounded per-leaf preview, never an executable FFmpeg command."""
    preflight_preview(request)
    if request["source_mode"] not in {"FILE", "EXTERNAL_PROJECT"}:
        raise ValueError("live streams require separate authorized live-source inspector")
    required = {"schema", "source_ref", "source_sha256", "inspector_receipt_ref",
                "inspector_authority", "inspector_status", "streams"}
    if not isinstance(inventory, dict) or set(inventory) != required:
        raise ValueError("unknown or missing inspector contract field")
    if (inventory["schema"] != SCHEMA or
        inventory["inspector_authority"] != "file.convert.inspect" or
        inventory["inspector_status"] != "INSPECTED_ONLY"):
        raise ValueError("not the existing File Conversion inspector preview")
    if (inventory["source_ref"] != request["source_ref"] or
        inventory["source_sha256"] != request["source_sha256"] or
        not isinstance(inventory["inspector_receipt_ref"], str) or
        not REF.fullmatch(inventory["inspector_receipt_ref"])):
        raise ValueError("invalid source identity, digest or opaque inspection receipt")
    rows = inventory["streams"]
    if (not isinstance(rows, list) or len(rows) > 64 or
        (not rows and request["source_kind"] != "TEXT")):
        raise ValueError("expected bounded streams, or zero for a text document")
    streams = {}
    for s in rows:
        if not isinstance(s, dict) or set(s) - {
            "index", "codec_type", "time_base_num", "time_base_den",
            "start_pts", "duration_ts", "sample_rate", "channels",
            "channel_layout", "width", "height", "role",
            "source_stem_attestation_ref"}:
            raise ValueError("unknown stream fields")
        i, kind = s.get("index"), s.get("codec_type")
        if not valid_int(i) or i > 32767 or i in streams or kind not in TYPES:
            raise ValueError("invalid, duplicated or unknown original stream index")
        if (not valid_int(s.get("time_base_num"), 1) or
            not valid_int(s.get("time_base_den"), 1) or
            type(s.get("start_pts")) is not int or
            ("duration_ts" in s and not valid_int(s["duration_ts"], 1))):
            raise ValueError("invalid original rational PTS/timebase")
        if kind == "audio" and (not valid_int(s.get("sample_rate"), 1) or
                                 not valid_int(s.get("channels"), 1)):
            raise ValueError("missing audio sampling/layout information")
        if kind == "video" and (not valid_int(s.get("width"), 1) or
                                 not valid_int(s.get("height"), 1)):
            raise ValueError("missing original video dimensions")
        role = s.get("role", "UNKNOWN")
        if role not in STEMS or (kind != "audio" and role != "UNKNOWN"):
            raise ValueError("untrusted stem classification")
        if "source_stem_attestation_ref" in s:
            if (kind != "audio" or role == "UNKNOWN" or
                not isinstance(s["source_stem_attestation_ref"], str) or
                not REF.fullmatch(s["source_stem_attestation_ref"])):
                raise ValueError("unsupported source stem attestation")
        if "channel_layout" in s and (
            not isinstance(s["channel_layout"], str) or
            not re.fullmatch(r"[A-Za-z0-9_.+]{1,48}", s["channel_layout"])):
            raise ValueError("unsafe channel layout metadata")
        streams[i] = s

    selections = {}
    if choices is not None and not isinstance(choices, list):
        raise ValueError("invalid operator choices")
    for row in choices or []:
        if not isinstance(row, dict) or set(row) != {"leaf_index", "stream_indices"}:
            raise ValueError("invalid operator choice fields")
        n, indexes = row["leaf_index"], row["stream_indices"]
        if not valid_int(n) or n >= len(request["requested_outputs"]) or n in selections:
            raise ValueError("invalid or repeated output leaf selection")
        if (not isinstance(indexes, list) or not 1 <= len(indexes) <= 64 or
            any(not valid_int(i) or i not in streams for i in indexes) or
            len(indexes) != len(set(indexes))):
            raise ValueError("unknown or repeated stream indices")
        selections[n] = indexes

    leaves = []
    for n, out in enumerate(request["requested_outputs"]):
        family, selector = out["family"], out["selector_id"]
        is_transcript = selector == "TRANSCRIPT_ONLY"
        full = (family, selector) in {
            ("AUDIO", "FULL_AUDIO"), ("VIDEO", "FULL_VIDEO"),
            ("VIDEO", "FULL_AUDIO_ONLY")}
        if family == "TEXT":
            # A derived text output may come from original timed text or ASR.
            # AUDIO sources need their audio stream; VIDEO with both audio and
            # subtitles requires an explicit choice rather than silent bias.
            kind = (None if request["source_kind"] == "TEXT"
                    else "audio" if request["source_kind"] == "AUDIO"
                    else "audio_or_subtitle")
        elif (family, selector) in AUDIO_LEAVES:
            kind = "audio"
        else:
            kind = "video"
        allowed_types = ({"audio", "subtitle"} if kind == "audio_or_subtitle"
                         else {kind} if kind is not None else set())
        available = [s for _, s in sorted(streams.items())
                     if s["codec_type"] in allowed_types]
        operator = selections.get(n)
        if kind is None:
            if operator is not None:
                raise ValueError("document text cannot bind a media stream")
            chosen = []
        elif operator is not None:
            if any(streams[i]["codec_type"] not in allowed_types
                   and (family, selector) != ("VIDEO", "FULL_VIDEO")
                   for i in operator):
                raise ValueError("operator selected wrong stream kind")
            chosen = [streams[i] for i in operator]
            if (family, selector) == ("VIDEO", "FULL_VIDEO"):
                if not any(s["codec_type"] == "video" for s in chosen):
                    raise ValueError("full-video selection requires a video stream")
            elif not full and len(chosen) != 1:
                raise ValueError("single source stream required for this output")
        elif (family, selector) == ("VIDEO", "FULL_VIDEO"):
            chosen = [s for _, s in sorted(streams.items())]
        elif full:
            chosen = available
        else:
            chosen = available if len(available) == 1 else []

        if kind is not None and not available:
            status = "BLOCKED_MISSING_REQUIRED_SOURCE_STREAM"
        elif kind is not None and not chosen:
            status = "PENDING_EXPLICIT_SOURCE_STREAM_SELECTION"
        elif (family, selector) in SPECIAL:
            requested = out["requested_stem_class"]
            orig = {s.get("role", "UNKNOWN") for s in chosen}
            attested = all(s.get("source_stem_attestation_ref") for s in chosen)
            status = ("PENDING_ORIGINAL_STEM_ATTESTATION_VERIFICATION"
                      if attested and requested in orig
                      else "PENDING_EXACT_STEM_PROVIDER_OR_UNSUPPORTED")
        elif (family, selector) == ("AUDIO", "DENOISED_SPEECH"):
            status = "PENDING_SEPARATE_DENOISE_ADMISSION"
        elif is_transcript or family == "TEXT" and kind is not None:
            status = "PENDING_STT_OR_SUBTITLE_LANGUAGE_AND_TIMING"
        else:
            status = "PENDING_CODEC_AND_SOURCE_TRACK_EVIDENCE"

        leaves.append({
            "leaf_index": n, "family": family, "selector_id": selector,
            "target_application": out["target_application"],
            "source_range": out["source_range"],
            "original_stream_indices": [s["index"] for s in chosen],
            "original_timebases": [{"stream_index": s["index"],
                "numerator": s["time_base_num"], "denominator": s["time_base_den"],
                "start_pts": s["start_pts"], "duration_ts": s.get("duration_ts")}
                for s in chosen],
            "target_languages": list(out["target_languages"]),
            "internal_audio_dependency_only": is_transcript or (
                family == "TEXT" and any(s["codec_type"] == "audio"
                                         for s in chosen)),
            "publish_audio": family != "TEXT" and not is_transcript and (
                kind == "audio" or (selector == "FULL_VIDEO" and
                any(s["codec_type"] == "audio" for s in chosen))),
            "publish_video": family != "TEXT" and kind == "video",
            "status": status, "execution_authorized": False,
            "original_exactness_verified": False,
        })
    return {
        "schema": "fa3.selective-source-stream-binding.v1",
        "source_ref": request["source_ref"],
        "inspector_receipt_ref": inventory["inspector_receipt_ref"],
        "status": "INSPECTED_STREAM_MAPPING_PREVIEW_ONLY",
        "outputs": leaves, "execution_authorized": False,
        "authority": False,
    }
