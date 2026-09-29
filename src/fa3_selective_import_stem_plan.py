"""S4: metadata-only selective audio-stem strategy preview.

Subordinate to FA3 file.convert.inspect and FA3 Audio Source Separation Fabric.
Never calls a model, extracts audio, verifies a receipt or authorizes execution.
Provider descriptions supplied by callers are UNTRUSTED capability claims.
"""
from __future__ import annotations

import re
from typing import Any

from fa3_selective_import_preview import STEM, preflight_preview
from fa3_selective_import_stream_binding import inspect_binding

SCHEMA = "fa3.selective-audio-stem-plan.v1"
_REF = re.compile(r"^ref:[A-Za-z0-9][A-Za-z0-9_.-]{0,247}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
CLASSES = frozenset({
    "SPEECH", "SINGING", "VOCALS", "INSTRUMENTAL", "MUSIC",
    "AMBIENCE", "SFX", "AMBIENCE_AND_SFX",
})
SPECIAL = frozenset(set(STEM) - {("AUDIO", "DENOISED_SPEECH")})
DENOISE = ("AUDIO", "DENOISED_SPEECH")
MAX_CANDIDATES = 32


def _validate_candidates(candidates: list[dict[str, Any]]) -> None:
    if not isinstance(candidates, list) or len(candidates) > MAX_CANDIDATES:
        raise ValueError("bounded candidate list required")
    seen: set[tuple[str, str]] = set()
    for row in candidates:
        if not isinstance(row, dict) or set(row) != {
            "provider_ref", "model_weight_sha256", "declared_stem_classes",
            "license_review_ref",
        }:
            raise ValueError("unknown or missing untrusted candidate fields")
        for field in ("provider_ref", "license_review_ref"):
            if not isinstance(row[field], str) or not _REF.fullmatch(row[field]):
                raise ValueError("opaque candidate refs only; no secrets or URLs")
        if (not isinstance(row["model_weight_sha256"], str)
                or not _HASH.fullmatch(row["model_weight_sha256"])):
            raise ValueError("model weight digest required for candidate preview")
        classes = row["declared_stem_classes"]
        if (not isinstance(classes, list) or not 1 <= len(classes) <= len(CLASSES)
                or any(not isinstance(c, str) or c not in CLASSES for c in classes)
                or len(set(classes)) != len(classes)):
            raise ValueError("bounded, explicit declared stem ontology required")
        key = (row["provider_ref"], row["model_weight_sha256"])
        if key in seen:
            raise ValueError("duplicate proposed model/provider identity")
        seen.add(key)


def stem_plan_preview(
    request: dict[str, Any],
    inventory: dict[str, Any],
    choices: list[dict[str, Any]] | None = None,
    *,
    untrusted_model_candidates: list[dict[str, Any]] | None = None,
    estimate_opt_in_leaf_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Produce an S4 planning preview; existing admission authorities decide later.

    Explicit estimate opt-in permits PREVIEW of a claimed model path only; it is
    NEVER runtime, model, license, GPU, quality or publication approval.
    """
    preflight_preview(request)
    if request["source_mode"] not in {"FILE", "EXTERNAL_PROJECT"}:
        raise ValueError("live inputs need the separately governed live inspector")
    mapping = inspect_binding(request, inventory, choices)
    candidates = [] if untrusted_model_candidates is None else untrusted_model_candidates
    _validate_candidates(candidates)
    opt_ins = [] if estimate_opt_in_leaf_indices is None else estimate_opt_in_leaf_indices
    if (not isinstance(opt_ins, list) or len(opt_ins) > 256
            or any(type(i) is not int or i < 0 or i >= len(request["requested_outputs"])
                   for i in opt_ins)
            or len(set(opt_ins)) != len(opt_ins)):
        raise ValueError("invalid or repeated explicit estimate opt-in")
    for i in opt_ins:
        leaf = request["requested_outputs"][i]
        if (leaf["family"], leaf["selector_id"]) not in SPECIAL:
            raise ValueError("estimate opt-in valid only for a matching stem output")

    source_streams = {row["index"]: row for row in inventory["streams"]}
    leaves: list[dict[str, Any]] = []
    for index, leaf in enumerate(request["requested_outputs"]):
        pair = (leaf["family"], leaf["selector_id"])
        if pair not in SPECIAL and pair != DENOISE:
            continue
        mapped = mapping["outputs"][index]
        requested_class = leaf["requested_stem_class"]
        indices = mapped["original_stream_indices"]
        stream_status = mapped["status"]
        exact = [
            i for i in indices
            if source_streams[i]["codec_type"] == "audio"
            and source_streams[i].get("role") == requested_class
            and source_streams[i].get("source_stem_attestation_ref")
        ]
        matching_candidates = [
            {"provider_ref": row["provider_ref"],
             "model_weight_sha256": row["model_weight_sha256"],
             "license_review_ref": row["license_review_ref"]}
            for row in candidates
            if requested_class in row["declared_stem_classes"]
        ] if pair in SPECIAL else []
        if stream_status == "BLOCKED_MISSING_REQUIRED_SOURCE_STREAM":
            state = "BLOCKED_MISSING_AUDIO"
            origin = "NONE"
        elif stream_status == "PENDING_EXPLICIT_SOURCE_STREAM_SELECTION":
            state = "PENDING_OPERATOR_STREAM_CHOICE"
            origin = "NONE"
        elif pair == DENOISE:
            state = "PENDING_SEPARATE_DENOISE_PROVIDER_AND_QUALITY_EVIDENCE"
            origin = "DENOISE_DERIVATIVE_ONLY"
        elif exact:
            state = "PENDING_INDEPENDENT_SOURCE_STEM_ATTESTATION_VERIFICATION"
            origin = "CLAIMED_ORIGINAL_TRACK"
        elif matching_candidates and index in opt_ins:
            state = "PENDING_INDEPENDENT_LICENSE_MODEL_HRB_AND_QUALITY_ADMISSION"
            origin = "PROPOSED_ESTIMATED_STEM"
        elif matching_candidates:
            state = "ESTIMATE_REQUIRES_EXPLICIT_OPERATOR_OPT_IN"
            origin = "NONE"
        else:
            state = "UNSUPPORTED_EXACT_STEM_WITH_AVAILABLE_PREVIEW_METADATA"
            origin = "NONE"

        leaves.append({
            "parent_leaf_index": index,
            "family": leaf["family"],
            "selector_id": leaf["selector_id"],
            "requested_stem_class": requested_class,
            "target_application": leaf["target_application"],
            "source_range": leaf["source_range"],
            "source_stream_indices": list(indices),
            "original_timebases": mapped["original_timebases"],
            "claimed_source_attestation_refs": [
                source_streams[i]["source_stem_attestation_ref"] for i in exact
            ],
            "untrusted_matching_model_candidates": matching_candidates,
            "operator_approved_estimate_preview": index in opt_ins,
            "origin": origin,
            "status": state,
            "quality_review_required": True,
            "publish_audio": False,
            "execution_authorized": False,
            "original_exactness_verified": False,
            "model_license_verified": False,
            "physical_host_verified": False,
        })
    return {
        "schema": SCHEMA,
        "source_ref": request["source_ref"],
        "source_sha256": request["source_sha256"],
        "inspector_receipt_ref": inventory["inspector_receipt_ref"],
        "state": "STEM_STRATEGY_PREVIEW_ONLY",
        "stem_leaf_count": len(leaves),
        "outputs": leaves,
        "execution_authorized": False,
        "authority": False,
        "existing_owners": [
            "FA3-FILE-CONVERSION-001",
            "FA3-AUDIO-SEPARATION-CONTRACTS-001",
            "FA3-AUTH-MODEL-ROUTER-001",
            "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "FA3-AUTH-OBS-EVIDENCE-001",
        ],
    }
