#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

PROVIDER_ID = "FA3-PROVIDER-DEMUCS-001"
PROFILE_ID = "FA3-AUDIO-SEPARATION-001"
PROVIDER_VERSION = "1.0.0"
HRB_AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
HRB_PROFILE_ID = "FA3-HOST-RESOURCE-BROKER-001"
HRB_LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
DEFAULT_HRB_VERIFY_COMMAND = ("/usr/local/bin/fa3-host-resource-broker", "validate-lease", "{lease}")
MODEL_ALLOWLIST_ID = "FA3-DEMUCS-MODEL-ALLOWLIST-001"

class ProviderError(RuntimeError):
    pass

class PolicyDenied(ProviderError):
    pass

class HRBLeaseDenied(ProviderError):
    pass

class ModelTrustDenied(ProviderError):
    pass

class ExecutionFailed(ProviderError):
    pass

@dataclass(frozen=True)
class SeparationRequest:
    input_path: str
    output_dir: str
    model: str = "htdemucs"
    stems: tuple[str, ...] = ("drums", "bass", "other", "vocals")
    device: str = "cpu"
    hrb_lease_path: str | None = None
    hrb_verify_command: tuple[str, ...] = DEFAULT_HRB_VERIFY_COMMAND
    segment: float | None = 7.0
    overlap: float = 0.25
    shifts: int = 1
    jobs: int = 0
    clipping: str = "rescale"
    offline: bool = True
    allow_experimental_stems: bool = False
    timeout_seconds: float = 3600.0
    cancel_file: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeparationRequest":
        return cls(
            input_path=str(data["input_path"]),
            output_dir=str(data["output_dir"]),
            model=str(data.get("model", "htdemucs")),
            stems=tuple(str(x) for x in data.get("stems", ["drums", "bass", "other", "vocals"])),
            device=str(data.get("device", "cpu")),
            hrb_lease_path=(None if data.get("hrb_lease_path") in (None, "") else str(data["hrb_lease_path"])),
            hrb_verify_command=tuple(str(x) for x in data.get("hrb_verify_command", DEFAULT_HRB_VERIFY_COMMAND)),
            segment=(None if data.get("segment") is None else float(data.get("segment"))),
            overlap=float(data.get("overlap", 0.25)),
            shifts=int(data.get("shifts", 1)),
            jobs=int(data.get("jobs", 0)),
            clipping=str(data.get("clipping", "rescale")),
            offline=bool(data.get("offline", True)),
            allow_experimental_stems=bool(data.get("allow_experimental_stems", False)),
            timeout_seconds=float(data.get("timeout_seconds", 3600.0)),
            cancel_file=(None if data.get("cancel_file") in (None, "") else str(data["cancel_file"])),
        )

@dataclass
class LoadedModel:
    model: Any
    model_name: str
    repo_id: str
    yaml_path: str
    yaml_sha256: str
    artifact_paths: list[str] = field(default_factory=list)
    artifact_sha256: list[str] = field(default_factory=list)
    model_classes: list[str] = field(default_factory=list)

    @property
    def aggregate_sha256(self) -> str:
        payload = {
            "model_name": self.model_name,
            "repo_id": self.repo_id,
            "yaml_sha256": self.yaml_sha256,
            "artifact_sha256": self.artifact_sha256,
            "model_classes": self.model_classes,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _parse_time(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)

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
    path = root / "canonical/FA3-DEMUCS-MODEL-ALLOWLIST-001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("id") != MODEL_ALLOWLIST_ID:
        raise ModelTrustDenied("Demucs model allowlist identity mismatch")
    if data.get("policy") != "ALLOWLIST_ONLY_FAIL_CLOSED":
        raise ModelTrustDenied("Demucs model allowlist is not fail-closed")
    return data

def _device_is_cuda(device: str) -> bool:
    return device == "cuda" or bool(re.fullmatch(r"cuda:\d+", device))

def validate_request(request: SeparationRequest, allowlist: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    models = allowlist.get("models", {})
    model = models.get(request.model)
    if model is None:
        findings.append("MODEL_NOT_ALLOWLISTED")
    if not request.stems:
        findings.append("STEM_SET_EMPTY")
    elif model is not None:
        supported = set(model.get("stems", []))
        unsupported = sorted(set(request.stems) - supported)
        if unsupported:
            findings.append("UNSUPPORTED_STEMS:" + ",".join(unsupported))
        experimental = set(model.get("experimental_stems", []))
        requested_experimental = sorted(set(request.stems) & experimental)
        if requested_experimental and not request.allow_experimental_stems:
            findings.append("EXPERIMENTAL_STEMS_NOT_EXPLICITLY_ALLOWED:" + ",".join(requested_experimental))
    if request.segment is not None and request.segment <= 0:
        findings.append("INVALID_SEGMENT")
    if not 0 <= request.overlap < 1:
        findings.append("INVALID_OVERLAP")
    if request.shifts < 1:
        findings.append("INVALID_SHIFTS")
    if request.jobs < 0:
        findings.append("INVALID_JOBS")
    if request.clipping not in {"rescale", "clamp", "none", "tanh"}:
        findings.append("INVALID_CLIPPING_POLICY")
    if request.timeout_seconds <= 0:
        findings.append("INVALID_TIMEOUT")
    if request.device != "cpu" and not _device_is_cuda(request.device):
        findings.append("UNSUPPORTED_DEVICE")
    if _device_is_cuda(request.device):
        if not request.hrb_lease_path:
            findings.append("CUDA_REQUIRES_HRB_LEASE")
        if not request.hrb_verify_command:
            findings.append("CUDA_REQUIRES_HRB_VERIFIER")
    if findings:
        raise PolicyDenied(";".join(findings))
    return model

def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _cuda_ordinal(device: str) -> int:
    if not _device_is_cuda(device):
        raise HRBLeaseDenied("CUDA device must be explicit cuda:N")
    return int(device.split(":", 1)[1])

def _nvidia_uuid_for_ordinal(ordinal: int) -> str:
    command = [
        "nvidia-smi",
        "--query-gpu=index,uuid",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
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
        parts = [part.strip() for part in line.split(",", 1)]
        if len(parts) != 2:
            raise HRBLeaseDenied("unexpected nvidia-smi UUID projection output")
        mapping[int(parts[0])] = parts[1]
    uuid = mapping.get(ordinal)
    if not uuid or not uuid.startswith("GPU-"):
        raise HRBLeaseDenied("requested CUDA ordinal has no canonical GPU UUID")
    return uuid

def validate_hrb_lease_document(lease: dict[str, Any], request: SeparationRequest) -> None:
    required = (
        "schema", "lease_id", "issuer", "accelerator_uuid", "memory_max_bytes",
        "expires_epoch", "issued_epoch", "purpose", "host", "status", "nonce",
        "placement", "enforcement", "signature",
    )
    missing = [key for key in required if key not in lease]
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
    accelerator_uuid = str(lease.get("accelerator_uuid", ""))
    if not accelerator_uuid.startswith("GPU-"):
        raise HRBLeaseDenied("lease accelerator UUID invalid")
    if not str(lease.get("purpose", "")).startswith("FA3 Demucs"):
        raise HRBLeaseDenied("lease purpose is not scoped to FA3 Demucs")
    signature = lease.get("signature")
    if not isinstance(signature, dict):
        raise HRBLeaseDenied("lease signature missing")
    if signature.get("alg") != "HMAC-SHA256" or signature.get("key_id") != "host-local-v1":
        raise HRBLeaseDenied("lease signature descriptor invalid")
    value = str(signature.get("value", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise HRBLeaseDenied("lease signature value invalid")
    placement = lease.get("placement")
    if not isinstance(placement, dict) or "pci_bus_id" not in placement or "numa_node" not in placement:
        raise HRBLeaseDenied("lease placement metadata invalid")

def validate_hrb_broker_output(returncode: int, stdout: str) -> None:
    if returncode != 0:
        raise HRBLeaseDenied("HRB broker validate-lease failed")
    if stdout.strip().splitlines()[-1:] != ["VALID"]:
        raise HRBLeaseDenied("HRB broker did not return VALID")

def verify_hrb_lease(request: SeparationRequest) -> dict[str, Any] | None:
    if not _device_is_cuda(request.device):
        return None
    assert request.hrb_lease_path is not None
    lease_path = Path(request.hrb_lease_path).resolve()
    if not lease_path.is_file():
        raise HRBLeaseDenied("HRB lease file not found")
    lease = _read_json(lease_path)
    validate_hrb_lease_document(lease, request)
    command = [
        part.replace("{lease}", str(lease_path)).replace("{device}", request.device)
        for part in request.hrb_verify_command
    ]
    if not any("{lease}" in part for part in request.hrb_verify_command):
        raise HRBLeaseDenied("HRB verifier command must contain {lease}")
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    validate_hrb_broker_output(completed.returncode, completed.stdout)
    ordinal = _cuda_ordinal(request.device)
    current_uuid = _nvidia_uuid_for_ordinal(ordinal)
    if current_uuid != lease.get("accelerator_uuid"):
        raise HRBLeaseDenied("CUDA ordinal resolves to a GPU UUID different from the broker lease")
    return {
        "lease_id": lease["lease_id"],
        "authority_id": HRB_AUTHORITY_ID,
        "issuer": lease["issuer"],
        "schema": lease["schema"],
        "accelerator_uuid": lease["accelerator_uuid"],
        "memory_max_bytes": int(lease["memory_max_bytes"]),
        "expires_epoch": int(lease["expires_epoch"]),
        "purpose": lease["purpose"],
        "device": request.device,
        "current_ordinal": ordinal,
        "broker_validation": "VALID",
    }

def _decode_json(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("_type") == "fraction":
            return Fraction(value["numerator"], value["denominator"])
        return {key: _decode_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_json(item) for item in value]
    return value

def _safe_unflatten_state(
    tensors: dict[str, Any],
    structure: Any,
    class_map: dict[str, Any],
) -> Any:
    def unflatten(node: Any) -> Any:
        if isinstance(node, dict):
            if "_tensor" in node:
                key = node["_tensor"]
                if key not in tensors:
                    raise ModelTrustDenied("state references missing tensor")
                return tensors[key]
            if "_dict" in node:
                return {key: unflatten(item) for key, item in node["_dict"]}
            if "_list" in node:
                return [unflatten(item) for item in node["_list"]]
            if "_tuple" in node:
                return tuple(unflatten(item) for item in node["_tuple"])
            if "_class" in node:
                class_name = str(node["_class"])
                if class_name not in class_map:
                    raise ModelTrustDenied("quantized-state class is not allowlisted: " + class_name)
                return class_map[class_name]
            raise ModelTrustDenied("invalid safetensors structure metadata")
        return node
    return unflatten(structure)

def _resolve_model_class(class_name: str, allowed_classes: set[str]) -> Any:
    if class_name not in allowed_classes:
        raise ModelTrustDenied("model class is not allowlisted: " + class_name)
    if class_name == "demucs.htdemucs.HTDemucs":
        from demucs.htdemucs import HTDemucs
        return HTDemucs
    if class_name == "demucs.hdemucs.HDemucs":
        from demucs.hdemucs import HDemucs
        return HDemucs
    raise ModelTrustDenied("allowlisted model class has no local implementation mapping")

def _load_safetensors_model(path: Path, allowed_classes: set[str]) -> tuple[Any, str]:
    from safetensors import safe_open
    from demucs.states import load_model

    with safe_open(str(path), framework="pt") as file:
        metadata = file.metadata() or {}
        tensors = {key: file.get_tensor(key) for key in file.keys()}
    class_name = metadata.get("klass")
    if not class_name:
        raise ModelTrustDenied("safetensors model missing klass metadata")
    klass = _resolve_model_class(class_name, allowed_classes)
    if "structure" in metadata:
        structure = json.loads(metadata["structure"])
        state = _safe_unflatten_state(tensors, structure, {})
    else:
        state = tensors
    args = _decode_json(json.loads(metadata.get("args", "[]")))
    kwargs = _decode_json(json.loads(metadata.get("kwargs", "{}")))
    model = load_model({"klass": klass, "args": args, "kwargs": kwargs, "state": state})
    model.eval()
    return model, class_name

def load_trusted_model(
    root: Path,
    request: SeparationRequest,
    model_descriptor: dict[str, Any],
) -> LoadedModel:
    if model_descriptor.get("quantized"):
        raise ModelTrustDenied("quantized Demucs models are not admitted by v1 production allowlist")
    repo_id = str(model_descriptor["repo_id"])
    namespace = repo_id.split("/", 1)[0]
    allowlist = load_allowlist(root)
    if namespace != allowlist.get("allowed_namespace"):
        raise ModelTrustDenied("HuggingFace namespace not allowlisted")
    if repo_id != model_descriptor.get("repo_id"):
        raise ModelTrustDenied("model repository identity mismatch")

    from huggingface_hub import hf_hub_download
    import yaml
    from demucs.apply import BagOfModels

    local_only = bool(request.offline)
    try:
        yaml_path = Path(hf_hub_download(
            repo_id=repo_id,
            filename=f"{request.model}.yaml",
            local_files_only=local_only,
        ))
    except Exception as exc:
        mode = "offline cache" if local_only else "HuggingFace"
        raise ModelTrustDenied(f"could not resolve trusted model bag from {mode}") from exc
    bag = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(bag, dict) or not isinstance(bag.get("models"), list) or not bag["models"]:
        raise ModelTrustDenied("invalid model bag manifest")
    allowed_classes = set(allowlist.get("allowed_model_classes", []))
    models = []
    artifact_paths: list[str] = []
    artifact_hashes: list[str] = []
    model_classes: list[str] = []
    for signature in bag["models"]:
        sig = str(signature)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", sig):
            raise ModelTrustDenied("unsafe model signature in bag")
        try:
            artifact = Path(hf_hub_download(
                repo_id=repo_id,
                filename=f"{sig}.safetensors",
                local_files_only=local_only,
            ))
        except Exception as exc:
            raise ModelTrustDenied("could not resolve trusted safetensors artifact") from exc
        model, class_name = _load_safetensors_model(artifact, allowed_classes)
        models.append(model)
        model_classes.append(class_name)
        artifact_paths.append(str(artifact))
        artifact_hashes.append(sha256_file(artifact))
    bag_model = BagOfModels(models, bag.get("weights"), bag.get("segment"))
    bag_model.eval()
    return LoadedModel(
        model=bag_model,
        model_name=request.model,
        repo_id=repo_id,
        yaml_path=str(yaml_path),
        yaml_sha256=sha256_file(yaml_path),
        artifact_paths=artifact_paths,
        artifact_sha256=artifact_hashes,
        model_classes=model_classes,
    )

def _load_audio(path: Path, samplerate: int, channels: int) -> Any:
    import sphn
    import torch as th
    from demucs.audio import AudioFile, convert_audio

    try:
        data, sr = sphn.read(str(path))
        wav = convert_audio(th.from_numpy(data), int(sr), samplerate, channels)
        return wav
    except Exception as first_error:
        try:
            return AudioFile(path).read(streams=0, samplerate=samplerate, channels=channels)
        except Exception as second_error:
            raise ExecutionFailed(
                f"audio decode failed via sphn and ffmpeg fallback: {first_error!r}; {second_error!r}"
            ) from second_error

def _tensor_quality(tensor: Any, expected_length: int) -> dict[str, Any]:
    import torch as th
    if not isinstance(tensor, th.Tensor):
        raise ExecutionFailed("stem output is not a tensor")
    if tensor.numel() == 0 or tensor.shape[-1] != expected_length:
        raise ExecutionFailed("stem output shape/length mismatch")
    if not bool(th.isfinite(tensor).all()):
        raise ExecutionFailed("stem output contains non-finite samples")
    peak = float(tensor.abs().max().detach().cpu())
    rms = float(th.sqrt(th.mean(tensor.float() ** 2)).detach().cpu())
    return {"samples": int(tensor.shape[-1]), "channels": int(tensor.shape[-2]), "peak": peak, "rms": rms}

def apply_hrb_cuda_memory_guard(hrb: dict[str, Any] | None, device: str) -> dict[str, Any] | None:
    if hrb is None:
        return None
    import torch
    ordinal = int(hrb["current_ordinal"])
    props = torch.cuda.get_device_properties(ordinal)
    total = int(props.total_memory)
    budget = int(hrb["memory_max_bytes"])
    if budget <= 0 or budget > total:
        raise HRBLeaseDenied("HRB memory budget is outside current device capacity")
    fraction = min(0.99, budget / total)
    torch.cuda.set_per_process_memory_fraction(fraction, ordinal)
    return {
        "mechanism": "torch.cuda.set_per_process_memory_fraction",
        "memory_max_bytes": budget,
        "device_total_bytes": total,
        "fraction": fraction,
        "scope": "PYTORCH_ALLOCATOR_GUARD",
    }

def execute_separation(root: Path, request: SeparationRequest) -> dict[str, Any]:
    allowlist = load_allowlist(root)
    model_descriptor = validate_request(request, allowlist)
    hrb = verify_hrb_lease(request)
    input_path = Path(request.input_path).resolve()
    output_dir = Path(request.output_dir).resolve()
    if not input_path.is_file():
        raise ExecutionFailed("input audio file does not exist")
    output_dir.mkdir(parents=True, exist_ok=True)

    loaded = load_trusted_model(root, request, model_descriptor)
    import torch as th
    from demucs.apply import apply_model
    from demucs.audio import save_audio

    allocator_guard = apply_hrb_cuda_memory_guard(hrb, request.device)
    model = loaded.model
    samplerate = int(model.samplerate)
    channels = int(model.audio_channels)
    wav = _load_audio(input_path, samplerate, channels)
    if wav.ndim != 2:
        raise ExecutionFailed("decoded audio must be [channels, samples]")
    ref = wav.mean(0)
    mean = ref.mean()
    std = ref.std() + 1e-8
    device = th.device(request.device)
    deadline = time.monotonic() + request.timeout_seconds
    cancel_path = Path(request.cancel_file).resolve() if request.cancel_file else None
    def cancellation_callback(_: dict[str, Any]) -> None:
        if time.monotonic() > deadline:
            raise KeyboardInterrupt("FA3 Demucs execution deadline exceeded")
        if cancel_path is not None and cancel_path.exists():
            raise KeyboardInterrupt("FA3 Demucs cancellation requested")
    try:
        out = apply_model(
        model,
        ((wav - mean) / std)[None],
        segment=request.segment,
        shifts=request.shifts,
        split=True,
        overlap=request.overlap,
        device=device,
        num_workers=request.jobs,
        progress=False,
        callback=cancellation_callback,
    )
    except KeyboardInterrupt as exc:
        raise ExecutionFailed(str(exc) or "Demucs execution cancelled") from exc
    out = out * std + mean
    result = dict(zip(model.sources, out[0]))
    output_hashes: dict[str, str] = {}
    quality: dict[str, Any] = {}
    artifacts: list[dict[str, Any]] = []
    for stem in request.stems:
        if stem not in result:
            raise ExecutionFailed("model did not return requested stem: " + stem)
        tensor = result[stem]
        quality[stem] = _tensor_quality(tensor, int(wav.shape[-1]))
        path = output_dir / f"{stem}.wav"
        save_audio(
            tensor,
            path,
            samplerate=samplerate,
            clip=request.clipping,
            bits_per_sample=24,
            as_float=False,
        )
        digest = sha256_file(path)
        output_hashes[stem] = digest
        artifacts.append({
            "id": f"stem:{stem}:{digest[:16]}",
            "stem": stem,
            "path": str(path),
            "output_hash": digest,
            "parent_mixture": sha256_file(input_path),
            "model_id": f"{MODEL_ALLOWLIST_ID}:{request.model}",
            "provider_id": PROVIDER_ID,
        })

    try:
        import demucs
        demucs_version = getattr(demucs, "__version__", "unknown")
    except Exception:
        demucs_version = "unknown"
    execution = {
        "schema": "fa3.demucs-execution-evidence.v1",
        "status": "PASS",
        "provider_id": PROVIDER_ID,
        "provider_version": PROVIDER_VERSION,
        "profile_id": PROFILE_ID,
        "execution_timestamp": _utc_now(),
        "input_path": str(input_path),
        "input_hash": sha256_file(input_path),
        "model_id": f"{MODEL_ALLOWLIST_ID}:{request.model}",
        "model_hash": loaded.aggregate_sha256,
        "model_repo_id": loaded.repo_id,
        "model_manifest_hash": loaded.yaml_sha256,
        "model_artifact_hashes": loaded.artifact_sha256,
        "model_classes": loaded.model_classes,
        "model_trust": {
            "container": "SAFETENSORS",
            "namespace_allowlisted": True,
            "class_allowlisted": True,
            "legacy_pickle_used": False,
        },
        "provider_runtime": {
            "demucs_version": demucs_version,
            "device": request.device,
            "segment": request.segment,
            "overlap": request.overlap,
            "shifts": request.shifts,
            "jobs": request.jobs,
            "offline": request.offline,
            "timeout_seconds": request.timeout_seconds,
            "cancel_file": request.cancel_file,
        },
        "stem_schema": list(model.sources),
        "requested_stems": list(request.stems),
        "samplerate": samplerate,
        "channels": channels,
        "device_lease": None if hrb is None else hrb["lease_id"],
        "hrb": hrb,
        "resource_guard": allocator_guard,
        "clipping_policy": request.clipping,
        "output_hashes": output_hashes,
        "quality_evidence": quality,
        "stem_artifacts": artifacts,
    }
    return execution

def evidence_complete(evidence: dict[str, Any]) -> bool:
    required = {
        "status", "provider_id", "provider_version", "profile_id", "execution_timestamp",
        "input_hash", "model_id", "model_hash", "model_repo_id", "model_classes",
        "stem_schema", "requested_stems", "samplerate", "channels", "device_lease",
        "clipping_policy", "output_hashes", "quality_evidence", "stem_artifacts",
    }
    return (
        required.issubset(evidence)
        and evidence.get("status") == "PASS"
        and evidence.get("provider_id") == PROVIDER_ID
        and bool(evidence.get("output_hashes"))
        and bool(evidence.get("quality_evidence"))
        and bool(evidence.get("stem_artifacts"))
    )

def run_executable_conformance(root: Path) -> dict[str, Any]:
    allowlist = load_allowlist(root)
    cases: list[dict[str, Any]] = []

    def case(name: str, passed: bool, detail: str) -> None:
        cases.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    base = SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", device="cpu")
    try:
        validate_request(base, allowlist)
        case("cpu_request_valid", True, "CPU path does not require HRB lease")
    except Exception as exc:
        case("cpu_request_valid", False, repr(exc))

    try:
        validate_request(SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", device="cuda:0"), allowlist)
        case("cuda_without_hrb_rejected", False, "request unexpectedly accepted")
    except PolicyDenied:
        case("cuda_without_hrb_rejected", True, "CUDA request fails closed without HRB lease and verifier")

    try:
        validate_request(SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", stems=("piano",), model="htdemucs"), allowlist)
        case("unsupported_stem_rejected", False, "request unexpectedly accepted")
    except PolicyDenied:
        case("unsupported_stem_rejected", True, "unsupported stem fails closed")

    try:
        validate_request(SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", stems=("piano",), model="htdemucs_6s"), allowlist)
        case("experimental_stem_requires_optin", False, "request unexpectedly accepted")
    except PolicyDenied:
        case("experimental_stem_requires_optin", True, "experimental stem requires explicit opt-in")

    try:
        validate_request(SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", model="hf://attacker/model"), allowlist)
        case("arbitrary_model_rejected", False, "request unexpectedly accepted")
    except PolicyDenied:
        case("arbitrary_model_rejected", True, "non-allowlisted model identifier rejected")

    case(
        "class_allowlist_fail_closed",
        "evil.module.Model" not in set(allowlist.get("allowed_model_classes", [])),
        "external metadata class outside allowlist cannot be resolved",
    )
    case(
        "legacy_pickle_denied",
        all(ext in " ".join(allowlist.get("denied_model_forms", [])) for ext in [".th", ".pt", ".pth"]),
        "legacy pickle checkpoint forms are denied by model policy",
    )

    good_request = SeparationRequest(
        input_path="/tmp/in.wav",
        output_dir="/tmp/out",
        device="cuda:0",
        hrb_lease_path="/tmp/lease.json",
        hrb_verify_command=DEFAULT_HRB_VERIFY_COMMAND,
    )
    lease = {
        "schema": HRB_LEASE_SCHEMA,
        "lease_id": "hrb-test",
        "issuer": HRB_PROFILE_ID,
        "accelerator_uuid": "GPU-test",
        "memory_max_bytes": 4096,
        "expires_epoch": int(time.time()) + 60,
        "issued_epoch": int(time.time()),
        "purpose": "FA3 Demucs provider conformance",
        "host": "test-host",
        "status": "ACTIVE",
        "nonce": "00" * 16,
        "placement": {"ordinal_at_issue": 0, "pci_bus_id": "00000000:01:00.0", "numa_node": 0},
        "enforcement": {"gpu_memory": "provider_guard+broker_reservation"},
        "signature": {"alg": "HMAC-SHA256", "key_id": "host-local-v1", "value": "11" * 32},
    }
    try:
        validate_hrb_lease_document(lease, good_request)
        validate_hrb_broker_output(0, "VALID\n")
        case("typed_hrb_lease_accepts_valid", True, "canonical AcceleratorExecutionLease@1 structure and broker VALID response accepted")
    except Exception as exc:
        case("typed_hrb_lease_accepts_valid", False, repr(exc))

    bad_lease = dict(lease)
    bad_lease["issuer"] = "OTHER"
    try:
        validate_hrb_lease_document(bad_lease, good_request)
        case("hrb_issuer_mismatch_rejected", False, "mismatched issuer unexpectedly accepted")
    except HRBLeaseDenied:
        case("hrb_issuer_mismatch_rejected", True, "HRB lease issuer is pinned to canonical broker profile")

    try:
        validate_request(SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", overlap=1.0), allowlist)
        case("invalid_overlap_rejected", False, "invalid overlap unexpectedly accepted")
    except PolicyDenied:
        case("invalid_overlap_rejected", True, "invalid overlap rejected")

    try:
        validate_request(SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", clipping="implicit"), allowlist)
        case("implicit_clipping_rejected", False, "implicit clipping unexpectedly accepted")
    except PolicyDenied:
        case("implicit_clipping_rejected", True, "clipping policy must be explicit")

    try:
        validate_request(SeparationRequest(input_path="/tmp/in.wav", output_dir="/tmp/out", timeout_seconds=0), allowlist)
        case("bounded_execution_required", False, "unbounded execution unexpectedly accepted")
    except PolicyDenied:
        case("bounded_execution_required", True, "execution requires a positive deadline")

    sample_evidence = {
        "status":"PASS","provider_id":PROVIDER_ID,"provider_version":PROVIDER_VERSION,
        "profile_id":PROFILE_ID,"execution_timestamp":_utc_now(),"input_hash":"a",
        "model_id":"m","model_hash":"h","model_repo_id":"r","model_classes":["demucs.htdemucs.HTDemucs"],
        "stem_schema":["vocals"],"requested_stems":["vocals"],"samplerate":44100,"channels":2,
        "device_lease":None,"clipping_policy":"rescale","output_hashes":{"vocals":"b"},
        "quality_evidence":{"vocals":{"samples":1}},"stem_artifacts":[{"id":"x"}],
    }
    case("execution_evidence_contract_complete", evidence_complete(sample_evidence), "minimum execution evidence fields enforced")

    passed = sum(item["status"] == "PASS" for item in cases)
    return {
        "schema":"fa3.demucs-provider-conformance-report.v1",
        "provider_id":PROVIDER_ID,
        "provider_version":PROVIDER_VERSION,
        "model_allowlist_id":MODEL_ALLOWLIST_ID,
        "result":"PASS" if passed == len(cases) else "FAIL",
        "passed":passed,
        "total":len(cases),
        "cases":cases,
    }

def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Demucs provider adapter")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = ap.add_subparsers(dest="command", required=True)

    conf = sub.add_parser("conformance")
    conf.add_argument("--report", default="reports/demucs-provider-conformance-report.json")

    run = sub.add_parser("run")
    run.add_argument("--request", required=True)
    run.add_argument("--evidence", required=True)

    args = ap.parse_args()
    root = Path(args.root).resolve()
    try:
        if args.command == "conformance":
            report = run_executable_conformance(root)
            path = Path(args.report)
            if not path.is_absolute():
                path = root / path
            _write_json(path, report)
            print(json.dumps(report, indent=2))
            return 0 if report["result"] == "PASS" else 2
        request = SeparationRequest.from_dict(_read_json(args.request))
        evidence = execute_separation(root, request)
        if not evidence_complete(evidence):
            raise ExecutionFailed("execution evidence contract incomplete")
        _write_json(Path(args.evidence), evidence)
        print(json.dumps(evidence, indent=2))
        return 0
    except ProviderError as exc:
        report = {"status":"FAIL","provider_id":PROVIDER_ID,"error_type":type(exc).__name__,"error":str(exc)}
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 2
    except Exception as exc:
        report = {"status":"FAIL","provider_id":PROVIDER_ID,"error_type":type(exc).__name__,"error":str(exc)}
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
