#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROVIDER_ID = "FA3-PROVIDER-GTCRN-001"
SAMPLE_RATE_HZ = 16000
CHANNELS = 1
N_FFT = 512
HOP_LENGTH = 256
ALLOWED_MODEL_NAMES = {"gtcrn.onnx", "gtcrn_simple.onnx"}
DENIED_SUFFIXES = {".tar", ".pt", ".pth", ".pkl", ".pickle", ".ckpt", ".bin"}
CACHE_SHAPES = {
    "conv_cache": (2, 1, 16, 16, 33),
    "tra_cache": (2, 3, 1, 1, 16),
    "inter_cache": (2, 1, 33, 16),
}

class AdmissionError(RuntimeError):
    pass

@dataclass(frozen=True)
class ExecutionSelection:
    requested: str
    selected: str
    accelerator: bool
    hrb_receipt: str | None

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def validate_model(path: str | Path, expected_sha256: str | None) -> str:
    p = Path(path)
    if p.suffix.lower() in DENIED_SUFFIXES:
        raise AdmissionError("dangerous serialized checkpoint forbidden for direct GTCRN runtime")
    if p.suffix.lower() != ".onnx" or p.name not in ALLOWED_MODEL_NAMES:
        raise AdmissionError("GTCRN direct runtime admits only allowlisted ONNX artifacts")
    if not p.is_file():
        raise AdmissionError("model artifact missing")
    if not expected_sha256 or len(expected_sha256) != 64:
        raise AdmissionError("quarantine SHA-256 required before runtime")
    actual = sha256_file(p)
    if actual.lower() != expected_sha256.lower():
        raise AdmissionError("model SHA-256 mismatch")
    return actual

def select_execution_provider(requested: str, available: Iterable[str], hrb_receipt: str | None = None) -> ExecutionSelection:
    av = set(available)
    if requested not in av:
        raise AdmissionError(f"requested execution provider unavailable: {requested}; silent fallback forbidden")
    accelerator = requested != "CPUExecutionProvider"
    if accelerator and not hrb_receipt:
        raise AdmissionError("accelerator execution requires Host Resource Broker admission receipt")
    return ExecutionSelection(requested, requested, accelerator, hrb_receipt)

def validate_audio_contract(sample_rate_hz: int, channels: int) -> None:
    if sample_rate_hz != SAMPLE_RATE_HZ:
        raise AdmissionError(f"GTCRN baseline requires explicit admitted resample to {SAMPLE_RATE_HZ} Hz")
    if channels != CHANNELS:
        raise AdmissionError("GTCRN baseline is mono; explicit admitted channel projection required")

def create_onnx_session(model_path: str | Path, expected_sha256: str, requested_provider: str = "CPUExecutionProvider", hrb_receipt: str | None = None):
    model_sha256 = validate_model(model_path, expected_sha256)
    try:
        import onnxruntime as ort
    except Exception as e:
        raise AdmissionError("onnxruntime unavailable in isolated GTCRN runtime") from e
    selection = select_execution_provider(requested_provider, ort.get_available_providers(), hrb_receipt)
    session = ort.InferenceSession(str(model_path), providers=[selection.selected])
    actual = session.get_providers()
    if not actual or actual[0] != selection.selected:
        raise AdmissionError("runtime did not honor requested execution provider")
    return session, selection, model_sha256

def run_spectral_frames(session: Any, frames: Any):
    """Run admitted GTCRN ONNX spectral frames shaped [1,257,T,2]. NumPy is imported lazily."""
    try:
        import numpy as np
    except Exception as e:
        raise AdmissionError("numpy unavailable in isolated GTCRN runtime") from e
    arr = np.asarray(frames, dtype=np.float32)
    if arr.ndim != 4 or arr.shape[0] != 1 or arr.shape[1] != 257 or arr.shape[3] != 2:
        raise AdmissionError("invalid GTCRN spectral tensor shape")
    conv = np.zeros(CACHE_SHAPES["conv_cache"], dtype=np.float32)
    tra = np.zeros(CACHE_SHAPES["tra_cache"], dtype=np.float32)
    inter = np.zeros(CACHE_SHAPES["inter_cache"], dtype=np.float32)
    outs = []
    t0 = time.perf_counter()
    for i in range(arr.shape[2]):
        out, conv, tra, inter = session.run([], {"mix": arr[:, :, i:i+1, :], "conv_cache": conv, "tra_cache": tra, "inter_cache": inter})
        outs.append(out)
    elapsed = time.perf_counter() - t0
    y = np.concatenate(outs, axis=2) if outs else np.empty_like(arr)
    if not np.isfinite(y).all():
        raise AdmissionError("non-finite GTCRN output")
    audio_seconds = max(arr.shape[2] * HOP_LENGTH / SAMPLE_RATE_HZ, 1e-12)
    return y, {"elapsed_seconds": elapsed, "audio_seconds": audio_seconds, "rtf": elapsed / audio_seconds, "frames": arr.shape[2]}

def reference_policy_conformance() -> dict[str, Any]:
    checks = []
    def ok(name, fn):
        try:
            fn()
            checks.append({"name": name, "result": "PASS"})
        except Exception as e:
            checks.append({"name": name, "result": "FAIL", "error": str(e)})
    ok("cpu-explicit", lambda: select_execution_provider("CPUExecutionProvider", ["CPUExecutionProvider"]))
    def no_silent():
        try:
            select_execution_provider("CUDAExecutionProvider", ["CPUExecutionProvider"])
        except AdmissionError:
            return
        raise AssertionError("silent fallback accepted")
    ok("no-silent-fallback", no_silent)
    def accelerator_guard():
        try:
            select_execution_provider("CUDAExecutionProvider", ["CUDAExecutionProvider"])
        except AdmissionError:
            return
        raise AssertionError("accelerator without HRB receipt accepted")
    ok("accelerator-hrb-guard", accelerator_guard)
    ok("accelerator-with-receipt", lambda: select_execution_provider("CUDAExecutionProvider", ["CUDAExecutionProvider"], "HRB-TEST-RECEIPT"))
    ok("16k-mono-contract", lambda: validate_audio_contract(16000, 1))
    def reject_rate():
        try:
            validate_audio_contract(48000, 1)
        except AdmissionError:
            return
        raise AssertionError("wrong sample rate accepted")
    ok("wrong-rate-rejected", reject_rate)
    result = "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL"
    return {"schema": "fa3.gtcrn-provider-reference-conformance.v1", "provider_id": PROVIDER_ID, "result": result, "checks": checks, "current_host_runtime_promoted": False}

def waveform_to_spectral_frames(waveform: Any):
    try:
        import numpy as np
    except Exception as e:
        raise AdmissionError("numpy unavailable in isolated GTCRN runtime") from e
    x = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if x.size == 0 or not np.isfinite(x).all():
        raise AdmissionError("input waveform empty or non-finite")
    pad = N_FFT // 2
    mode = "reflect" if x.size > 1 else "constant"
    xp = np.pad(x, (pad, pad), mode=mode)
    if xp.size < N_FFT:
        xp = np.pad(xp, (0, N_FFT - xp.size))
    window = np.sqrt(np.hanning(N_FFT + 1)[:-1]).astype(np.float32)
    count = 1 + (xp.size - N_FFT) // HOP_LENGTH
    spec = np.empty((1, N_FFT // 2 + 1, count, 2), dtype=np.float32)
    for i in range(count):
        frame = xp[i * HOP_LENGTH:i * HOP_LENGTH + N_FFT] * window
        z = np.fft.rfft(frame, n=N_FFT)
        spec[0, :, i, 0] = z.real
        spec[0, :, i, 1] = z.imag
    return spec, x.size

def spectral_frames_to_waveform(frames: Any, original_samples: int):
    try:
        import numpy as np
    except Exception as e:
        raise AdmissionError("numpy unavailable in isolated GTCRN runtime") from e
    s = np.asarray(frames, dtype=np.float32)
    if s.ndim != 4 or s.shape[0] != 1 or s.shape[1] != 257 or s.shape[3] != 2:
        raise AdmissionError("invalid GTCRN spectral output shape")
    window = np.sqrt(np.hanning(N_FFT + 1)[:-1]).astype(np.float32)
    total = (s.shape[2] - 1) * HOP_LENGTH + N_FFT
    y = np.zeros(total, dtype=np.float64)
    norm = np.zeros(total, dtype=np.float64)
    for i in range(s.shape[2]):
        z = s[0, :, i, 0].astype(np.float64) + 1j * s[0, :, i, 1].astype(np.float64)
        frame = np.fft.irfft(z, n=N_FFT) * window
        pos = i * HOP_LENGTH
        y[pos:pos + N_FFT] += frame
        norm[pos:pos + N_FFT] += window.astype(np.float64) ** 2
    nz = norm > 1e-10
    y[nz] /= norm[nz]
    pad = N_FFT // 2
    y = y[pad:pad + original_samples].astype(np.float32)
    if y.size != original_samples or not np.isfinite(y).all():
        raise AdmissionError("invalid reconstructed GTCRN waveform")
    return y

def enhance_waveform(session: Any, waveform: Any, sample_rate_hz: int = SAMPLE_RATE_HZ, channels: int = 1):
    validate_audio_contract(sample_rate_hz, channels)
    spec, n = waveform_to_spectral_frames(waveform)
    out, perf = run_spectral_frames(session, spec)
    y = spectral_frames_to_waveform(out, n)
    import numpy as np
    perf.update({"sample_rate_hz": sample_rate_hz, "channels": channels, "samples": int(n), "peak_abs": float(np.max(np.abs(y))) if y.size else 0.0, "clipped_samples": int(np.count_nonzero(np.abs(y) > 1.0)), "finite": bool(np.isfinite(y).all())})
    return y, perf

if __name__ == "__main__":
    print(json.dumps(reference_policy_conformance(), indent=2))
