#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(argv: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    return {
        "argv": argv,
        "returncode": completed.returncode,
        "output": completed.stdout,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect build/static evidence for the FA3 Blackhole custom FFmpeg runtime."
    )
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    ffmpeg = args.ffmpeg.resolve()
    report: dict[str, Any] = {
        "schema": "fa3.blackhole-zerocopy-probe.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ffmpeg": str(ffmpeg),
        "status": "FAIL_CLOSED",
        "runtime_zero_copy_status": "PENDING_EXECUTABLE_EVIDENCE",
        "zero_copy_claim_scope": "FRAME_TO_TENSOR_ONLY",
        "end_to_end_gpu_resident_claim": False,
    }

    if not ffmpeg.is_file():
        report["failure"] = "ffmpeg binary missing"
    else:
        report["ffmpeg_sha256"] = sha256_file(ffmpeg)
        version = run([str(ffmpeg), "-hide_banner", "-version"])
        hwaccels = run([str(ffmpeg), "-hide_banner", "-hwaccels"])
        encoders = run([str(ffmpeg), "-hide_banner", "-encoders"])
        ldd = run(["ldd", str(ffmpeg)])
        report["probes"] = {
            "version": version,
            "hwaccels": hwaccels,
            "encoders": encoders,
            "ldd": ldd,
        }

        probe_text = "\n".join(
            item["output"] for item in (version, hwaccels, encoders, ldd)
        ).lower()
        static_checks = {
            "ffmpeg_executes": version["returncode"] == 0,
            "cuda_hwaccel_visible": "cuda" in hwaccels["output"].lower(),
            "nvenc_encoder_visible": "nvenc" in encoders["output"].lower(),
            "cuda_linkage_or_configuration_visible": "cuda" in probe_text,
            "onnxruntime_linkage_or_configuration_visible": "onnx" in probe_text,
        }
        report["static_checks"] = static_checks
        if all(static_checks.values()):
            report["status"] = "BUILD_PROBE_PASS_RUNTIME_PENDING"
        else:
            report["failure"] = "one or more static/build probes failed"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output)}))
    return 0 if report["status"] == "BUILD_PROBE_PASS_RUNTIME_PENDING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
