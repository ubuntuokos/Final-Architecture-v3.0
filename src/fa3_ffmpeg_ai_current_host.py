#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
PROFILE_ID = "FA3-NEURAL-MEDIA-EXECUTION-001"
FFMPEG_PROVIDER_ID = "FA3-PROVIDER-FFMPEG-001"
CURRENT_HOST_GATE_ID = "FA3-FFMPEG-AI-CURRENT-HOST-GATESET-001"
CURRENT_HOST_EXECUTABLE_GATE_ID = "FA3-GATE-FFMPEG-AI-CURRENT-HOST-001"
CURRENT_HOST_CONFORMANCE_ID = "FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001"
EVIDENCE_LEVEL = "CURRENT_HOST_FFMPEG_EXECUTION_CONFORMANCE_PASS"
PRODUCTION_EVIDENCE_LEVEL = "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS"
HRB_AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
HRB_PROFILE_ID = "FA3-HOST-RESOURCE-BROKER-001"
HRB_LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
HARDWARE_PROFILE_ID = "FA3-HARDWARE-BASELINE-001"
HARDWARE_DISCOVERY_CONTRACT_ID = "FA3-HARDWARE-DISCOVERY-CONTRACTS-001"

REQUIRED_BUILD_FLAGS = {"--enable-libonnxruntime", "--enable-libopenvino", "--enable-libvmaf"}
REQUIRED_FILTERS = {"dnn_processing", "libvmaf", "ssim", "psnr", "scale_cuda"}
REQUIRED_ENCODERS = {"h264_nvenc"}
REQUIRED_DECODERS = {"h264_cuvid"}
REQUIRED_HWACCELS = {"cuda"}

# Deterministic smoke-fixture acceptance only. These are NOT portable production-quality policy.
SMOKE_FIXTURE_THRESHOLDS = {
    "vmaf_min": 80.0,
    "ssim_min": 0.95,
    "psnr_min_db": 30.0,
    "av_duration_delta_max_seconds": 0.075,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_json(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", value) is not None


def normalize_bdf(value: Any) -> str:
    value = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{8}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", value):
        value = value[-12:]
    if re.fullmatch(r"[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", value):
        value = "0000:" + value
    return value


def valid_bdf(value: Any) -> bool:
    return re.fullmatch(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", normalize_bdf(value)) is not None


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        out.append(b | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _key(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _v(field: int, value: int) -> bytes:
    return _key(field, 0) + _varint(value)


def _b(field: int, payload: bytes) -> bytes:
    return _key(field, 2) + _varint(len(payload)) + payload


def _s(field: int, value: str) -> bytes:
    return _b(field, value.encode("utf-8"))


def build_identity_onnx(width: int = 64, height: int = 64) -> bytes:
    """Dependency-free FLOAT32 NCHW single-input ONNX Identity smoke model."""
    if width < 1 or height < 1:
        raise ValueError("invalid shape")

    def dim(n: int) -> bytes:
        return _b(1, _v(1, n))

    shape = b"".join(dim(n) for n in (1, 3, height, width))
    tensor_type = _v(1, 1) + _b(2, shape)  # TensorProto.FLOAT == 1
    type_proto = _b(1, tensor_type)

    def vi(name: str) -> bytes:
        return _s(1, name) + _b(2, type_proto)

    node = _s(1, "input") + _s(2, "output") + _s(3, "fa3_identity") + _s(4, "Identity")
    graph = _b(1, node) + _s(2, "fa3_ffmpeg_identity_graph") + _b(11, vi("input")) + _b(12, vi("output"))
    return _v(1, 8) + _s(2, "fa3") + _s(3, "2.0") + _b(7, graph) + _b(8, _v(2, 13))


def parse_ffmpeg_version(text: str) -> str | None:
    m = re.search(r"^ffmpeg version\s+([^\s]+)", text or "", flags=re.MULTILINE)
    return m.group(1) if m else None


def observed_onnx_provider(log_text: str) -> str:
    text = log_text or ""
    if re.search(r"falling back to cpu", text, re.I):
        return "FALLBACK_CPU"
    if re.search(r"Using CUDA execution provider on device\s+\d+", text):
        return "cuda"
    if re.search(r"Using CPU execution provider", text):
        return "cpu"
    return "UNKNOWN"


def feature_manifest_valid(feature: dict[str, Any]) -> bool:
    return bool(
        valid_digest(feature.get("ffmpeg_binary_sha256"))
        and valid_digest(feature.get("ffprobe_binary_sha256"))
        and parse_ffmpeg_version(feature.get("version_first_line", ""))
        and REQUIRED_BUILD_FLAGS <= set(feature.get("build_flags", []))
        and REQUIRED_FILTERS <= set(feature.get("filters", []))
        and REQUIRED_ENCODERS <= set(feature.get("encoders", []))
        and REQUIRED_DECODERS <= set(feature.get("decoders", []))
        and REQUIRED_HWACCELS <= set(feature.get("hwaccels", []))
    )


def build_trust_receipt_valid(value: dict[str, Any], feature: dict[str, Any]) -> bool:
    observed = parse_ffmpeg_version(feature.get("version_first_line", ""))
    verifier = value.get("verifier", {})
    signing = value.get("signing_identity", {})
    identity = str(value.get("immutable_version_identity", ""))
    return bool(
        value.get("schema") == "fa3.ffmpeg-build-trust-receipt.v2"
        and value.get("status") == "PASS"
        and value.get("trust_mode") in {"UPSTREAM_SIGNED_RELEASE", "DISTRIBUTION_SIGNED_PACKAGE"}
        and value.get("release_channel") == "STABLE"
        and value.get("signature_verified") is True
        and value.get("floating_master_or_nightly") is False
        and observed
        and value.get("observed_ffmpeg_version") == observed
        and identity
        and not re.search(r"(?:master|snapshot|nightly)", identity, re.I)
        and value.get("installed_ffmpeg_binary_sha256") == feature.get("ffmpeg_binary_sha256")
        and valid_digest(value.get("source_or_package_sha256"))
        and valid_digest(value.get("sbom_sha256"))
        and valid_digest(value.get("provenance_attestation_sha256"))
        and isinstance(verifier, dict)
        and bool(verifier.get("tool"))
        and bool(verifier.get("version"))
        and bool(verifier.get("verification_method"))
        and valid_digest(verifier.get("verification_result_sha256"))
        and isinstance(signing, dict)
        and bool(signing.get("type"))
        and bool(signing.get("value"))
    )


def hardware_snapshot_valid(hw: dict[str, Any]) -> bool:
    """Portable hardware evidence: no vendor/model/socket-count pinning."""
    try:
        online = hw.get("online_logical_cpus", [])
        effective = hw.get("effective_logical_cpus", [])
        return bool(
            hw.get("source") == "LIVE_SYSFS_PROCFS_CGROUP_NVML"
            and hw.get("hardware_profile_id") == HARDWARE_PROFILE_ID
            and hw.get("hardware_discovery_contract_id") == HARDWARE_DISCOVERY_CONTRACT_ID
            and hw.get("reference_host_is_normative") is False
            and isinstance(online, list) and online
            and isinstance(effective, list) and effective
            and set(effective) <= set(online)
            and int(hw.get("host_package_count", 0)) >= 1
            and int(hw.get("host_physical_core_count", 0)) >= 8
            and int(hw.get("effective_physical_core_count", 0)) >= 1
            and valid_digest(hw.get("fingerprint_sha256"))
        )
    except (TypeError, ValueError):
        return False


def _lease_time_valid(lease: dict[str, Any], now_epoch: int | None = None) -> bool:
    now_epoch = int(time.time()) if now_epoch is None else int(now_epoch)
    try:
        return int(lease.get("issued_epoch", now_epoch + 1)) <= now_epoch < int(lease.get("expires_epoch", 0))
    except (TypeError, ValueError):
        return False


def broker_validation_valid(v: dict[str, Any], lease_sha256: str) -> bool:
    return bool(
        v.get("schema") == "fa3.hrb-lease-validation-evidence.v1"
        and v.get("authority_id") == HRB_AUTHORITY_ID
        and v.get("profile_id") == HRB_PROFILE_ID
        and v.get("status") == "VALID"
        and v.get("lease_sha256") == lease_sha256
        and valid_digest(v.get("verifier_binary_sha256"))
        and valid_digest(v.get("command_sha256"))
        and valid_digest(v.get("stdout_sha256"))
    )


def hrb_lease_valid(lease: dict[str, Any], live_gpus: list[dict[str, Any]], broker_validation: dict[str, Any], now_epoch: int | None = None) -> bool:
    required = {"schema", "lease_id", "issuer", "accelerator_uuid", "memory_max_bytes", "expires_epoch", "issued_epoch", "purpose", "host", "status", "nonce", "placement", "enforcement", "signature"}
    if not required <= set(lease):
        return False
    sig = lease.get("signature", {})
    placement = lease.get("placement", {})
    lease_hash = digest_json(lease)
    if not (
        lease.get("schema") == HRB_LEASE_SCHEMA
        and lease.get("issuer") == HRB_PROFILE_ID
        and lease.get("status") == "ACTIVE"
        and str(lease.get("accelerator_uuid", "")).startswith("GPU-")
        and int(lease.get("memory_max_bytes", 0)) > 0
        and str(lease.get("purpose", "")).startswith("FA3 FFmpeg")
        and isinstance(placement, dict)
        and valid_bdf(placement.get("pci_bus_id"))
        and "numa_node" in placement
        and isinstance(lease.get("enforcement"), dict)
        and isinstance(sig, dict)
        and sig.get("alg") == "HMAC-SHA256"
        and sig.get("key_id") == "host-local-v1"
        and re.fullmatch(r"[0-9a-f]{64}", str(sig.get("value", "")))
        and _lease_time_valid(lease, now_epoch)
        and broker_validation_valid(broker_validation, lease_hash)
    ):
        return False
    uuid = str(lease["accelerator_uuid"])
    bus = normalize_bdf(placement["pci_bus_id"])
    return sum(str(g.get("uuid")) == uuid and normalize_bdf(g.get("pci_bdf")) == bus for g in live_gpus) == 1


def hrb_receipt_valid(value: dict[str, Any], live_gpus: list[dict[str, Any]], now: datetime | None = None, broker_validation: dict[str, Any] | None = None) -> bool:
    """Compatibility alias: only canonical AcceleratorExecutionLease@1 is accepted."""
    epoch = int((now or datetime.now(timezone.utc)).timestamp())
    return hrb_lease_valid(value, live_gpus, broker_validation or {}, epoch)


def resolved_runtime_index(lease: dict[str, Any], live_gpus: list[dict[str, Any]], broker_validation: dict[str, Any] | None = None) -> int | None:
    if not hrb_lease_valid(lease, live_gpus, broker_validation or {}):
        return None
    uuid = str(lease["accelerator_uuid"])
    bus = normalize_bdf(lease["placement"]["pci_bus_id"])
    for gpu in live_gpus:
        if str(gpu.get("uuid")) == uuid and normalize_bdf(gpu.get("pci_bdf")) == bus:
            try:
                return int(gpu["index"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def quality_valid(q: dict[str, Any]) -> bool:
    try:
        return bool(
            q.get("status") == "PASS"
            and q.get("threshold_policy") == "DETERMINISTIC_SMOKE_FIXTURE_NOT_PRODUCTION_QUALITY_POLICY"
            and float(q.get("vmaf", -1)) >= SMOKE_FIXTURE_THRESHOLDS["vmaf_min"]
            and float(q.get("ssim", -1)) >= SMOKE_FIXTURE_THRESHOLDS["ssim_min"]
            and float(q.get("psnr_db", -1)) >= SMOKE_FIXTURE_THRESHOLDS["psnr_min_db"]
            and float(q.get("av_duration_delta_seconds", 999)) <= SMOKE_FIXTURE_THRESHOLDS["av_duration_delta_max_seconds"]
            and q.get("timestamps_monotonic") is True
            and q.get("color_primaries") == "bt709"
            and q.get("color_transfer") == "bt709"
            and q.get("color_space") == "bt709"
            and q.get("hdr_expected") is False
            and q.get("hdr_absence_validated") is True
        )
    except (TypeError, ValueError):
        return False


def media_validation_valid(m: dict[str, Any]) -> bool:
    return bool(
        m.get("status") == "PASS"
        and m.get("container_mp4_validated") is True
        and m.get("video_codec") == "h264"
        and m.get("audio_codec") == "aac"
        and m.get("video_stream_count") == 1
        and m.get("audio_stream_count") == 1
        and m.get("width") == 320
        and m.get("height") == 180
        and str(m.get("audio_sample_rate")) == "48000"
    )


def validate_current_host_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    fs: list[dict[str, Any]] = []
    def fail(code: str, message: str) -> None:
        fs.append({"code": code, "severity": "P0", "message": message})

    if not (receipt.get("schema") == "fa3.ffmpeg-ai-current-host-receipt.v2" and receipt.get("conformance_id") == CURRENT_HOST_CONFORMANCE_ID and receipt.get("status") == "PASS" and receipt.get("evidence_level") == EVIDENCE_LEVEL and receipt.get("production_e2e_claim") is False):
        fail("FFMPEG-AI-HOST-001", "execution-conformance receipt identity/evidence semantics mismatch")
    if not hardware_snapshot_valid(receipt.get("hardware", {})):
        fail("FFMPEG-AI-HOST-002", "portable live hardware discovery evidence invalid")
    feature = receipt.get("ffmpeg_feature_manifest", {})
    if not feature_manifest_valid(feature):
        fail("FFMPEG-AI-HOST-003", "FFmpeg build/filter/codec capability manifest incomplete")
    if not build_trust_receipt_valid(receipt.get("ffmpeg_build_trust", {}), feature):
        fail("FFMPEG-AI-HOST-004", "FFmpeg build trust/provenance evidence invalid")

    gpus = receipt.get("live_gpus", [])
    lease = receipt.get("hrb_accelerator_lease", {})
    broker = receipt.get("hrb_broker_validation", {})
    if not hrb_lease_valid(lease, gpus, broker):
        fail("FFMPEG-AI-HOST-005", "canonical HRB AcceleratorExecutionLease@1 is invalid/unverified/mismatched")
    resolved = receipt.get("accelerator_resolution", {})
    if not (resolved.get("canonical_identity") == "UUID_PLUS_PCI_BDF" and resolved.get("ordinal_is_ephemeral") is True and resolved.get("runtime_index_resolved_from_uuid_bdf") is True and resolved.get("runtime_index") == resolved_runtime_index(lease, gpus, broker)):
        fail("FFMPEG-AI-HOST-006", "CUDA ordinal was not derived from canonical HRB UUID+BDF identity")

    dnn = receipt.get("onnx_cuda_dnn", {})
    if not (dnn.get("status") == "PASS" and dnn.get("requested_provider") == "cuda" and dnn.get("observed_provider") == "cuda" and dnn.get("silent_cpu_fallback_observed") is False and dnn.get("identity_model_generated_locally") is True and dnn.get("model_is_smoke_fixture_not_production_model") is True and valid_digest(dnn.get("model_sha256")) and dnn.get("model_contract") == "4D_NCHW_FLOAT32_SINGLE_INPUT" and valid_digest(dnn.get("cpu_framemd5_sha256")) and dnn.get("cpu_framemd5_sha256") == dnn.get("cuda_framemd5_sha256")):
        fail("FFMPEG-AI-HOST-007", "observed ONNX CUDA execution proof incomplete or CPU fallback detected")

    media = receipt.get("gpu_media_e2e", {})
    if not (media.get("status") == "PASS" and media.get("hardware_decode_requested") is True and media.get("hardware_decode_observed") is True and media.get("cuda_filter_requested") is True and media.get("cuda_filter_observed") is True and media.get("nvenc_encode_requested") is True and media.get("nvenc_encode_observed") is True and media.get("gpu_uuid") == lease.get("accelerator_uuid") and normalize_bdf(media.get("pci_bdf")) == normalize_bdf(lease.get("placement", {}).get("pci_bus_id")) and valid_digest(media.get("source_sha256")) and valid_digest(media.get("output_sha256"))):
        fail("FFMPEG-AI-HOST-008", "observed hardware decode/CUDA-filter/NVENC E2E evidence incomplete")

    copies = receipt.get("copy_boundary_evidence", {})
    if not (copies.get("zero_copy_claimed") is False and copies.get("stable_ffmpeg_dnn_cuda_hwframe_baseline") is False and copies.get("dnn_cpu_gpu_transfer_expected") is True and copies.get("gpu_media_pipeline_hwdownload_present") is False and copies.get("gpu_media_pipeline_hwupload_present") is False):
        fail("FFMPEG-AI-HOST-009", "copy-boundary/zero-copy semantics invalid")
    if not quality_valid(receipt.get("quality", {})) or not media_validation_valid(receipt.get("media_validation", {})):
        fail("FFMPEG-AI-HOST-010", "smoke QA/container/codec/A-V/timestamp/color validation failed")

    neg = receipt.get("negative_tests", {})
    required_neg = {"missing_hrb_denied", "wrong_hrb_issuer_denied", "expired_hrb_denied", "uuid_bdf_mismatch_denied", "invalid_broker_validation_denied", "ordinal_only_identity_denied", "silent_cuda_to_cpu_fallback_denied", "weak_build_trust_denied", "zero_copy_claim_denied", "missing_quality_metrics_denied"}
    if set(neg) != required_neg or not all(neg.values()):
        fail("FFMPEG-AI-HOST-011", "required fail-closed negative tests incomplete")

    rollback = receipt.get("rollback", {})
    if not (rollback.get("status") == "PASS" and rollback.get("persistent_environment_mutation") is False and rollback.get("persistent_system_configuration_mutation") is False and rollback.get("network_model_fetch_performed") is False and rollback.get("temporary_workspace_cleanable") is True and rollback.get("failure_injection_cleanup_pass") is True):
        fail("FFMPEG-AI-HOST-012", "rollback/cleanup evidence incomplete")

    provenance = receipt.get("provenance", {})
    chain_material = provenance.get("chain_material", {})
    if not (valid_digest(provenance.get("chain_sha256")) and provenance.get("chain_sha256") == digest_json(chain_material) and all(valid_digest(v) for v in chain_material.values())):
        fail("FFMPEG-AI-HOST-013", "execution evidence provenance chain incomplete")

    if not (receipt.get("production_e2e_required_separately") is True and receipt.get("production_evidence_level_required") == PRODUCTION_EVIDENCE_LEVEL and receipt.get("vs_mlrt_runtime") == "DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_FFMPEG_PRIMARY_CONFORMANCE" and receipt.get("new_capabilities") == 0 and receipt.get("new_architectural_authorities") == 0 and receipt.get("capability_count_after") == CAPABILITY_COUNT and receipt.get("global_promotion_claim") is False):
        fail("FFMPEG-AI-HOST-014", "production-evidence/capability/authority/promotion invariant drift")
    return fs


def make_reference_receipt() -> dict[str, Any]:
    """Synthetic unit-test fixture only; gate must reject it as current-host evidence."""
    now = int(time.time())
    gpu = {"index": 1, "uuid": "GPU-test", "pci_bdf": "0000:05:00.0", "name": "NVIDIA GeForce RTX 3080"}
    lease = {
        "schema": HRB_LEASE_SCHEMA, "lease_id": "lease-test", "issuer": HRB_PROFILE_ID,
        "accelerator_uuid": "GPU-test", "memory_max_bytes": 1024, "expires_epoch": now + 3600,
        "issued_epoch": now - 1, "purpose": "FA3 FFmpeg neural-media smoke", "host": "fixture",
        "status": "ACTIVE", "nonce": "fixture", "placement": {"pci_bus_id": "0000:05:00.0", "numa_node": 0},
        "enforcement": {"mode": "fixture"}, "signature": {"alg": "HMAC-SHA256", "key_id": "host-local-v1", "value": "1" * 64},
    }
    lease_hash = digest_json(lease)
    broker = {"schema": "fa3.hrb-lease-validation-evidence.v1", "authority_id": HRB_AUTHORITY_ID, "profile_id": HRB_PROFILE_ID, "status": "VALID", "lease_sha256": lease_hash, "verifier_binary_sha256": "2"*64, "command_sha256": "3"*64, "stdout_sha256": "4"*64}
    ffhash = "5" * 64
    feature = {"ffmpeg_binary_sha256": ffhash, "ffprobe_binary_sha256": "6"*64, "version_first_line": "ffmpeg version 9.0.1", "build_flags": sorted(REQUIRED_BUILD_FLAGS), "filters": sorted(REQUIRED_FILTERS), "encoders": sorted(REQUIRED_ENCODERS), "decoders": sorted(REQUIRED_DECODERS), "hwaccels": sorted(REQUIRED_HWACCELS)}
    trust = {"schema": "fa3.ffmpeg-build-trust-receipt.v2", "status": "PASS", "trust_mode": "UPSTREAM_SIGNED_RELEASE", "release_channel": "STABLE", "signature_verified": True, "floating_master_or_nightly": False, "observed_ffmpeg_version": "9.0.1", "immutable_version_identity": "n9.0.1", "installed_ffmpeg_binary_sha256": ffhash, "source_or_package_sha256": "7"*64, "sbom_sha256": "8"*64, "provenance_attestation_sha256": "9"*64, "verifier": {"tool": "gpg", "version": "fixture", "verification_method": "detached-signature", "verification_result_sha256": "a"*64}, "signing_identity": {"type": "key-fingerprint", "value": "fixture"}}
    chain = {"source_sha256": "b"*64, "model_sha256": "c"*64, "output_sha256": "d"*64, "ffmpeg_binary_sha256": ffhash, "ffprobe_binary_sha256": "6"*64, "hrb_lease_sha256": lease_hash, "hrb_validation_sha256": digest_json(broker), "build_trust_sha256": digest_json(trust), "vmaf_artifact_sha256": "e"*64}
    return {
        "schema": "fa3.ffmpeg-ai-current-host-receipt.v2", "conformance_id": CURRENT_HOST_CONFORMANCE_ID,
        "status": "PASS", "evidence_level": EVIDENCE_LEVEL, "fixture_semantics": "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST",
        "production_e2e_claim": False, "production_e2e_required_separately": True, "production_evidence_level_required": PRODUCTION_EVIDENCE_LEVEL,
        "hardware": {"source": "LIVE_SYSFS_PROCFS_CGROUP_NVML", "hardware_profile_id": HARDWARE_PROFILE_ID, "hardware_discovery_contract_id": HARDWARE_DISCOVERY_CONTRACT_ID, "reference_host_is_normative": False, "online_logical_cpus": list(range(8)), "effective_logical_cpus": list(range(8)), "host_package_count": 1, "host_physical_core_count": 8, "effective_physical_core_count": 8, "fingerprint_sha256": "f"*64},
        "ffmpeg_feature_manifest": feature, "ffmpeg_build_trust": trust, "live_gpus": [gpu], "hrb_accelerator_lease": lease, "hrb_broker_validation": broker,
        "accelerator_resolution": {"canonical_identity": "UUID_PLUS_PCI_BDF", "ordinal_is_ephemeral": True, "runtime_index_resolved_from_uuid_bdf": True, "runtime_index": 1},
        "onnx_cuda_dnn": {"status": "PASS", "requested_provider": "cuda", "observed_provider": "cuda", "silent_cpu_fallback_observed": False, "identity_model_generated_locally": True, "model_is_smoke_fixture_not_production_model": True, "model_sha256": "c"*64, "model_contract": "4D_NCHW_FLOAT32_SINGLE_INPUT", "cpu_framemd5_sha256": "0"*64, "cuda_framemd5_sha256": "0"*64},
        "gpu_media_e2e": {"status": "PASS", "hardware_decode_requested": True, "hardware_decode_observed": True, "cuda_filter_requested": True, "cuda_filter_observed": True, "nvenc_encode_requested": True, "nvenc_encode_observed": True, "gpu_uuid": "GPU-test", "pci_bdf": "0000:05:00.0", "source_sha256": "b"*64, "output_sha256": "d"*64},
        "copy_boundary_evidence": {"zero_copy_claimed": False, "stable_ffmpeg_dnn_cuda_hwframe_baseline": False, "dnn_cpu_gpu_transfer_expected": True, "gpu_media_pipeline_hwdownload_present": False, "gpu_media_pipeline_hwupload_present": False},
        "quality": {"status": "PASS", "threshold_policy": "DETERMINISTIC_SMOKE_FIXTURE_NOT_PRODUCTION_QUALITY_POLICY", "vmaf": 95.0, "ssim": 0.99, "psnr_db": 40.0, "av_duration_delta_seconds": 0.01, "timestamps_monotonic": True, "color_primaries": "bt709", "color_transfer": "bt709", "color_space": "bt709", "hdr_expected": False, "hdr_absence_validated": True},
        "media_validation": {"status": "PASS", "container_mp4_validated": True, "video_codec": "h264", "audio_codec": "aac", "video_stream_count": 1, "audio_stream_count": 1, "width": 320, "height": 180, "audio_sample_rate": "48000"},
        "negative_tests": {"missing_hrb_denied": True, "wrong_hrb_issuer_denied": True, "expired_hrb_denied": True, "uuid_bdf_mismatch_denied": True, "invalid_broker_validation_denied": True, "ordinal_only_identity_denied": True, "silent_cuda_to_cpu_fallback_denied": True, "weak_build_trust_denied": True, "zero_copy_claim_denied": True, "missing_quality_metrics_denied": True},
        "rollback": {"status": "PASS", "persistent_environment_mutation": False, "persistent_system_configuration_mutation": False, "network_model_fetch_performed": False, "temporary_workspace_cleanable": True, "failure_injection_cleanup_pass": True},
        "provenance": {"chain_material": chain, "chain_sha256": digest_json(chain)},
        "vs_mlrt_runtime": "DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_FFMPEG_PRIMARY_CONFORMANCE",
        "new_capabilities": 0, "new_architectural_authorities": 0, "capability_count_after": 143, "global_promotion_claim": False,
    }
