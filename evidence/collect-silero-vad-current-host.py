#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_silero_vad_provider import SileroVadProvider, sha256_file


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_pcm16_mono(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if channels != 1:
        raise RuntimeError(f"input must be mono, got {channels} channels")
    if width != 2:
        raise RuntimeError(f"input must be PCM16 WAV, got sample width {width}")
    if rate not in (8000, 16000):
        raise RuntimeError(f"unsupported sample rate {rate}; only 8000/16000 are admitted")
    import numpy as np
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if len(audio) == 0:
        raise RuntimeError("empty input audio")
    return rate, audio.tolist()


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect fail-closed FA3 current-host Silero VAD runtime evidence")
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--provider", default="CPUExecutionProvider")
    parser.add_argument("--hrb-lease")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output", default="evidence/current-host/FA3-SILERO-VAD-RUNTIME-CONFORMANCE-001.json")
    args = parser.parse_args()

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and os.environ.get("FA3_CURRENT_HOST_RUNNER") != "1":
        raise SystemExit("CURRENT_HOST evidence is forbidden on non-designated GitHub runners")

    model = Path(args.model).expanduser().resolve()
    audio_path = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    receipt = {
        "schema": "fa3.runtime-conformance-receipt.v1",
        "id": "FA3-SILERO-VAD-RUNTIME-CONFORMANCE-001",
        "provider_id": "FA3-PROVIDER-SILERO-VAD-001",
        "status": "FAIL",
        "runtime_promotion": False,
        "document_derived": False,
        "collected_at": now(),
        "current_host": True,
        "host": {"platform": platform.platform(), "python": platform.python_version()},
        "request": {
            "model": str(model),
            "input": str(audio_path),
            "execution_provider": args.provider,
            "threshold": args.threshold,
            "hrb_lease": args.hrb_lease,
        },
        "checks": {},
        "errors": [],
    }

    try:
        if not audio_path.is_file():
            raise RuntimeError("input audio file missing")
        rate, audio = read_pcm16_mono(audio_path)
        receipt["checks"]["sample_rate_hz"] = rate
        receipt["checks"]["input_sha256"] = sha256_file(audio_path)
        receipt["checks"]["implicit_resampling"] = False
        receipt["checks"]["network_acquisition"] = False

        provider = SileroVadProvider(
            model_path=model,
            expected_sha256=args.expected_sha256,
            execution_provider=args.provider,
            hrb_lease_path=args.hrb_lease,
        )
        started = time.perf_counter()
        probabilities = provider.process_audio(audio, rate)
        elapsed = time.perf_counter() - started
        duration = len(audio) / float(rate)
        rtf = elapsed / duration
        speech_frames = sum(1 for p in probabilities if p >= args.threshold)

        receipt["checks"].update({
            "model_sha256": provider.model_sha256,
            "duration_seconds": duration,
            "elapsed_seconds": elapsed,
            "rtf": rtf,
            "frames": len(probabilities),
            "speech_frames": speech_frames,
            "probability_min": min(probabilities),
            "probability_max": max(probabilities),
            "state_continuity_exercised": True,
            "explicit_state_reset_exercised": True,
            "execution_evidence": provider.execution_evidence(),
        })
        receipt["status"] = "PASS"
        receipt["note"] = (
            "This real-audio receipt is necessary but not sufficient for provider promotion; "
            "both 8k and 16k plus quality, concurrency and soak evidence are required."
        )
    except Exception as exc:
        receipt["errors"].append(str(exc))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
