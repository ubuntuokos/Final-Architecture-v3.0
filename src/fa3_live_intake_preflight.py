"""Fail-closed, side-effect-free LIVE selective import plan preflight.

This module does not connect, fetch, store, install models or authorize capture.
It is a proposed subordinate inspector for the existing FA3 ProductionImportPlan.
Execution still needs canonical rights/endpoint/independence receipts, UAF, HRB,
Security, Model Router (when needed), Temporal and exact-host evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / "canonical/schemas/live-production-source.v1.json"
TEXT = frozenset({"ORIGINAL_LANGUAGE", "ONE_TRANSLATION", "MULTI_TRANSLATION",
                  "ORIGINAL_PLUS_TRANSLATIONS"})
AUDIO = frozenset({"FULL_AUDIO", "TRANSCRIPT_ONLY", "SPEECH_OR_SINGING_SEPARATE",
                   "INSTRUMENTAL_ONLY", "AMBIENCE_AND_SFX", "DENOISED_SPEECH"})
VIDEO = frozenset({"FULL_VIDEO", "VIDEO_WITHOUT_AUDIO", "FULL_AUDIO_ONLY",
                   "TRANSCRIPT_ONLY", "MUSIC_OR_INSTRUMENTAL_ONLY",
                   "AMBIENCE_AND_SFX_ONLY", "FRAMES_OR_SCENES"})
LANG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
REF = re.compile(r"^ref:[A-Za-z0-9][A-Za-z0-9_.-]{0,247}$")
PROTOCOLS = {
    "LIVE_CAPTIONS": frozenset({"EBU_TT_LIVE_WS", "HLS_SUBTITLES"}),
    "LIVE_AUDIO": frozenset({"HLS_AUDIO", "SRT", "RTMP", "RTSP",
                             "WEBRTC", "ICECAST", "OBS_LOCAL"}),
    "LIVE_VIDEO": frozenset({"HLS_EMBEDDED_CC", "HLS_VIDEO", "SRT", "RTMP",
                             "RTSP", "WEBRTC", "OBS_LOCAL"}),
}
MODES = frozenset({"MONITOR_ONLY", "SELECTIVE_CAPTURE",
                   "AUTHORIZED_RECORD_AND_DERIVE", "CAPTION_ONLY"})


class LiveIntakePreflightError(ValueError):
    """A request was rejected before transport/model execution."""


def _ref(req: dict[str, Any], key: str, *, required: bool = True) -> None:
    value = req.get(key)
    if value is None and not required:
        return
    if not isinstance(value, str) or not REF.fullmatch(value):
        raise LiveIntakePreflightError(f"{key}: require opaque authorized ref:, never raw URL or credentials")


def preflight(request: dict[str, Any]) -> dict[str, Any]:
    """Return non-executing prospective worker bounds, never an admission receipt."""
    if not isinstance(request, dict):
        raise LiveIntakePreflightError("request must be an object")
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    properties = schema["properties"]
    missing = sorted(set(schema["required"]) - set(request))
    extra = sorted(set(request) - set(properties))
    if missing or extra:
        raise LiveIntakePreflightError(f"missing={missing}; unrecognized={extra}")
    if request.get("schema") != "fa3.live-production-source.v1":
        raise LiveIntakePreflightError("unknown request version")
    source = request.get("source_mode")
    protocol = request.get("source_protocol")
    mode = request.get("delivery_mode")
    if source not in PROTOCOLS or protocol not in PROTOCOLS[source]:
        raise LiveIntakePreflightError("source protocol not admitted for selected live source")
    if mode not in MODES:
        raise LiveIntakePreflightError("invalid delivery mode")
    _ref(request, "authorized_endpoint_ref")
    _ref(request, "rights_receipt_ref")
    _ref(request, "approved_capture_scope_ref")
    if mode == "AUTHORIZED_RECORD_AND_DERIVE":
        _ref(request, "recording_authorization_ref")
    else:
        _ref(request, "recording_authorization_ref", required=False)
    if "independence_inspection_ref" in request:
        _ref(request, "independence_inspection_ref")
    if "source_epoch_ref" in request:
        _ref(request, "source_epoch_ref")
    if "source_timing_ref" in request:
        _ref(request, "source_timing_ref")
    for key in ("no_av_fetch", "no_media_persist"):
        if type(request.get(key)) is not bool:
            raise LiveIntakePreflightError(f"{key} must be an explicit boolean")
    for field, low, high in (("buffer_max_bytes", 1024, 1073741824),
                             ("max_duration_seconds", 1, 86400)):
        value = request.get(field)
        if type(value) is not int or not low <= value <= high:
            raise LiveIntakePreflightError(f"{field} outside bounded policy")
    allowed = {
        "LIVE_CAPTIONS": TEXT,
        "LIVE_AUDIO": TEXT | AUDIO,
        "LIVE_VIDEO": TEXT | VIDEO,
    }[source]
    requested = request.get("requested_outputs")
    if not isinstance(requested, list) or len(requested) > 17 or any(
        not isinstance(x, str) for x in requested
    ) or len(requested) != len(set(requested)) or not set(requested) <= allowed:
        raise LiveIntakePreflightError("unknown, duplicate or source-incompatible output")
    if mode != "MONITOR_ONLY" and not requested:
        raise LiveIntakePreflightError("must select at least one output for capture")
    if mode == "CAPTION_ONLY":
        if set(requested) - (TEXT | {"TRANSCRIPT_ONLY"}):
            raise LiveIntakePreflightError("caption-only plan cannot publish AV outputs")
        if request["no_media_persist"] is not True:
            raise LiveIntakePreflightError("caption-only plan must not persist media")
    if source == "LIVE_CAPTIONS":
        if mode not in {"CAPTION_ONLY", "MONITOR_ONLY"} or not request["no_av_fetch"] or not request["no_media_persist"]:
            raise LiveIntakePreflightError("independent caption feeds must not receive/persist AV")
        _ref(request, "independence_inspection_ref")
    elif request["no_av_fetch"]:
        raise LiveIntakePreflightError("NO_AV_FETCH requires verified standalone caption endpoint")
    source_lang = request.get("source_language")
    if not isinstance(source_lang, str) or (
        source_lang != "auto" and not LANG.fullmatch(source_lang)
    ):
        raise LiveIntakePreflightError("source_language requires valid BCP-47-like code or auto")
    langs = request.get("target_languages")
    if not isinstance(langs, list) or len(langs) > 64 or len(langs) != len(set(map(str, langs))) or any(
        not isinstance(x, str) or not LANG.fullmatch(x) for x in langs
    ):
        raise LiveIntakePreflightError("target language tags invalid or duplicate")
    single_locale = request.get("one_translation_language")
    if single_locale is not None and (
        not isinstance(single_locale, str) or not LANG.fullmatch(single_locale)
    ):
        raise LiveIntakePreflightError("dedicated one-translation language is invalid")
    if "ONE_TRANSLATION" in requested:
        if single_locale is None:
            if "MULTI_TRANSLATION" in requested or len(langs) != 1:
                raise LiveIntakePreflightError("one translation needs its own locale when combined with multi")
            single_locale = langs[0]
    if "MULTI_TRANSLATION" in requested and len(langs) < 2:
        raise LiveIntakePreflightError("multi translation needs at least two target locales")
    if "ORIGINAL_PLUS_TRANSLATIONS" in requested and not langs:
        raise LiveIntakePreflightError("original-plus-translations needs targets")
    if request.get("destination_application") not in properties["destination_application"]["enum"]:
        raise LiveIntakePreflightError("unknown FA3 destination application")
    return {
        "plan_status": "PREFLIGHT_ONLY_NOT_RUNTIME_ADMITTED",
        "source_mode": source,
        "source_protocol": protocol,
        "delivery_mode": mode,
        "selected_outputs": list(requested),
        "target_languages": list(langs),
        "one_translation_language": single_locale,
        "no_av_fetch_required": bool(request["no_av_fetch"]),
        "media_persistence_permitted": not request["no_media_persist"],
        "prospective_audio_workers_for_independent_captions": 0 if source == "LIVE_CAPTIONS" else None,
        "prospective_video_workers_for_independent_captions": 0 if source == "LIVE_CAPTIONS" else None,
        "existing_inspector_must_verify_refs_before_execution": True,
        "runtime_execution_authorized": False,
        "recording_authorized_by_preflight": False,
    }
