#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROVIDER_ID = "FA3-PROVIDER-SILERO-VAD-001"
PROFILE_ID = "FA3-VOICE-ACTIVITY-DETECTION-001"
CONTRACT_ID = "FA3-VAD-CONTRACTS-001"
UPSTREAM_RELEASE = "v6.2.1"
UPSTREAM_REVISION = "7e30209a3e901f9842f81b225f3e93d8199902b1"
SUPPORTED_SAMPLE_RATES = {8000: 256, 16000: 512}
SUPPORTED_EXECUTION_PROVIDERS = {"CPUExecutionProvider", "CUDAExecutionProvider"}


class VadAdmissionDenied(RuntimeError):
    pass


class VadRuntimeDenied(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_hrb_lease(execution_provider: str, lease_path: str | None) -> dict[str, Any] | None:
    if execution_provider == "CPUExecutionProvider":
        return None
    if execution_provider != "CUDAExecutionProvider":
        raise VadAdmissionDenied(f"accelerator execution provider not admitted by this adapter: {execution_provider}")
    if not lease_path:
        raise VadAdmissionDenied("accelerator execution requires an HRB lease")
    lease = _load_json(Path(lease_path).expanduser().resolve())
    if lease.get("schema") != "AcceleratorExecutionLease@1":
        raise VadAdmissionDenied("HRB lease schema mismatch")
    if not str(lease.get("lease_id", "")).strip():
        raise VadAdmissionDenied("HRB lease_id missing")
    if not str(lease.get("gpu_uuid", "")).strip():
        raise VadAdmissionDenied("HRB gpu_uuid missing")
    ordinal = lease.get("device_ordinal")
    if not isinstance(ordinal, int) or ordinal < 0:
        raise VadAdmissionDenied("HRB device_ordinal missing or invalid")
    expires = lease.get("expires_at")
    if expires:
        dt = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
        if dt <= datetime.now(timezone.utc):
            raise VadAdmissionDenied("HRB lease expired")
    return lease


class SileroVadProvider:
    """Fail-closed ONNX adapter implementing the FA3 provider-neutral VAD projection."""

    def __init__(
        self,
        model_path: str | Path,
        expected_sha256: str,
        execution_provider: str = "CPUExecutionProvider",
        hrb_lease_path: str | None = None,
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_file():
            raise VadAdmissionDenied("Silero model file missing")
        expected = expected_sha256.strip().lower()
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise VadAdmissionDenied("expected model SHA-256 must be 64 hexadecimal characters")
        actual = sha256_file(self.model_path)
        if actual != expected:
            raise VadAdmissionDenied("Silero model SHA-256 mismatch")
        if execution_provider not in SUPPORTED_EXECUTION_PROVIDERS:
            raise VadAdmissionDenied(f"execution provider not admitted by this adapter: {execution_provider}")

        self.model_sha256 = actual
        self.execution_provider = execution_provider
        self.hrb_lease = validate_hrb_lease(execution_provider, hrb_lease_path)

        try:
            import numpy as np
            import onnxruntime as ort
        except Exception as exc:
            raise VadRuntimeDenied(f"required ONNX runtime dependency unavailable: {exc}") from exc
        self.np = np
        self.ort = ort

        available = ort.get_available_providers()
        if execution_provider not in available:
            raise VadAdmissionDenied(f"requested execution provider unavailable: {execution_provider}")

        session_options = ort.SessionOptions()
        provider_spec: list[Any]
        if execution_provider == "CPUExecutionProvider":
            provider_spec = ["CPUExecutionProvider"]
        else:
            # ORT normally permits implicit CPU fallback. FA3 forbids that for an
            # explicitly requested accelerator route, so disable it and bind the
            # CUDA device ordinal exclusively from the HRB lease.
            session_options.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
            ordinal = int(self.hrb_lease["device_ordinal"])
            provider_spec = [("CUDAExecutionProvider", {"device_id": ordinal})]

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=session_options,
            providers=provider_spec,
        )
        actual_providers = self.session.get_providers()
        if not actual_providers or actual_providers[0] != execution_provider:
            raise VadAdmissionDenied("execution-provider mismatch detected")
        if execution_provider == "CUDAExecutionProvider":
            configured = self.session.get_provider_options().get("CUDAExecutionProvider", {})
            if int(configured.get("device_id", -1)) != int(self.hrb_lease["device_ordinal"]):
                raise VadAdmissionDenied("CUDA device ordinal is not bound to HRB lease")

        names = {i.name for i in self.session.get_inputs()}
        if not {"input", "state", "sr"}.issubset(names):
            raise VadAdmissionDenied("unexpected Silero ONNX signature; expected input/state/sr")
        self.reset_state()

    def reset_state(self) -> None:
        self.state = self.np.zeros((2, 1, 128), dtype=self.np.float32)
        self._active_sample_rate: int | None = None

    def process_chunk(self, samples: Iterable[float], sample_rate: int) -> float:
        if sample_rate not in SUPPORTED_SAMPLE_RATES:
            raise VadAdmissionDenied(f"unsupported sample rate: {sample_rate}")
        if self._active_sample_rate not in (None, sample_rate):
            raise VadAdmissionDenied("sample-rate change requires explicit state reset")
        self._active_sample_rate = sample_rate
        window = SUPPORTED_SAMPLE_RATES[sample_rate]
        chunk = self.np.asarray(list(samples), dtype=self.np.float32)
        if chunk.ndim != 1 or len(chunk) != window:
            raise VadAdmissionDenied(
                f"streaming chunk must contain exactly {window} mono samples at {sample_rate} Hz"
            )
        out, state = self.session.run(
            None,
            {
                "input": chunk.reshape(1, -1),
                "state": self.state,
                "sr": self.np.asarray(sample_rate, dtype=self.np.int64),
            },
        )
        self.state = self.np.asarray(state, dtype=self.np.float32)
        return float(self.np.asarray(out).reshape(-1)[0])

    def process_audio(self, samples: Iterable[float], sample_rate: int) -> list[float]:
        if sample_rate not in SUPPORTED_SAMPLE_RATES:
            raise VadAdmissionDenied(f"unsupported sample rate: {sample_rate}")
        audio = self.np.asarray(list(samples), dtype=self.np.float32)
        if audio.ndim != 1 or len(audio) == 0:
            raise VadAdmissionDenied("audio must be a non-empty mono vector")
        self.reset_state()
        window = SUPPORTED_SAMPLE_RATES[sample_rate]
        probabilities: list[float] = []
        for offset in range(0, len(audio), window):
            chunk = audio[offset:offset + window]
            if len(chunk) < window:
                chunk = self.np.pad(chunk, (0, window - len(chunk)))
            probabilities.append(self.process_chunk(chunk, sample_rate))
        return probabilities

    def execution_evidence(self) -> dict[str, Any]:
        return {
            "provider_id": PROVIDER_ID,
            "profile_id": PROFILE_ID,
            "contract_id": CONTRACT_ID,
            "upstream_release": UPSTREAM_RELEASE,
            "upstream_revision": UPSTREAM_REVISION,
            "model_path": str(self.model_path),
            "model_sha256": self.model_sha256,
            "execution_provider": self.execution_provider,
            "session_execution_providers": self.session.get_providers(),
            "hrb_lease_id": None if self.hrb_lease is None else self.hrb_lease.get("lease_id"),
            "gpu_uuid": None if self.hrb_lease is None else self.hrb_lease.get("gpu_uuid"),
            "device_ordinal": None if self.hrb_lease is None else self.hrb_lease.get("device_ordinal"),
            "cpu_ep_fallback_disabled": self.execution_provider != "CPUExecutionProvider",
            "silent_fallback": False,
        }
