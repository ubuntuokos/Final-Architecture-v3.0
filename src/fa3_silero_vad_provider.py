#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any

SUPPORTED_SAMPLE_RATES = (8000, 16000)
DEFAULT_SAMPLE_RATE = 16000


class SileroVadPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class SpeechSegment:
    start_sample: int
    end_sample: int
    confidence: float

    def validate(self) -> None:
        if self.start_sample < 0 or self.end_sample <= self.start_sample:
            raise SileroVadPolicyError("invalid speech segment bounds")
        if not 0.0 <= self.confidence <= 1.0:
            raise SileroVadPolicyError("speech confidence must be within [0, 1]")


def validate_request(request: Mapping[str, Any]) -> None:
    sample_rate = int(request.get("sample_rate_hz", 0))
    channels = int(request.get("channels", 0))
    if sample_rate not in SUPPORTED_SAMPLE_RATES:
        raise SileroVadPolicyError("Silero VAD requires an admitted 8 kHz or 16 kHz analysis projection")
    if channels != 1:
        raise SileroVadPolicyError("Silero VAD analysis projection must be mono")
    if request.get("mutate_master_audio", False):
        raise SileroVadPolicyError("VAD is metadata-only and cannot mutate master audio")
    if request.get("runtime_auto_download", False):
        raise SileroVadPolicyError("runtime model download is forbidden")
    if request.get("reset_state_on_discontinuity") is not True:
        raise SileroVadPolicyError("VAD state reset on discontinuity is mandatory")
    if request.get("execution_provider") not in (None, "CPUExecutionProvider"):
        if not request.get("hrb_receipt_ref"):
            raise SileroVadPolicyError("accelerator execution requires an HRB receipt")


def build_speech_activity_map(
    *,
    request_id: str,
    source_artifact_ref: str,
    source_sha256: str,
    sample_rate_hz: int,
    source_timebase: str,
    segments: Iterable[SpeechSegment],
    provider_model_ref: str,
) -> dict:
    if sample_rate_hz not in SUPPORTED_SAMPLE_RATES:
        raise SileroVadPolicyError("unsupported analysis sample rate")
    result = []
    last_end = 0
    for segment in segments:
        segment.validate()
        if segment.start_sample < last_end:
            raise SileroVadPolicyError("speech segments must be ordered and non-overlapping")
        last_end = segment.end_sample
        result.append({
            "start_sample": segment.start_sample,
            "end_sample": segment.end_sample,
            "start_seconds": segment.start_sample / sample_rate_hz,
            "end_seconds": segment.end_sample / sample_rate_hz,
            "confidence": segment.confidence,
        })
    return {
        "schema": "fa3.speech-activity-map.v1",
        "request_id": request_id,
        "source_artifact_ref": source_artifact_ref,
        "source_sha256": source_sha256,
        "analysis_sample_rate_hz": sample_rate_hz,
        "analysis_channels": 1,
        "source_timebase": source_timebase,
        "metadata_only": True,
        "master_audio_mutated": False,
        "provider_id": "FA3-PROVIDER-SILERO-VAD-001",
        "provider_model_ref": provider_model_ref,
        "state_reset_on_discontinuity": True,
        "segments": result,
    }


def reference_policy_conformance() -> dict:
    request = {
        "sample_rate_hz": 16000,
        "channels": 1,
        "mutate_master_audio": False,
        "runtime_auto_download": False,
        "reset_state_on_discontinuity": True,
        "execution_provider": "CPUExecutionProvider",
    }
    validate_request(request)
    activity = build_speech_activity_map(
        request_id="reference",
        source_artifact_ref="sha256:source",
        source_sha256="0" * 64,
        sample_rate_hz=16000,
        source_timebase="1/48000",
        segments=[SpeechSegment(1600, 3200, 0.95)],
        provider_model_ref="sha256:model",
    )
    return {
        "result": "PASS" if activity["metadata_only"] and not activity["master_audio_mutated"] else "FAIL",
        "sample_rate_hz": 16000,
        "channels": 1,
        "metadata_only": True,
        "runtime_promoted": False,
    }
