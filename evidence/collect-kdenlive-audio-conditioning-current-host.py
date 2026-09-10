#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def version(argv: list[str]) -> str | None:
    try:
        proc = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=15, shell=False)
        text = (proc.stdout or proc.stderr).strip().splitlines()
        return text[0] if text else None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect non-promotional current-host evidence for Kdenlive audio conditioning.")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--silero-model", type=Path)
    parser.add_argument("--expected-silero-sha256")
    parser.add_argument("--output", type=Path, default=Path("evidence/current-host/kdenlive-audio-conditioning.json"))
    args = parser.parse_args()

    tools = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe", "kdenlive", "python3")}
    checks = {
        "ffmpeg_present": bool(tools["ffmpeg"]),
        "ffprobe_present": bool(tools["ffprobe"]),
        "kdenlive_present": bool(tools["kdenlive"]),
        "python3_present": bool(tools["python3"]),
        "real_input_supplied": bool(args.input and args.input.is_file()),
        "silero_model_supplied": bool(args.silero_model and args.silero_model.is_file()),
        "silero_hash_verified": False,
    }
    observed_model_sha = None
    if checks["silero_model_supplied"]:
        observed_model_sha = sha256(args.silero_model)
        checks["silero_hash_verified"] = bool(
            args.expected_silero_sha256 and observed_model_sha == args.expected_silero_sha256.lower()
        )

    # This collector deliberately does not convert installation/preflight facts into a production PASS.
    # A real composite receipt must execute admitted Silero + GTCRN + LavaSR and conditional Demucs
    # against real media, then validate derived 48 kHz audio integrity and Kdenlive projection.
    report = {
        "schema": "fa3.kdenlive-audio-conditioning-current-host-evidence.v1",
        "gate_set_id": "FA3-KDENLIVE-AUDIO-CONDITIONING-GATESET-001",
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "tools": tools,
        "versions": {
            "ffmpeg": version([tools["ffmpeg"], "-version"]) if tools["ffmpeg"] else None,
            "kdenlive": version([tools["kdenlive"], "--version"]) if tools["kdenlive"] else None,
        },
        "checks": checks,
        "silero_model_sha256": observed_model_sha,
        "status": "PENDING_CURRENT_HOST",
        "production_admitted": False,
        "missing_production_evidence": [
            "real Silero inference receipt with admitted model hash",
            "real GTCRN enhancement receipt",
            "real LavaSR restoration/BWE receipt",
            "conditional Demucs receipt when mixed-dialogue path is tested",
            "composite duration/timebase/clipping/NaN/Inf/hash-lineage validation",
            "derived artifact import/projection receipt in Kdenlive",
        ],
        "document_only_promotion_forbidden": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
