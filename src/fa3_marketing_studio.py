from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol


class SecurityError(RuntimeError):
    pass


class ConsentError(SecurityError):
    pass


class LicenseAdmissionError(SecurityError):
    pass


class ResourceLeaseError(SecurityError):
    pass


@dataclass(frozen=True)
class LanguageValidationResult:
    locale: str
    confidence: float
    validator: str


@dataclass(frozen=True)
class GPULease:
    lease_id: str
    gpu_uuid: str
    cuda_ordinal: int
    current_host_attested: bool = False


class LanguageValidator(Protocol):
    def validate(self, text: str, expected_locale: str) -> LanguageValidationResult: ...


class HostResourceBroker(Protocol):
    def request_gpu_lease(self, *, purpose: str, min_vram_gib: int = 0) -> Mapping[str, Any]: ...
    def release_gpu_lease(self, lease_id: str) -> None: ...


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ConsentRegistry:
    """Exact, purpose-bound, revocable HMAC-SHA256 voice consent registry."""

    def __init__(self, path: str | os.PathLike[str], hmac_key: bytes):
        if not hmac_key:
            raise ValueError("consent HMAC key is required")
        self.path = Path(path)
        self.hmac_key = hmac_key

    def verify(self, consent_id: str, *, purpose: str, provider: str, model: str,
               speaker_wav_path: str | os.PathLike[str], now: datetime | None = None) -> Mapping[str, Any]:
        document = json.loads(self.path.read_text(encoding="utf-8"))
        receipts = document.get("receipts")
        if not isinstance(receipts, list):
            raise ConsentError("FAIL-CLOSED: malformed consent registry")
        receipt = next((r for r in receipts if r.get("consent_id") == consent_id), None)
        if receipt is None:
            raise ConsentError("FAIL-CLOSED: consent receipt not found")
        signature = receipt.get("signature")
        if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
            raise ConsentError("FAIL-CLOSED: consent signature missing or malformed")
        signed = dict(receipt)
        signed.pop("signature", None)
        expected = hmac.new(self.hmac_key, canonical_json(signed), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ConsentError("FAIL-CLOSED: consent receipt integrity failure")
        required = {"voice_owner_id", "audit_receipt_id", "valid_from", "expires_at",
                    "permitted_purposes", "allowed_providers", "allowed_models", "speaker_sha256"}
        missing = required.difference(receipt)
        if missing:
            raise ConsentError(f"FAIL-CLOSED: consent fields missing: {sorted(missing)}")
        instant = (now or utcnow()).astimezone(timezone.utc)
        if receipt.get("revoked_at"):
            raise ConsentError("FAIL-CLOSED: consent revoked")
        if instant < parse_utc(str(receipt["valid_from"])) or instant >= parse_utc(str(receipt["expires_at"])):
            raise ConsentError("FAIL-CLOSED: consent outside validity window")
        if purpose not in receipt["permitted_purposes"]:
            raise ConsentError("FAIL-CLOSED: purpose outside consent scope")
        if provider not in receipt["allowed_providers"] or model not in receipt["allowed_models"]:
            raise ConsentError("FAIL-CLOSED: provider/model outside consent scope")
        actual = sha256_file(speaker_wav_path)
        if not hmac.compare_digest(str(receipt["speaker_sha256"]).lower(), actual.lower()):
            raise ConsentError("FAIL-CLOSED: speaker WAV does not match consent")
        return receipt


class ProviderAdmissionGate:
    """Deny-by-default provider/model/voice license and intended-use gate."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def assert_allowed(self, *, provider: str, model: str, purpose: str, voice: str | None = None) -> Mapping[str, Any]:
        document = json.loads(self.path.read_text(encoding="utf-8"))
        rows = document.get("admissions")
        if not isinstance(rows, list):
            raise LicenseAdmissionError("FAIL-CLOSED: malformed provider admission registry")
        row = next((r for r in rows if r.get("provider") == provider and r.get("model") == model and r.get("voice") == voice), None)
        if row is None or row.get("status") != "APPROVED":
            raise LicenseAdmissionError("FAIL-CLOSED: provider/model/voice is not APPROVED")
        if purpose not in row.get("allowed_purposes", []):
            raise LicenseAdmissionError("FAIL-CLOSED: intended use is not admitted")
        digest = str(row.get("license_review_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise LicenseAdmissionError("FAIL-CLOSED: immutable license review evidence missing")
        return row


def validate_wav(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 44:
        raise SecurityError("FAIL-CLOSED: generated WAV missing or empty")
    try:
        with wave.open(str(path), "rb") as wav:
            channels, rate, frames, width = wav.getnchannels(), wav.getframerate(), wav.getnframes(), wav.getsampwidth()
            probe = wav.readframes(min(frames, rate))
    except (wave.Error, EOFError) as exc:
        raise SecurityError("FAIL-CLOSED: invalid PCM WAV") from exc
    if channels < 1 or rate < 8000 or frames < 1 or width < 1 or not probe or not any(probe):
        raise SecurityError("FAIL-CLOSED: invalid/silent WAV")
    return {"channels": channels, "sample_rate": rate, "frames": frames, "sample_width": width,
            "duration_seconds": frames / rate}


class EvidenceTrail:
    def __init__(self, directory: str | os.PathLike[str], pipeline: str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.pipeline = pipeline
        self.started = utcnow()
        self.id = f"{pipeline}-{self.started.strftime('%Y%m%dT%H%M%S.%fZ')}-{uuid.uuid4().hex[:8]}"
        self.events: list[dict[str, Any]] = []

    def event(self, state: str, **details: Any) -> None:
        self.events.append({"state": state, "timestamp": utcnow().isoformat().replace("+00:00", "Z"), **details})

    def write(self, payload: Mapping[str, Any]) -> Path:
        path = self.directory / f"{self.id}.evidence.json"
        body = {"schema": "fa3.hu-content-studio-evidence.v1", "pipeline": self.pipeline,
                "started_at": self.started.isoformat().replace("+00:00", "Z"), "events": self.events, **payload}
        path.write_text(json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        return path


class FA3HungarianMarketingStudio:
    XTTS_PROVIDER = "idiap/coqui-ai-TTS"
    XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
    PIPER_PROVIDER = "OHF-Voice/piper1-gpl"

    def __init__(self, *, consent_registry: ConsentRegistry, provider_gate: ProviderAdmissionGate,
                 resource_broker: HostResourceBroker, evidence_dir: str | os.PathLike[str],
                 language_validator: LanguageValidator | None = None, suppression: set[str] | None = None,
                 xtts_runner: Any | None = None, current_host_attestation: Mapping[str, Any] | None = None):
        self.consent_registry = consent_registry
        self.provider_gate = provider_gate
        self.resource_broker = resource_broker
        self.evidence_dir = Path(evidence_dir)
        self.language_validator = language_validator
        self.suppression = {v.casefold() for v in (suppression or set())}
        self.xtts_runner = xtts_runner or self._run_xtts_isolated
        self.current_host_attestation = dict(current_host_attestation or {})

    def assert_recipient_allowed(self, recipient: str) -> None:
        if recipient.strip().casefold() in self.suppression:
            raise PermissionError("FAIL-CLOSED: recipient is suppressed")

    def generate_native_hungarian_copy(self, campaign_context: Mapping[str, Any], engine_client: Any) -> str:
        if campaign_context.get("target_locale") != "hu-HU":
            raise ValueError("FAIL-CLOSED: only hu-HU is accepted")
        purpose = str(campaign_context.get("purpose", "")).strip()
        if not purpose or self.language_validator is None:
            raise SecurityError("FAIL-CLOSED: purpose and real Hungarian language validator are required")
        response = engine_client.chat.completions.create(
            model=str(campaign_context.get("model", "liquidai/lfm2.5-350m")),
            messages=[{"role": "user", "content": f"Írj professzionális, natív magyar marketing szöveget erre a célra: {purpose}."}],
            temperature=float(campaign_context.get("temperature", 0.7)),
        )
        text = str(response.choices[0].message.content).strip()
        result = self.language_validator.validate(text, "hu-HU")
        if not text or result.locale != "hu-HU" or result.confidence < 0.90:
            raise SecurityError("FAIL-CLOSED: Hungarian language validation failed")
        return text

    def execute_voice_cloning_pipeline(self, *, target_text: str, consent_id: str,
                                       speaker_wav_path: str, purpose: str = "VOICE_CLONE_MARKETING") -> str:
        if not target_text.strip():
            raise ValueError("FAIL-CLOSED: target text is empty")
        speaker = Path(speaker_wav_path)
        if not speaker.is_file():
            raise FileNotFoundError("FAIL-CLOSED: speaker reference WAV missing")
        trail = EvidenceTrail(self.evidence_dir, "xtts-voice-clone")
        trail.event("STARTED", consent_reference=consent_id)
        lease: GPULease | None = None
        output = self.evidence_dir / f"{trail.id}.wav"
        try:
            receipt = self.consent_registry.verify(consent_id, purpose=purpose, provider=self.XTTS_PROVIDER,
                                                   model=self.XTTS_MODEL, speaker_wav_path=speaker)
            trail.event("CONSENT_PASS", audit_receipt_id=receipt["audit_receipt_id"])
            admission = self.provider_gate.assert_allowed(provider=self.XTTS_PROVIDER, model=self.XTTS_MODEL,
                                                          purpose=purpose, voice=None)
            trail.event("LICENSE_PASS", license_review_sha256=admission["license_review_sha256"])
            lease = self._request_gpu_lease()
            trail.event("RESOURCE_LEASE_PASS", lease_id=lease.lease_id, gpu_uuid=lease.gpu_uuid)
            self.xtts_runner(target_text, str(speaker), str(output), lease.cuda_ordinal)
            trail.event("SYNTHESIS_PASS")
            audio = validate_wav(output)
            trail.event("AUDIO_VALIDATION_PASS", **audio)
            artifact_hash, speaker_hash = sha256_file(output), sha256_file(speaker)
            trail.event("PROVENANCE_PASS", artifact_sha256=artifact_hash)
            status = self._current_host_status(lease)
            trail.event("EVIDENCE_READY", pipeline_status=status)
            trail.write({"pipeline_status": status, "artifact_path": str(output), "artifact_sha256": artifact_hash,
                         "text_lineage_sha256": hashlib.sha256(target_text.encode()).hexdigest(),
                         "source_speaker_wav_sha256": speaker_hash, "consent_reference": consent_id,
                         "provider": self.XTTS_PROVIDER, "model": self.XTTS_MODEL, "lease_id": lease.lease_id,
                         "gpu_uuid": lease.gpu_uuid, "current_host_attestation_sha256": self.current_host_attestation.get("sha256")})
            return str(output)
        except Exception as exc:
            trail.event("FAILED", error_type=type(exc).__name__)
            trail.write({"pipeline_status": "FAIL_CLOSED", "consent_reference": consent_id,
                         "provider": self.XTTS_PROVIDER, "model": self.XTTS_MODEL})
            raise
        finally:
            if lease is not None:
                self.resource_broker.release_gpu_lease(lease.lease_id)

    def execute_generic_hungarian_tts(self, *, text: str, voice_model: str, model_path: str | os.PathLike[str],
                                      piper_binary: str = "piper", purpose: str = "GENERIC_HU_TTS") -> str:
        if not text.strip():
            raise ValueError("FAIL-CLOSED: TTS text empty")
        model = Path(model_path)
        if not model.is_file():
            raise FileNotFoundError("FAIL-CLOSED: Piper model missing")
        admission = self.provider_gate.assert_allowed(provider=self.PIPER_PROVIDER, model=voice_model,
                                                      purpose=purpose, voice=voice_model)
        trail = EvidenceTrail(self.evidence_dir, "piper-generic-hu-tts")
        trail.event("STARTED", provider=self.PIPER_PROVIDER, license_review_sha256=admission["license_review_sha256"])
        output = self.evidence_dir / f"{trail.id}.wav"
        completed = subprocess.run([piper_binary, "--model", str(model), "--output_file", str(output)],
                                   input=text, text=True, check=True, capture_output=True)
        trail.event("SYNTHESIS_PASS", returncode=completed.returncode)
        trail.event("AUDIO_VALIDATION_PASS", **validate_wav(output))
        artifact_hash = sha256_file(output)
        trail.event("PROVENANCE_PASS", artifact_sha256=artifact_hash)
        trail.write({"pipeline_status": "PROVIDER_EXECUTION_PASS", "capability": "GENERIC_HU_TTS",
                     "voice_cloning": False, "artifact_path": str(output), "artifact_sha256": artifact_hash,
                     "text_lineage_sha256": hashlib.sha256(text.encode()).hexdigest(),
                     "provider": self.PIPER_PROVIDER, "model": voice_model})
        return str(output)

    def _request_gpu_lease(self) -> GPULease:
        raw = self.resource_broker.request_gpu_lease(purpose="FA3 Hungarian voice cloning", min_vram_gib=4)
        try:
            lease = GPULease(str(raw["lease_id"]), str(raw["gpu_uuid"]), int(raw["cuda_ordinal"]),
                             bool(raw.get("current_host_attested", False)))
        except (KeyError, TypeError, ValueError) as exc:
            raise ResourceLeaseError("FAIL-CLOSED: invalid HRB GPU lease") from exc
        if not lease.lease_id or not lease.gpu_uuid or lease.cuda_ordinal < 0:
            raise ResourceLeaseError("FAIL-CLOSED: invalid HRB GPU lease")
        return lease

    def _current_host_status(self, lease: GPULease) -> str:
        digest = str(self.current_host_attestation.get("sha256", ""))
        if lease.current_host_attested and self.current_host_attestation.get("qualified") is True and re.fullmatch(r"[0-9a-f]{64}", digest):
            return "CURRENT_HOST_E2E_PASS"
        return "PENDING_CURRENT_HOST"

    @staticmethod
    def _run_xtts_isolated(text: str, speaker_wav: str, output_path: str, cuda_ordinal: int) -> None:
        worker = Path(__file__).with_name("fa3_xtts_worker.py")
        if not worker.is_file():
            raise FileNotFoundError("FAIL-CLOSED: XTTS worker missing")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(cuda_ordinal)
        subprocess.run([sys.executable, str(worker), "--speaker-wav", speaker_wav, "--output", output_path,
                        "--language", "hu"], input=text, text=True, check=True, env=env)
