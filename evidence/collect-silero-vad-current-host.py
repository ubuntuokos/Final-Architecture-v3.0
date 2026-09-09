#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
import wave
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    return rate, audio.tolist()


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect fail-closed FA3 current-host Silero VAD runtime evidence")
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--provider", default="CPUExecutionProvider")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output", default="evidence/current-host/FA3-SILERO-VAD-RUNTIME-CONFORMANCE-001.json")
    args = parser.parse_args()

    model = Path(args.model).resolve()
    audio_path = Path(args.input).resolve()
    output = Path(args.output).resolve()

    receipt = {
        "schema": "fa3.runtime-conformance-receipt.v1",
        "id": "FA3-SILERO-VAD-RUNTIME-CONFORMANCE-001",
        "provider_id": "FA3-PROVIDER-SILERO-VAD-001",
        "status": "FAIL",
        "runtime_promotion": false,
        "document_derived": false,
        "host": {"platform": platform.platform(), "python": platform.python_version()},
        "request": {
            "model": str(model),
            "input": str(audio_path),
            "execution_provider": args.provider,
            "threshold": args.threshold,
        },
        "checks": {},
        "errors": [],
    }

    try:
        if not model.is_file():
            raise RuntimeError("model file missing")
        if not audio_path.is_file():
            raise RuntimeError("input audio file missing")

        actual_hash = sha256(model)
        receipt["checks"]["model_sha256"] = actual_hash
        if actual_hash.lower() != args.expected_sha256.lower():
            raise RuntimeError("model SHA-256 mismatch")

        rate, audio_list = read_pcm16_mono(audio_path)
        receipt["checks"]["sample_rate_hz"] = rate
        receipt["checks"]["input_sha256"] = sha256(audio_path)

        try:
            import numpy as np
            import onnxruntime as ort
        except Exception as exc:
            raise RuntimeError(f"required runtime dependency unavailable: {exc}") from exc

        available = ort.get_available_providers()
        receipt["checks"]["available_execution_providers"] = available
        if args.provider not in available:
            raise RuntimeError(f"requested execution provider unavailable: {args.provider}")

        # No fallback provider is supplied: if the requested EP cannot execute the model,
        # session creation/inference fails closed instead of silently falling back.
        session = ort.InferenceSession(str(model), providers=[args.provider])
        actual_session_providers = session.get_providers()
        receipt["checks"]["session_execution_providers"] = actual_session_providers
        if not actual_session_providers or actual_session_providers[0] != args.provider:
            raise RuntimeError("execution-provider mismatch or fallback detected")

        inputs = {i.name: i for i in session.get_inputs()}
        receipt["checks"]["model_inputs"] = {name: {"shape": inp.shape, "type": inp.type} for name, inp in inputs.items()}

        if "input" not in inputs or "state" not in inputs or "sr" not in inputs:
            raise RuntimeError("unexpected Silero ONNX input signature; expected input/state/sr")

        audio = np.asarray(audio_list, dtype=np.float32)
        window = 256 if rate == 8000 else 512
        state = np.zeros((2, 1, 128), dtype=np.float32)
        sr = np.asarray(rate, dtype=np.int64)
        probabilities: list[float] = []

        started = time.perf_counter()
        for offset in range(0, len(audio), window):
            chunk = audio[offset:offset + window]
            if len(chunk) < window:
                chunk = np.pad(chunk, (0, window - len(chunk)))
            out, state = session.run(None, {"input": chunk.reshape(1, -1), "state": state, "sr": sr})
            probabilities.append(float(np.asarray(out).reshape(-1)[0]))
        elapsed = time.perf_counter() - started

        duration = len(audio) / float(rate) if len(audio) else 0.0
        if duration <= 0:
            raise RuntimeError("empty input audio")
        rtf = elapsed / duration
        speech_frames = sum(1 for p in probabilities if p >= args.threshold)

        receipt["checks"]["duration_seconds"] = duration
        receipt["checks"]["elapsed_seconds"] = elapsed
        receipt["checks"]["rtf"] = rtf
        receipt["checks"]["frames"] = len(probabilities)
        receipt["checks"]["speech_frames"] = speech_frames
        receipt["checks"]["probability_min"] = min(probabilities)
        receipt["checks"]["probability_max"] = max(probabilities)
        receipt["checks"]["state_continuity_exercised"] = True
        receipt["checks"]["implicit_resampling"] = False
        receipt["checks"]["network_acquisition"] = False
        receipt["status"] = "PASS"
        receipt["runtime_promotion"] = False
        receipt["note"] = "A single real-audio receipt is necessary but not sufficient for provider promotion; 8k, 16k, quality, concurrency and soak evidence remain required."
    except Exception as exc:
        receipt["errors"].append(str(exc))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
