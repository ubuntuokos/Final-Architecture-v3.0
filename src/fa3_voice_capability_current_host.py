#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_voice_quality_router import VoiceQualityRoutingDenied, resolve_quality_route
from fa3_voice_synthesis_gate import VoicePolicyDenied, gate as voice_gate, resolve_route

CAPABILITY_COUNT = module_active_capability_count(__file__)
CONFORMANCE_ID = "FA3-VOICE-CAPABILITY-CURRENT-HOST-CONFORMANCE-001"
GATE_ID = "FA3-VOICE-CAPABILITY-CURRENT-HOST-GATESET-001"
VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
BUNDLE_SCHEMA = "fa3.voice-capability-current-host-bundle.v1"
SUBJECTS = ("CAP-115", "CAP-116", "CAP-117")
MODES = ("positive", "negative", "rollback")
CLONING_MODES = {
    "zero_shot",
    "cross_lingual",
    "voice_clone",
    "controllable_clone",
    "ultimate_clone",
    "instruct2",
}
PROVIDER_COLLECTOR_BINDINGS = {
    "FA3-PROVIDER-COSYVOICE-001": "evidence/collect-cosyvoice-current-host.py",
    "FA3-PROVIDER-XTTS-001": "evidence/collect-xtts-current-host.py",
    "FA3-PROVIDER-PIPER-001": "evidence/collect-piper-current-host.py",
}

RIGHTS_DIMENSIONS = (
    "code_license",
    "runtime_license",
    "model_license",
    "voice_or_dataset_license",
    "output_usage_rights",
    "commercial_use_status",
    "attribution_obligations",
    "evidence_ref",
)


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def repo_head(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"top-level object required: {path}")
    return value


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fresh_timestamp(value: Any, *, max_age_hours: int = 24) -> bool:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        age = dt.datetime.now(dt.timezone.utc) - parsed.astimezone(dt.timezone.utc)
        return dt.timedelta(0) <= age <= dt.timedelta(hours=max_age_hours)
    except Exception:
        return False


def normalize_locale(value: Any) -> str:
    raw = str(value or "").strip().replace("_", "-").lower()
    if raw in {"hu", "hu-hu"}:
        return "hu-HU"
    return raw


def _bundle_path(root: Path, subject_id: str) -> Path:
    return root / ".fa3-current-host/input/voice-capabilities" / f"{subject_id}.json"


def _resolve_bundle_artifact(bundle_path: Path, value: Any) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("artifact path missing")
    path = Path(raw)
    if not path.is_absolute():
        path = (bundle_path.parent / path).resolve()
    else:
        path = path.expanduser().resolve()
    base = bundle_path.parent.resolve()
    if path != base and base not in path.parents:
        raise ValueError(f"bundle artifact escapes staged evidence root: {path}")
    return path


def _checked_artifact(bundle_path: Path, spec: Any, label: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(spec, dict):
        raise ValueError(f"{label} artifact spec missing")
    path = _resolve_bundle_artifact(bundle_path, spec.get("path"))
    expected = str(spec.get("sha256", "")).lower()
    if not path.is_file():
        raise ValueError(f"{label} artifact missing: {path}")
    actual = sha256_file(path)
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or actual != expected:
        raise ValueError(f"{label} artifact digest mismatch")
    return path, spec


def _collector_bound(root: Path, spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("collector binding missing")
    rel = str(spec.get("path", "")).strip()
    expected = str(spec.get("sha256", "")).lower()
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError("collector path must be repository-relative")
    path = (root / rel).resolve()
    if not path.is_file() or root not in path.parents:
        raise ValueError("collector path is not a repository file")
    actual = sha256_file(path)
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or actual != expected:
        raise ValueError("collector digest mismatch")
    if not (rel.startswith("evidence/collect-") and rel.endswith("-current-host.py")):
        raise ValueError("collector is not an admitted current-host collector path")
    return {"path": rel, "sha256": actual}


def expected_source_decisions(root: Path, subject_id: str) -> list[str]:
    registry = loadj(root / "evidence/evidence-registry.json")
    record = next(
        (row for row in registry.get("records", []) if row.get("subject_id") == subject_id),
        None,
    )
    if not isinstance(record, dict):
        raise RuntimeError(f"{subject_id} Evidence Registry record missing")
    ids = record.get("source_decision_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids):
        raise RuntimeError(f"{subject_id} source-decision coverage invalid")
    return ids


def validate_coverage(root: Path, subject_id: str) -> list[str]:
    expected = expected_source_decisions(root, subject_id)
    supplied = json.loads(required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"))
    if supplied != expected:
        raise RuntimeError(f"{subject_id} producer coverage does not exactly match Evidence Registry")
    return expected


def _validate_hu_aqc(
    root: Path,
    bundle_path: Path,
    quality: Any,
    *,
    cloning: bool,
    expected_audio_sha256: str,
) -> dict[str, Any]:
    path, spec = _checked_artifact(bundle_path, quality, "HU-AQC")
    receipt = loadj(path)
    if not (
        receipt.get("schema") == "fa3.hu-aqc-current-host-receipt.v1"
        and receipt.get("surface") == "HU_AQC"
        and receipt.get("repository_head") == repo_head(root)
        and receipt.get("synthetic") is False
        and receipt.get("global_promotion_claim") is False
        and receipt.get("locale") == "hu-HU"
        and receipt.get("result") == "PASS"
        and receipt.get("status") == "CURRENT_HOST_PASS"
        and receipt.get("scorer_provenance_admitted") is True
        and receipt.get("signal_metrics_recomputed_locally") is True
        and receipt.get("asr_error_rates_recomputed_locally") is True
        and receipt.get("audio_sha256") == expected_audio_sha256
    ):
        raise ValueError("HU-AQC current-host receipt invariant mismatch")
    aqc = receipt.get("aqc", {})
    dims = aqc.get("dimensions", {})
    if aqc.get("passed") is not True or aqc.get("single_metric_authority") is not False:
        raise ValueError("HU-AQC multi-signal verdict is not PASS")
    required = {
        "text_language",
        "grammar_style",
        "toxicity_policy",
        "intelligibility",
        "naturalness",
        "signal_integrity",
        "speaker_identity",
    }
    if set(dims) != required or not all(bool(dims.get(k)) for k in required):
        raise ValueError("HU-AQC dimensions are incomplete or failed")
    if cloning and dims.get("speaker_identity") is not True:
        raise ValueError("cloning requires speaker identity quality PASS")
    return {"path": str(path), "sha256": spec["sha256"], "aqc_pass": True}


def _validate_rights(rights: Any) -> dict[str, Any]:
    if not isinstance(rights, dict):
        raise ValueError("license/output-rights evidence missing")
    dimensions = rights.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("license dimensions missing")
    missing = [key for key in RIGHTS_DIMENSIONS if key not in dimensions]
    if missing:
        raise ValueError("license dimensions incomplete: " + ",".join(missing))
    for key in RIGHTS_DIMENSIONS:
        value = dimensions[key]
        if key == "attribution_obligations":
            if not isinstance(value, list):
                raise ValueError("attribution obligations must be explicit list")
        elif key == "evidence_ref":
            if not str(value).strip():
                raise ValueError("license evidence_ref missing")
        elif value != "PASS":
            raise ValueError(f"license/right dimension not PASS: {key}")
    if rights.get("production_use_admitted") is not True:
        raise ValueError("production output rights not admitted")
    return {"production_use_admitted": True, "evidence_ref": dimensions["evidence_ref"]}


def _validate_provider(root: Path, bundle_path: Path, provider: Any) -> dict[str, Any]:
    if not isinstance(provider, dict):
        raise ValueError("provider evidence missing")
    provider_id = str(provider.get("provider_id", "")).strip()
    expected_collector = PROVIDER_COLLECTOR_BINDINGS.get(provider_id)
    if not expected_collector:
        raise ValueError("provider has no admitted current-host collector binding")
    collector_spec = provider.get("collector")
    if not isinstance(collector_spec, dict) or collector_spec.get("path") != expected_collector:
        raise ValueError("provider current-host collector binding mismatch")
    collector = _collector_bound(root, collector_spec)
    receipt_path, receipt_spec = _checked_artifact(bundle_path, provider.get("receipt"), "provider")
    receipt = loadj(receipt_path)
    if provider.get("provider_id") != receipt.get("provider_id"):
        raise ValueError("provider identity does not match provider receipt")
    if normalize_locale(provider.get("locale")) != "hu-HU":
        raise ValueError("voice capability baseline requires hu-HU provider evidence")
    if provider.get("current_host_production_e2e") is not True:
        raise ValueError("provider current-host production E2E is not PASS")
    if provider.get("production_language_admitted") is not True:
        raise ValueError("provider language is not production-admitted")
    if provider.get("local_execution") is not True:
        raise ValueError("provider execution is not local")
    if provider.get("optional_runtime_global_dependency") is not False:
        raise ValueError("optional provider became a global runtime dependency")
    if provider.get("architectural_authority") is not False:
        raise ValueError("provider attempted architectural authority")
    if not str(provider.get("runtime_identity", "")).strip():
        raise ValueError("provider runtime identity missing")
    if not str(provider.get("model_identity", "")).strip():
        raise ValueError("provider model identity missing")
    if receipt.get("repository_head") != repo_head(root):
        raise ValueError("provider receipt repository HEAD mismatch")
    if receipt.get("current_host") is not True:
        raise ValueError("provider receipt is not current-host evidence")
    if receipt.get("synthetic") is True:
        raise ValueError("synthetic provider receipt forbidden")
    if receipt.get("global_promotion_claim") is True:
        raise ValueError("provider receipt attempted global promotion")
    if provider_id == "FA3-PROVIDER-COSYVOICE-001":
        language_status = str(
            receipt.get("language_promotion_status", provider.get("language_status", ""))
        )
        if "EXPERIMENTAL" in language_status or normalize_locale(receipt.get("language")) == "hu-HU":
            raise ValueError("CosyVoice experimental Hungarian evidence cannot satisfy production hu-HU capability PASS")
    output_sha = str(receipt.get("output_audio_sha256", receipt.get("audio_sha256", ""))).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", output_sha):
        raise ValueError("provider receipt output audio digest missing")
    return {
        "provider_id": provider_id,
        "collector": collector,
        "receipt_path": str(receipt_path),
        "receipt_sha256": receipt_spec["sha256"],
        "output_audio_sha256": output_sha,
    }


def _wav_contract(path: Path) -> dict[str, int]:
    try:
        with wave.open(str(path), "rb") as wav:
            return {
                "sample_rate_hz": wav.getframerate(),
                "channels": wav.getnchannels(),
                "sample_width_bytes": wav.getsampwidth(),
                "frames": wav.getnframes(),
            }
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"voice artifact is not readable PCM WAV: {path}") from exc


def _validate_audio(bundle_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    native_path, native = _checked_artifact(bundle_path, bundle.get("native_output"), "native output")
    native_wav = _wav_contract(native_path)
    native_sr = int(native.get("sample_rate_hz", 0))
    if (
        native_sr not in {22050, 24000, 48000}
        or int(native.get("channels", 0)) < 1
        or native_wav["sample_rate_hz"] != native_sr
        or native_wav["channels"] != int(native.get("channels", 0))
        or native_wav["frames"] <= 0
    ):
        raise ValueError("native output audio contract invalid")

    media_path, media = _checked_artifact(bundle_path, bundle.get("media_projection"), "48k media projection")
    media_wav = _wav_contract(media_path)
    if int(media.get("sample_rate_hz", 0)) != 48000 or media_wav["sample_rate_hz"] != 48000:
        raise ValueError("media projection must be 48 kHz")
    if str(media.get("sample_format", "")).upper() not in {"PCM", "PCM_S16LE", "PCM_S24LE"}:
        raise ValueError("media projection must use explicit PCM format")
    if media_wav["frames"] <= 0 or media_wav["channels"] != int(media.get("channels", media_wav["channels"])):
        raise ValueError("media projection WAV contract invalid")
    lineage = media.get("lineage", {})
    if not isinstance(lineage, dict):
        raise ValueError("media projection lineage missing")
    if lineage.get("source_sha256") != native.get("sha256"):
        raise ValueError("media projection source hash does not match native master")
    if not str(lineage.get("algorithm", "")).strip():
        raise ValueError("media projection resample algorithm missing")
    return {
        "native_path": str(native_path),
        "native_sha256": native["sha256"],
        "media_path": str(media_path),
        "media_sha256": media["sha256"],
    }


def _validate_stt(root: Path, bundle_path: Path, stt: Any) -> dict[str, Any]:
    if not isinstance(stt, dict):
        raise ValueError("STT current-host evidence required")
    collector = _collector_bound(root, stt.get("collector"))
    path, spec = _checked_artifact(bundle_path, stt.get("receipt"), "STT")
    receipt = loadj(path)
    if not (
        receipt.get("schema") == "fa3.whisper-stt-current-host-evidence.v1"
        and receipt.get("status") == "CURRENT_HOST_WHISPER_STT_E2E_PASS"
        and receipt.get("current_host") is True
        and receipt.get("ci") is False
        and int(receipt.get("segment_count", 0)) > 0
        and normalize_locale(receipt.get("detected_language")) in {"hu", "hu-HU"}
    ):
        raise ValueError("STT current-host receipt invariant mismatch")
    if receipt.get("repository_head") != repo_head(root):
        raise ValueError("STT receipt repository head mismatch")
    if receipt.get("synthetic") is not False or receipt.get("global_promotion_claim") is not False:
        raise ValueError("STT receipt synthetic/promotion invariant mismatch")
    return {
        "collector": collector,
        "receipt_path": str(path),
        "receipt_sha256": spec["sha256"],
        "segments": int(receipt["segment_count"]),
    }


def _validate_rollback(rollback: Any) -> dict[str, Any]:
    if not isinstance(rollback, dict):
        raise ValueError("rollback/unload evidence missing")
    expected = {
        "provider_unloaded": True,
        "active_resource_leases_after": 0,
        "temporary_assets_removed": True,
        "pending_streams_after": 0,
    }
    for key, value in expected.items():
        if rollback.get(key) != value:
            raise ValueError(f"rollback invariant failed: {key}")
    return dict(expected)


def _consent_valid(consent: Any, *, cloning: bool) -> bool:
    if not isinstance(consent, dict):
        return False
    if consent.get("status") != "GRANTED" or consent.get("subject_authorized") is not True:
        return False
    scopes = consent.get("scope")
    scopes = {scopes} if isinstance(scopes, str) else set(scopes or [])
    required = {"VOICE_SYNTHESIS"}
    if cloning:
        required.add("VOICE_CLONING")
    if not required.issubset(scopes):
        return False
    if not str(consent.get("purpose", "")).strip():
        return False
    if not str(consent.get("provenance_ref", "")).strip():
        return False
    if not str(consent.get("revocation_ref", "")).strip():
        return False
    if consent.get("revoked") is True:
        return False
    try:
        expires = dt.datetime.fromisoformat(str(consent.get("expires_at", "")).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=dt.timezone.utc)
        if expires <= dt.datetime.now(dt.timezone.utc):
            return False
    except Exception:
        return False
    return True


def _validate_common(root: Path, bundle_path: Path, bundle: dict[str, Any], subject_id: str) -> dict[str, Any]:
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("subject_id") != subject_id:
        raise ValueError("voice capability bundle schema/subject mismatch")
    if bundle.get("repository_head") != repo_head(root):
        raise ValueError("voice capability bundle repository HEAD mismatch")
    if not fresh_timestamp(bundle.get("captured_at")):
        raise ValueError("voice capability bundle is stale")
    if bundle.get("current_host") is not True or bundle.get("synthetic") is not False:
        raise ValueError("voice capability bundle is not real current-host evidence")
    if bundle.get("global_promotion_claim") is not False:
        raise ValueError("voice capability bundle attempted global promotion")
    if normalize_locale(bundle.get("locale")) != "hu-HU":
        raise ValueError("voice capability bundle locale must be hu-HU")
    provider = _validate_provider(root, bundle_path, bundle.get("provider"))
    rights = _validate_rights(bundle.get("license_and_rights"))
    audio = _validate_audio(bundle_path, bundle)
    if provider["output_audio_sha256"] != audio["native_sha256"]:
        raise ValueError("provider receipt output does not match native master")
    rollback = _validate_rollback(bundle.get("rollback"))
    return {
        "provider": provider,
        "rights": rights,
        "audio": audio,
        "rollback": rollback,
    }


def _validate_cap115(root: Path, bundle_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    common = _validate_common(root, bundle_path, bundle, "CAP-115")
    quality = _validate_hu_aqc(
        root,
        bundle_path,
        bundle.get("quality"),
        cloning=False,
        expected_audio_sha256=common["audio"]["native_sha256"],
    )
    stt = _validate_stt(root, bundle_path, bundle.get("stt"))
    control = bundle.get("control_surface", {})
    if not (
        isinstance(control, dict)
        and control.get("central_gateway_mediated") is True
        and control.get("direct_provider_client") is False
        and control.get("provider_session_authority") is False
        and control.get("voice_identity_ref_bound") is True
        and str(control.get("session_id", "")).strip()
    ):
        raise ValueError("CAP-115 control-surface/session mediation proof incomplete")
    return {**common, "quality": quality, "stt": stt, "control_surface": control}


def _validate_streaming(streaming: Any) -> dict[str, Any]:
    if not isinstance(streaming, dict):
        raise ValueError("streaming evidence missing")
    chunk_count = int(streaming.get("chunk_count", 0))
    first_ms = float(streaming.get("first_audio_ms", -1))
    completion_ms = float(streaming.get("completion_ms", -1))
    audio_seconds = float(streaming.get("audio_duration_seconds", 0))
    wall_seconds = float(streaming.get("wall_time_seconds", 0))
    rtf = float(streaming.get("real_time_factor", 999))
    if streaming.get("requested") is not True or chunk_count < 2:
        raise ValueError("CAP-116 requires true streaming with at least two chunks")
    if first_ms < 0 or completion_ms <= first_ms:
        raise ValueError("first audio must precede completion")
    if audio_seconds <= 0 or wall_seconds <= 0:
        raise ValueError("streaming timing durations invalid")
    calculated = wall_seconds / audio_seconds
    if abs(calculated - rtf) > 0.02:
        raise ValueError("streaming real-time factor does not match durations")
    if rtf > 1.0:
        raise ValueError("CAP-116 real-time factor exceeds 1.0")
    if streaming.get("session_correlation_bound") is not True:
        raise ValueError("streaming session correlation is not bound")
    if streaming.get("provider_session_authority") is not False:
        raise ValueError("provider cannot own conversational session authority")
    return {
        "chunk_count": chunk_count,
        "first_audio_ms": first_ms,
        "completion_ms": completion_ms,
        "real_time_factor": rtf,
    }


def _validate_cap116(root: Path, bundle_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    common = _validate_common(root, bundle_path, bundle, "CAP-116")
    quality = _validate_hu_aqc(
        root,
        bundle_path,
        bundle.get("quality"),
        cloning=False,
        expected_audio_sha256=common["audio"]["native_sha256"],
    )
    stt = _validate_stt(root, bundle_path, bundle.get("stt"))
    streaming = _validate_streaming(bundle.get("streaming"))
    return {**common, "quality": quality, "stt": stt, "streaming": streaming}


def _validate_cap117(root: Path, bundle_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    common = _validate_common(root, bundle_path, bundle, "CAP-117")
    production = bundle.get("production", {})
    mode = str(production.get("mode", "")).strip()
    cloning = mode in CLONING_MODES
    if not cloning:
        raise ValueError("CAP-117 production proof requires a cloning/human-reference voice mode")
    if not _consent_valid(production.get("consent"), cloning=True):
        raise ValueError("CAP-117 cloning consent is missing, expired, revoked or scope-insufficient")
    reference = production.get("reference", {})
    audio_hash = str(reference.get("audio_sha256", "")).lower()
    consumed_hash = str(reference.get("consumed_audio_sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", audio_hash) or audio_hash != consumed_hash:
        raise ValueError("CAP-117 reference audio hash lineage mismatch")
    if production.get("synthetic_disclosure") is not True:
        raise ValueError("CAP-117 synthetic disclosure missing")
    if production.get("impersonation_fraud_disinformation_use") is not False:
        raise ValueError("CAP-117 forbidden misuse disposition missing")
    quality = _validate_hu_aqc(
        root,
        bundle_path,
        bundle.get("quality"),
        cloning=True,
        expected_audio_sha256=common["audio"]["native_sha256"],
    )
    return {
        **common,
        "quality": quality,
        "production": {
            "mode": mode,
            "consent": "PASS",
            "reference_audio_sha256": audio_hash,
            "synthetic_disclosure": True,
        },
    }


VALIDATORS = {
    "CAP-115": _validate_cap115,
    "CAP-116": _validate_cap116,
    "CAP-117": _validate_cap117,
}


def validate_bundle(root: Path, subject_id: str, bundle_path: Path | None = None) -> dict[str, Any]:
    if subject_id not in SUBJECTS:
        raise ValueError(f"unsupported voice capability subject: {subject_id}")
    path = (bundle_path or _bundle_path(root, subject_id)).resolve()
    bundle = loadj(path)
    details = VALIDATORS[subject_id](root.resolve(), path, bundle)
    return {
        "schema": "fa3.voice-capability-current-host-validation.v1",
        "subject_id": subject_id,
        "bundle_path": str(path),
        "bundle_sha256": sha256_file(path),
        "result": "PASS",
        "details": details,
    }


def _negative_cases(root: Path, subject_id: str) -> dict[str, bool]:
    policy = loadj(root / "canonical/FA3-VOICE-QUALITY-ROUTING-001.json")
    cases: dict[str, bool] = {}

    try:
        resolve_route(
            {"language": "hu-HU", "mode": "voice_clone"},
            {"FA3-PROVIDER-COSYVOICE-001"},
        )
        cases["cosyvoice_experimental_hu_not_production_route"] = False
    except VoicePolicyDenied:
        cases["cosyvoice_experimental_hu_not_production_route"] = True

    try:
        resolve_quality_route(
            policy=policy,
            language="hu-HU",
            requested_quality="PRODUCTION",
            workflow="MARKETING_PRODUCTION",
            admitted_provider_ids={"FA3-PROVIDER-XTTS-001"},
            provider_language_support={"FA3-PROVIDER-XTTS-001": {"hu-HU", "hu"}},
            hrb_accelerator_lease=False,
            accelerator_provider_ids={"FA3-PROVIDER-XTTS-001"},
        )
        cases["unleased_accelerator_route_denied"] = False
    except VoiceQualityRoutingDenied:
        cases["unleased_accelerator_route_denied"] = True

    cases["expired_consent_denied"] = not _consent_valid(
        {
            "status": "GRANTED",
            "scope": ["VOICE_SYNTHESIS", "VOICE_CLONING"],
            "subject_authorized": True,
            "purpose": "test",
            "provenance_ref": "p",
            "revocation_ref": "r",
            "revoked": False,
            "expires_at": "2000-01-01T00:00:00Z",
        },
        cloning=True,
    )
    cases["revoked_consent_denied"] = not _consent_valid(
        {
            "status": "GRANTED",
            "scope": ["VOICE_SYNTHESIS", "VOICE_CLONING"],
            "subject_authorized": True,
            "purpose": "test",
            "provenance_ref": "p",
            "revocation_ref": "r",
            "revoked": True,
            "expires_at": "2999-01-01T00:00:00Z",
        },
        cloning=True,
    )
    cases["scope_insufficient_consent_denied"] = not _consent_valid(
        {
            "status": "GRANTED",
            "scope": ["VOICE_SYNTHESIS"],
            "subject_authorized": True,
            "purpose": "test",
            "provenance_ref": "p",
            "revocation_ref": "r",
            "revoked": False,
            "expires_at": "2999-01-01T00:00:00Z",
        },
        cloning=True,
    )
    if subject_id == "CAP-116":
        try:
            _validate_streaming(
                {
                    "requested": True,
                    "chunk_count": 2,
                    "first_audio_ms": 100,
                    "completion_ms": 1200,
                    "audio_duration_seconds": 1.0,
                    "wall_time_seconds": 1.2,
                    "real_time_factor": 1.2,
                    "session_correlation_bound": True,
                    "provider_session_authority": False,
                }
            )
            cases["rtf_over_one_denied"] = False
        except ValueError:
            cases["rtf_over_one_denied"] = True
    return cases


def _rollback_probe(scope: Path, subject_id: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    state = scope / f"{subject_id.lower()}-voice-state.json"
    baseline_obj = {
        "subject_id": subject_id,
        "provider_session_authority": False,
        "active_resource_leases": 0,
        "provider_loaded": False,
        "temporary_assets": [],
        "state": "BASELINE",
    }
    baseline = (
        json.dumps(baseline_obj, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    state.write_bytes(baseline)
    pre = hashlib.sha256(baseline).hexdigest()
    fault = dict(baseline_obj)
    fault.update(
        {
            "provider_session_authority": True,
            "active_resource_leases": 1,
            "provider_loaded": True,
            "temporary_assets": ["transient.wav"],
            "state": "FAULT_INJECTED",
        }
    )
    writej(state, fault)
    mutated = sha256_file(state)
    state.write_bytes(baseline)
    post = sha256_file(state)
    with tempfile.TemporaryDirectory(prefix="voice-cap-", dir=scope) as td:
        transient = Path(td)
        (transient / "temp.wav").write_bytes(b"FA3 transient voice artifact")
        transient_path = transient
    destroyed = not transient_path.exists()
    if pre != post or pre == mutated or not destroyed:
        raise RuntimeError("voice rollback probe failed")
    return {
        "pre_sha256": pre,
        "mutated_sha256": mutated,
        "post_sha256": post,
        "rollback_hash_equal": pre == post,
        "ephemeral_workspace_destroyed": destroyed,
    }


def validate_static_voice_gates(root: Path) -> dict[str, Any]:
    voice = voice_gate(root)
    if voice.get("result") != "PASS":
        raise RuntimeError("provider-neutral voice synthesis canonical gate is not PASS")
    return {
        "voice_synthesis_gate": voice.get("result"),
        "current_host_production_claim": voice.get("current_host_production_claim"),
        "hungarian_quality_claim": voice.get("hungarian_quality_claim"),
    }


def run_mode(
    root: Path,
    subject_id: str,
    mode: str,
    scope: Path,
    *,
    bundle_path: Path | None = None,
) -> dict[str, Any]:
    if subject_id not in SUBJECTS or mode not in MODES:
        raise ValueError("unsupported subject/mode")
    coverage = validate_coverage(root, subject_id)
    static = validate_static_voice_gates(root)
    bundle = validate_bundle(root, subject_id, bundle_path)
    if mode == "positive":
        return {
            "mode": mode,
            "status": "PASS",
            "coverage_count": len(coverage),
            "static_gates": static,
            "bundle": bundle,
        }
    if mode == "negative":
        cases = _negative_cases(root, subject_id)
        if not cases or not all(cases.values()):
            raise RuntimeError("voice negative matrix admitted forbidden path")
        return {
            "mode": mode,
            "status": "PASS",
            "coverage_count": len(coverage),
            "static_gates": static,
            "bundle": bundle,
            "negative_cases": cases,
        }
    rollback = _rollback_probe(scope, subject_id)
    return {
        "mode": mode,
        "status": "PASS",
        "coverage_count": len(coverage),
        "static_gates": static,
        "bundle": bundle,
        "rollback_probe": rollback,
    }


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FA3 CAP-115/116/117 provider-neutral current-host qualification producer"
    )
    parser.add_argument("--subject-id", choices=SUBJECTS, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if required_env("FA3_CAPABILITY_ID") != args.subject_id:
            raise RuntimeError("producer subject does not match orchestrator capability")
        root = Path(required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, args.subject_id, args.mode, scope)
        artifact = scope / "voice-capability-current-host-evidence.json"
        payload = {
            "schema": "fa3.voice-capability-current-host-evidence.v1",
            "subject_id": args.subject_id,
            "test_kind": required_env("FA3_TEST_KIND"),
            "test_id": required_env("FA3_TEST_ID"),
            "qualification_id": required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": required_env("FA3_CONSTITUENT_ID"),
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "result": result,
        }
        writej(artifact, payload)
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": required_env("FA3_CONSTITUENT_ID"),
            "subject_id": args.subject_id,
            "test_kind": required_env("FA3_TEST_KIND"),
            "test_id": required_env("FA3_TEST_ID"),
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "source_evidence_class": required_env("FA3_SOURCE_EVIDENCE_CLASS"),
            "covers_source_decision_ids": json.loads(
                required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON")
            ),
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": sha256_file(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
