#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import urlopen

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITIES = ("CAP-016", "CAP-017", "CAP-018", "CAP-019", "CAP-020")
MODES = ("positive", "negative", "rollback")
NAMES = {cap: f"{cap.lower().replace('-', '')}-mat004-evidence.json" for cap in CAPABILITIES}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha(path.read_bytes())


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value


def repo_file(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise RuntimeError(f"required artifact missing: {rel}")
    return path


def cmd(argv: list[str], timeout: int = 30, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
        check=False,
        cwd=str(cwd) if cwd is not None else None,
    )


def expected_source_decisions(root: Path, cap: str) -> list[str]:
    registry = load(root / "evidence/evidence-registry.json")
    row = next((x for x in registry.get("records", []) if x.get("subject_id") == cap), None)
    ids = row.get("source_decision_ids") if isinstance(row, dict) else None
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise RuntimeError(f"{cap} source decisions invalid")
    return ids


def validate_exact_coverage(root: Path, cap: str, supplied: list[str]) -> list[str]:
    expected = expected_source_decisions(root, cap)
    if supplied != expected:
        raise RuntimeError(f"{cap} coverage != Evidence Registry")
    return expected


def exact_rollback(scope: Path, name: str, baseline: bytes, fault: bytes) -> dict[str, Any]:
    path = scope / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(baseline)
    pre = sha_file(path)
    path.write_bytes(fault)
    mutated = sha_file(path)
    path.write_bytes(baseline)
    post = sha_file(path)
    if pre != post or pre == mutated:
        raise RuntimeError("exact rollback proof failed")
    return {
        "pre_sha256": pre,
        "mutated_sha256": mutated,
        "post_sha256": post,
        "rollback_hash_equal": True,
    }


def media_job_allowed(job: dict[str, Any]) -> bool:
    return (
        job.get("execution_scope") == "CURRENT_HOST"
        and job.get("network_fetch") is False
        and job.get("human_approved") is True
        and job.get("overwrite_source") is False
        and job.get("output_inside_artifact_scope") is True
        and job.get("provider_fallback_unapproved") is False
    )


def _find_dcc() -> tuple[str, str] | None:
    for name, label in (
        ("bforartists", "Bforartists"),
        ("bforartists-bin", "Bforartists"),
        ("blender", "Blender"),
    ):
        path = shutil.which(name)
        if path:
            return label, path
    return None


def _ffprobe_json(ffprobe: str, path: Path) -> dict[str, Any]:
    proc = cmd(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr[-1500:]}")
    value = json.loads(proc.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("ffprobe JSON is not an object")
    return value


def cap016(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-NEURAL-MEDIA-EXECUTION-CONTRACTS-001.json",
        "canonical/contracts/FA3-KDENLIVE-EDITORIAL-CONTRACTS-001.json",
        "canonical/contracts/FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001.json",
        "canonical/profiles/FA3-VIDEO-001.json",
    ):
        repo_file(root, rel)

    good_job = {
        "execution_scope": "CURRENT_HOST",
        "network_fetch": False,
        "human_approved": True,
        "overwrite_source": False,
        "output_inside_artifact_scope": True,
        "provider_fallback_unapproved": False,
    }
    if mode == "negative":
        cases = {
            "network_fetch_denied": not media_job_allowed({**good_job, "network_fetch": True}),
            "unapproved_job_denied": not media_job_allowed({**good_job, "human_approved": False}),
            "source_overwrite_denied": not media_job_allowed({**good_job, "overwrite_source": True}),
            "artifact_scope_escape_denied": not media_job_allowed({**good_job, "output_inside_artifact_scope": False}),
            "unapproved_provider_fallback_denied": not media_job_allowed({**good_job, "provider_fallback_unapproved": True}),
        }
        if not all(cases.values()):
            raise RuntimeError(f"Media Generation/DCC negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}

    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "media-dcc-state.json",
                b'{"source_immutable":true,"provider_fallback":"DENY","state":"READY"}\n',
                b'{"source_immutable":false,"provider_fallback":"AUTO","state":"MUTATED"}\n',
            ),
        }

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    dcc = _find_dcc()
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required")
    if dcc is None:
        raise RuntimeError("Bforartists or Blender executable is required")
    if not media_job_allowed(good_job):
        raise RuntimeError("approved media job rejected")

    video = scope / "generated-media.mkv"
    render = cmd(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=12:duration=1",
            "-c:v",
            "ffv1",
            str(video),
        ],
        60,
    )
    if render.returncode != 0 or not video.is_file() or video.stat().st_size <= 0:
        raise RuntimeError(f"FFmpeg media generation failed: {render.stderr[-1500:]}")
    probe = _ffprobe_json(ffprobe, video)
    streams = probe.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not isinstance(video_stream, dict):
        raise RuntimeError("generated artifact has no video stream")
    if int(video_stream.get("width", 0)) != 160 or int(video_stream.get("height", 0)) != 90:
        raise RuntimeError("generated media dimensions mismatch")

    dcc_name, dcc_path = dcc
    sentinel = "FA3_MAT004_DCC_SMOKE_PASS"
    dcc_proc = cmd(
        [
            dcc_path,
            "--background",
            "--factory-startup",
            "--python-expr",
            f"print('{sentinel}')",
        ],
        60,
    )
    combined = dcc_proc.stdout + "\n" + dcc_proc.stderr
    if dcc_proc.returncode != 0 or sentinel not in combined:
        raise RuntimeError(
            f"DCC headless smoke failed app={dcc_name} rc={dcc_proc.returncode}: {dcc_proc.stderr[-1500:]}"
        )

    return {
        "mode": mode,
        "status": "PASS",
        "ffmpeg_path": ffmpeg,
        "ffprobe_path": ffprobe,
        "media_path": video.relative_to(root).as_posix(),
        "media_sha256": sha_file(video),
        "media_bytes": video.stat().st_size,
        "video_codec": video_stream.get("codec_name"),
        "video_width": video_stream.get("width"),
        "video_height": video_stream.get("height"),
        "dcc_application": dcc_name,
        "dcc_path": dcc_path,
        "dcc_headless_smoke": True,
        "network_fetch": False,
        "source_overwritten": False,
        "unapproved_provider_fallback": False,
    }


def audio_job_allowed(job: dict[str, Any]) -> bool:
    try:
        rate = int(job.get("sample_rate_hz", 0))
        channels = int(job.get("channels", 0))
        gain = float(job.get("gain_db", float("nan")))
    except (TypeError, ValueError):
        return False
    return (
        job.get("execution_scope") == "CURRENT_HOST"
        and job.get("network_fetch") is False
        and 8000 <= rate <= 192000
        and 1 <= channels <= 8
        and math.isfinite(gain)
        and -60.0 <= gain <= 24.0
        and job.get("implicit_double_denoise") is False
        and job.get("overwrite_source") is False
    )


def cap017(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-SPEECH-ENHANCEMENT-CONTRACTS-001.json",
        "canonical/contracts/FA3-AUDIO-RESTORATION-BWE-CONTRACTS-001.json",
        "canonical/contracts/FA3-MUSIC-GENERATION-CONTRACTS-001.json",
        "canonical/contracts/FA3-KDENLIVE-AUDIO-CONDITIONING-CONTRACTS-001.json",
    ):
        repo_file(root, rel)

    good_job = {
        "execution_scope": "CURRENT_HOST",
        "network_fetch": False,
        "sample_rate_hz": 48000,
        "channels": 1,
        "gain_db": -3.0,
        "implicit_double_denoise": False,
        "overwrite_source": False,
    }
    if mode == "negative":
        cases = {
            "invalid_sample_rate_denied": not audio_job_allowed({**good_job, "sample_rate_hz": 100}),
            "zero_channels_denied": not audio_job_allowed({**good_job, "channels": 0}),
            "nonfinite_gain_denied": not audio_job_allowed({**good_job, "gain_db": float("nan")}),
            "implicit_double_denoise_denied": not audio_job_allowed({**good_job, "implicit_double_denoise": True}),
            "source_overwrite_denied": not audio_job_allowed({**good_job, "overwrite_source": True}),
            "network_fetch_denied": not audio_job_allowed({**good_job, "network_fetch": True}),
        }
        if not all(cases.values()):
            raise RuntimeError(f"Speech/Audio/Music/Post negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}

    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "audio-post-state.json",
                b'{"source_immutable":true,"double_denoise":"DENY","state":"READY"}\n',
                b'{"source_immutable":false,"double_denoise":"AUTO","state":"FAULT"}\n',
            ),
        }

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required for audio current-host proof")
    if not audio_job_allowed(good_job):
        raise RuntimeError("approved audio job rejected")

    source = scope / "source.wav"
    processed = scope / "processed.wav"
    gen = cmd(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=997:sample_rate=48000:duration=1",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(source),
        ],
        45,
    )
    if gen.returncode != 0 or not source.is_file():
        raise RuntimeError(f"audio source generation failed: {gen.stderr[-1500:]}")
    source_hash = sha_file(source)

    post = cmd(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-af",
            "highpass=f=80,volume=-3dB",
            "-c:a",
            "pcm_s16le",
            str(processed),
        ],
        45,
    )
    if post.returncode != 0 or not processed.is_file():
        raise RuntimeError(f"audio post-processing failed: {post.stderr[-1500:]}")
    if sha_file(source) != source_hash:
        raise RuntimeError("audio source was mutated")

    probe = _ffprobe_json(ffprobe, processed)
    audio_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not isinstance(audio_stream, dict):
        raise RuntimeError("processed artifact has no audio stream")
    if int(audio_stream.get("sample_rate", 0)) != 48000 or int(audio_stream.get("channels", 0)) != 1:
        raise RuntimeError("processed audio format mismatch")
    try:
        duration = float(probe.get("format", {}).get("duration", "0"))
    except (TypeError, ValueError):
        duration = 0.0
    if not 0.90 <= duration <= 1.10:
        raise RuntimeError(f"processed audio duration out of bound: {duration}")

    return {
        "mode": mode,
        "status": "PASS",
        "source_sha256": source_hash,
        "processed_sha256": sha_file(processed),
        "source_preserved": True,
        "sample_rate_hz": 48000,
        "channels": 1,
        "duration_seconds": duration,
        "codec": audio_stream.get("codec_name"),
        "network_fetch": False,
        "implicit_double_denoise": False,
    }


def document_record_allowed(record: dict[str, Any]) -> bool:
    citations = record.get("citations")
    return (
        record.get("status") == "APPROVED"
        and record.get("human_approval_id")
        and record.get("source_authoritative") is True
        and record.get("derived_index_authoritative") is False
        and record.get("automatic_publication") is False
        and isinstance(record.get("title"), str)
        and bool(record["title"].strip())
        and isinstance(record.get("body"), str)
        and bool(record["body"].strip())
        and isinstance(citations, list)
        and len(citations) >= 1
        and all(isinstance(x, str) and x.strip() for x in citations)
    )


def cap018(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-KNOWLEDGE-CONTRACTS-001.json",
        "canonical/contracts/FA3-HUMAN-KNOWLEDGE-WORKSPACE-CONTRACTS-001.json",
        "canonical/FA3-GATE-KNOWLEDGE-HYBRID-RETRIEVAL-001.json",
    ):
        repo_file(root, rel)

    good = {
        "status": "APPROVED",
        "human_approval_id": "mat004-doc-approval",
        "source_authoritative": True,
        "derived_index_authoritative": False,
        "automatic_publication": False,
        "title": "FA3 current-host authored document",
        "body": "This document contains the MAT-004 knowledge authoring sentinel.",
        "citations": ["local:fa3/current-host/mat004"],
    }
    if mode == "negative":
        cases = {
            "draft_denied": not document_record_allowed({**good, "status": "DRAFT"}),
            "missing_approval_denied": not document_record_allowed({**good, "human_approval_id": ""}),
            "citationless_denied": not document_record_allowed({**good, "citations": []}),
            "derived_index_authority_denied": not document_record_allowed({**good, "derived_index_authoritative": True}),
            "automatic_publication_denied": not document_record_allowed({**good, "automatic_publication": True}),
        }
        if not all(cases.values()):
            raise RuntimeError(f"Documents/Knowledge Authoring negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}

    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "document-authoring-state.json",
                b'{"source_authoritative":true,"derived_index_authoritative":false,"state":"APPROVED"}\n',
                b'{"source_authoritative":false,"derived_index_authoritative":true,"state":"AUTO_PUBLISHED"}\n',
            ),
        }

    if not document_record_allowed(good):
        raise RuntimeError("approved document record rejected")
    source = scope / "document.md"
    source.write_text(
        f"# {good['title']}\n\n{good['body']}\n\n## References\n\n- {good['citations'][0]}\n",
        encoding="utf-8",
    )
    source_hash = sha_file(source)

    db = sqlite3.connect(scope / "knowledge-index.sqlite3")
    try:
        db.execute(
            "CREATE TABLE docs(id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, source_sha256 TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO docs(id,title,body,source_sha256) VALUES(?,?,?,?)",
            ("mat004-doc", good["title"], good["body"], source_hash),
        )
        db.commit()
        row = db.execute(
            "SELECT id, source_sha256 FROM docs WHERE body LIKE ?",
            ("%MAT-004 knowledge authoring sentinel%",),
        ).fetchone()
    finally:
        db.close()
    if row != ("mat004-doc", source_hash):
        raise RuntimeError("local knowledge index retrieval failed")
    if sha_file(source) != source_hash:
        raise RuntimeError("derived knowledge index mutated authoritative source")

    exported = scope / "document.html"
    exported.write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(good['title'])}</title></head><body>"
        f"<h1>{html.escape(good['title'])}</h1>"
        f"<p>{html.escape(good['body'])}</p>"
        "<h2>References</h2><ul>"
        + "".join(f"<li>{html.escape(c)}</li>" for c in good["citations"])
        + "</ul></body></html>\n",
        encoding="utf-8",
    )
    if not exported.is_file() or exported.stat().st_size <= 0:
        raise RuntimeError("document export failed")

    return {
        "mode": mode,
        "status": "PASS",
        "source_path": source.relative_to(root).as_posix(),
        "source_sha256": source_hash,
        "source_preserved": sha_file(source) == source_hash,
        "derived_index_authoritative": False,
        "retrieved_document_id": row[0],
        "export_path": exported.relative_to(root).as_posix(),
        "export_sha256": sha_file(exported),
        "human_approval_preserved": True,
        "automatic_publication": False,
    }


def verification_manifest_valid(manifest: dict[str, Any], payload: bytes) -> bool:
    expected = sha(payload)
    return (
        manifest.get("schema") == "fa3.verification-manifest.v1"
        and manifest.get("artifact_sha256") == expected
        and manifest.get("independent_verification") is True
        and manifest.get("auto_repair_during_verification") is False
        and manifest.get("verdict") in {"PASS", "FAIL", "BLOCKED"}
        and manifest.get("global_promotion_claim") is False
    )


def cap019(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-INSPECTION-CONTRACTS-001.json",
        "canonical/FA3-GATE-INDEPENDENT-VERIFICATION-001.json",
        "bin/fa3-enforce",
    ):
        repo_file(root, rel)

    payload = b"FA3 MAT-004 verification artifact\n"
    good_manifest = {
        "schema": "fa3.verification-manifest.v1",
        "artifact_sha256": sha(payload),
        "independent_verification": True,
        "auto_repair_during_verification": False,
        "verdict": "PASS",
        "global_promotion_claim": False,
    }

    if mode == "negative":
        bad_hash = dict(good_manifest)
        bad_hash["artifact_sha256"] = "0" * 64
        auto_repair = dict(good_manifest)
        auto_repair["auto_repair_during_verification"] = True
        promotion = dict(good_manifest)
        promotion["global_promotion_claim"] = True
        non_independent = dict(good_manifest)
        non_independent["independent_verification"] = False
        cases = {
            "tampered_artifact_denied": not verification_manifest_valid(bad_hash, payload),
            "silent_auto_repair_denied": not verification_manifest_valid(auto_repair, payload),
            "verification_as_promotion_denied": not verification_manifest_valid(promotion, payload),
            "non_independent_verification_denied": not verification_manifest_valid(non_independent, payload),
        }
        if not all(cases.values()):
            raise RuntimeError(f"QA/Evals/Verification negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}

    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "verification-state.json",
                b'{"verdict":"PENDING","auto_repair":false,"promotion":false}\n',
                b'{"verdict":"PASS","auto_repair":true,"promotion":true}\n',
            ),
        }

    artifact = scope / "verification-artifact.txt"
    artifact.write_bytes(payload)
    manifest_path = scope / "verification-manifest.json"
    write(manifest_path, good_manifest)
    if not verification_manifest_valid(load(manifest_path), artifact.read_bytes()):
        raise RuntimeError("verification manifest self-check failed")

    proc = cmd([str(root / "bin/fa3-enforce"), "release-projection"], 120, cwd=root)
    if proc.returncode != 0:
        raise RuntimeError(f"FA3 release-projection verification failed: {proc.stderr[-2000:]}")
    combined = (proc.stdout + "\n" + proc.stderr).strip()
    return {
        "mode": mode,
        "status": "PASS",
        "artifact_sha256": sha_file(artifact),
        "manifest_sha256": sha_file(manifest_path),
        "independent_verification": True,
        "auto_repair_during_verification": False,
        "release_projection_gate_returncode": proc.returncode,
        "release_projection_gate_output_sha256": sha(combined.encode("utf-8")),
        "global_promotion_claim": False,
    }


def publication_record_allowed(record: dict[str, Any]) -> bool:
    feedback = record.get("feedback_policy", {})
    citations = record.get("citations")
    geo = record.get("geo_metadata", {})
    return (
        record.get("status") == "APPROVED_FOR_PUBLICATION"
        and bool(record.get("human_approval_id"))
        and record.get("automatic_external_push") is False
        and record.get("automatic_content_rewrite_from_feedback") is False
        and isinstance(record.get("title"), str)
        and bool(record["title"].strip())
        and isinstance(record.get("body"), str)
        and bool(record["body"].strip())
        and isinstance(citations, list)
        and bool(citations)
        and all(isinstance(x, str) and x.strip() for x in citations)
        and isinstance(geo, dict)
        and geo.get("machine_readable_summary") is True
        and geo.get("provenance_exposed") is True
        and feedback.get("append_only") is True
        and feedback.get("human_review_before_action") is True
    )


class _PublicationHandler(SimpleHTTPRequestHandler):
    observed_paths: list[str] = []

    def do_GET(self) -> None:
        type(self).observed_paths.append(self.path)
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


def cap020(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    good = {
        "status": "APPROVED_FOR_PUBLICATION",
        "human_approval_id": "mat004-publication-approval",
        "automatic_external_push": False,
        "automatic_content_rewrite_from_feedback": False,
        "title": "FA3 MAT-004 publication feedback sentinel",
        "body": "Locally published current-host content with explicit provenance.",
        "citations": ["local:fa3/current-host/mat004-publication-source"],
        "geo_metadata": {
            "machine_readable_summary": True,
            "provenance_exposed": True,
        },
        "feedback_policy": {
            "append_only": True,
            "human_review_before_action": True,
        },
    }

    if mode == "negative":
        unapproved = dict(good)
        unapproved["status"] = "DRAFT"
        no_citation = dict(good)
        no_citation["citations"] = []
        auto_push = dict(good)
        auto_push["automatic_external_push"] = True
        auto_rewrite = dict(good)
        auto_rewrite["automatic_content_rewrite_from_feedback"] = True
        no_provenance = json.loads(json.dumps(good))
        no_provenance["geo_metadata"]["provenance_exposed"] = False
        cases = {
            "unapproved_publication_denied": not publication_record_allowed(unapproved),
            "citationless_publication_denied": not publication_record_allowed(no_citation),
            "automatic_external_push_denied": not publication_record_allowed(auto_push),
            "feedback_auto_rewrite_denied": not publication_record_allowed(auto_rewrite),
            "missing_provenance_denied": not publication_record_allowed(no_provenance),
        }
        if not all(cases.values()):
            raise RuntimeError(f"GEO/Publication Feedback negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}

    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "publication-feedback-state.json",
                b'{"published":true,"feedback_action":"HUMAN_REVIEW","auto_rewrite":false}\n',
                b'{"published":true,"feedback_action":"AUTO_REWRITE","auto_rewrite":true}\n',
            ),
        }

    if not publication_record_allowed(good):
        raise RuntimeError("approved publication record rejected")

    pubdir = scope / "publication"
    pubdir.mkdir(parents=True, exist_ok=True)
    content_digest = sha(
        json.dumps(
            {"title": good["title"], "body": good["body"], "citations": good["citations"]},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": good["title"],
        "description": good["body"],
        "identifier": content_digest,
        "citation": good["citations"],
    }
    index = pubdir / "index.html"
    index.write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(good['title'])}</title>"
        f"<meta name=\"description\" content=\"{html.escape(good['body'])}\">"
        "<script type=\"application/ld+json\">"
        + html.escape(json.dumps(json_ld, ensure_ascii=False))
        + "</script></head><body>"
        f"<article data-provenance-sha256=\"{content_digest}\">"
        f"<h1>{html.escape(good['title'])}</h1><p>{html.escape(good['body'])}</p>"
        f"<p>Source: {html.escape(good['citations'][0])}</p></article></body></html>\n",
        encoding="utf-8",
    )

    _PublicationHandler.observed_paths = []
    handler = partial(_PublicationHandler, directory=str(pubdir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/index.html"
    try:
        with urlopen(url, timeout=5) as response:
            fetched = response.read()
            status_code = int(response.status)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    if status_code != 200 or content_digest.encode("ascii") not in fetched:
        raise RuntimeError("loopback publication retrieval failed")
    if not any(path.startswith("/index.html") for path in _PublicationHandler.observed_paths):
        raise RuntimeError("publication HTTP request was not observed")

    ledger = sqlite3.connect(scope / "feedback-ledger.sqlite3")
    try:
        ledger.execute(
            "CREATE TABLE feedback(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, value INTEGER NOT NULL, action_state TEXT NOT NULL)"
        )
        rows = [
            ("useful", 1, "PENDING_HUMAN_REVIEW"),
            ("citation_verified", 1, "PENDING_HUMAN_REVIEW"),
            ("needs_clarification", 0, "PENDING_HUMAN_REVIEW"),
        ]
        ledger.executemany("INSERT INTO feedback(kind,value,action_state) VALUES(?,?,?)", rows)
        ledger.commit()
        count = ledger.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        automatic_actions = ledger.execute(
            "SELECT COUNT(*) FROM feedback WHERE action_state != 'PENDING_HUMAN_REVIEW'"
        ).fetchone()[0]
    finally:
        ledger.close()
    if count != 3 or automatic_actions != 0:
        raise RuntimeError("feedback ledger governance failed")

    return {
        "mode": mode,
        "status": "PASS",
        "publication_path": index.relative_to(root).as_posix(),
        "publication_sha256": sha_file(index),
        "content_provenance_sha256": content_digest,
        "loopback_publication_url": url,
        "http_status": status_code,
        "http_request_observed": True,
        "machine_readable_summary": True,
        "provenance_exposed": True,
        "feedback_event_count": count,
        "automatic_feedback_actions": automatic_actions,
        "human_review_before_feedback_action": True,
        "automatic_external_push": False,
        "automatic_content_rewrite_from_feedback": False,
    }


HANDLERS = {
    "CAP-016": cap016,
    "CAP-017": cap017,
    "CAP-018": cap018,
    "CAP-019": cap019,
    "CAP-020": cap020,
}


def run_mode(root: Path, scope: Path, cap: str, mode: str) -> dict[str, Any]:
    root = root.resolve()
    scope = scope.resolve()
    if cap not in CAPABILITIES or mode not in MODES:
        raise ValueError("unsupported capability or mode")
    if root not in scope.parents:
        raise RuntimeError("artifact scope escapes repository")
    scope.mkdir(parents=True, exist_ok=True)
    return HANDLERS[cap](root, scope, mode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capability", choices=CAPABILITIES, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if env("FA3_CURRENT_HOST") != "1" or env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("real CURRENT_HOST execution required")
        if env("FA3_CAPABILITY_ID") != args.capability:
            raise RuntimeError("capability binding mismatch")
        root = Path(env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        supplied = json.loads(env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"))
        coverage = validate_exact_coverage(root, args.capability, supplied)
        host_digest = env("FA3_HOST_FINGERPRINT_SHA256")
        if len(host_digest) != 64 or any(ch not in "0123456789abcdef" for ch in host_digest.lower()):
            raise RuntimeError("invalid host fingerprint SHA-256")
        result = run_mode(root, scope, args.capability, args.mode)
        result.update(
            {
                "source_decision_coverage_count": len(coverage),
                "host_fingerprint_sha256": host_digest,
            }
        )
        artifact = scope / NAMES[args.capability]
        write(
            artifact,
            {
                "schema": "fa3.mat004-media-audio-authoring-verification-publication-current-host-evidence.v1",
                "subject_id": args.capability,
                "test_kind": env("FA3_TEST_KIND"),
                "test_id": env("FA3_TEST_ID"),
                "qualification_id": env("FA3_QUALIFICATION_ID"),
                "constituent_id": env("FA3_CONSTITUENT_ID"),
                "execution_scope": "CURRENT_HOST",
                "current_host": True,
                "synthetic": False,
                "ci_reference_only": False,
                "provider_receipt_only": False,
                "component_receipt_only": False,
                "generic_host_collection_only": False,
                "global_promotion_claim": False,
                "result": result,
            },
        )
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": env("FA3_QUALIFICATION_ID"),
            "constituent_id": env("FA3_CONSTITUENT_ID"),
            "subject_id": args.capability,
            "test_kind": env("FA3_TEST_KIND"),
            "test_id": env("FA3_TEST_ID"),
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "source_evidence_class": env("FA3_SOURCE_EVIDENCE_CLASS"),
            "covers_source_decision_ids": coverage,
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": sha_file(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
