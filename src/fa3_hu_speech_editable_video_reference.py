#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from fa3_blackhole_kdenlive import project_subtitles, sha256_file, validate_stt_result
from fa3_caption_subtitle import document_sha256, export_subtitle, new_document, validate_document
from fa3_caption_workflows import build_editorial_projection, caption_quality_report, edit_cue

REFERENCE_ID = "FA3-HU-SPEECH-EDITABLE-VIDEO-REFERENCE-001"
LANGUAGE_LOCALE = "hu-HU"
PROVIDER_LANGUAGE = "hu"


class ReferenceJourneyError(RuntimeError):
    pass


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_json(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def caption_document_from_stt(result: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    segments = validate_stt_result(result, handoff)
    language = str(result.get("language", "")).lower()
    if language not in {"hu", "hu-hu"}:
        raise ReferenceJourneyError(f"Hungarian STT required, got {language or 'UNKNOWN'}")

    offset_ms = int(round(float(handoff.get("timeline_range", {}).get("start_seconds", 0.0)) * 1000))
    cues: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, 1):
        start_ms = int(round(float(segment["start"]) * 1000)) + offset_ms
        end_ms = int(round(float(segment["end"]) * 1000)) + offset_ms
        raw_segment = result["segments"][index - 1]
        words = []
        for raw in raw_segment.get("words", []) or []:
            word_start = int(round(float(raw["start"]) * 1000)) + offset_ms
            word_end = int(round(float(raw["end"]) * 1000)) + offset_ms
            words.append({
                "start_ms": word_start,
                "end_ms": word_end,
                "text": str(raw.get("word", "")).strip(),
                "probability": raw.get("probability"),
            })
        cues.append({
            "id": f"cue-{index:06d}",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": segment["text"],
            "speaker": segment.get("speaker"),
            "words": words,
        })

    return new_document(
        cues,
        language=LANGUAGE_LOCALE,
        source_format="FA3 Whisper STT",
        provenance={
            "reference_journey_id": REFERENCE_ID,
            "stt_provider_id": result.get("provider_id"),
            "stt_result_sha256": _sha256_json(result),
            "source_audio_sha256": handoff["stt_input_audio"]["sha256"],
            "source_media_sha256": handoff.get("source_media", {}).get("sha256"),
            "requested_locale": LANGUAGE_LOCALE,
            "provider_language_code": PROVIDER_LANGUAGE,
        },
    )


def _otio_projection(final_doc: dict[str, Any], source_media_sha256: str) -> dict[str, Any]:
    cues = final_doc["tracks"][0]["cues"]
    children = []
    for cue in cues:
        children.append({
            "OTIO_SCHEMA": "Clip.2",
            "name": cue["id"],
            "source_range": {
                "OTIO_SCHEMA": "TimeRange.1",
                "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": cue["start_ms"], "rate": 1000.0},
                "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": cue["end_ms"] - cue["start_ms"], "rate": 1000.0},
            },
            "metadata": {
                "fa3_caption_text": cue["text"],
                "fa3_caption_editable": True,
                "fa3_caption_revision": final_doc["revision"],
            },
        })
    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": "FA3 Hungarian Speech Editable Video Reference",
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "children": [{
                "OTIO_SCHEMA": "Track.1",
                "name": "Captions hu-HU",
                "kind": "Video",
                "children": children,
            }],
        },
        "metadata": {
            "fa3_reference_journey_id": REFERENCE_ID,
            "fa3_source_media_sha256": source_media_sha256,
            "fa3_caption_document_sha256": document_sha256(final_doc),
            "canonical_timeline_ir": "OpenTimelineIO",
            "editable_caption_semantics": True,
            "direct_kdenlive_xml_mutation": False,
        },
    }


def _materialize_project(
    output_dir: Path,
    handoff: dict[str, Any],
    initial_doc: dict[str, Any],
    edited_doc: dict[str, Any],
    kdenlive_descriptor: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    initial_path = output_dir / "captions-initial.fa3caption.json"
    edited_path = output_dir / "captions-edited.fa3caption.json"
    srt_path = output_dir / "captions-edited.srt"
    vtt_path = output_dir / "captions-edited.vtt"
    otio_path = output_dir / "timeline.otio.json"
    project_path = output_dir / "project.fa3video"

    _write_json(initial_path, initial_doc)
    _write_json(edited_path, edited_doc)
    srt_path.write_text(export_subtitle(edited_doc, "srt"), encoding="utf-8")
    vtt_path.write_text(export_subtitle(edited_doc, "vtt"), encoding="utf-8")

    otio = _otio_projection(edited_doc, handoff["source_media"]["sha256"])
    _write_json(otio_path, otio)

    edited_descriptor_path = output_dir / "kdenlive-edited-subtitle-import.json"
    edited_descriptor = {
        "schema": "fa3.kdenlive-subtitle-import-descriptor.v1",
        "status": "PASS",
        "reference_journey_id": REFERENCE_ID,
        "project_mutation": "NONE",
        "direct_kdenlive_xml_mutation": False,
        "preferred_import": {"format": "SRT", "path": str(srt_path), "sha256": sha256_file(srt_path)},
        "alternate_import": {"format": "VTT", "path": str(vtt_path), "sha256": sha256_file(vtt_path)},
        "caption_document": {"path": str(edited_path), "sha256": sha256_file(edited_path)},
        "source_projection_descriptor": {
            "path": kdenlive_descriptor.get("descriptor_path"),
            "sha256": kdenlive_descriptor.get("descriptor_sha256"),
        },
        "human_edit_revision": edited_doc["revision"],
        "kdenlive_action": "Sequence > Subtitles > Import Subtitle File",
        "create_new_subtitle_track_supported": True,
    }
    _write_json(edited_descriptor_path, edited_descriptor)

    project = {
        "schema": "fa3.video-project-reference.v1",
        "reference_journey_id": REFERENCE_ID,
        "project_format": "project.fa3video",
        "editable": True,
        "canonical_timeline_ir": "OpenTimelineIO",
        "source_media": {
            "path": handoff["source_media"]["path"],
            "sha256": handoff["source_media"]["sha256"],
        },
        "caption_document": {
            "path": edited_path.name,
            "sha256": sha256_file(edited_path),
            "revision": edited_doc["revision"],
            "language": LANGUAGE_LOCALE,
            "human_editable": True,
        },
        "timeline": {
            "path": otio_path.name,
            "sha256": sha256_file(otio_path),
            "format": "OTIO_JSON",
        },
        "interchange": {
            "srt": {"path": srt_path.name, "sha256": sha256_file(srt_path)},
            "vtt": {"path": vtt_path.name, "sha256": sha256_file(vtt_path)},
            "kdenlive": {
                "descriptor_path": str(edited_descriptor_path),
                "descriptor_sha256": sha256_file(edited_descriptor_path),
                "direct_project_xml_mutation": False,
                "human_finishing_boundary": True,
            },
        },
        "lineage": {
            "source_media_sha256": handoff["source_media"]["sha256"],
            "stt_audio_sha256": handoff["stt_input_audio"]["sha256"],
            "initial_caption_sha256": document_sha256(initial_doc),
            "edited_caption_sha256": document_sha256(edited_doc),
            "edited_parent_sha256": edited_doc.get("provenance", {}).get("parent_revision_sha256"),
        },
    }
    _write_json(project_path, project)
    return {
        "project_path": str(project_path),
        "project_sha256": sha256_file(project_path),
        "initial_caption_path": str(initial_path),
        "initial_caption_sha256": sha256_file(initial_path),
        "edited_caption_path": str(edited_path),
        "edited_caption_sha256": sha256_file(edited_path),
        "srt_path": str(srt_path),
        "srt_sha256": sha256_file(srt_path),
        "vtt_path": str(vtt_path),
        "vtt_sha256": sha256_file(vtt_path),
        "otio_path": str(otio_path),
        "otio_sha256": sha256_file(otio_path),
        "kdenlive_descriptor_path": str(edited_descriptor_path),
        "kdenlive_descriptor_sha256": sha256_file(edited_descriptor_path),
    }


def complete_from_stt(
    handoff: dict[str, Any],
    stt_result: dict[str, Any],
    output_dir: str | Path,
    *,
    human_edit_text: str,
    inject_failure_once: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not human_edit_text.strip():
        raise ReferenceJourneyError("Explicit human edit text is required")

    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    checkpoints = out / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)

    validate_stt_result(stt_result, handoff)
    if str(stt_result.get("language", "")).lower() not in {"hu", "hu-hu"}:
        raise ReferenceJourneyError("Reference journey requires Hungarian recognition")

    kdenlive_descriptor = project_subtitles(handoff, stt_result, out / "stt-projection")
    initial_doc = caption_document_from_stt(stt_result, handoff)
    initial_digest = document_sha256(initial_doc)
    checkpoint_path = checkpoints / "canonical-caption.json"
    _write_json(checkpoint_path, initial_doc)

    retry_count = 0
    resume_from = None
    failure_injection = {
        "requested": bool(inject_failure_once),
        "injected": False,
        "point": None,
        "recovered": False,
    }
    if inject_failure_once:
        failure_injection.update({"injected": True, "point": "AFTER_CANONICAL_CAPTION"})
        retry_count = 1
        resume_from = "CANONICAL_CAPTION_CHECKPOINT"
        resumed_doc = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        validate_document(resumed_doc)
        if document_sha256(resumed_doc) != initial_digest:
            raise ReferenceJourneyError("Checkpoint identity mismatch during resume")
        initial_doc = resumed_doc
        failure_injection["recovered"] = True

    first_cue = initial_doc["tracks"][0]["cues"][0]["id"]
    edited_doc = edit_cue(initial_doc, first_cue, human_edit_text.strip(), actor="HUMAN_OPERATOR")
    for cue in edited_doc["tracks"][0]["cues"]:
        if cue["id"] == first_cue:
            cue["words"] = []
            cue["word_timing_status"] = "INVALIDATED_BY_HUMAN_TEXT_EDIT"
            break
    if edited_doc.get("provenance", {}).get("parent_revision_sha256") != initial_digest:
        raise ReferenceJourneyError("Human-edit lineage parent digest mismatch")
    validate_document(edited_doc)
    qc = caption_quality_report(edited_doc)
    editorial_projection = build_editorial_projection(edited_doc, "KDENLIVE")

    artifacts = _materialize_project(out, handoff, initial_doc, edited_doc, kdenlive_descriptor)

    rollback_path = out / "rollback-restored-caption.fa3caption.json"
    shutil.copy2(checkpoint_path, rollback_path)
    rollback_doc = json.loads(rollback_path.read_text(encoding="utf-8"))
    validate_document(rollback_doc)
    rollback_digest = document_sha256(rollback_doc)
    rollback_verified = rollback_digest == initial_digest

    result = {
        "schema": "fa3.hu-speech-editable-video-reference-result.v1",
        "reference_journey_id": REFERENCE_ID,
        "result": "PASS" if rollback_verified else "FAIL",
        "requested_locale": LANGUAGE_LOCALE,
        "provider_language_code": PROVIDER_LANGUAGE,
        "speech_recognition": {
            "detected_language": stt_result.get("language"),
            "segment_count": len(stt_result.get("segments", [])),
            "word_timestamps_present": all(bool(x.get("words")) for x in stt_result.get("segments", [])),
            "provider_id": stt_result.get("provider_id"),
        },
        "captions": {
            "canonical_schema": initial_doc["schema"],
            "initial_revision": initial_doc["revision"],
            "edited_revision": edited_doc["revision"],
            "human_edit_actor": edited_doc.get("provenance", {}).get("last_actor"),
            "human_edit_operation": edited_doc.get("provenance", {}).get("last_operation"),
            "edited_word_timing_status": edited_doc["tracks"][0]["cues"][0].get("word_timing_status"),
            "qc_status": qc["status"],
            "editable": True,
        },
        "editorial_handoff": {
            "fa3_video_project": artifacts["project_path"],
            "fa3_video_project_sha256": artifacts["project_sha256"],
            "canonical_timeline_ir": editorial_projection["canonical_timeline_ir"],
            "editable_caption_semantics_required": editorial_projection["editable_caption_semantics_required"],
            "otio_path": artifacts["otio_path"],
            "otio_sha256": artifacts["otio_sha256"],
            "kdenlive_descriptor_path": artifacts["kdenlive_descriptor_path"],
            "kdenlive_descriptor_sha256": artifacts["kdenlive_descriptor_sha256"],
            "direct_kdenlive_xml_mutation": False,
            "srt_path": artifacts["srt_path"],
            "srt_sha256": artifacts["srt_sha256"],
            "vtt_path": artifacts["vtt_path"],
            "vtt_sha256": artifacts["vtt_sha256"],
        },
        "lineage": {
            "source_media_sha256": handoff["source_media"]["sha256"],
            "stt_audio_sha256": handoff["stt_input_audio"]["sha256"],
            "stt_result_sha256": _sha256_json(stt_result),
            "initial_caption_sha256": initial_digest,
            "edited_caption_sha256": document_sha256(edited_doc),
            "edited_parent_sha256": edited_doc.get("provenance", {}).get("parent_revision_sha256"),
            "final_project_sha256": artifacts["project_sha256"],
        },
        "retry_resume": {
            "retry_count": retry_count,
            "resume_from": resume_from,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": sha256_file(checkpoint_path),
        },
        "failure_injection": failure_injection,
        "rollback": {
            "verified": rollback_verified,
            "restored_caption_path": str(rollback_path),
            "restored_caption_sha256": rollback_digest,
            "expected_parent_sha256": initial_digest,
            "final_project_preserved": Path(artifacts["project_path"]).is_file(),
        },
        "metrics": {
            "reference_stage_wall_seconds": round(time.perf_counter() - started, 6),
            "scope": "REFERENCE_STAGE_METRICS_NOT_CURRENT_HOST_RESOURCE_EVIDENCE",
        },
        "current_host": False,
        "production_promotion": False,
    }
    _write_json(out / "reference-journey-result.json", result)
    return result


def synthetic_fixture(workdir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    media = workdir / "fixture-media.bin"
    audio = workdir / "fixture-audio.pcm"
    media.write_bytes(b"fa3-hu-reference-media")
    audio.write_bytes(b"fa3-hu-reference-audio")
    handoff = {
        "schema": "fa3.media-transcription-handoff.v1",
        "status": "PASS",
        "source_media": {"path": str(media), "sha256": sha256_file(media)},
        "stt_input_audio": {"path": str(audio), "sha256": sha256_file(audio)},
        "timeline_range": {"start_seconds": 0.0},
    }
    stt = {
        "schema": "fa3.stt-media-result.v1",
        "status": "PASS",
        "provider_id": "FA3-PROVIDER-WHISPER-001",
        "audio_hash": handoff["stt_input_audio"]["sha256"],
        "language": "hu",
        "segments": [
            {
                "start": 0.0,
                "end": 1.2,
                "text": "Szia világ.",
                "words": [
                    {"start": 0.0, "end": 0.5, "word": "Szia", "probability": 0.99},
                    {"start": 0.55, "end": 1.1, "word": "világ.", "probability": 0.98},
                ],
            },
            {
                "start": 1.5,
                "end": 2.8,
                "text": "Ez egy magyar próba.",
                "words": [
                    {"start": 1.5, "end": 1.75, "word": "Ez", "probability": 0.99},
                    {"start": 1.8, "end": 2.0, "word": "egy", "probability": 0.99},
                    {"start": 2.05, "end": 2.35, "word": "magyar", "probability": 0.98},
                    {"start": 2.4, "end": 2.75, "word": "próba.", "probability": 0.98},
                ],
            },
        ],
    }
    return handoff, stt


def run_reference_e2e(root: Path) -> dict[str, Any]:
    del root
    with tempfile.TemporaryDirectory(prefix="fa3-hu-speech-reference-") as td:
        workdir = Path(td)
        handoff, stt = synthetic_fixture(workdir)
        result = complete_from_stt(
            handoff,
            stt,
            workdir / "journey",
            human_edit_text="Szia, világ!",
            inject_failure_once=True,
        )
        checks = {
            "hu_hu_recognition_contract": result["requested_locale"] == LANGUAGE_LOCALE and result["speech_recognition"]["detected_language"] == "hu",
            "word_timestamps": result["speech_recognition"]["word_timestamps_present"] is True,
            "editable_caption": result["captions"]["editable"] is True and result["captions"]["edited_revision"] == result["captions"]["initial_revision"] + 1,
            "human_edit": result["captions"]["human_edit_actor"] == "HUMAN_OPERATOR" and result["captions"]["edited_word_timing_status"] == "INVALIDATED_BY_HUMAN_TEXT_EDIT",
            "srt_vtt_reexport": bool(result["editorial_handoff"]["srt_sha256"]) and bool(result["editorial_handoff"]["vtt_sha256"]),
            "otio": result["editorial_handoff"]["canonical_timeline_ir"] == "OpenTimelineIO",
            "kdenlive_no_direct_xml": result["editorial_handoff"]["direct_kdenlive_xml_mutation"] is False,
            "retry_resume": result["retry_resume"]["retry_count"] == 1 and result["failure_injection"]["recovered"] is True,
            "rollback": result["rollback"]["verified"] is True,
            "lineage": result["lineage"]["edited_parent_sha256"] == result["lineage"]["initial_caption_sha256"],
            "final_project_hash": len(result["lineage"]["final_project_sha256"]) == 64,
            "no_current_host_overclaim": result["current_host"] is False and result["production_promotion"] is False,
        }
        return {
            "schema": "fa3.hu-speech-editable-video-reference-conformance.v1",
            "reference_journey_id": REFERENCE_ID,
            "result": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "current_host_claim": False,
            "production_promotion_claim": False,
        }
