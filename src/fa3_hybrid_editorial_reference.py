#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any

PROFILE_ID = "FA3-HYBRID-EDITORIAL-001"
GATE_ID = "FA3-GATE-HYBRID-EDITORIAL-001"
CAPABILITY_COUNT = 143

REQUIRED_MEDIA_KEYS = {
    "frame_rate", "timebase", "duration", "resolution", "pixel_aspect",
    "color_primaries", "transfer_characteristic", "matrix_or_colorspace",
    "hdr_sdr_intent", "alpha_mode", "audio_sample_rate", "audio_channel_layout",
}
REQUIRED_SEQUENCE_KEYS = {
    "frame_numbering", "sequence_start", "sequence_end",
    "frame_duration_or_hold_semantics", "missing_frame_policy",
}
REQUIRED_PROVENANCE_KEYS = {
    "source_asset_ids", "operation", "provider_id", "parameters",
    "output_hash", "qc_status", "human_approval_id", "timeline_id",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def media_metadata_valid(metadata: dict[str, Any]) -> bool:
    return REQUIRED_MEDIA_KEYS.issubset(metadata) and all(
        metadata.get(key) not in (None, "") for key in REQUIRED_MEDIA_KEYS
    )


def image_sequence_valid(sequence: dict[str, Any]) -> bool:
    return (
        REQUIRED_SEQUENCE_KEYS.issubset(sequence)
        and sequence.get("missing_frame_policy") in {"FAIL_CLOSED", "EXPLICIT_HOLD"}
        and int(sequence.get("sequence_start", 1))
        <= int(sequence.get("sequence_end", 0))
    )


def ai_job_allowed(job: dict[str, Any]) -> bool:
    if job.get("via_central_mcp") is not True:
        return False
    if job.get("execution_mode") != "ASYNC":
        return False
    if job.get("cancellable") is not True:
        return False

    intent = job.get("intent")
    if (
        intent == "speech.transcribe"
        and job.get("delegated_profile") != "FA3-STT-MEDIA-001"
    ):
        return False
    if (
        intent == "audio.cleanup"
        and job.get("delegated_profile") != "FA3-AUDIO-SEPARATION-001"
    ):
        return False

    if job.get("local_accelerator") is True and not job.get("hrb_lease_id"):
        return False
    if job.get("destructive") is True and job.get("human_approved") is not True:
        return False
    return True


def external_direct_kdenlive_xml_mutation_allowed(enabled: bool) -> bool:
    return not enabled


def final_master_source_allowed(asset: dict[str, Any]) -> bool:
    return asset.get("quality_role") in {
        "ORIGINAL",
        "APPROVED_HIGH_QUALITY_DERIVATIVE",
    }


def roundtrip_valid(before: dict[str, Any], after: dict[str, Any]) -> bool:
    try:
        before_version = int(before.get("version", 0))
        after_version = int(after.get("version", 0))
    except (TypeError, ValueError):
        return False
    return (
        before.get("logical_asset_id") == after.get("logical_asset_id")
        and after_version > before_version
        and after.get("relinked_from_version") == before_version
        and bool(after.get("content_hash"))
    )


def provenance_valid(provenance: dict[str, Any]) -> bool:
    return (
        REQUIRED_PROVENANCE_KEYS.issubset(provenance)
        and provenance.get("qc_status") == "PASS"
        and bool(provenance.get("human_approval_id"))
        and bool(provenance.get("output_hash"))
    )


def run_reference_e2e(request: dict[str, Any] | None = None) -> dict[str, Any]:
    request = request or {}
    metadata = {
        "frame_rate": "24/1",
        "timebase": "1/24",
        "duration": "00:00:08:00",
        "resolution": "1920x1080",
        "pixel_aspect": "1/1",
        "color_primaries": "bt709",
        "transfer_characteristic": "bt709",
        "matrix_or_colorspace": "bt709",
        "hdr_sdr_intent": "SDR",
        "alpha_mode": "STRAIGHT",
        "audio_sample_rate": 48000,
        "audio_channel_layout": "stereo",
    }

    frame_hashes = [
        sha256_bytes(f"krita-frame-{index:04d}".encode("utf-8"))
        for index in range(1, 49)
    ]
    animation = {
        "logical_asset_id": "anim-shot-010",
        "version": 2,
        "provider_id": "FA3-PROVIDER-KRITA-001",
        "provider_local_source_format": ".kra",
        "canonical_projection": "ImageSequence",
        "canonical_format": "PNG_SEQUENCE",
        "quality_role": "APPROVED_HIGH_QUALITY_DERIVATIVE",
        "content_hash": sha256_bytes("".join(frame_hashes).encode("utf-8")),
        "metadata": metadata,
        "sequence": {
            "frame_numbering": "frame_%04d.png",
            "sequence_start": 1,
            "sequence_end": 48,
            "frame_duration_or_hold_semantics": "1 frame per image",
            "missing_frame_policy": "FAIL_CLOSED",
        },
    }
    live_action = {
        "logical_asset_id": "live-shot-020",
        "version": 1,
        "quality_role": "ORIGINAL",
        "content_hash": sha256_bytes(b"synthetic-live-action-original"),
        "metadata": metadata,
    }
    proxy = {
        "logical_asset_id": "live-shot-020-proxy",
        "version": 1,
        "quality_role": "PROXY",
        "content_hash": sha256_bytes(b"synthetic-live-action-proxy"),
        "metadata": metadata,
    }

    jobs = [
        {
            "intent": "media.scene.detect",
            "via_central_mcp": True,
            "execution_mode": "ASYNC",
            "cancellable": True,
            "local_accelerator": False,
            "destructive": False,
        },
        {
            "intent": "speech.transcribe",
            "via_central_mcp": True,
            "execution_mode": "ASYNC",
            "cancellable": True,
            "delegated_profile": "FA3-STT-MEDIA-001",
            "local_accelerator": True,
            "hrb_lease_id": "lease-stt-ref",
            "destructive": False,
        },
        {
            "intent": "audio.cleanup",
            "via_central_mcp": True,
            "execution_mode": "ASYNC",
            "cancellable": True,
            "delegated_profile": "FA3-AUDIO-SEPARATION-001",
            "local_accelerator": True,
            "hrb_lease_id": "lease-audio-ref",
            "destructive": False,
        },
        {
            "intent": "media.auto_edit.propose",
            "via_central_mcp": True,
            "execution_mode": "ASYNC",
            "cancellable": True,
            "local_accelerator": False,
            "destructive": True,
            "human_approved": True,
        },
    ]

    timeline = {
        "OTIO_SCHEMA": "Timeline.1",
        "canonical_ir": "OpenTimelineIO",
        "name": "FA3 Hybrid Editorial Reference",
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "Animation",
                    "asset_id": animation["logical_asset_id"],
                    "asset_version": animation["version"],
                },
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "Live Action",
                    "asset_id": live_action["logical_asset_id"],
                    "asset_version": live_action["version"],
                },
            ],
        },
        "analysis_proxy_id": proxy["logical_asset_id"],
        "final_source_ids": [
            animation["logical_asset_id"],
            live_action["logical_asset_id"],
        ],
    }

    kdenlive_projection = {
        "provider_id": "FA3-PROVIDER-KDENLIVE-001",
        "role": "HUMAN_FINISHING_NLE",
        "otio_imported": True,
        "direct_project_xml_mutation": False,
        "picture_lock": {
            "approval_id": "HITL-PICTURE-LOCK-001",
            "approved": True,
        },
    }

    before = {
        "logical_asset_id": "anim-shot-010",
        "version": 1,
        "content_hash": sha256_bytes(b"animation-v1"),
    }
    after = {
        "logical_asset_id": "anim-shot-010",
        "version": 2,
        "relinked_from_version": 1,
        "content_hash": animation["content_hash"],
    }

    provenance = {
        "source_asset_ids": [
            animation["logical_asset_id"],
            live_action["logical_asset_id"],
        ],
        "operation": "hybrid_editorial_reference_e2e",
        "provider_id": "FA3-REFERENCE-RUNTIME",
        "parameters": {
            "timeline_ir": "OpenTimelineIO",
            "request_name": request.get("name", "default"),
        },
        "output_hash": sha256_bytes(
            (animation["content_hash"] + live_action["content_hash"])
            .encode("utf-8")
        ),
        "qc_status": "PASS",
        "human_approval_id": "HITL-PICTURE-LOCK-001",
        "timeline_id": "otio-hybrid-reference-001",
    }

    checks = {
        "animation_metadata": media_metadata_valid(animation["metadata"]),
        "image_sequence_invariants": image_sequence_valid(animation["sequence"]),
        "live_action_metadata": media_metadata_valid(live_action["metadata"]),
        "proxy_not_final_source": not final_master_source_allowed(proxy),
        "approved_animation_final_source_allowed":
            final_master_source_allowed(animation),
        "original_final_source_allowed":
            final_master_source_allowed(live_action),
        "ai_jobs_delegated_async": all(ai_job_allowed(job) for job in jobs),
        "otio_canonical": (
            timeline["OTIO_SCHEMA"] == "Timeline.1"
            and timeline["canonical_ir"] == "OpenTimelineIO"
        ),
        "kdenlive_human_finishing": (
            kdenlive_projection["role"] == "HUMAN_FINISHING_NLE"
            and not kdenlive_projection["direct_project_xml_mutation"]
        ),
        "picture_lock_approved":
            kdenlive_projection["picture_lock"]["approved"] is True,
        "roundtrip_version_relink": roundtrip_valid(before, after),
        "provenance_complete": provenance_valid(provenance),
        "provider_local_kra_not_canonical": (
            animation["provider_local_source_format"] == ".kra"
            and animation["canonical_projection"] == "ImageSequence"
        ),
    }

    return {
        "schema": "fa3.hybrid-editorial-reference-e2e-report.v1",
        "profile_id": PROFILE_ID,
        "gate_id": GATE_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "artifacts": {
            "animation": animation,
            "live_action": live_action,
            "proxy": proxy,
        },
        "ai_jobs": jobs,
        "timeline": timeline,
        "kdenlive_projection": kdenlive_projection,
        "roundtrip": {"before": before, "after": after},
        "provenance": provenance,
        "current_host_krita_runtime_claim": False,
        "current_host_kdenlive_runtime_claim": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_reference_e2e(), indent=2, ensure_ascii=False))
