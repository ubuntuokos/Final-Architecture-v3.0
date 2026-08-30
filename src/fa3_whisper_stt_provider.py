#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PROVIDER_ID = "FA3-PROVIDER-WHISPER-001"
PROVIDER_VERSION = "1.0.0"
PROFILE_ID = "FA3-STT-MEDIA-001"
REQUEST_SCHEMA = "fa3.stt-media-request.v1"
RESULT_SCHEMA = "fa3.stt-media-result.v1"
MODEL_ALLOWLIST_ID = "FA3-WHISPER-MODEL-ALLOWLIST-001"
PINNED_WHISPER_VERSION = "20250625"
HRB_AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
HRB_PROFILE_ID = "FA3-HOST-RESOURCE-BROKER-001"
HRB_LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
DEFAULT_HRB_VERIFY_COMMAND = (
    "/usr/local/bin/fa3-host-resource-broker",
    "validate-lease",
    "{lease}",
)

class ProviderError(RuntimeError):
    pass

class PolicyDenied(ProviderError):
    pass

class ModelTrustDenied(ProviderError):
    pass

class HRBLeaseDenied(ProviderError):
    pass

class ExecutionFailed(ProviderError):
    pass

@dataclass(frozen=True)
class RuntimeOptions:
    model: str = "turbo"
    device: str = "cpu"
    offline: bool = True
    model_cache: str | None = None
    word_timestamps: bool = True
    hrb_lease_path: str | None = None
    hrb_verify_command: tuple[str, ...] = DEFAULT_HRB_VERIFY_COMMAND

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _write_json(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()

def load_allowlist(root: Path) -> dict[str, Any]:
    path = root / "canonical/FA3-WHISPER-MODEL-ALLOWLIST-001.json"
    data = _read_json(path)
    if data.get("id") != MODEL_ALLOWLIST_ID:
        raise ModelTrustDenied("Whisper model allowlist identity mismatch")
    if data.get("policy") != "ALLOWLIST_ONLY_FAIL_CLOSED":
        raise ModelTrustDenied("Whisper model allowlist is not fail-closed")
    return data

def _device_is_cuda(device: str) -> bool:
    return bool(re.fullmatch(r"cuda:\d+", device))

def validate_provider_request(
    request: dict[str, Any],
    options: RuntimeOptions,
    allowlist: dict[str, Any],
    *,
    require_existing_audio: bool = True,
) -> dict[str, Any]:
    findings: list[str] = []
    if request.get("schema") != REQUEST_SCHEMA:
        findings.append("REQUEST_SCHEMA_MISMATCH")
    if request.get("required_result_schema") != RESULT_SCHEMA:
        findings.append("RESULT_SCHEMA_MISMATCH")
    if request.get("time_origin") != "RELATIVE_ZERO":
        findings.append("TIME_ORIGIN_MUST_BE_RELATIVE_ZERO")
    if str(request.get("task", "transcribe")) != "transcribe":
        findings.append("TRANSLATION_NOT_STT_SURFACE")
    if not str(request.get("audio_hash", "")):
        findings.append("AUDIO_HASH_REQUIRED")
    if not str(request.get("audio_path", "")):
        findings.append("AUDIO_PATH_REQUIRED")
    if not str(request.get("language", "")):
        findings.append("LANGUAGE_REQUIRED")
    model = allowlist.get("models", {}).get(options.model)
    if model is None:
        findings.append("MODEL_NOT_ALLOWLISTED")
    if options.device != "cpu" and not _device_is_cuda(options.device):
        findings.append("DEVICE_MUST_BE_CPU_OR_EXPLICIT_CUDA_ORDINAL")
    if _device_is_cuda(options.device):
        if not options.hrb_lease_path:
            findings.append("CUDA_REQUIRES_HRB_LEASE")
        if not options.hrb_verify_command:
            findings.append("CUDA_REQUIRES_HRB_VERIFIER")
    if require_existing_audio and request.get("audio_path"):
        audio = Path(str(request["audio_path"])).expanduser()
        if not audio.is_file():
            findings.append("AUDIO_FILE_NOT_FOUND")
        elif str(request.get("audio_hash")) != sha256_file(audio):
            findings.append("AUDIO_HASH_MISMATCH")
    if findings:
        raise PolicyDenied(";".join(findings))
    assert model is not None
    return model

def validate_audio_contract(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    try:
        with wave.open(str(p), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            compression = wav.getcomptype()
            frames = wav.getnframes()
    except (wave.Error, EOFError) as exc:
        raise PolicyDenied("STT_INPUT_MUST_BE_PCM_WAV") from exc
    findings: list[str] = []
    if channels != 1:
        findings.append("STT_INPUT_MUST_BE_MONO")
    if sample_rate != 16000:
        findings.append("STT_INPUT_MUST_BE_16KHZ")
    if sample_width != 2:
        findings.append("STT_INPUT_MUST_BE_PCM16")
    if compression != "NONE":
        findings.append("STT_INPUT_MUST_BE_UNCOMPRESSED_PCM")
    if frames <= 0:
        findings.append("STT_INPUT_EMPTY")
    if findings:
        raise PolicyDenied(";".join(findings))
    return {
        "path": str(p),
        "sha256": sha256_file(p),
        "samplerate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "encoding": "PCM_S16LE",
        "frames": frames,
    }

def resolve_model_cache(options: RuntimeOptions) -> Path:
    if options.model_cache:
        return Path(options.model_cache).expanduser().resolve()
    import os
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
    return (base / "whisper").resolve()

def validate_cached_model(cache_dir: Path, descriptor: dict[str, Any], *, require_present: bool) -> Path | None:
    path = cache_dir / str(descriptor["artifact_filename"])
    if not path.exists():
        if require_present:
            raise ModelTrustDenied("OFFLINE_MODEL_ARTIFACT_MISSING")
        return None
    if not path.is_file():
        raise ModelTrustDenied("MODEL_CACHE_ENTRY_NOT_REGULAR_FILE")
    actual = sha256_file(path)
    expected = str(descriptor["sha256"])
    if actual != expected:
        raise ModelTrustDenied("MODEL_ARTIFACT_SHA256_MISMATCH")
    return path

def validate_runtime_version(version: str) -> None:
    if str(version) != PINNED_WHISPER_VERSION:
        raise ModelTrustDenied(
            f"WHISPER_RUNTIME_VERSION_DRIFT expected={PINNED_WHISPER_VERSION} actual={version}"
        )

def _cuda_ordinal(device: str) -> int:
    if not _device_is_cuda(device):
        raise HRBLeaseDenied("CUDA device must be explicit cuda:N")
    return int(device.split(":", 1)[1])

def _nvidia_uuid_for_ordinal(ordinal: int) -> str:
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader,nounits"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise HRBLeaseDenied("NVIDIA ordinal-to-UUID projection unavailable") from exc
    if completed.returncode != 0:
        raise HRBLeaseDenied("nvidia-smi ordinal-to-UUID projection failed")
    mapping: dict[int, str] = {}
    for line in completed.stdout.splitlines():
        parts = [x.strip() for x in line.split(",", 1)]
        if len(parts) != 2:
            raise HRBLeaseDenied("unexpected nvidia-smi UUID projection output")
        mapping[int(parts[0])] = parts[1]
    value = mapping.get(ordinal)
    if not value or not value.startswith("GPU-"):
        raise HRBLeaseDenied("requested CUDA ordinal has no canonical GPU UUID")
    return value

def validate_hrb_lease_document(lease: dict[str, Any]) -> None:
    required = (
        "schema", "lease_id", "issuer", "accelerator_uuid", "memory_max_bytes",
        "expires_epoch", "issued_epoch", "purpose", "host", "status", "nonce",
        "placement", "enforcement", "signature",
    )
    missing = [x for x in required if x not in lease]
    if missing:
        raise HRBLeaseDenied("lease missing fields: " + ",".join(missing))
    if lease.get("schema") != HRB_LEASE_SCHEMA:
        raise HRBLeaseDenied("lease schema mismatch")
    if lease.get("issuer") != HRB_PROFILE_ID:
        raise HRBLeaseDenied("lease issuer mismatch")
    if str(lease.get("status")) != "ACTIVE":
        raise HRBLeaseDenied("lease is not ACTIVE")
    if int(lease.get("expires_epoch", 0)) <= int(time.time()):
        raise HRBLeaseDenied("lease expired")
    if int(lease.get("memory_max_bytes", 0)) < 4:
        raise HRBLeaseDenied("lease memory budget invalid")
    if not str(lease.get("accelerator_uuid", "")).startswith("GPU-"):
        raise HRBLeaseDenied("lease accelerator UUID invalid")
    if not str(lease.get("purpose", "")).startswith("FA3 Whisper STT"):
        raise HRBLeaseDenied("lease purpose is not scoped to FA3 Whisper STT")
    signature = lease.get("signature")
    if not isinstance(signature, dict):
        raise HRBLeaseDenied("lease signature missing")
    if signature.get("alg") != "HMAC-SHA256" or signature.get("key_id") != "host-local-v1":
        raise HRBLeaseDenied("lease signature descriptor invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(signature.get("value", ""))):
        raise HRBLeaseDenied("lease signature value invalid")
    placement = lease.get("placement")
    if not isinstance(placement, dict) or "pci_bus_id" not in placement or "numa_node" not in placement:
        raise HRBLeaseDenied("lease placement metadata invalid")

def validate_hrb_broker_output(returncode: int, stdout: str) -> None:
    if returncode != 0 or stdout.strip().splitlines()[-1:] != ["VALID"]:
        raise HRBLeaseDenied("HRB broker did not validate lease")

def verify_hrb_lease(options: RuntimeOptions) -> dict[str, Any] | None:
    if not _device_is_cuda(options.device):
        return None
    assert options.hrb_lease_path
    lease_path = Path(options.hrb_lease_path).expanduser().resolve()
    if not lease_path.is_file():
        raise HRBLeaseDenied("HRB lease file not found")
    lease = _read_json(lease_path)
    validate_hrb_lease_document(lease)
    if not any("{lease}" in x for x in options.hrb_verify_command):
        raise HRBLeaseDenied("HRB verifier command must contain {lease}")
    command = [x.replace("{lease}", str(lease_path)).replace("{device}", options.device) for x in options.hrb_verify_command]
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    validate_hrb_broker_output(completed.returncode, completed.stdout)
    ordinal = _cuda_ordinal(options.device)
    current_uuid = _nvidia_uuid_for_ordinal(ordinal)
    if current_uuid != lease.get("accelerator_uuid"):
        raise HRBLeaseDenied("CUDA ordinal resolves to GPU UUID different from HRB lease")
    return {
        "lease_id": lease["lease_id"],
        "authority_id": HRB_AUTHORITY_ID,
        "issuer": lease["issuer"],
        "schema": lease["schema"],
        "accelerator_uuid": lease["accelerator_uuid"],
        "memory_max_bytes": int(lease["memory_max_bytes"]),
        "expires_epoch": int(lease["expires_epoch"]),
        "purpose": lease["purpose"],
        "device": options.device,
        "current_ordinal": ordinal,
        "broker_validation": "VALID",
    }

def apply_hrb_cuda_memory_guard(hrb: dict[str, Any] | None) -> dict[str, Any] | None:
    if hrb is None:
        return None
    import torch
    ordinal = int(hrb["current_ordinal"])
    props = torch.cuda.get_device_properties(ordinal)
    total = int(props.total_memory)
    budget = int(hrb["memory_max_bytes"])
    if budget <= 0 or budget > total:
        raise HRBLeaseDenied("HRB memory budget outside current device capacity")
    fraction = min(0.99, budget / total)
    torch.cuda.set_per_process_memory_fraction(fraction, ordinal)
    return {
        "mechanism": "torch.cuda.set_per_process_memory_fraction",
        "memory_max_bytes": budget,
        "device_total_bytes": total,
        "fraction": fraction,
        "scope": "PYTORCH_ALLOCATOR_GUARD",
    }

def validate_segments(raw_segments: Sequence[dict[str, Any]], *, require_words: bool) -> list[dict[str, Any]]:
    if not raw_segments:
        raise ExecutionFailed("WHISPER_RETURNED_NO_SEGMENTS")
    out: list[dict[str, Any]] = []
    previous_end = 0.0
    for index, raw in enumerate(raw_segments):
        start = float(raw.get("start", -1))
        end = float(raw.get("end", -1))
        text = str(raw.get("text", "")).strip()
        if not (math.isfinite(start) and math.isfinite(end)):
            raise ExecutionFailed(f"segment {index} has non-finite timing")
        if start < 0 or end <= start:
            raise ExecutionFailed(f"segment {index} has invalid timing")
        if index and start < previous_end - 1e-6:
            raise ExecutionFailed(f"segment {index} overlaps previous segment")
        if not text:
            raise ExecutionFailed(f"segment {index} text empty")
        segment: dict[str, Any] = {
            "start": start,
            "end": end,
            "text": text,
        }
        if "avg_logprob" in raw:
            segment["avg_logprob"] = float(raw["avg_logprob"])
        if "no_speech_prob" in raw:
            segment["no_speech_prob"] = float(raw["no_speech_prob"])
        if require_words:
            words = raw.get("words")
            if not isinstance(words, list) or not words:
                raise ExecutionFailed(f"segment {index} missing requested word timestamps")
            clean_words: list[dict[str, Any]] = []
            last_word_end = start
            for widx, word in enumerate(words):
                ws = float(word.get("start", -1))
                we = float(word.get("end", -1))
                wt = str(word.get("word", "")).strip()
                if not (math.isfinite(ws) and math.isfinite(we)) or ws < 0 or we < ws:
                    raise ExecutionFailed(f"segment {index} word {widx} invalid timing")
                if widx and ws < last_word_end - 1e-6:
                    raise ExecutionFailed(f"segment {index} word {widx} overlaps previous word")
                if not wt:
                    raise ExecutionFailed(f"segment {index} word {widx} empty")
                item = {"start": ws, "end": we, "word": wt}
                if "probability" in word:
                    item["probability"] = float(word["probability"])
                clean_words.append(item)
                last_word_end = we
            segment["words"] = clean_words
        out.append(segment)
        previous_end = end
    return out

def evidence_complete(result: dict[str, Any]) -> bool:
    required = {
        "schema","status","provider_id","provider_version","audio_hash","language",
        "segments","model_id","device","execution_evidence",
    }
    if not required.issubset(result) or result.get("status") != "PASS":
        return False
    evidence = result.get("execution_evidence")
    if not isinstance(evidence, dict):
        return False
    ereq = {
        "runtime_version","model_artifact_sha256","model_cache_path","audio_contract",
        "word_timestamps","task","offline","device","device_lease","hrb","resource_guard",
        "started_at","completed_at",
    }
    return ereq.issubset(evidence)

def execute_transcription(root: Path, request: dict[str, Any], options: RuntimeOptions) -> dict[str, Any]:
    allowlist = load_allowlist(root)
    model_desc = validate_provider_request(request, options, allowlist)
    audio = validate_audio_contract(str(request["audio_path"]))
    if audio["sha256"] != request["audio_hash"]:
        raise PolicyDenied("AUDIO_HASH_MISMATCH")

    hrb = verify_hrb_lease(options)
    started = _utc_now()

    try:
        import whisper
    except ImportError as exc:
        raise ExecutionFailed("openai-whisper runtime not installed") from exc
    validate_runtime_version(getattr(whisper, "__version__", "unknown"))

    allocator_guard = apply_hrb_cuda_memory_guard(hrb)
    cache_dir = resolve_model_cache(options)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = validate_cached_model(cache_dir, model_desc, require_present=options.offline)

    try:
        model = whisper.load_model(options.model, device=options.device, download_root=str(cache_dir))
    except Exception as exc:
        raise ExecutionFailed(f"Whisper model load failed: {exc}") from exc

    artifact = validate_cached_model(cache_dir, model_desc, require_present=True)
    assert artifact is not None
    if cached is None and options.offline:
        raise ModelTrustDenied("network fetch occurred while offline")

    language = str(request.get("language", "auto"))
    language_arg = None if language == "auto" else language
    fp16 = _device_is_cuda(options.device)
    try:
        raw = model.transcribe(
            str(Path(request["audio_path"]).expanduser().resolve()),
            language=language_arg,
            task="transcribe",
            word_timestamps=options.word_timestamps,
            verbose=None,
            fp16=fp16,
        )
    except Exception as exc:
        raise ExecutionFailed(f"Whisper transcription failed: {exc}") from exc

    segments = validate_segments(raw.get("segments", []), require_words=options.word_timestamps)
    detected_language = str(raw.get("language") or language)
    result = {
        "schema": RESULT_SCHEMA,
        "status": "PASS",
        "provider_id": PROVIDER_ID,
        "provider_version": PROVIDER_VERSION,
        "audio_hash": audio["sha256"],
        "language": detected_language,
        "segments": segments,
        "model_id": f"{MODEL_ALLOWLIST_ID}:{options.model}",
        "device": options.device,
        "execution_evidence": {
            "runtime_version": str(getattr(whisper, "__version__", "unknown")),
            "model_artifact_sha256": sha256_file(artifact),
            "model_cache_path": str(artifact),
            "audio_contract": audio,
            "word_timestamps": options.word_timestamps,
            "task": "transcribe",
            "offline": options.offline,
            "device": options.device,
            "device_lease": None if hrb is None else hrb["lease_id"],
            "hrb": hrb,
            "resource_guard": allocator_guard,
            "started_at": started,
            "completed_at": _utc_now(),
        },
    }
    if not evidence_complete(result):
        raise ExecutionFailed("PASS result evidence contract incomplete")
    return result

def _write_test_wav(path: Path, *, rate: int = 16000, channels: int = 1, width: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * rate * channels * width // 10)

def run_executable_conformance(root: Path) -> dict[str, Any]:
    import tempfile
    cases: list[dict[str, Any]] = []
    def add(name: str, ok: bool, detail: str) -> None:
        cases.append({"name":name,"status":"PASS" if ok else "FAIL","detail":detail})

    allowlist = load_allowlist(root)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        audio = t / "audio.wav"
        _write_test_wav(audio)
        base = {
            "schema":REQUEST_SCHEMA,
            "audio_path":str(audio),
            "audio_hash":sha256_file(audio),
            "language":"hu",
            "time_origin":"RELATIVE_ZERO",
            "required_result_schema":RESULT_SCHEMA,
        }
        opts = RuntimeOptions(model="turbo", device="cpu", offline=True, model_cache=str(t/"cache"))
        try:
            validate_provider_request(base, opts, allowlist)
            add("typed_request_contract", True, "canonical typed STT request accepted")
        except Exception as exc:
            add("typed_request_contract", False, repr(exc))

        wrong = dict(base); wrong["audio_hash"]="bad"
        try:
            validate_provider_request(wrong, opts, allowlist)
            add("audio_hash_mismatch_rejected", False, "mismatch accepted")
        except PolicyDenied:
            add("audio_hash_mismatch_rejected", True, "audio hash binding fails closed")

        bad = t/"bad.bin"; bad.write_bytes(b"not wav")
        try:
            validate_audio_contract(bad)
            add("non_wav_input_rejected", False, "non-WAV accepted")
        except PolicyDenied:
            add("non_wav_input_rejected", True, "non-WAV rejected")

        r8=t/"8k.wav"; _write_test_wav(r8, rate=8000)
        try:
            validate_audio_contract(r8)
            add("wrong_samplerate_rejected", False, "8k accepted")
        except PolicyDenied:
            add("wrong_samplerate_rejected", True, "16 kHz required")

        stereo=t/"stereo.wav"; _write_test_wav(stereo, channels=2)
        try:
            validate_audio_contract(stereo)
            add("stereo_input_rejected", False, "stereo accepted")
        except PolicyDenied:
            add("stereo_input_rejected", True, "mono required")

        pcm8=t/"pcm8.wav"; _write_test_wav(pcm8, width=1)
        try:
            validate_audio_contract(pcm8)
            add("non_pcm16_input_rejected", False, "PCM8 accepted")
        except PolicyDenied:
            add("non_pcm16_input_rejected", True, "PCM16 required")

        try:
            validate_provider_request(base, RuntimeOptions(model="../../evil.pt"), allowlist)
            add("unknown_model_rejected", False, "unknown model accepted")
        except PolicyDenied:
            add("unknown_model_rejected", True, "unknown model rejected")

        try:
            validate_provider_request(base, RuntimeOptions(model="/tmp/model.pt"), allowlist)
            add("arbitrary_checkpoint_path_rejected", False, "path accepted")
        except PolicyDenied:
            add("arbitrary_checkpoint_path_rejected", True, "arbitrary checkpoint path rejected")

        try:
            validate_cached_model(t/"empty-cache", allowlist["models"]["turbo"], require_present=True)
            add("offline_missing_model_rejected", False, "missing model accepted")
        except ModelTrustDenied:
            add("offline_missing_model_rejected", True, "offline cache miss fails closed")

        try:
            validate_runtime_version("99999999")
            add("runtime_version_drift_rejected", False, "version drift accepted")
        except ModelTrustDenied:
            add("runtime_version_drift_rejected", True, "runtime version drift rejected")

        try:
            validate_provider_request(base, RuntimeOptions(model="turbo",device="cuda:0"), allowlist)
            add("cuda_without_hrb_rejected", False, "CUDA without HRB accepted")
        except PolicyDenied:
            add("cuda_without_hrb_rejected", True, "CUDA requires HRB lease")

        now=int(time.time())
        lease={
            "schema":HRB_LEASE_SCHEMA,"lease_id":"L1","issuer":HRB_PROFILE_ID,
            "accelerator_uuid":"GPU-TEST","memory_max_bytes":1024,"expires_epoch":now+60,
            "issued_epoch":now,"purpose":"WRONG","host":"host","status":"ACTIVE","nonce":"n",
            "placement":{"pci_bus_id":"0000:01:00.0","numa_node":0},
            "enforcement":{},"signature":{"alg":"HMAC-SHA256","key_id":"host-local-v1","value":"a"*64}
        }
        try:
            validate_hrb_lease_document(lease)
            add("invalid_hrb_purpose_rejected", False, "wrong purpose accepted")
        except HRBLeaseDenied:
            add("invalid_hrb_purpose_rejected", True, "lease purpose scoped to Whisper")

        issuer=dict(lease); issuer["purpose"]="FA3 Whisper STT test"; issuer["issuer"]="WRONG"
        try:
            validate_hrb_lease_document(issuer)
            add("invalid_hrb_issuer_rejected", False, "wrong issuer accepted")
        except HRBLeaseDenied:
            add("invalid_hrb_issuer_rejected", True, "issuer validated")

        sig=dict(lease); sig["purpose"]="FA3 Whisper STT test"; sig["signature"]={"alg":"none","key_id":"x","value":"x"}
        try:
            validate_hrb_lease_document(sig)
            add("invalid_hrb_signature_rejected", False, "bad signature accepted")
        except HRBLeaseDenied:
            add("invalid_hrb_signature_rejected", True, "signature descriptor validated")

        overlap=[
            {"start":0.0,"end":2.0,"text":"a","words":[{"start":0.0,"end":1.0,"word":"a"}]},
            {"start":1.0,"end":3.0,"text":"b","words":[{"start":1.0,"end":2.0,"word":"b"}]},
        ]
        try:
            validate_segments(overlap, require_words=True)
            add("segment_overlap_rejected", False, "overlap accepted")
        except ExecutionFailed:
            add("segment_overlap_rejected", True, "overlapping timing rejected")

        tr=dict(base); tr["task"]="translate"
        try:
            validate_provider_request(tr, opts, allowlist)
            add("translation_task_rejected", False, "translate accepted")
        except PolicyDenied:
            add("translation_task_rejected", True, "translation remains separate typed stage")

        valid=[{"start":0.0,"end":1.0,"text":"hello","words":[{"start":0.0,"end":0.9,"word":"hello","probability":0.9}]}]
        try:
            out=validate_segments(valid, require_words=True)
            add("word_timing_preserved", bool(out[0].get("words")), "word timestamps retained")
        except Exception as exc:
            add("word_timing_preserved", False, repr(exc))

        fake={
            "schema":RESULT_SCHEMA,"status":"PASS","provider_id":PROVIDER_ID,"provider_version":PROVIDER_VERSION,
            "audio_hash":"x","language":"hu","segments":valid,"model_id":"m","device":"cpu",
            "execution_evidence":{
                "runtime_version":PINNED_WHISPER_VERSION,"model_artifact_sha256":"h","model_cache_path":"p",
                "audio_contract":{},"word_timestamps":True,"task":"transcribe","offline":True,"device":"cpu",
                "device_lease":None,"hrb":None,"resource_guard":None,"started_at":"s","completed_at":"e"
            }
        }
        add("execution_evidence_complete", evidence_complete(fake), "PASS result carries required lineage/evidence")

    passed=sum(x["status"]=="PASS" for x in cases)
    return {
        "schema":"fa3.whisper-stt-conformance-report.v1",
        "provider_id":PROVIDER_ID,
        "provider_version":PROVIDER_VERSION,
        "result":"PASS" if passed==len(cases) else "FAIL",
        "passed":passed,"total":len(cases),"cases":cases,
        "scope":"CI_EXECUTABLE_CONFORMANCE_NOT_CURRENT_HOST",
    }

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 Whisper STT provider")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    sub=ap.add_subparsers(dest="command",required=True)

    conf=sub.add_parser("conformance")
    conf.add_argument("--report",default="reports/whisper-stt-conformance-report.json")

    tr=sub.add_parser("transcribe")
    tr.add_argument("--request",required=True)
    tr.add_argument("--result",required=True)
    tr.add_argument("--model",default="turbo")
    tr.add_argument("--device",default="cpu")
    tr.add_argument("--model-cache")
    tr.add_argument("--allow-network-model-fetch",action="store_true")
    tr.add_argument("--hrb-lease")
    tr.add_argument("--hrb-verifier-bin",default="/usr/local/bin/fa3-host-resource-broker")
    tr.add_argument("--word-timestamps",action=argparse.BooleanOptionalAction,default=True)

    args=ap.parse_args()
    root=Path(args.root).resolve()
    try:
        if args.command=="conformance":
            report=run_executable_conformance(root)
            path=Path(args.report)
            if not path.is_absolute():
                path=root/path
            _write_json(path,report)
            print(json.dumps(report,indent=2))
            return 0 if report["result"]=="PASS" else 2

        request=_read_json(args.request)
        opts=RuntimeOptions(
            model=args.model,
            device=args.device,
            offline=not args.allow_network_model_fetch,
            model_cache=args.model_cache,
            word_timestamps=args.word_timestamps,
            hrb_lease_path=args.hrb_lease,
            hrb_verify_command=(args.hrb_verifier_bin,"validate-lease","{lease}"),
        )
        result=execute_transcription(root,request,opts)
        _write_json(args.result,result)
        print(json.dumps({"status":"PASS","provider_id":PROVIDER_ID,"result":str(Path(args.result).resolve())},indent=2))
        return 0
    except ProviderError as exc:
        print(json.dumps({"status":"FAIL","provider_id":PROVIDER_ID,"error_type":type(exc).__name__,"error":str(exc)},indent=2),file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({"status":"FAIL","provider_id":PROVIDER_ID,"error_type":type(exc).__name__,"error":str(exc)},indent=2),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
