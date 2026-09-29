"""FA3 selective import S1 preflight-only policy checker.

Consumes an already-authorized ProductionImportPlan child request. No file reads,
process execution, networking, GUI, model or codec selection, registration or
production admission. Full JSON Schema and existing UAF/HRB/Security/Reuse/Evidence
gates remain independent.
"""
from __future__ import annotations

import json
import re
from typing import Any

SCHEMA = "fa3.selective-production-import.v1"
_REF = re.compile(r"^ref:[A-Za-z0-9][A-Za-z0-9_.-]{0,247}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_LANG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
TEXT = frozenset({"ORIGINAL_LANGUAGE", "ONE_TRANSLATION", "MULTI_TRANSLATION", "ORIGINAL_PLUS_TRANSLATIONS"})
AUDIO = frozenset({"FULL_AUDIO", "TRANSCRIPT_ONLY", "SPEECH_OR_SINGING_SEPARATE", "INSTRUMENTAL_ONLY", "AMBIENCE_AND_SFX", "DENOISED_SPEECH"})
VIDEO = frozenset({"FULL_VIDEO", "VIDEO_WITHOUT_AUDIO", "FULL_AUDIO_ONLY", "TRANSCRIPT_ONLY", "MUSIC_OR_INSTRUMENTAL_ONLY", "AMBIENCE_AND_SFX_ONLY", "FRAMES_OR_SCENES"})
ALL = {"TEXT": TEXT, "AUDIO": AUDIO, "VIDEO": VIDEO}
STEM = {
    ("AUDIO", "SPEECH_OR_SINGING_SEPARATE"): {"SPEECH", "SINGING"},
    ("AUDIO", "INSTRUMENTAL_ONLY"): {"INSTRUMENTAL"},
    ("AUDIO", "AMBIENCE_AND_SFX"): {"AMBIENCE", "SFX", "AMBIENCE_AND_SFX"},
    ("AUDIO", "DENOISED_SPEECH"): {"DENOISED_SPEECH"},
    ("VIDEO", "MUSIC_OR_INSTRUMENTAL_ONLY"): {"MUSIC", "INSTRUMENTAL"},
    ("VIDEO", "AMBIENCE_AND_SFX_ONLY"): {"AMBIENCE", "SFX", "AMBIENCE_AND_SFX"},
}
SOURCE_MODES = {
    "FILE": {"TEXT", "AUDIO", "VIDEO"},
    "EXTERNAL_PROJECT": {"TEXT", "AUDIO", "VIDEO"},
    "LIVE_VIDEO": {"VIDEO"},
    "LIVE_AUDIO": {"AUDIO"},
    "LIVE_CAPTIONS": {"LIVE_CAPTIONS"},
}
TARGETS = {
    "Story/Screenplay", "Subtitle Studio", "Audio Fabric", "Music Studio",
    "Sound Design", "Video Editor", "QuickClip", "Photo/Image Studio",
    "Shot Designer", "Director", "Live Studio", "FA3 Archive",
}
DERIVATIVE_STEM_SELECTORS = set(STEM)
RANGE_TYPES = {"FULL", "DOCUMENT_SPAN", "AUDIO_SAMPLES", "VIDEO_PTS", "SCENE_IDS", "LIVE_WINDOW"}
DELIVERY_TYPES = {"DERIVED_ONLY", "COPY_EDITABLE_IF_ADMITTED", "HYBRID_LINK", "ARCHIVAL_COPY", "LINK_ONLY"}
ORIGINAL_POLICIES = {"PRESERVE_IMMUTABLE_SNAPSHOT", "AUTHORIZED_READONLY_LINK"}
TOP_REQUIRED = {
    "schema", "production_ref", "source_ref", "source_kind", "source_mode",
    "source_rights_ref", "source_language", "original_policy",
    "requested_outputs", "execution_authorized",
}
TOP_ALLOWED = TOP_REQUIRED | {
    "source_sha256", "live_source_plan_ref",
    "cross_app_delivery_authorization_ref", "preview_only",
}
OUTPUT_REQUIRED = {
    "family", "selector_id", "target_application", "source_range",
    "target_languages", "translation_mode", "delivery_class",
    "requested_stem_class",
}
OUTPUT_ALLOWED = OUTPUT_REQUIRED | {"quality_review_required"}


def _ref(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise ValueError(f"{field}: opaque ref:<id> required; URLs and credentials are forbidden")


def _range(value: Any) -> None:
    if not isinstance(value, dict) or value.get("kind") not in RANGE_TYPES:
        raise ValueError("source_range: unknown/missing kind")
    kind = value["kind"]
    allowed = {"kind"}
    if kind == "DOCUMENT_SPAN":
        allowed |= {"document_start", "document_end"}
        a, b = value.get("document_start"), value.get("document_end")
        if not isinstance(a, int) or not isinstance(b, int) or a < 0 or a >= b:
            raise ValueError("source_range: invalid document span")
    if kind in {"AUDIO_SAMPLES", "VIDEO_PTS", "LIVE_WINDOW"}:
        allowed |= {"tick_start", "tick_end", "timebase_num", "timebase_den"}
        a, b = value.get("tick_start"), value.get("tick_end")
        num, den = value.get("timebase_num"), value.get("timebase_den")
        if any(type(x) is not int for x in (a, b, num, den)) or a < 0 or a >= b or num <= 0 or den <= 0:
            raise ValueError("source_range: invalid rational time range")
    if kind == "SCENE_IDS":
        allowed |= {"scene_ids"}
        ids = value.get("scene_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError("source_range: unique nonempty scene_ids required")
    if set(value) - allowed:
        raise ValueError("source_range: unexpected fields")


def preflight_preview(request: dict[str, Any]) -> dict[str, Any]:
    """Reject invalid selector/authorization data and return *no-execution* leaves.

    The status of all leaves remains PENDING_* even for an apparently original
    track; only existing source inspector, rights/security, codec/admission and
    canonical Evidence can verify them. Caller MUST run the JSON Schema and
    delegated live-source schema separately before issuing typed UAF tasks.
    """
    if not isinstance(request, dict):
        raise ValueError("request must be object")
    if TOP_REQUIRED - request.keys() or request.keys() - TOP_ALLOWED:
        raise ValueError("unknown/missing request properties")
    if request["schema"] != SCHEMA or request["execution_authorized"] is not False:
        raise ValueError("preview-only schema and no execution authority required")
    if request.get("preview_only") is not True:
        raise ValueError("preview_only must be true")
    for field in ("production_ref", "source_ref", "source_rights_ref"):
        _ref(request[field], field)
    for field in ("cross_app_delivery_authorization_ref",):
        if field in request:
            _ref(request[field], field)
    mode, kind = request["source_mode"], request["source_kind"]
    if mode not in SOURCE_MODES or kind not in SOURCE_MODES[mode]:
        raise ValueError("incompatible source kind and source mode")
    sha, live = request.get("source_sha256"), request.get("live_source_plan_ref")
    if mode in {"FILE", "EXTERNAL_PROJECT"}:
        if not isinstance(sha, str) or not _HASH.fullmatch(sha) or live is not None:
            raise ValueError("stored source requires source digest and no live source plan")
    else:
        if sha is not None:
            raise ValueError("live source digest belongs to captured segments, not request")
        _ref(live, "live_source_plan_ref")
    language = request["source_language"]
    if not isinstance(language, str) or (language != "auto" and not _LANG.fullmatch(language)):
        raise ValueError("invalid source language")
    if request["original_policy"] not in ORIGINAL_POLICIES:
        raise ValueError("unknown original retention policy")
    outputs = request["requested_outputs"]
    if not isinstance(outputs, list) or not (1 <= len(outputs) <= 17):
        raise ValueError("1..17 selected output requests required")
    seen = set()
    plan = []
    for index, out in enumerate(outputs):
        if not isinstance(out, dict) or OUTPUT_REQUIRED - out.keys() or out.keys() - OUTPUT_ALLOWED:
            raise ValueError(f"output[{index}]: missing/unknown properties")
        family, selector = out["family"], out["selector_id"]
        if family not in ALL or selector not in ALL[family]:
            raise ValueError(f"output[{index}]: invalid family-scoped selector")
        if kind == "TEXT" and family != "TEXT" or kind == "LIVE_CAPTIONS" and family != "TEXT":
            raise ValueError("text/caption source cannot silently produce AV")
        if kind == "AUDIO" and family == "VIDEO":
            raise ValueError("audio source cannot silently produce video")
        if out["target_application"] not in TARGETS:
            raise ValueError("target FA3 application unknown")
        _range(out["source_range"])
        key = (family, selector, out["target_application"], json.dumps(out["source_range"], sort_keys=True))
        if key in seen:
            raise ValueError("duplicate requested leaf; use one request per selector/destination/range")
        seen.add(key)
        langs, translation_mode = out["target_languages"], out["translation_mode"]
        if not isinstance(langs, list) or len(langs) > 64 or any(not isinstance(l, str) or not _LANG.fullmatch(l) for l in langs) or len({l.lower() for l in langs}) != len(langs):
            raise ValueError("invalid or duplicate BCP-47 target language")
        if translation_mode not in TEXT:
            raise ValueError("invalid translation mode")
        if family == "TEXT" and selector != translation_mode:
            raise ValueError("TEXT selector must match translation mode")
        if family in {"AUDIO", "VIDEO"} and selector != "TRANSCRIPT_ONLY" and (translation_mode != "ORIGINAL_LANGUAGE" or langs):
            raise ValueError("language fan-out is only attached to transcript/text outputs")
        if translation_mode == "ORIGINAL_LANGUAGE" and langs:
            raise ValueError("original-language output must not silently translate")
        if translation_mode == "ONE_TRANSLATION" and len(langs) != 1:
            raise ValueError("ONE_TRANSLATION requires exactly one target language")
        if translation_mode == "MULTI_TRANSLATION" and len(langs) < 2:
            raise ValueError("MULTI_TRANSLATION requires two or more distinct target languages")
        if translation_mode == "ORIGINAL_PLUS_TRANSLATIONS" and not langs:
            raise ValueError("ORIGINAL_PLUS_TRANSLATIONS requires target languages")
        stem = out["requested_stem_class"]
        accepted_stems = STEM.get((family, selector), {"NONE"})
        if stem not in accepted_stems:
            raise ValueError("requested stem incompatible with exact selector; no class conflation")
        if out["delivery_class"] not in DELIVERY_TYPES:
            raise ValueError("unsupported delivery mode")
        if "quality_review_required" in out and type(out["quality_review_required"]) is not bool:
            raise ValueError("quality review must be boolean")
        if (family, selector) in DERIVATIVE_STEM_SELECTORS:
            status = "PENDING_ORIGINAL_TRACK_OR_ADMITTED_EXACT_STEM_MODEL"
        elif family == "TEXT" and selector != "ORIGINAL_LANGUAGE" or selector == "TRANSCRIPT_ONLY":
            status = "PENDING_LANGUAGE_STT_TIMING_AND_REVIEW"
        else:
            status = "PENDING_SOURCE_INSPECTION_AND_ADMISSION"
        if out["delivery_class"] == "COPY_EDITABLE_IF_ADMITTED":
            status = "PENDING_EXTERNAL_FORMAT_ROUNDTRIP_EVIDENCE"
        plan.append({
            "family": family, "selector_id": selector,
            "target_application": out["target_application"],
            "target_languages": langs,
            "status": status, "execution_authorized": False,
        })
    if kind == "LIVE_CAPTIONS" and any(out["family"] != "TEXT" for out in outputs):
        raise ValueError("live caption only source cannot deliver media")
    return {
        "status": "PREVIEW_ONLY", "schema": SCHEMA,
        "production_ref": request["production_ref"],
        "source_ref": request["source_ref"], "source_kind": kind,
        "request_count": len(outputs), "outputs": plan,
        "execution_authorized": False,
        "requires_existing_authorities": [
            "file.convert.inspect", "ProductionImportPlan", "Security Governance",
            "UAF", "HRB", "Model Router", "canonical Evidence",
        ],
    }
