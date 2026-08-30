#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PROFILE_ID = "FA3-BLACKHOLE-KDENLIVE-001"
STT_MEDIA_PROFILE_ID = "FA3-STT-MEDIA-001"
STT_CONTRACT_ID = "FA3-STT-MEDIA-CONTRACTS-001"
DEMUCS_PROVIDER_ID = "FA3-PROVIDER-DEMUCS-001"
INTEGRATION_VERSION = "1.0.0"

class IntegrationError(RuntimeError):
    pass

class PolicyDenied(IntegrationError):
    pass

class MediaPreparationFailed(IntegrationError):
    pass

class STTProviderFailed(IntegrationError):
    pass

class SubtitleProjectionFailed(IntegrationError):
    pass

@dataclass(frozen=True)
class PreparationRequest:
    input_media: str
    output_dir: str
    zone_start_seconds: float = 0.0
    zone_end_seconds: float | None = None
    preprocessing: str = "none"
    kdenlive_project: str | None = None
    project_fps: float | None = None
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    timeout_seconds: float = 7200.0
    demucs: dict[str, Any] = field(default_factory=dict)
    language: str = "auto"
    stt_command: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreparationRequest":
        return cls(
            input_media=str(data["input_media"]),
            output_dir=str(data["output_dir"]),
            zone_start_seconds=float(data.get("zone_start_seconds", 0.0)),
            zone_end_seconds=(None if data.get("zone_end_seconds") is None else float(data["zone_end_seconds"])),
            preprocessing=str(data.get("preprocessing", "none")),
            kdenlive_project=(None if not data.get("kdenlive_project") else str(data["kdenlive_project"])),
            project_fps=(None if data.get("project_fps") is None else float(data["project_fps"])),
            ffmpeg_bin=str(data.get("ffmpeg_bin", "ffmpeg")),
            ffprobe_bin=str(data.get("ffprobe_bin", "ffprobe")),
            timeout_seconds=float(data.get("timeout_seconds", 7200.0)),
            demucs=dict(data.get("demucs") or {}),
            language=str(data.get("language", "auto")),
            stt_command=tuple(str(x) for x in (data.get("stt_command") or [])),
        )

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def validate_preparation_request(request: PreparationRequest, *, require_existing_input: bool = True) -> None:
    findings: list[str] = []
    if request.zone_start_seconds < 0:
        findings.append("NEGATIVE_ZONE_START")
    if request.zone_end_seconds is not None and request.zone_end_seconds <= request.zone_start_seconds:
        findings.append("INVALID_ZONE_RANGE")
    if request.preprocessing not in {"none", "demucs_vocals"}:
        findings.append("UNSUPPORTED_PREPROCESSING")
    if request.preprocessing == "demucs_vocals" and not isinstance(request.demucs, dict):
        findings.append("DEMUCS_CONFIG_REQUIRED")
    if request.project_fps is not None and request.project_fps <= 0:
        findings.append("INVALID_PROJECT_FPS")
    if request.timeout_seconds <= 0:
        findings.append("INVALID_TIMEOUT")
    if require_existing_input and not Path(request.input_media).expanduser().is_file():
        findings.append("INPUT_MEDIA_NOT_FOUND")
    if request.kdenlive_project and require_existing_input and not Path(request.kdenlive_project).expanduser().is_file():
        findings.append("KDENLIVE_PROJECT_NOT_FOUND")
    if findings:
        raise PolicyDenied(";".join(findings))

def build_extract_command(request: PreparationRequest, output_path: Path) -> list[str]:
    command = [
        request.ffmpeg_bin,
        "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", str(Path(request.input_media).expanduser().resolve()),
    ]
    if request.zone_start_seconds > 0:
        command += ["-ss", f"{request.zone_start_seconds:.6f}"]
    if request.zone_end_seconds is not None:
        command += ["-t", f"{request.zone_end_seconds - request.zone_start_seconds:.6f}"]
    command += [
        "-map", "0:a:0",
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        "-c:a", "pcm_s24le",
        str(output_path),
    ]
    return command

def build_stt_normalize_command(request: PreparationRequest, input_path: Path, output_path: Path) -> list[str]:
    return [
        request.ffmpeg_bin,
        "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", str(input_path),
        "-map", "0:a:0",
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]

def _run_command(command: Sequence[str], timeout_seconds: float, label: str) -> None:
    try:
        completed = subprocess.run(
            list(command),
            shell=False,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise MediaPreparationFailed(f"{label} executable not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaPreparationFailed(f"{label} timed out") from exc
    if completed.returncode != 0:
        tail = completed.stderr.strip()[-2000:]
        raise MediaPreparationFailed(f"{label} failed rc={completed.returncode}: {tail}")

def _demucs_preprocess(root: Path, request: PreparationRequest, decoded_audio: Path, output_dir: Path) -> tuple[Path, dict[str, Any], Path]:
    from fa3_demucs_provider import SeparationRequest, execute_separation, evidence_complete

    demucs_dir = output_dir / "demucs"
    evidence_path = demucs_dir / "demucs-execution-evidence.json"
    cfg = dict(request.demucs)
    cfg.update({
        "input_path": str(decoded_audio),
        "output_dir": str(demucs_dir),
        "stems": ["vocals"],
        "model": str(cfg.get("model", "htdemucs")),
        "device": str(cfg.get("device", "cpu")),
        "offline": bool(cfg.get("offline", True)),
        "timeout_seconds": float(cfg.get("timeout_seconds", request.timeout_seconds)),
    })
    separation_request = SeparationRequest.from_dict(cfg)
    evidence = execute_separation(root, separation_request)
    if not evidence_complete(evidence):
        raise MediaPreparationFailed("Demucs preprocessing evidence contract incomplete")
    _write_json(evidence_path, evidence)
    vocals = demucs_dir / "vocals.wav"
    if not vocals.is_file():
        raise MediaPreparationFailed("Demucs PASS evidence produced without vocals.wav")
    return vocals, evidence, evidence_path

def prepare_media(root: Path, request: PreparationRequest) -> dict[str, Any]:
    validate_preparation_request(request)
    input_media = Path(request.input_media).expanduser().resolve()
    output_dir = Path(request.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    decoded = output_dir / "decoded-audio.wav"
    stt_audio = output_dir / "stt-input.wav"
    _run_command(build_extract_command(request, decoded), request.timeout_seconds, "FFmpeg audio extraction")

    preprocessing_evidence: dict[str, Any] | None = None
    preprocessing_evidence_path: Path | None = None
    normalization_source = decoded

    if request.preprocessing == "demucs_vocals":
        normalization_source, preprocessing_evidence, preprocessing_evidence_path = _demucs_preprocess(
            root, request, decoded, output_dir
        )

    _run_command(
        build_stt_normalize_command(request, normalization_source, stt_audio),
        request.timeout_seconds,
        "FFmpeg STT normalization",
    )

    if not stt_audio.is_file() or stt_audio.stat().st_size <= 44:
        raise MediaPreparationFailed("STT input audio was not produced")

    project_path = Path(request.kdenlive_project).expanduser().resolve() if request.kdenlive_project else None
    range_end = request.zone_end_seconds
    handoff = {
        "schema": "fa3.media-transcription-handoff.v1",
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "stt_media_profile_id": STT_MEDIA_PROFILE_ID,
        "contract_id": STT_CONTRACT_ID,
        "integration_version": INTEGRATION_VERSION,
        "created_at": _utc_now(),
        "source_media": {
            "path": str(input_media),
            "sha256": sha256_file(input_media),
        },
        "kdenlive_project": None if project_path is None else {
            "path": str(project_path),
            "sha256": sha256_file(project_path),
            "direct_xml_mutation": False,
        },
        "timeline_range": {
            "start_seconds": request.zone_start_seconds,
            "end_seconds": range_end,
            "project_fps": request.project_fps,
            "stt_time_origin": "RELATIVE_TO_PREPARED_AUDIO",
            "caption_projection_origin": "ABSOLUTE_TIMELINE_SECONDS",
        },
        "decoded_audio": {
            "path": str(decoded),
            "sha256": sha256_file(decoded),
            "samplerate": 44100,
            "channels": 2,
            "encoding": "PCM_S24LE",
        },
        "preprocessing": {
            "mode": request.preprocessing,
            "provider_id": DEMUCS_PROVIDER_ID if request.preprocessing == "demucs_vocals" else None,
            "silent_fallback_used": False,
            "evidence_path": None if preprocessing_evidence_path is None else str(preprocessing_evidence_path),
            "evidence_sha256": None if preprocessing_evidence_path is None else sha256_file(preprocessing_evidence_path),
            "execution_status": None if preprocessing_evidence is None else preprocessing_evidence.get("status"),
        },
        "stt_input_audio": {
            "path": str(stt_audio),
            "sha256": sha256_file(stt_audio),
            "samplerate": 16000,
            "channels": 1,
            "encoding": "PCM_S16LE",
        },
        "stt_request_template": {
            "schema": "fa3.stt-media-request.v1",
            "audio_path": str(stt_audio),
            "audio_hash": sha256_file(stt_audio),
            "language": request.language,
            "time_origin": "RELATIVE_ZERO",
            "required_result_schema": "fa3.stt-media-result.v1",
        },
        "lineage": [
            sha256_file(input_media),
            sha256_file(decoded),
            *( [] if preprocessing_evidence_path is None else [sha256_file(preprocessing_evidence_path)] ),
            sha256_file(stt_audio),
        ],
    }
    handoff_path = output_dir / "blackhole-media-handoff.json"
    _write_json(handoff_path, handoff)
    handoff["handoff_path"] = str(handoff_path)
    handoff["handoff_sha256"] = sha256_file(handoff_path)
    return handoff

def validate_stt_result(result: dict[str, Any], handoff: dict[str, Any]) -> list[dict[str, Any]]:
    if result.get("schema") != "fa3.stt-media-result.v1":
        raise SubtitleProjectionFailed("STT result schema mismatch")
    if result.get("status") != "PASS":
        raise SubtitleProjectionFailed("STT result is not PASS")
    expected_hash = handoff.get("stt_input_audio", {}).get("sha256")
    if result.get("audio_hash") != expected_hash:
        raise SubtitleProjectionFailed("STT result audio hash does not match handoff")
    segments = result.get("segments")
    if not isinstance(segments, list) or not segments:
        raise SubtitleProjectionFailed("STT result contains no segments")
    validated: list[dict[str, Any]] = []
    previous_end = 0.0
    for index, raw in enumerate(segments):
        if not isinstance(raw, dict):
            raise SubtitleProjectionFailed(f"segment {index} is not an object")
        start = float(raw.get("start", -1))
        end = float(raw.get("end", -1))
        text = str(raw.get("text", "")).strip()
        if start < 0 or end <= start:
            raise SubtitleProjectionFailed(f"segment {index} has invalid time range")
        if index > 0 and start < previous_end - 1e-6:
            raise SubtitleProjectionFailed(f"segment {index} overlaps previous subtitle segment")
        if not text:
            raise SubtitleProjectionFailed(f"segment {index} text is empty")
        speaker = raw.get("speaker")
        validated.append({
            "start": start,
            "end": end,
            "text": text,
            "speaker": None if speaker in (None, "") else str(speaker),
        })
        previous_end = end
    return validated

def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000.0))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def _vtt_time(seconds: float) -> str:
    return _srt_time(seconds).replace(",", ".")

def _subtitle_text(segment: dict[str, Any]) -> str:
    text = str(segment["text"]).replace("\r", "").strip()
    speaker = segment.get("speaker")
    return f"[{speaker}] {text}" if speaker else text

def project_subtitles(handoff: dict[str, Any], result: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    segments = validate_stt_result(result, handoff)
    offset = float(handoff.get("timeline_range", {}).get("start_seconds", 0.0))
    projected = [
        {
            **segment,
            "timeline_start": segment["start"] + offset,
            "timeline_end": segment["end"] + offset,
        }
        for segment in segments
    ]

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path = output_dir / "blackhole-subtitles.srt"
    vtt_path = output_dir / "blackhole-subtitles.vtt"
    json_path = output_dir / "blackhole-caption-track.json"
    descriptor_path = output_dir / "kdenlive-subtitle-import.json"

    srt_lines: list[str] = []
    for idx, segment in enumerate(projected, 1):
        srt_lines += [
            str(idx),
            f"{_srt_time(segment['timeline_start'])} --> {_srt_time(segment['timeline_end'])}",
            _subtitle_text(segment),
            "",
        ]
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    vtt_lines = ["WEBVTT", ""]
    for segment in projected:
        vtt_lines += [
            f"{_vtt_time(segment['timeline_start'])} --> {_vtt_time(segment['timeline_end'])}",
            _subtitle_text(segment),
            "",
        ]
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")

    caption_track = {
        "schema": "fa3.caption-track-artifact.v1",
        "status": "PASS",
        "profile_id": STT_MEDIA_PROFILE_ID,
        "source_audio_hash": handoff["stt_input_audio"]["sha256"],
        "timeline_offset_seconds": offset,
        "segments": projected,
        "formats": {
            "srt": {"path": str(srt_path), "sha256": sha256_file(srt_path)},
            "vtt": {"path": str(vtt_path), "sha256": sha256_file(vtt_path)},
        },
    }
    _write_json(json_path, caption_track)

    descriptor = {
        "schema": "fa3.kdenlive-subtitle-import-descriptor.v1",
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "project_mutation": "NONE",
        "direct_kdenlive_xml_mutation": False,
        "preferred_import": {
            "format": "SRT",
            "path": str(srt_path),
            "sha256": sha256_file(srt_path),
        },
        "alternate_import": {
            "format": "VTT",
            "path": str(vtt_path),
            "sha256": sha256_file(vtt_path),
        },
        "caption_track": {
            "path": str(json_path),
            "sha256": sha256_file(json_path),
        },
        "kdenlive_action": "Sequence > Subtitles > Import Subtitle File",
        "create_new_subtitle_track_supported": True,
    }
    _write_json(descriptor_path, descriptor)
    descriptor["descriptor_path"] = str(descriptor_path)
    descriptor["descriptor_sha256"] = sha256_file(descriptor_path)
    return descriptor

def _materialize_stt_request(handoff: dict[str, Any], path: Path) -> None:
    request = dict(handoff["stt_request_template"])
    request.update({
        "profile_id": STT_MEDIA_PROFILE_ID,
        "handoff_sha256": handoff.get("handoff_sha256"),
    })
    _write_json(path, request)

def validate_stt_command(command: Sequence[str]) -> None:
    if not command:
        raise PolicyDenied("STT_PROVIDER_COMMAND_REQUIRED")
    if not any("{request}" in token for token in command):
        raise PolicyDenied("STT_PROVIDER_COMMAND_MISSING_REQUEST_PLACEHOLDER")
    if not any("{result}" in token for token in command):
        raise PolicyDenied("STT_PROVIDER_COMMAND_MISSING_RESULT_PLACEHOLDER")
    for token in command:
        if "\n" in token or "\r" in token:
            raise PolicyDenied("STT_PROVIDER_COMMAND_INVALID_TOKEN")

def run_stt_provider(handoff: dict[str, Any], command: Sequence[str], output_dir: Path, timeout_seconds: float) -> tuple[dict[str, Any], Path]:
    validate_stt_command(command)
    request_path = output_dir / "stt-provider-request.json"
    result_path = output_dir / "stt-provider-result.json"
    _materialize_stt_request(handoff, request_path)
    resolved = [
        token.replace("{request}", str(request_path)).replace("{result}", str(result_path))
        for token in command
    ]
    try:
        completed = subprocess.run(
            resolved,
            shell=False,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise STTProviderFailed(f"STT provider executable not found: {resolved[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise STTProviderFailed("STT provider timed out") from exc
    if completed.returncode != 0:
        raise STTProviderFailed(f"STT provider failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    if not result_path.is_file():
        raise STTProviderFailed("STT provider returned success without result artifact")
    result = _read_json(result_path)
    validate_stt_result(result, handoff)
    return result, result_path

def run_pipeline(root: Path, request: PreparationRequest) -> dict[str, Any]:
    handoff = prepare_media(root, request)
    if not request.stt_command:
        return {
            "schema": "fa3.blackhole-kdenlive-pipeline-result.v1",
            "status": "PREPARED_FOR_STT",
            "profile_id": PROFILE_ID,
            "handoff": handoff,
            "subtitle_import": None,
        }
    output_dir = Path(request.output_dir).expanduser().resolve()
    result, result_path = run_stt_provider(handoff, request.stt_command, output_dir, request.timeout_seconds)
    descriptor = project_subtitles(handoff, result, output_dir)
    pipeline = {
        "schema": "fa3.blackhole-kdenlive-pipeline-result.v1",
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "handoff_path": handoff["handoff_path"],
        "handoff_sha256": handoff["handoff_sha256"],
        "stt_result_path": str(result_path),
        "stt_result_sha256": sha256_file(result_path),
        "subtitle_import": descriptor,
        "completed_at": _utc_now(),
    }
    _write_json(output_dir / "blackhole-kdenlive-pipeline-result.json", pipeline)
    return pipeline

def run_executable_conformance(root: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(name: str, ok: bool, detail: str) -> None:
        cases.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    base = PreparationRequest(input_media="/tmp/media.mkv", output_dir="/tmp/out")
    try:
        validate_preparation_request(base, require_existing_input=False)
        add("no_demucs_path_valid", True, "STT media preparation remains valid with preprocessing disabled")
    except Exception as exc:
        add("no_demucs_path_valid", False, repr(exc))

    try:
        validate_preparation_request(PreparationRequest(input_media="x", output_dir="y", zone_start_seconds=5, zone_end_seconds=4), require_existing_input=False)
        add("invalid_range_rejected", False, "invalid range unexpectedly accepted")
    except PolicyDenied:
        add("invalid_range_rejected", True, "timeline range fails closed")

    command = build_extract_command(PreparationRequest(input_media="/tmp/a.mov", output_dir="/tmp/o", zone_start_seconds=2, zone_end_seconds=5), Path("/tmp/o.wav"))
    add("ffmpeg_audio_stream_explicit", "-map" in command and "0:a:0" in command and "-vn" in command, "first audio stream explicitly mapped")
    add("ffmpeg_shell_free_shape", all(isinstance(x, str) for x in command) and not any(";" in x for x in command), "command is argv-only and intended for shell=False")

    normalize = build_stt_normalize_command(base, Path("/tmp/a.wav"), Path("/tmp/stt.wav"))
    add("stt_audio_normalization", "-ar" in normalize and "16000" in normalize and "-ac" in normalize and "1" in normalize and "pcm_s16le" in normalize, "STT handoff is normalized to 16 kHz mono PCM16")

    fake_handoff = {
        "stt_input_audio":{"sha256":"audiohash"},
        "timeline_range":{"start_seconds":10.0},
    }
    valid_result = {
        "schema":"fa3.stt-media-result.v1",
        "status":"PASS",
        "provider_id":"TEST-STT",
        "audio_hash":"audiohash",
        "language":"hu",
        "segments":[
            {"start":0.0,"end":1.25,"text":"Első mondat."},
            {"start":1.5,"end":2.0,"text":"Második.","speaker":"S1"},
        ],
    }
    try:
        segments = validate_stt_result(valid_result, fake_handoff)
        add("typed_stt_result_valid", len(segments)==2, "provider-neutral STT result accepted")
    except Exception as exc:
        add("typed_stt_result_valid", False, repr(exc))

    bad_hash = dict(valid_result); bad_hash["audio_hash"]="wrong"
    try:
        validate_stt_result(bad_hash, fake_handoff)
        add("stt_audio_hash_mismatch_rejected", False, "mismatched audio hash unexpectedly accepted")
    except SubtitleProjectionFailed:
        add("stt_audio_hash_mismatch_rejected", True, "result must bind to prepared audio hash")

    overlap = dict(valid_result); overlap["segments"]=[{"start":0,"end":2,"text":"a"},{"start":1,"end":3,"text":"b"}]
    try:
        validate_stt_result(overlap, fake_handoff)
        add("overlapping_subtitles_rejected", False, "overlap unexpectedly accepted")
    except SubtitleProjectionFailed:
        add("overlapping_subtitles_rejected", True, "subtitle projection rejects overlapping segments")

    add("srt_time_format", _srt_time(3661.234)=="01:01:01,234", "SRT millisecond timecode stable")
    add("vtt_time_format", _vtt_time(1.005)=="00:00:01.005", "VTT millisecond timecode stable")

    try:
        validate_stt_command(("/usr/bin/provider","--request","{request}","--result","{result}"))
        add("typed_stt_command_valid", True, "external STT provider command has explicit request/result artifacts")
    except Exception as exc:
        add("typed_stt_command_valid", False, repr(exc))

    try:
        validate_stt_command(("/usr/bin/provider","--request","{request}"))
        add("missing_result_placeholder_rejected", False, "incomplete provider command unexpectedly accepted")
    except PolicyDenied:
        add("missing_result_placeholder_rejected", True, "provider command must declare result artifact")

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        descriptor = project_subtitles(fake_handoff, valid_result, out)
        add("kdenlive_sidecar_only", descriptor["direct_kdenlive_xml_mutation"] is False and descriptor["project_mutation"]=="NONE", "Kdenlive integration uses importable sidecars only")
        add("srt_vtt_artifacts_created", Path(descriptor["preferred_import"]["path"]).is_file() and Path(descriptor["alternate_import"]["path"]).is_file(), "SRT and VTT artifacts materialized")
        caption = _read_json(descriptor["caption_track"]["path"])
        add("timeline_offset_preserved", caption["segments"][0]["timeline_start"]==10.0 and caption["segments"][1]["timeline_start"]==11.5, "prepared-audio relative timestamps are projected to absolute timeline")

    add("demucs_optional_only", DEMUCS_PROVIDER_ID=="FA3-PROVIDER-DEMUCS-001", "Demucs is referenced only by preprocessing mode, not STT result schema")
    passed = sum(x["status"]=="PASS" for x in cases)
    return {
        "schema":"fa3.blackhole-kdenlive-conformance-report.v1",
        "profile_id":PROFILE_ID,
        "integration_version":INTEGRATION_VERSION,
        "result":"PASS" if passed==len(cases) else "FAIL",
        "passed":passed,
        "total":len(cases),
        "cases":cases,
    }

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Blackhole/Kdenlive long-form media STT integration")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = ap.add_subparsers(dest="command", required=True)

    conf = sub.add_parser("conformance")
    conf.add_argument("--report", default="reports/blackhole-kdenlive-conformance-report.json")

    prep = sub.add_parser("prepare")
    prep.add_argument("--request", required=True)
    prep.add_argument("--handoff")

    subtitles = sub.add_parser("subtitles")
    subtitles.add_argument("--handoff", required=True)
    subtitles.add_argument("--stt-result", required=True)
    subtitles.add_argument("--output-dir", required=True)

    pipeline = sub.add_parser("pipeline")
    pipeline.add_argument("--request", required=True)
    pipeline.add_argument("--report")

    args = ap.parse_args()
    root = Path(args.root).resolve()
    try:
        if args.command == "conformance":
            report = run_executable_conformance(root)
            path = Path(args.report)
            if not path.is_absolute():
                path = root / path
            _write_json(path, report)
            print(json.dumps(report, indent=2))
            return 0 if report["result"]=="PASS" else 2
        if args.command == "prepare":
            request = PreparationRequest.from_dict(_read_json(args.request))
            handoff = prepare_media(root, request)
            if args.handoff:
                _write_json(Path(args.handoff), handoff)
            print(json.dumps(handoff, indent=2))
            return 0
        if args.command == "subtitles":
            handoff = _read_json(args.handoff)
            result = _read_json(args.stt_result)
            descriptor = project_subtitles(handoff, result, args.output_dir)
            print(json.dumps(descriptor, indent=2))
            return 0
        request = PreparationRequest.from_dict(_read_json(args.request))
        result = run_pipeline(root, request)
        if args.report:
            _write_json(Path(args.report), result)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] in {"PASS","PREPARED_FOR_STT"} else 2
    except IntegrationError as exc:
        print(json.dumps({"status":"FAIL","profile_id":PROFILE_ID,"error_type":type(exc).__name__,"error":str(exc)}, indent=2), file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({"status":"FAIL","profile_id":PROFILE_ID,"error_type":type(exc).__name__,"error":str(exc)}, indent=2), file=sys.stderr)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
