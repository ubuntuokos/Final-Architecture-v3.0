"""Pure language-dependency preview under FA3's existing File Conversion/Language Fabric.

S3 plans only. It never runs STT, translation, media decode, file operations,
network requests, model routing, application delivery, or authorization.
"""
from __future__ import annotations

import json
from typing import Any

from fa3_selective_import_preview import preflight_preview
from fa3_selective_import_stream_binding import inspect_binding

SCHEMA = "fa3.selective-language-fanout.v1"
MAX_BRANCHES = 1024
LANGUAGE_MODES = {
    "ORIGINAL_LANGUAGE", "ONE_TRANSLATION", "MULTI_TRANSLATION",
    "ORIGINAL_PLUS_TRANSLATIONS",
}
BLOCKED_STREAM_STATUSES = {
    "BLOCKED_MISSING_REQUIRED_SOURCE_STREAM",
    "PENDING_EXPLICIT_SOURCE_STREAM_SELECTION",
}


def language_fanout_preview(
    request: dict[str, Any],
    inventory: dict[str, Any],
    choices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive bounded 0/1/N language leaves without executing any worker.

    Caller must authenticate the file.convert.inspect receipt via FA3's existing
    Security/Evidence authorities. Metadata here cannot prove source identity,
    rights, source words, recognized speech, alignment or translation quality.
    """
    validated = preflight_preview(request)
    if request["source_mode"] not in {"FILE", "EXTERNAL_PROJECT"}:
        raise ValueError("live/caption sources use the separately governed live intake")
    mapped = inspect_binding(request, inventory, choices)
    by_index = {row["index"]: row for row in inventory["streams"]}
    branches: list[dict[str, Any]] = []
    skipped = 0
    collision_keys: dict[tuple[str, str, str], list[str]] = {}

    for leaf_index, output in enumerate(request["requested_outputs"]):
        family, selector = output["family"], output["selector_id"]
        if family != "TEXT" and selector != "TRANSCRIPT_ONLY":
            skipped += 1
            continue

        mapping = mapped["outputs"][leaf_index]
        indices = mapping["original_stream_indices"]
        mode = output["translation_mode"]
        if mode not in LANGUAGE_MODES:
            raise ValueError("unknown language mode")
        if request["source_kind"] == "TEXT":
            source_step = "DOCUMENT_FABRIC_SOURCE_TEXT_INSPECT"
            if indices:
                raise ValueError("a text document must not bind a media stream")
        elif len(indices) == 1:
            source_kind = by_index[indices[0]]["codec_type"]
            if source_kind == "subtitle":
                source_step = "CAPTION_SUBTITLE_ORIGINAL_TIMED_TEXT_INSPECT"
            elif source_kind == "audio":
                source_step = "EXISTING_STT_SOURCE_TRANSCRIPTION"
            else:
                raise ValueError("text derivation requires a single audio or subtitle stream")
        else:
            source_step = None

        # ORIGINAL_PLUS_TRANSLATIONS intentionally delivers source plus all
        # user-requested locales, never an unrequested extra language.
        locales = (
            [(request["source_language"], "ORIGINAL")]
            if mode in {"ORIGINAL_LANGUAGE", "ORIGINAL_PLUS_TRANSLATIONS"}
            else []
        )
        if mode != "ORIGINAL_LANGUAGE":
            locales += [(lang, "TRANSLATION") for lang in output["target_languages"]]
        if not locales:
            raise ValueError("text selection produced no requested language")
        if len(branches) + len(locales) > MAX_BRANCHES:
            raise ValueError("language fanout exceeds bounded per-request branch budget")

        for locale, variant in locales:
            if source_step is None or mapping["status"] in BLOCKED_STREAM_STATUSES:
                status = "BLOCKED_SOURCE_STREAM_SELECTION_OR_AVAILABILITY"
                stages: list[str] = []
            elif variant == "TRANSLATION" and request["source_language"] == "auto":
                status = "PENDING_PER_SEGMENT_SOURCE_LANGUAGE_IDENTIFICATION"
                stages = [source_step, "LANGUAGE_FABRIC_IDENTIFY_SOURCE_LOCALE",
                          "LANGUAGE_FABRIC_TRANSLATE_AND_GLOSSARY_REVIEW"]
            else:
                status = "PENDING_INSPECTION_STT_TIMING_AND_LANGUAGE_QC"
                stages = [source_step]
                if variant == "TRANSLATION":
                    stages.append("LANGUAGE_FABRIC_TRANSLATE_AND_GLOSSARY_REVIEW")
                stages.append("SUBTITLE_STUDIO_TIMING_REVIEW_IF_TIMED")
            identity = f"leaf-{leaf_index}:{variant}:{locale}"
            collision_key = (
                output["target_application"],
                json.dumps(output["source_range"], sort_keys=True),
                locale.lower(),
            )
            collision_keys.setdefault(collision_key, []).append(identity)
            branches.append({
                "branch_ref": identity,
                "parent_leaf_index": leaf_index,
                "family": family,
                "selector_id": selector,
                "target_application": output["target_application"],
                "variant": variant,
                "source_locale": request["source_language"],
                "target_locale": locale,
                "original_stream_indices": list(indices),
                "original_timebases": mapping["original_timebases"],
                "source_range": output["source_range"],
                "source_step": source_step,
                "steps": stages,
                "status": status,
                "source_per_segment_language_review_required": True,
                "publish_audio": False,
                "publish_video": False,
                "execution_authorized": False,
                "verified": False,
            })

    collisions = [identities for identities in collision_keys.values()
                  if len(identities) > 1]
    for branch in branches:
        if any(branch["branch_ref"] in collision for collision in collisions):
            branch["status"] = "PENDING_DUPLICATE_DESTINATION_REVIEW"
            branch["steps"] = []

    return {
        "schema": SCHEMA,
        "source_ref": validated["source_ref"],
        "source_sha256": request["source_sha256"],
        "inspection_receipt_ref": mapped["inspector_receipt_ref"],
        "state": "LANGUAGE_FANOUT_PREVIEW_ONLY",
        "languages_count": len(branches),
        "skipped_non_text_leaves": skipped,
        "duplicate_destination_candidates": collisions,
        "branches": branches,
        "execution_authorized": False,
        "authority": False,
        "existing_owners": ["FA3-FILE-CONVERSION-001", "FA3-LANGUAGE-FABRIC-001",
                            "FA3-CAPTION-SUBTITLE-CONTRACTS-001"],
    }
