"""S5: compose existing selective import previews into a delivery manifest.

Side-effect-free. This module cannot certify a source, execute conversion,
approve a model, publish an output, mutate a project, or authorize a host.
Each deliverable remains subordinate to the existing FA3 conversion, language,
audio, security, distribution, and canonical Evidence authorities.
"""
from __future__ import annotations

import json
from typing import Any

from fa3_selective_import_preview import preflight_preview, STEM
from fa3_selective_import_stream_binding import inspect_binding
from fa3_selective_import_language_fanout import language_fanout_preview
from fa3_selective_import_audio_qc import audio_qc_plan_preview

SCHEMA = "fa3.selective-delivery-preview.v1"
COMMON_CHECKS = (
    "SOURCE_RIGHTS_AND_SCOPE",
    "AUTHENTIC_INSPECTOR_AND_SOURCE_HASH",
    "TARGET_APPLICATION_FORMAT_SUPPORT",
    "CANONICAL_EVIDENCE_AND_HUMAN_PUBLICATION_APPROVAL",
    "SOFTWARE_COEXISTENCE_AND_HOST_NONINTERFERENCE",
)
ROUNDTRIP_CHECK = "EXACT_FORMAT_PAIR_VERSION_AND_FEATURE_ROUNDTRIP"
CROSS_APP_CHECK = "EXISTING_UAF_CROSS_APP_AUTHORIZATION"
LANGUAGE_CHECKS = (
    "ORIGINAL_TEXT_OR_STT_SUBTITLE_PROVENANCE",
    "SOURCE_LANGUAGE_AND_TIMING_REVIEW",
    "LANGUAGE_FABRIC_TERMINOLOGY_AND_TRANSLATION_QC",
)
MEDIA_CHECKS = (
    "EXACT_STREAM_CODEC_TIMING_AND_CHANNEL_QC",
    "NO_UNREQUESTED_AUDIO_OR_VIDEO_PUBLICATION",
)


def delivery_preview(
    request: dict[str, Any],
    inventory: dict[str, Any],
    choices: list[dict[str, Any]] | None = None,
    *,
    untrusted_model_candidates: list[dict[str, Any]] | None = None,
    estimate_opt_in_leaf_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Compose S1/S2/S3/S4/S4.2 plans. No adapter invocation or publication.

    All caller-supplied inventory and external provider descriptions remain
    untrusted. Real execution requires independent, existing FA3 authorities.
    """
    source_plan = preflight_preview(request)
    if request["source_mode"] not in {"FILE", "EXTERNAL_PROJECT"}:
        raise ValueError("live and caption streams require separate live-source intake")
    binding = inspect_binding(request, inventory, choices)
    language = language_fanout_preview(request, inventory, choices)
    audio = audio_qc_plan_preview(
        request, inventory, choices,
        untrusted_model_candidates=untrusted_model_candidates,
        estimate_opt_in_leaf_indices=estimate_opt_in_leaf_indices,
    )
    identity = (request["source_ref"], request["source_sha256"])
    for result in (language, audio):
        if (result["source_ref"], result["source_sha256"]) != identity:
            raise ValueError("composed previews have different source identities")
    if (binding["inspector_receipt_ref"] != inventory["inspector_receipt_ref"]
            or language["inspection_receipt_ref"] != inventory["inspector_receipt_ref"]
            or audio["inspector_receipt_ref"] != inventory["inspector_receipt_ref"]):
        raise ValueError("inspector receipt mismatch across planning stages")
    bound = binding["outputs"]
    if len(bound) != len(request["requested_outputs"]):
        raise ValueError("source binding does not cover all requested leaves")
    by_language: dict[int, list[dict[str, Any]]] = {}
    for branch in language["branches"]:
        by_language.setdefault(branch["parent_leaf_index"], []).append(branch)
    by_audio = {item["parent_leaf_index"]: item for item in audio["outputs"]}
    if len(by_audio) != len(audio["outputs"]):
        raise ValueError("duplicate stem QC plan index")

    deliverables: list[dict[str, Any]] = []
    binding_groups: dict[tuple[str, tuple[int, ...]], str] = {}
    # Shared source inspection is an optimization HINT only, not permission
    # to share an execution workspace across data classifications or outputs.
    for index, selected in enumerate(request["requested_outputs"]):
        mapped = bound[index]
        if mapped["leaf_index"] != index:
            raise ValueError("unexpected stream binding order")
        pair = (selected["family"], selected["selector_id"])
        is_text = selected["family"] == "TEXT" or selected["selector_id"] == "TRANSCRIPT_ONLY"
        is_stem = pair in STEM
        original_indices = mapped["original_stream_indices"]
        key = (json.dumps(selected["source_range"], sort_keys=True),
               tuple(original_indices))
        if key not in binding_groups:
            binding_groups[key] = f"source-binding-{len(binding_groups)}"
        group = binding_groups[key]
        gate = list(COMMON_CHECKS)
        if selected["delivery_class"] == "COPY_EDITABLE_IF_ADMITTED":
            gate.append(ROUNDTRIP_CHECK)
        if request.get("cross_app_delivery_authorization_ref") is None:
            gate.append(CROSS_APP_CHECK)
        if is_text:
            variants = by_language.get(index)
            if not variants:
                raise ValueError("missing requested language branch")
            for variant_index, v in enumerate(variants):
                checks = list(gate + list(LANGUAGE_CHECKS))
                deliverables.append({
                    "deliverable_ref": f"leaf-{index}-language-{variant_index}",
                    "parent_leaf_index": index,
                    "family": selected["family"],
                    "selector_id": selected["selector_id"],
                    "target_application": selected["target_application"],
                    "delivery_class": selected["delivery_class"],
                    "source_range": selected["source_range"],
                    "source_stream_indices": v["original_stream_indices"],
                    "source_timebases": v["original_timebases"],
                    "source_binding_group": group,
                    "variant": v["variant"],
                    "target_locale": v["target_locale"],
                    "source_locale": v["source_locale"],
                    "planned_steps": list(v["steps"]),
                    "status": v["status"],
                    "required_independent_checks": checks,
                    "requested_publication": {"text": True, "audio": False, "video": False},
                    "publish_text": False, "publish_audio": False, "publish_video": False,
                    "editable_project_verified": False,
                    "independent_evidence_verified": False,
                    "execution_authorized": False,
                })
        elif is_stem:
            qc = by_audio.get(index)
            if qc is None:
                raise ValueError("missing stem-specific independent QC plan")
            checks = list(gate) + list(qc["required_independent_evidence_checks"])
            deliverables.append({
                "deliverable_ref": f"leaf-{index}-audio",
                "parent_leaf_index": index,
                "family": selected["family"],
                "selector_id": selected["selector_id"],
                "target_application": selected["target_application"],
                "delivery_class": selected["delivery_class"],
                "source_range": selected["source_range"],
                "source_stream_indices": qc["source_stream_indices"],
                "source_timebases": qc["original_timebases"],
                "source_binding_group": group,
                "variant": qc["origin"],
                "target_locale": None,
                "source_locale": None,
                "planned_steps": ["EXISTING_AUDIO_SOURCE_SEPARATION_OR_DENOISE_AFTER_ADMISSION",
                                  "EXISTING_AUDIO_FABRIC_INDEPENDENT_QC"],
                "status": qc["quality_readiness"],
                "required_independent_checks": list(dict.fromkeys(checks)),
                "requested_publication": {"text": False, "audio": True, "video": False},
                "publish_text": False, "publish_audio": False, "publish_video": False,
                "editable_project_verified": False,
                "independent_evidence_verified": False,
                "execution_authorized": False,
            })
        else:
            # Exact stream extraction still needs authenticated inspection,
            # real codec/format and timebase tests. Never infer completed work
            # from an inspector-supplied opaque receipt.
            video_intent = selected["selector_id"] in {
                "FULL_VIDEO", "VIDEO_WITHOUT_AUDIO", "FRAMES_OR_SCENES"}
            audio_intent = selected["selector_id"] in {"FULL_VIDEO", "FULL_AUDIO", "FULL_AUDIO_ONLY"}
            # A silent FULL_VIDEO source does not request an invented audio stream.
            if selected["selector_id"] == "FULL_VIDEO":
                audio_intent = any(
                    item["index"] in original_indices and item["codec_type"] == "audio"
                    for item in inventory["streams"]
                )
            deliverables.append({
                "deliverable_ref": f"leaf-{index}-media",
                "parent_leaf_index": index,
                "family": selected["family"],
                "selector_id": selected["selector_id"],
                "target_application": selected["target_application"],
                "delivery_class": selected["delivery_class"],
                "source_range": selected["source_range"],
                "source_stream_indices": list(original_indices),
                "source_timebases": mapped["original_timebases"],
                "source_binding_group": group,
                "variant": "ORIGINAL_MEDIA_PROJECTION",
                "target_locale": None, "source_locale": None,
                "planned_steps": (
                    [] if mapped["status"].startswith("BLOCKED_")
                    else ["EXISTING_FILE_CONVERSION_ADMITTED_EXACT_STREAM_EXTRACTION",
                          "EXISTING_TARGET_APPLICATION_OPEN_AND_FORMAT_QC"]
                ),
                "status": mapped["status"],
                "required_independent_checks": list(gate + list(MEDIA_CHECKS)),
                "requested_publication": {
                    "text": False, "audio": audio_intent, "video": video_intent},
                "publish_text": False, "publish_audio": False, "publish_video": False,
                "editable_project_verified": False,
                "independent_evidence_verified": False,
                "execution_authorized": False,
            })

    if len(deliverables) > 1024:
        raise ValueError("delivery preview exceeds bounded language and media leaf budget")
    return {
        "schema": SCHEMA,
        "production_ref": source_plan["production_ref"],
        "source_ref": identity[0],
        "source_sha256": identity[1],
        "inspector_receipt_ref": inventory["inspector_receipt_ref"],
        "state": "SELECTIVE_DELIVERY_PREVIEW_ONLY",
        "requested_output_count": len(request["requested_outputs"]),
        "planned_deliverable_count": len(deliverables),
        "language_branch_count": language["languages_count"],
        "audio_qc_leaf_count": audio["output_count"],
        "shared_source_binding_groups": len(binding_groups),
        "duplicate_language_destinations": language["duplicate_destination_candidates"],
        "deliverables": deliverables,
        "publish_text": False, "publish_audio": False, "publish_video": False,
        "execution_authorized": False,
        "authority": False, "capability_count": 175,
        "existing_owners": [
            "FA3-FILE-CONVERSION-001", "FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001",
            "FA3-AUDIO-SEPARATION-CONTRACTS-001", "FA3-LANGUAGE-FABRIC-001",
            "FA3-AUTH-OBS-EVIDENCE-001", "FA3-UNIFIED-ACTION-FABRIC-001",
        ],
    }
