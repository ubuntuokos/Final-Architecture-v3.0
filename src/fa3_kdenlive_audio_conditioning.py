#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

PRESETS = {
    "clean-dialogue": "CLEAN_DIALOGUE",
    "mixed-dialogue": "RESTORE_DIALOGUE_IN_MIXED_AUDIO",
    "noise-reduction": "NOISE_REDUCTION",
    "restore-bandwidth": "RESTORE_SPEECH_BANDWIDTH",
    "separate": "SEPARATE_VOCALS_MUSIC",
    "prepare-for-transcription": "PREPARE_CLEAN_AUDIO_FOR_TRANSCRIPTION",
}

USER_FACING_LABELS = {
    "clean-dialogue": "AI · Clean Dialogue",
    "mixed-dialogue": "AI · Restore Dialogue in Mixed Audio",
    "noise-reduction": "AI · Noise Reduction",
    "restore-bandwidth": "AI · Restore Speech Bandwidth",
    "separate": "AI · Separate Vocals / Music",
    "prepare-for-transcription": "AI · Prepare Clean Audio for Transcription",
}

_PROVIDER_TOKENS = ("silero", "gtcrn", "lavasr", "demucs")


class AudioConditioningPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class PlanPolicy:
    source_separation: bool = False
    speech_activity: bool = False
    speech_enhancement: bool = False
    restoration_bwe: bool = False
    restoration_denoise: bool = False
    delegate_to_stt: bool = False


POLICIES = {
    "clean-dialogue": PlanPolicy(speech_activity=True, speech_enhancement=True, restoration_bwe=True),
    "mixed-dialogue": PlanPolicy(source_separation=True, speech_activity=True, speech_enhancement=True, restoration_bwe=True),
    "noise-reduction": PlanPolicy(speech_activity=True, speech_enhancement=True),
    "restore-bandwidth": PlanPolicy(restoration_bwe=True),
    "separate": PlanPolicy(source_separation=True),
    "prepare-for-transcription": PlanPolicy(speech_activity=True, speech_enhancement=True, delegate_to_stt=True),
}


def validate_editorial_labels() -> None:
    for label in USER_FACING_LABELS.values():
        low = label.lower()
        if any(token in low for token in _PROVIDER_TOKENS):
            raise AudioConditioningPolicyError("provider names are forbidden in Kdenlive editorial preset labels")


def build_execution_plan(request: Mapping[str, Any]) -> dict:
    preset = str(request.get("preset", ""))
    if preset not in POLICIES:
        raise AudioConditioningPolicyError(f"unsupported preset: {preset}")
    if request.get("source_artifact_ref") == request.get("output_artifact_ref"):
        raise AudioConditioningPolicyError("source overwrite is forbidden")
    if request.get("direct_kdenlive_xml_mutation", False):
        raise AudioConditioningPolicyError("direct Kdenlive project XML mutation is forbidden")

    policy = POLICIES[preset]
    if policy.speech_enhancement and policy.restoration_bwe and request.get("restoration_denoise", False):
        if not request.get("explicit_cascade_policy_ref") or not request.get("quality_evidence_ref"):
            raise AudioConditioningPolicyError("implicit double denoise is forbidden")

    if request.get("execution_provider") not in (None, "CPUExecutionProvider"):
        if not request.get("hrb_receipt_ref"):
            raise AudioConditioningPolicyError("accelerator execution requires HRB admission")

    stages = [{"capability": "deterministic_media_probe", "tool": "ffprobe"}]
    if policy.source_separation:
        stages.append({"capability": "audio_source_separation", "conditional": preset == "mixed-dialogue"})
    if policy.speech_activity or policy.speech_enhancement or policy.restoration_bwe:
        stages.append({
            "capability": "explicit_analysis_projection",
            "sample_rate_hz": 16000,
            "channels": 1,
            "master_audio_mutation": False,
        })
    if policy.speech_activity:
        stages.append({
            "capability": "speech_activity_detection",
            "output_artifact_type": "SpeechActivityMap",
            "metadata_only": True,
            "context_padding_ms": int(request.get("context_padding_ms", 120)),
            "rejoin_crossfade_ms": int(request.get("rejoin_crossfade_ms", 15)),
        })
    if policy.speech_enhancement:
        stages.append({"capability": "speech_enhancement", "sample_rate_hz": 16000, "channels": 1})
    if policy.restoration_bwe:
        stages.append({
            "capability": "speech_restoration_bwe",
            "output_sample_rate_hz": 48000,
            "denoise": bool(request.get("restoration_denoise", False)),
        })
    if preset == "mixed-dialogue":
        stages.append({"capability": "deterministic_stem_remix", "tool": "ffmpeg", "output_sample_rate_hz": 48000})
    if policy.delegate_to_stt:
        stages.append({"capability": "delegate_transcription", "target_profile": "FA3-STT-MEDIA-001"})
    if preset != "prepare-for-transcription":
        stages.append({
            "capability": "editorial_mezzanine_validation",
            "sample_rate_hz": 48000,
            "lossless": True,
            "checks": ["finite", "nan_inf", "clipping", "gain", "dc_offset", "duration", "timebase", "sha256_lineage"],
        })

    return {
        "schema": "fa3.kdenlive-audio-conditioning-plan.v1",
        "request_id": request.get("request_id"),
        "preset": PRESETS[preset],
        "editorial_label": USER_FACING_LABELS[preset],
        "source_artifact_ref": request.get("source_artifact_ref"),
        "output_artifact_ref": request.get("output_artifact_ref"),
        "source_immutable": True,
        "direct_kdenlive_xml_mutation": False,
        "provider_neutral": True,
        "capability_mediation": "CENTRAL_MCP_EXISTING_AUTHORITY",
        "stages": stages,
        "production_runtime_promoted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a provider-neutral FA3 Kdenlive audio-conditioning request/plan.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--preset", required=True, choices=sorted(PRESETS))
    parser.add_argument("--output", required=True)
    parser.add_argument("--request-id", default="kdenlive-media-job")
    parser.add_argument("--emit-plan", type=Path)
    args = parser.parse_args()

    validate_editorial_labels()
    plan = build_execution_plan({
        "request_id": args.request_id,
        "source_artifact_ref": args.source,
        "output_artifact_ref": args.output,
        "preset": args.preset,
        "direct_kdenlive_xml_mutation": False,
    })
    payload = json.dumps(plan, indent=2) + "\n"
    if args.emit_plan:
        args.emit_plan.parent.mkdir(parents=True, exist_ok=True)
        args.emit_plan.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
