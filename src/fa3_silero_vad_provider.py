#!/usr/bin/env python3
"""FA3 Silero VAD adapter boundary.

Produces metadata-only SpeechActivityMap artifacts. It deliberately does not
own source media, editorial state, routing, workflow orchestration or host
resource admission.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping, Any

SUPPORTED_SAMPLE_RATES = {8000, 16000}


@dataclass(frozen=True)
class SpeechSegment:
    start_sample: int
    end_sample: int
    confidence: float | None = None


@dataclass(frozen=True)
class SpeechActivityMap:
    source_hash: str
    analysis_sample_rate_hz: int
    channels: int
    segments: tuple[SpeechSegment, ...]
    provider_revision: str
    model_hash: str
    source_timebase: str

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["artifact_type"] = "SpeechActivityMap"
        out["metadata_only"] = True
        return out


def hash_file(path: str | Path) -> str:
    h = sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_analysis_projection(sample_rate_hz: int, channels: int) -> None:
    if sample_rate_hz not in SUPPORTED_SAMPLE_RATES:
        raise ValueError(f"Silero VAD analysis rate must be one of {sorted(SUPPORTED_SAMPLE_RATES)}")
    if channels != 1:
        raise ValueError("Silero VAD analysis projection must be mono")


def build_speech_activity_map(
    *,
    source_hash: str,
    sample_rate_hz: int,
    channels: int,
    segments: Iterable[Mapping[str, Any]],
    provider_revision: str,
    model_hash: str,
    source_timebase: str,
) -> SpeechActivityMap:
    validate_analysis_projection(sample_rate_hz, channels)
    if len(source_hash) != 64 or len(model_hash) != 64:
        raise ValueError("source_hash and model_hash must be SHA-256 hex digests")
    normalized: list[SpeechSegment] = []
    previous_end = -1
    for item in segments:
        start = int(item["start_sample"])
        end = int(item["end_sample"])
        confidence = item.get("confidence")
        confidence = None if confidence is None else float(confidence)
        if start < 0 or end <= start:
            raise ValueError("speech segment bounds are invalid")
        if start < previous_end:
            raise ValueError("speech segments must be ordered and non-overlapping")
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            raise ValueError("speech confidence must be in [0,1]")
        normalized.append(SpeechSegment(start, end, confidence))
        previous_end = end
    return SpeechActivityMap(
        source_hash=source_hash,
        analysis_sample_rate_hz=sample_rate_hz,
        channels=channels,
        segments=tuple(normalized),
        provider_revision=provider_revision,
        model_hash=model_hash,
        source_timebase=source_timebase,
    )
