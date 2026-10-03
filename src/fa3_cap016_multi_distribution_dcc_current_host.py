#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fa3_application_installation_resolver import discover_registered_application
from fa3_mat004_media_authoring_verification_current_host import (
    VERDICT_SCHEMA,
    env,
    exact_rollback,
    media_job_allowed,
    repo_file,
    sha_file,
    validate_exact_coverage,
    write,
)

CAPABILITY = "CAP-016"
ARTIFACT_NAME = "cap016-multi-distribution-dcc-evidence.json"


def cmd(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
        check=False,
    )


def _positive(root: Path, scope: Path) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-NEURAL-MEDIA-EXECUTION-CONTRACTS-001.json",
        "canonical/contracts/FA3-KDENLIVE-EDITORIAL-CONTRACTS-001.json",
        "canonical/contracts/FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001.json",
        "canonical/profiles/FA3-VIDEO-001.json",
        "canonical/FA3-APPLICATION-INSTALLATION-REGISTRY-001.json",
    ):
        repo_file(root, rel)

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required")

    good_job = {
        "execution_scope": "CURRENT_HOST",
        "network_fetch": False,
        "human_approved": True,
        "overwrite_source": False,
        "output_inside_artifact_scope": True,
        "provider_fallback_unapproved": False,
    }
    if not media_job_allowed(good_job):
        raise RuntimeError("approved media job rejected")

    candidates = []
    for app_id in ("bforartists", "blender"):
        candidates.extend(discover_registered_application(root, app_id, perform_health_check=True))
    healthy = [row for row in candidates if row.get("health") == "HEALTHY"]
    if not healthy:
        raise RuntimeError("no healthy registered Bforartists/Blender installation instance")

    video = scope / "generated-media.mkv"
    render = cmd([
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=12:duration=1",
        "-c:v", "ffv1", str(video),
    ])
    if render.returncode != 0 or not video.is_file() or video.stat().st_size <= 0:
        raise RuntimeError(f"FFmpeg media generation failed: {render.stderr[-1200:]}")

    probe = cmd([
        ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)
    ], 30)
    if probe.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {probe.stderr[-1200:]}")
    payload = json.loads(probe.stdout)
    stream = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), None)
    if not isinstance(stream, dict) or int(stream.get("width", 0)) != 160 or int(stream.get("height", 0)) != 90:
        raise RuntimeError("generated media dimensions mismatch")

    return {
        "mode": "positive",
        "status": "PASS",
        "healthy_dcc_instance_count": len(healthy),
        "dcc_instances": candidates,
        "selection_semantics": "NO_RUNTIME_DEFAULT_NO_SILENT_FALLBACK_AT_LEAST_ONE_HEALTHY_FOR_QUALIFICATION",
        "media_path": video.relative_to(root).as_posix(),
        "media_sha256": sha_file(video),
        "media_bytes": video.stat().st_size,
        "video_codec": stream.get("codec_name"),
        "video_width": stream.get("width"),
        "video_height": stream.get("height"),
        "network_fetch": False,
        "source_overwritten": False,
        "unapproved_provider_fallback": False,
    }


def _negative() -> dict[str, Any]:
    good = {
        "execution_scope": "CURRENT_HOST",
        "network_fetch": False,
        "human_approved": True,
        "overwrite_source": False,
        "output_inside_artifact_scope": True,
        "provider_fallback_unapproved": False,
    }
    cases = {
        "network_fetch_denied": not media_job_allowed({**good, "network_fetch": True}),
        "unapproved_job_denied": not media_job_allowed({**good, "human_approved": False}),
        "source_overwrite_denied": not media_job_allowed({**good, "overwrite_source": True}),
        "artifact_scope_escape_denied": not media_job_allowed({**good, "output_inside_artifact_scope": False}),
        "unapproved_provider_fallback_denied": not media_job_allowed({**good, "provider_fallback_unapproved": True}),
    }
    if not all(cases.values()):
        raise RuntimeError(f"Media Generation/DCC negative matrix failed: {cases}")
    return {"mode": "negative", "status": "PASS", "cases": cases}


def _rollback(scope: Path) -> dict[str, Any]:
    return {
        "mode": "rollback",
        "status": "PASS",
        **exact_rollback(
            scope,
            "media-dcc-state.json",
            b'{"source_immutable":true,"provider_fallback":"DENY","state":"READY"}\n',
            b'{"source_immutable":false,"provider_fallback":"AUTO","state":"MUTATED"}\n',
        ),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--capability", choices=(CAPABILITY,), required=True)
    parser.add_argument("--mode", choices=("positive", "negative", "rollback"), required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()

    try:
        if env("FA3_CURRENT_HOST") != "1" or env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("real CURRENT_HOST execution required")
        if env("FA3_CAPABILITY_ID") != CAPABILITY:
            raise RuntimeError("capability binding mismatch")
        root = Path(env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        supplied = json.loads(env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"))
        coverage = validate_exact_coverage(root, CAPABILITY, supplied)
        host_digest = env("FA3_HOST_FINGERPRINT_SHA256")
        if len(host_digest) != 64:
            raise RuntimeError("invalid host fingerprint SHA-256")

        if args.mode == "positive":
            result = _positive(root, scope)
        elif args.mode == "negative":
            result = _negative()
        else:
            result = _rollback(scope)
        result.update({"source_decision_coverage_count": len(coverage), "host_fingerprint_sha256": host_digest})

        artifact = scope / ARTIFACT_NAME
        write(artifact, {
            "schema": "fa3.cap016-multi-distribution-dcc-current-host-evidence.v1",
            "subject_id": CAPABILITY,
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
        })
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": env("FA3_QUALIFICATION_ID"),
            "constituent_id": env("FA3_CONSTITUENT_ID"),
            "subject_id": CAPABILITY,
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
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
