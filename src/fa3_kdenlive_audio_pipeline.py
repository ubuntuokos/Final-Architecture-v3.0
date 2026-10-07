#!/usr/bin/env python3
"""Provider-neutral FA3 Kdenlive audio-conditioning projection.

This module plans and validates typed audio-conditioning work. Actual provider
selection remains outside Kdenlive and is delegated to existing FA3 routing and
Host Resource Broker authorities.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

OPERATIONS = {
    "dialogue_clean",
    "mixed_dialogue_restore",
    "noise_reduction",
    "speech_bandwidth_restore",
    "separate_vocals_music",
    "prepare_clean_audio_for_stt",
}


@dataclass(frozen=True)
class AudioConditioningRequest:
    source_artifact: str
    source_hash: str
    operation: str
    timebase: str
    output_sample_rate_hz: int = 48000
    output_channels: int = 2
    allow_accelerator: bool = False
    hrb_lease_id: str | None = None


@dataclass(frozen=True)
class AudioConditioningPlan:
    operation: str
    steps: tuple[str, ...]
    source_in_place_mutation: bool
    direct_kdenlive_xml_mutation: bool
    output_kind: str
    lavasr_denoise: bool | None
    requires_hrb_lease: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_request(req: AudioConditioningRequest) -> None:
    if req.operation not in OPERATIONS:
        raise ValueError(f"unsupported audio-conditioning operation: {req.operation}")
    if len(req.source_hash) != 64:
        raise ValueError("source_hash must be a SHA-256 hex digest")
    if req.output_sample_rate_hz != 48000:
        raise ValueError("Kdenlive editorial derived audio baseline is 48 kHz")
    if req.output_channels < 1:
        raise ValueError("output_channels must be positive")
    if req.allow_accelerator and not req.hrb_lease_id:
        raise PermissionError("accelerator execution requires an HRB lease")


def build_plan(req: AudioConditioningRequest) -> AudioConditioningPlan:
    validate_request(req)
    steps: dict[str, tuple[str, ...]] = {
        "dialogue_clean": (
            "ffmpeg_lossless_extract",
            "explicit_16khz_mono_analysis_projection",
            "speech_activity_map",
            "speech_enhancement",
            "speech_restoration_bwe_48khz",
            "validate_and_version_derived_artifact",
        ),
        "mixed_dialogue_restore": (
            "ffmpeg_lossless_extract",
            "conditional_source_separation",
            "explicit_16khz_mono_vocal_analysis_projection",
            "speech_activity_map",
            "speech_enhancement",
            "speech_restoration_bwe_48khz",
            "explicit_stem_remix_48khz",
            "validate_and_version_derived_artifact",
        ),
        "noise_reduction": (
            "ffmpeg_lossless_extract",
            "explicit_16khz_mono_analysis_projection",
            "speech_activity_map",
            "speech_enhancement",
            "restore_editorial_sample_rate",
            "validate_and_version_derived_artifact",
        ),
        "speech_bandwidth_restore": (
            "ffmpeg_lossless_extract",
            "explicit_restoration_input_projection",
            "speech_restoration_bwe_48khz",
            "validate_and_version_derived_artifact",
        ),
        "separate_vocals_music": (
            "ffmpeg_lossless_extract",
            "source_separation",
            "validate_and_version_stem_artifacts",
        ),
        "prepare_clean_audio_for_stt": (
            "ffmpeg_lossless_extract",
            "explicit_16khz_mono_analysis_projection",
            "speech_activity_map",
            "optional_speech_enhancement",
            "delegate_to_fa3_stt_media_001",
        ),
    }
    uses_lavasr_after_enhancement = req.operation in {"dialogue_clean", "mixed_dialogue_restore"}
    return AudioConditioningPlan(
        operation=req.operation,
        steps=steps[req.operation],
        source_in_place_mutation=False,
        direct_kdenlive_xml_mutation=False,
        output_kind="versioned_derived_media_artifact",
        lavasr_denoise=False if uses_lavasr_after_enhancement else None,
        requires_hrb_lease=req.allow_accelerator,
    )


def validate_plan(plan: AudioConditioningPlan) -> None:
    if plan.source_in_place_mutation:
        raise ValueError("source in-place mutation is forbidden")
    if plan.direct_kdenlive_xml_mutation:
        raise ValueError("direct Kdenlive project XML mutation is forbidden")
    if "speech_enhancement" in plan.steps and "speech_restoration_bwe_48khz" in plan.steps:
        if plan.lavasr_denoise is not False:
            raise ValueError("GTCRN->LavaSR composition requires LavaSR denoise disabled")
    if plan.operation == "mixed_dialogue_restore" and "conditional_source_separation" not in plan.steps:
        raise ValueError("mixed-dialogue restoration must keep source separation conditional")


def plan_request(req: AudioConditioningRequest) -> AudioConditioningPlan:
    plan = build_plan(req)
    validate_plan(plan)
    return plan
