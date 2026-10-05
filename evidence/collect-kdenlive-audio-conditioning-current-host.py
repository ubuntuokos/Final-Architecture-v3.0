#!/usr/bin/env python3
"""Collect current-host evidence for Kdenlive audio conditioning.

This collector is intentionally conservative. It never promotes production from
static configuration. Missing runtimes/models produce PENDING_CURRENT_HOST.
"""
from __future__ import annotations
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def present(executable: str) -> bool:
    return shutil.which(executable) is not None


def module_present(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    checks = {
        "kdenlive_executable": present("kdenlive"),
        "ffmpeg_executable": present("ffmpeg"),
        "ffprobe_executable": present("ffprobe"),
        "python_onnxruntime": module_present("onnxruntime"),
        "silero_adapter": (ROOT / "src/fa3_silero_vad_provider.py").is_file(),
        "gtcrn_adapter": (ROOT / "src/fa3_gtcrn_provider.py").is_file(),
        "lavasr_adapter": (ROOT / "src/fa3_lavasr_provider.py").is_file(),
        "demucs_enforcement": (ROOT / "canonical/demucs-enforcement.json").is_file(),
    }
    runtime_ready = all(checks.values())
    report = {
        "evidence_id": "FA3-EVIDENCE-KDENLIVE-AUDIO-CONDITIONING-CURRENT-HOST-001",
        "kind": "CURRENT_HOST_READINESS_PROBE",
        "checks": checks,
        "runtime_ready_for_real_e2e": runtime_ready,
        "production_status": "READY_FOR_REAL_E2E" if runtime_ready else "PENDING_CURRENT_HOST",
        "note": "Readiness is not a production PASS. Production promotion requires a real audio fixture through admitted Silero/GTCRN/LavaSR paths, conditional Demucs where selected, artifact hashes, duration/timebase, finite/clipping QC and a Kdenlive-derived-artifact receipt.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
