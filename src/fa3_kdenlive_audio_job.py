#!/usr/bin/env python3
"""Kdenlive Media Job -> FA3 typed audio-conditioning request adapter.

The adapter is intentionally provider-neutral. It compiles an editorial intent
into an AudioConditioningRequest JSON handoff. A downstream Central MCP adapter
may consume the request; this module never calls Silero, GTCRN, LavaSR or
Demucs directly and never edits a .kdenlive project file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_kdenlive_audio_pipeline import AudioConditioningRequest, plan_request
from fa3_silero_vad_provider import hash_file


KDENLIVE_PRESETS = {
    "dialogue-clean": "dialogue_clean",
    "mixed-dialogue": "mixed_dialogue_restore",
    "denoise": "noise_reduction",
    "restore-bandwidth": "speech_bandwidth_restore",
    "separate": "separate_vocals_music",
    "prepare-stt": "prepare_clean_audio_for_stt",
}


def compile_handoff(source: str, preset: str, output: str) -> dict[str, Any]:
    source_path = Path(source).expanduser().resolve()
    output_path = Path(output).expanduser().resolve()
    if preset not in KDENLIVE_PRESETS:
        raise ValueError(f"unsupported Kdenlive audio preset: {preset}")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path == output_path:
        raise ValueError("source in-place mutation is forbidden")
    if source_path.suffix.lower() == ".kdenlive" or output_path.suffix.lower() == ".kdenlive":
        raise ValueError("direct Kdenlive project XML mutation is forbidden")

    req = AudioConditioningRequest(
        source_artifact=str(source_path),
        source_hash=hash_file(source_path),
        operation=KDENLIVE_PRESETS[preset],
        timebase="SOURCE_MEDIA_TIMEBASE",
        output_sample_rate_hz=48000,
        output_channels=2,
    )
    plan = plan_request(req)
    return {
        "schema": "fa3.kdenlive-audio-conditioning-request.v1",
        "contract_id": "FA3-KDENLIVE-AUDIO-CONDITIONING-CONTRACTS-001",
        "editorial_client": "Kdenlive",
        "preset": preset,
        "request": {
            "source_artifact": req.source_artifact,
            "source_hash": req.source_hash,
            "operation": req.operation,
            "timebase": req.timebase,
            "output_policy": {
                "path": str(output_path),
                "sample_rate_hz": req.output_sample_rate_hz,
                "channels": req.output_channels,
                "source_in_place_mutation": False,
                "derived_artifact": True,
            },
        },
        "plan": plan.to_dict(),
        "dispatch": {
            "authority": "Central MCP",
            "provider_selection_owned_by_kdenlive": False,
            "accelerator_admission_authority": "Host Resource Broker",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile a Kdenlive FA3 audio-conditioning handoff")
    ap.add_argument("source")
    ap.add_argument("preset", choices=sorted(KDENLIVE_PRESETS))
    ap.add_argument("output")
    ap.add_argument("--request-out", help="write the typed handoff JSON here")
    args = ap.parse_args()

    handoff = compile_handoff(args.source, args.preset, args.output)
    payload = json.dumps(handoff, ensure_ascii=False, indent=2) + "\n"
    if args.request_out:
        request_path = Path(args.request_out).expanduser().resolve()
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
