#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROVIDER_ID = "FA3-PROVIDER-LAVASR-001"
SOURCE_REVISION = "33ac040892519c1bb4aed7eb32e79af51cc29e2a"
RUNTIME_REVISION = "1a979b80d760f00d973b13d530fdd8da51be160b"
NATIVE_SAMPLE_RATE_HZ = 16000
OUTPUT_SAMPLE_RATE_HZ = 48000
NATIVE_CHANNELS = 1
EXTERNAL_MIN_SAMPLE_RATE_HZ = 8000
EXTERNAL_MAX_SAMPLE_RATE_HZ = 48000

MODEL_ASSETS = {
    "denoiser_core_legacy_fixed63.onnx": (1815317, "8afa7f4db9f356f7bfb575bb207d8673a728a7baf6773e0b10226a5e15687f2a"),
    "enhancer_backbone.onnx": (190195, "841e96d261dffdf1dc974f3d29e2cfcf1b16fd0b358749c1ace0bbfa1d4c8ddd"),
    "enhancer_backbone.onnx.data": (51773440, "a125a4ede7cfdd1073d906a3cadf2171a30be6a40f296ad28772e0ba258de8c5"),
    "enhancer_spec_head.onnx": (7484, "f66fd164c55fd1b07e5cea5e687c71522b192f452691128fd7ae4e6b26dbc683"),
    "enhancer_spec_head.onnx.data": (4263936, "b855e309b027af9aa75285b97b345571b6bd695a30fde434d06c979d83885fd6"),
}
DENIED_SUFFIXES = {".bin", ".pt", ".pth", ".pkl", ".pickle", ".ckpt", ".tar"}
RUNTIME_REQUIRED_FILES = {"lavasr_core.py", "config.yaml"}


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
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_runtime_checkout(runtime_dir: str | Path) -> dict[str, Any]:
    root = Path(runtime_dir)
    if not root.is_dir():
        raise AdmissionError("pinned LavaSR ONNX runtime checkout missing")
    missing = sorted(name for name in RUNTIME_REQUIRED_FILES if not (root / name).is_file())
    if missing:
        raise AdmissionError(f"runtime checkout incomplete: {', '.join(missing)}")
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception as exc:
        raise AdmissionError("runtime checkout identity cannot be verified with git") from exc
    if head != RUNTIME_REVISION:
        raise AdmissionError(f"LavaSR ONNX runtime revision mismatch: {head}")
    if dirty:
        raise AdmissionError("LavaSR ONNX runtime checkout has uncommitted drift")
    return {"revision": head, "clean": True}


def reject_dangerous_source_artifact(path: str | Path) -> None:
    suffix = Path(path).suffix.lower()
    if suffix in DENIED_SUFFIXES:
        raise AdmissionError("dangerous serialized LavaSR source checkpoint forbidden for direct runtime")


def validate_model_bundle(model_dir: str | Path) -> dict[str, dict[str, Any]]:
    root = Path(model_dir)
    if not root.is_dir():
        raise AdmissionError("LavaSR ONNX model bundle directory missing")
    for child in root.iterdir():
        if child.is_file() and child.suffix.lower() in DENIED_SUFFIXES:
            raise AdmissionError(f"dangerous serialized artifact present in runtime bundle: {child.name}")
    verified: dict[str, dict[str, Any]] = {}
    for name, (expected_size, expected_hash) in MODEL_ASSETS.items():
        path = root / name
        if not path.is_file():
            raise AdmissionError(f"required LavaSR ONNX asset missing: {name}")
        size = path.stat().st_size
        if size != expected_size:
            raise AdmissionError(f"LavaSR ONNX asset size mismatch: {name}")
        actual = sha256_file(path)
        if actual.lower() != expected_hash.lower():
            raise AdmissionError(f"LavaSR ONNX asset SHA-256 mismatch: {name}")
        verified[name] = {"size_bytes": size, "sha256": actual}
    return verified


def select_execution_provider(
    requested: str,
    available: Iterable[str],
    hrb_receipt: str | None = None,
) -> ExecutionSelection:
    available_set = set(available)
    if requested not in available_set:
        raise AdmissionError(f"requested execution provider unavailable: {requested}; silent fallback forbidden")
    accelerator = requested != "CPUExecutionProvider"
    if accelerator and not hrb_receipt:
        raise AdmissionError("accelerator execution requires Host Resource Broker admission receipt")
    return ExecutionSelection(requested=requested, selected=requested, accelerator=accelerator, hrb_receipt=hrb_receipt)


def validate_session_provider(session: Any, requested: str, accelerator: bool) -> list[str]:
    providers = list(session.get_providers())
    if not providers or providers[0] != requested:
        raise AdmissionError(f"ONNX Runtime did not honor requested provider: {requested}")
    if accelerator and "CPUExecutionProvider" in providers:
        raise AdmissionError("accelerator session exposes CPU fallback; fail-closed FA3 promotion forbids silent fallback")
    return providers


def validate_audio_contract(
    input_sample_rate_hz: int,
    channels: int,
    explicit_resample_projection: bool = False,
    explicit_channel_projection: bool = False,
) -> None:
    if not (EXTERNAL_MIN_SAMPLE_RATE_HZ <= int(input_sample_rate_hz) <= EXTERNAL_MAX_SAMPLE_RATE_HZ):
        raise AdmissionError("input sample rate outside admitted 8-48 kHz contract range")
    if int(input_sample_rate_hz) != NATIVE_SAMPLE_RATE_HZ and not explicit_resample_projection:
        raise AdmissionError("non-16 kHz input requires explicit admitted resample projection")
    if int(channels) != NATIVE_CHANNELS and not explicit_channel_projection:
        raise AdmissionError("non-mono input requires explicit admitted channel projection")


def validate_denoise_policy(
    denoise_requested: bool,
    input_already_denoised: bool,
    allow_cascaded_denoise: bool = False,
) -> None:
    if denoise_requested and input_already_denoised and not allow_cascaded_denoise:
        raise AdmissionError("implicit double denoise forbidden; explicit cascaded-denoise policy required")


def validate_output_integrity(
    output: Any,
    input_duration_seconds: float,
    output_sample_rate_hz: int = OUTPUT_SAMPLE_RATE_HZ,
    tolerance_seconds: float = 0.025,
) -> dict[str, Any]:
    try:
        import numpy as np
    except Exception as exc:
        raise AdmissionError("numpy unavailable for LavaSR output-integrity validation") from exc
    y = np.asarray(output, dtype=np.float32).reshape(-1)
    if y.size == 0 or not np.isfinite(y).all():
        raise AdmissionError("LavaSR output is empty or non-finite")
    output_duration = y.size / float(output_sample_rate_hz)
    duration_error = abs(output_duration - float(input_duration_seconds))
    if duration_error > tolerance_seconds:
        raise AdmissionError(
            f"LavaSR duration/padding integrity failure: error={duration_error:.6f}s exceeds {tolerance_seconds:.6f}s"
        )
    peak = float(np.max(np.abs(y)))
    clipped = int(np.count_nonzero(np.abs(y) > 1.0))
    return {
        "finite": True,
        "samples": int(y.size),
        "output_sample_rate_hz": int(output_sample_rate_hz),
        "output_duration_seconds": output_duration,
        "input_duration_seconds": float(input_duration_seconds),
        "duration_error_seconds": duration_error,
        "peak_abs": peak,
        "clipped_samples": clipped,
    }


def reference_policy_conformance() -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def record(name: str, fn) -> None:
        try:
            fn()
            checks.append({"name": name, "result": "PASS"})
        except Exception as exc:
            checks.append({"name": name, "result": "FAIL", "error": str(exc)})

    record("cpu-explicit", lambda: select_execution_provider("CPUExecutionProvider", ["CPUExecutionProvider"]))

    def no_silent_fallback() -> None:
        try:
            select_execution_provider("CUDAExecutionProvider", ["CPUExecutionProvider"])
        except AdmissionError:
            return
        raise AssertionError("silent execution-provider fallback accepted")

    record("no-silent-fallback", no_silent_fallback)

    def accelerator_guard() -> None:
        try:
            select_execution_provider("CUDAExecutionProvider", ["CUDAExecutionProvider"])
        except AdmissionError:
            return
        raise AssertionError("accelerator without HRB receipt accepted")

    record("accelerator-hrb-guard", accelerator_guard)
    record(
        "accelerator-with-receipt",
        lambda: select_execution_provider("CUDAExecutionProvider", ["CUDAExecutionProvider"], "HRB-TEST-RECEIPT"),
    )
    record("16k-mono-native-contract", lambda: validate_audio_contract(16000, 1))
    record("8k-explicit-resample-projection", lambda: validate_audio_contract(8000, 1, explicit_resample_projection=True))
    record("48k-explicit-resample-projection", lambda: validate_audio_contract(48000, 1, explicit_resample_projection=True))

    def reject_unprojected_rate() -> None:
        try:
            validate_audio_contract(48000, 1)
        except AdmissionError:
            return
        raise AssertionError("non-native sample rate accepted without explicit projection")

    record("unprojected-rate-rejected", reject_unprojected_rate)

    def reject_double_denoise() -> None:
        try:
            validate_denoise_policy(True, True, False)
        except AdmissionError:
            return
        raise AssertionError("implicit double denoise accepted")

    record("implicit-double-denoise-rejected", reject_double_denoise)
    record("explicit-cascaded-denoise", lambda: validate_denoise_policy(True, True, True))

    def reject_pickle() -> None:
        try:
            reject_dangerous_source_artifact("pytorch_model.bin")
        except AdmissionError:
            return
        raise AssertionError("dangerous source checkpoint accepted")

    record("dangerous-source-checkpoint-rejected", reject_pickle)
    result = "PASS" if all(check["result"] == "PASS" for check in checks) else "FAIL"
    return {
        "schema": "fa3.lavasr-provider-reference-conformance.v1",
        "provider_id": PROVIDER_ID,
        "result": result,
        "checks": checks,
        "current_host_runtime_promoted": False,
    }


if __name__ == "__main__":
    print(json.dumps(reference_policy_conformance(), indent=2))
