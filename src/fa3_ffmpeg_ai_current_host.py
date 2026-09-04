#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
PROFILE_ID = "FA3-NEURAL-MEDIA-EXECUTION-001"
FFMPEG_PROVIDER_ID = "FA3-PROVIDER-FFMPEG-001"
CURRENT_HOST_GATE_ID = "FA3-FFMPEG-AI-CURRENT-HOST-GATESET-001"
CURRENT_HOST_EXECUTABLE_GATE_ID = "FA3-GATE-FFMPEG-AI-CURRENT-HOST-001"
CURRENT_HOST_CONFORMANCE_ID = "FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001"
EVIDENCE_LEVEL = "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS"
HRB_AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
HRB_PROFILE_ID = "FA3-HOST-RESOURCE-BROKER-001"
HRB_LEASE_SCHEMA = "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
HARDWARE_BASELINE_ID = "FA3-HARDWARE-BASELINE-001"
REAL_MEDIA_PROVENANCE_SCHEMA = "fa3.real-media-input-provenance.v1"

REQUIRED_BUILD_FLAGS = {
    "--enable-libonnxruntime",
    "--enable-libopenvino",
    "--enable-libvmaf",
}
REQUIRED_FILTERS = {"dnn_processing", "libvmaf", "ssim", "psnr", "scale_cuda"}
REQUIRED_ENCODERS = {"h264_nvenc"}
REQUIRED_HWACCELS = {"cuda"}

QUALITY_THRESHOLDS = {
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
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(raw)


def _varint(value: int) -> bytes:
    if value < 0:
        value &= (1 << 64) - 1
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _key(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _v(field: int, value: int) -> bytes:
    return _key(field, 0) + _varint(value)


def _b(field: int, payload: bytes) -> bytes:
    return _key(field, 2) + _varint(len(payload)) + payload


def _s(field: int, value: str) -> bytes:
    return _b(field, value.encode("utf-8"))


def build_identity_onnx(width: int = 320, height: int = 180) -> bytes:
    """Dependency-free ONNX Identity model: FLOAT NCHW [1,3,H,W]."""
    if width < 1 or height < 1:
        raise ValueError("width and height must be positive")

    def dim(value: int) -> bytes:
        return _b(1, _v(1, value))

    shape = b"".join(dim(v) for v in (1, 3, height, width))
    tensor_type = _v(1, 1) + _b(2, shape)  # TensorProto.FLOAT == 1
    type_proto = _b(1, tensor_type)

    def value_info(name: str) -> bytes:
        return _s(1, name) + _b(2, type_proto)

    node = _s(1, "input") + _s(2, "output") + _s(3, "fa3_identity") + _s(4, "Identity")
    graph = _b(1, node) + _s(2, "fa3_ffmpeg_identity_graph") + _b(11, value_info("input")) + _b(12, value_info("output"))
    return _v(1, 8) + _s(2, "fa3") + _s(3, "2.0") + _b(7, graph) + _b(8, _v(2, 13))


def normalize_bdf(value: str) -> str:
    value = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{8}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", value):
        value = value[-12:]
    if re.fullmatch(r"[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", value):
        value = "0000:" + value
    return value


def valid_bdf(value: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", normalize_bdf(value)) is not None


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", value) is not None


def observed_onnx_provider(log_text: str) -> str:
    text = log_text or ""
    if re.search(r"falling back to cpu", text, flags=re.IGNORECASE):
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
        and REQUIRED_BUILD_FLAGS.issubset(set(feature.get("build_flags", [])))
        and REQUIRED_FILTERS.issubset(set(feature.get("filters", [])))
        and REQUIRED_ENCODERS.issubset(set(feature.get("encoders", [])))
        and REQUIRED_HWACCELS.issubset(set(feature.get("hwaccels", [])))
    )


def build_trust_receipt_valid(value: dict[str, Any], ffmpeg_sha256: str, ffprobe_sha256: str) -> bool:
    return bool(
        value.get("schema") == "fa3.ffmpeg-build-trust-receipt.v2"
        and value.get("status") == "PASS"
        and value.get("trust_mode") in {"UPSTREAM_SIGNED_RELEASE", "DISTRIBUTION_SIGNED_PACKAGE"}
        and value.get("signature_verified") is True
        and valid_digest(value.get("source_or_package_sha256"))
        and value.get("installed_ffmpeg_binary_sha256") == ffmpeg_sha256
        and value.get("installed_ffprobe_binary_sha256") == ffprobe_sha256
        and bool(value.get("immutable_version_identity"))
        and value.get("floating_master_or_nightly") is False
    )


def live_hardware_snapshot_valid(hw: dict[str, Any]) -> bool:
    per_package = hw.get("physical_cores_per_package")
    return bool(
        hw.get("source") == "LIVE_SYSFS_PROCFS_NVML"
        and isinstance(hw.get("machine"), str)
        and bool(hw.get("machine"))
        and isinstance(hw.get("cpu_models"), list)
        and bool(hw.get("cpu_models"))
        and isinstance(hw.get("packages"), int)
        and hw.get("packages", 0) >= 1
        and isinstance(hw.get("physical_cores"), int)
        and hw.get("physical_cores", 0) >= 1
        and isinstance(hw.get("logical_cpus"), int)
        and hw.get("logical_cpus", 0) >= hw.get("physical_cores", 0)
        and isinstance(hw.get("numa_domains"), int)
        and hw.get("numa_domains", 0) >= 1
        and isinstance(per_package, dict)
        and len(per_package) == hw.get("packages")
        and all(isinstance(v, int) and v >= 1 for v in per_package.values())
        and valid_digest(hw.get("fingerprint_sha256"))
        and hw.get("policy_binding") == HARDWARE_BASELINE_ID
        and hw.get("current_host_facts_are_evidence_only") is True
        and hw.get("reference_host_match_required") is False
    )


def hrb_lease_valid(value: dict[str, Any], live_gpus: list[dict[str, Any]], now_epoch: int | None = None) -> bool:
    now_epoch = int(datetime.now(timezone.utc).timestamp()) if now_epoch is None else int(now_epoch)
    placement = value.get("placement")
    signature = value.get("signature")
    if not (
        value.get("schema") == HRB_LEASE_SCHEMA
        and value.get("issuer") == HRB_PROFILE_ID
        and value.get("authority_id") == HRB_AUTHORITY_ID
        and value.get("status") == "ACTIVE"
        and value.get("lease_id")
        and str(value.get("accelerator_uuid", "")).startswith("GPU-")
        and int(value.get("memory_max_bytes", 0)) > 0
        and int(value.get("expires_epoch", 0)) > now_epoch
        and int(value.get("issued_epoch", 0)) > 0
        and str(value.get("purpose", "")).startswith("FA3 FFmpeg")
        and value.get("broker_validation") == "VALID"
        and isinstance(placement, dict)
        and valid_bdf(placement.get("pci_bus_id", ""))
        and isinstance(signature, dict)
        and signature.get("alg") == "HMAC-SHA256"
        and bool(signature.get("key_id"))
        and re.fullmatch(r"[0-9a-f]{64}", str(signature.get("value", ""))) is not None
    ):
        return False
    target_uuid = str(value["accelerator_uuid"])
    target_bdf = normalize_bdf(placement["pci_bus_id"])
    return sum(
        str(gpu.get("uuid", "")) == target_uuid and normalize_bdf(gpu.get("pci_bdf", "")) == target_bdf
        for gpu in live_gpus
    ) == 1


def resolved_runtime_index(value: dict[str, Any], live_gpus: list[dict[str, Any]]) -> int | None:
    if not hrb_lease_valid(value, live_gpus):
        return None
    target_uuid = str(value["accelerator_uuid"])
    target_bdf = normalize_bdf(value["placement"]["pci_bus_id"])
    for gpu in live_gpus:
        if str(gpu.get("uuid", "")) == target_uuid and normalize_bdf(gpu.get("pci_bdf", "")) == target_bdf:
            try:
                return int(gpu["index"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def real_media_provenance_valid(value: dict[str, Any], media_sha256: str) -> bool:
    return bool(
        value.get("schema") == REAL_MEDIA_PROVENANCE_SCHEMA
        and value.get("status") == "PASS"
        and value.get("synthetic") is False
        and value.get("source_kind") in {"USER_SUPPLIED", "PROJECT_ASSET", "CAPTURED_MEDIA"}
        and value.get("media_sha256") == media_sha256
        and value.get("usage_authorized") is True
    )


def quality_valid(q: dict[str, Any]) -> bool:
    try:
        return bool(
            q.get("status") == "PASS"
            and q.get("fixture_profile") == "REAL_MEDIA_SDR_BT709_GOLDEN_FIXTURE"
            and float(q.get("vmaf", -1)) >= QUALITY_THRESHOLDS["vmaf_min"]
            and float(q.get("ssim", -1)) >= QUALITY_THRESHOLDS["ssim_min"]
            and float(q.get("psnr_db", -1)) >= QUALITY_THRESHOLDS["psnr_min_db"]
            and float(q.get("av_duration_delta_seconds", 999)) <= QUALITY_THRESHOLDS["av_duration_delta_max_seconds"]
            and q.get("timestamps_monotonic") is True
            and q.get("expected_color") == {"primaries": "bt709", "transfer": "bt709", "space": "bt709"}
            and q.get("observed_color") == q.get("expected_color")
            and q.get("hdr_expected") is False
            and q.get("hdr_observed") is False
            and q.get("fixture_profile_is_evidence_only_not_provider_limit") is True
        )
    except (TypeError, ValueError):
        return False


def validate_current_host_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "severity": "P0", "message": message})

    if not (
        receipt.get("schema") == "fa3.ffmpeg-ai-current-host-receipt.v2"
        and receipt.get("conformance_id") == CURRENT_HOST_CONFORMANCE_ID
        and receipt.get("status") == "PASS"
        and receipt.get("evidence_level") == EVIDENCE_LEVEL
    ):
        fail("FFMPEG-AI-HOST-001", "production current-host receipt identity/status/evidence level mismatch")

    if not live_hardware_snapshot_valid(receipt.get("hardware", {})):
        fail("FFMPEG-AI-HOST-002", "live hardware discovery evidence is incomplete or incorrectly used as machine identity")

    feature = receipt.get("ffmpeg_feature_manifest", {})
    if not feature_manifest_valid(feature):
        fail("FFMPEG-AI-HOST-003", "FFmpeg build/filter/codec capability manifest incomplete")
    if not build_trust_receipt_valid(
        receipt.get("ffmpeg_build_trust", {}),
        feature.get("ffmpeg_binary_sha256", ""),
        feature.get("ffprobe_binary_sha256", ""),
    ):
        fail("FFMPEG-AI-HOST-004", "immutable signed FFmpeg/ffprobe build trust receipt missing or invalid")

    live_gpus = receipt.get("live_gpus", [])
    lease = receipt.get("hrb_lease", {})
    if not hrb_lease_valid(lease, live_gpus):
        fail("FFMPEG-AI-HOST-005", "canonical HRB AcceleratorExecutionLease is absent, invalid, expired, broker-unverified, or mismatched")

    resolved = receipt.get("accelerator_resolution", {})
    if not (
        resolved.get("canonical_identity") == "UUID_PLUS_PCI_BDF"
        and resolved.get("ordinal_is_ephemeral") is True
        and resolved.get("runtime_index_resolved_from_uuid_bdf") is True
        and resolved.get("runtime_index") == resolved_runtime_index(lease, live_gpus)
    ):
        fail("FFMPEG-AI-HOST-006", "runtime CUDA ordinal was not derived from canonical HRB UUID/BDF identity")

    media = receipt.get("input_media", {})
    if not (
        media.get("status") == "PASS"
        and media.get("synthetic_input") is False
        and valid_digest(media.get("sha256"))
        and media.get("has_video") is True
        and media.get("has_audio") is True
        and media.get("video_codec") == "h264"
        and media.get("fixture_profile") == "REAL_MEDIA_SDR_BT709_GOLDEN_FIXTURE"
        and real_media_provenance_valid(receipt.get("input_media_provenance", {}), media.get("sha256", ""))
    ):
        fail("FFMPEG-AI-HOST-007", "production PASS requires provenance-bound non-synthetic real H.264/A-V golden media")

    neural = receipt.get("real_media_neural_e2e", {})
    if not (
        neural.get("status") == "PASS"
        and neural.get("requested_provider") == "cuda"
        and neural.get("observed_provider") == "cuda"
        and neural.get("silent_cpu_fallback_observed") is False
        and neural.get("identity_model_generated_locally") is True
        and valid_digest(neural.get("model_sha256"))
        and neural.get("model_contract") == "4D_NCHW_FLOAT32_SINGLE_INPUT"
        and neural.get("decode_filter_neural_encode_mux_executed") is True
        and neural.get("neural_filter_executed") is True
        and valid_digest(neural.get("cpu_framemd5_sha256"))
        and neural.get("cpu_framemd5_sha256") == neural.get("cuda_framemd5_sha256")
        and valid_digest(neural.get("output_sha256"))
        and valid_digest(neural.get("reference_output_sha256"))
    ):
        fail("FFMPEG-AI-HOST-008", "real-media ONNX CUDA neural E2E is incomplete or CPU fallback was observed")

    gpu = receipt.get("gpu_resident_media_e2e", {})
    if not (
        gpu.get("status") == "PASS"
        and gpu.get("cuda_hwframes_filter_chain_succeeded") is True
        and gpu.get("scale_cuda_executed") is True
        and gpu.get("nvenc_encode_executed") is True
        and gpu.get("gpu_uuid") == lease.get("accelerator_uuid")
        and normalize_bdf(gpu.get("pci_bdf", "")) == normalize_bdf(lease.get("placement", {}).get("pci_bus_id", ""))
        and valid_digest(gpu.get("output_sha256"))
    ):
        fail("FFMPEG-AI-HOST-009", "GPU-resident decode/filter/encode/mux path is incomplete")

    copies = receipt.get("copy_boundary_evidence", {})
    if not (
        copies.get("zero_copy_claimed") is False
        and copies.get("stable_ffmpeg_dnn_cuda_hwframe_baseline") is False
        and copies.get("neural_path_cpu_gpu_transfer_expected") is True
        and copies.get("gpu_resident_path_explicit_hwdownload_present") is False
        and copies.get("gpu_resident_path_explicit_hwupload_present") is False
    ):
        fail("FFMPEG-AI-HOST-010", "copy-boundary evidence improperly claims stable DNN zero-copy or weakens transfer accounting")

    if not quality_valid(receipt.get("quality", {})):
        fail("FFMPEG-AI-HOST-011", "VMAF/SSIM/PSNR/A-V/timestamp/color validation failed")

    negative = receipt.get("negative_tests", {})
    required_negative = {
        "missing_hrb_lease_denied",
        "uuid_bdf_mismatch_denied",
        "invalid_hrb_signature_descriptor_denied",
        "missing_broker_validation_denied",
        "synthetic_production_input_denied",
        "missing_real_media_provenance_denied",
        "silent_cuda_to_cpu_fallback_denied",
        "zero_copy_claim_without_stable_capability_denied",
        "missing_quality_metrics_denied",
        "build_trust_without_ffprobe_binding_denied",
        "reference_host_identity_not_required",
    }
    if set(negative) != required_negative or not all(negative.values()):
        fail("FFMPEG-AI-HOST-012", "required fail-closed negative/portability tests incomplete")

    rollback = receipt.get("rollback", {})
    if not (
        rollback.get("status") == "PASS"
        and rollback.get("persistent_environment_mutation") is False
        and rollback.get("persistent_system_configuration_mutation") is False
        and rollback.get("network_model_fetch_performed") is False
        and rollback.get("temporary_workspace_cleanable") is True
        and rollback.get("failure_injection_cleanup_pass") is True
    ):
        fail("FFMPEG-AI-HOST-013", "rollback/cleanup evidence incomplete")

    if not (
        receipt.get("vs_mlrt_runtime") == "DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_THIS_FFMPEG_PRIMARY_E2E"
        and receipt.get("new_capabilities") == 0
        and receipt.get("new_architectural_authorities") == 0
        and receipt.get("capability_count_after") == CAPABILITY_COUNT
        and receipt.get("global_promotion_claim") is False
    ):
        fail("FFMPEG-AI-HOST-014", "authority/capability/provider/promotion invariant drift")
    return findings


def make_reference_receipt() -> dict[str, Any]:
    """Synthetic contract fixture for unit tests only; never current-host evidence."""
    now = int(datetime.now(timezone.utc).timestamp())
    gpu = {"index": 3, "uuid": "GPU-test", "pci_bdf": "0000:41:00.0", "name": "NVIDIA RTX Test", "memory_total_mib": 24576}
    ffmpeg_hash, ffprobe_hash = "a" * 64, "b" * 64
    lease = {
        "schema": HRB_LEASE_SCHEMA,
        "lease_id": "lease-test",
        "issuer": HRB_PROFILE_ID,
        "authority_id": HRB_AUTHORITY_ID,
        "accelerator_uuid": "GPU-test",
        "memory_max_bytes": 8 * 1024**3,
        "expires_epoch": now + 3600,
        "issued_epoch": now - 5,
        "purpose": "FA3 FFmpeg neural-media test",
        "host": "portable-test-host",
        "status": "ACTIVE",
        "nonce": "test",
        "placement": {"pci_bus_id": "0000:41:00.0", "numa_node": 0},
        "enforcement": {"mode": "TEST"},
        "signature": {"alg": "HMAC-SHA256", "key_id": "host-local-v1", "value": "c" * 64},
        "broker_validation": "VALID",
    }
    return {
        "schema": "fa3.ffmpeg-ai-current-host-receipt.v2",
        "conformance_id": CURRENT_HOST_CONFORMANCE_ID,
        "status": "PASS",
        "evidence_level": EVIDENCE_LEVEL,
        "fixture_semantics": "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST",
        "hardware": {
            "source": "LIVE_SYSFS_PROCFS_NVML",
            "machine": "Portable Test Workstation",
            "cpu_models": ["Generic 16-core CPU"],
            "packages": 1,
            "physical_cores": 16,
            "logical_cpus": 32,
            "numa_domains": 1,
            "physical_cores_per_package": {"0": 16},
            "fingerprint_sha256": "d" * 64,
            "policy_binding": HARDWARE_BASELINE_ID,
            "current_host_facts_are_evidence_only": True,
            "reference_host_match_required": False,
        },
        "live_gpus": [gpu],
        "ffmpeg_feature_manifest": {
            "ffmpeg_binary_sha256": ffmpeg_hash,
            "ffprobe_binary_sha256": ffprobe_hash,
            "build_flags": sorted(REQUIRED_BUILD_FLAGS),
            "filters": sorted(REQUIRED_FILTERS),
            "encoders": sorted(REQUIRED_ENCODERS),
            "hwaccels": sorted(REQUIRED_HWACCELS),
        },
        "ffmpeg_build_trust": {
            "schema": "fa3.ffmpeg-build-trust-receipt.v2",
            "status": "PASS",
            "trust_mode": "UPSTREAM_SIGNED_RELEASE",
            "signature_verified": True,
            "source_or_package_sha256": "e" * 64,
            "installed_ffmpeg_binary_sha256": ffmpeg_hash,
            "installed_ffprobe_binary_sha256": ffprobe_hash,
            "immutable_version_identity": "n9.0.1",
            "floating_master_or_nightly": False,
        },
        "hrb_lease": lease,
        "accelerator_resolution": {
            "canonical_identity": "UUID_PLUS_PCI_BDF",
            "ordinal_is_ephemeral": True,
            "runtime_index_resolved_from_uuid_bdf": True,
            "runtime_index": 3,
        },
        "input_media": {
            "status": "PASS",
            "synthetic_input": False,
            "sha256": "f" * 64,
            "has_video": True,
            "has_audio": True,
            "video_codec": "h264",
            "fixture_profile": "REAL_MEDIA_SDR_BT709_GOLDEN_FIXTURE",
        },
        "input_media_provenance": {
            "schema": REAL_MEDIA_PROVENANCE_SCHEMA,
            "status": "PASS",
            "synthetic": False,
            "source_kind": "USER_SUPPLIED",
            "media_sha256": "f" * 64,
            "usage_authorized": True,
        },
        "real_media_neural_e2e": {
            "status": "PASS",
            "requested_provider": "cuda",
            "observed_provider": "cuda",
            "silent_cpu_fallback_observed": False,
            "identity_model_generated_locally": True,
            "model_sha256": "1" * 64,
            "model_contract": "4D_NCHW_FLOAT32_SINGLE_INPUT",
            "decode_filter_neural_encode_mux_executed": True,
            "neural_filter_executed": True,
            "cpu_framemd5_sha256": "2" * 64,
            "cuda_framemd5_sha256": "2" * 64,
            "output_sha256": "3" * 64,
            "reference_output_sha256": "4" * 64,
        },
        "gpu_resident_media_e2e": {
            "status": "PASS",
            "cuda_hwframes_filter_chain_succeeded": True,
            "scale_cuda_executed": True,
            "nvenc_encode_executed": True,
            "gpu_uuid": "GPU-test",
            "pci_bdf": "0000:41:00.0",
            "output_sha256": "5" * 64,
        },
        "copy_boundary_evidence": {
            "zero_copy_claimed": False,
            "stable_ffmpeg_dnn_cuda_hwframe_baseline": False,
            "neural_path_cpu_gpu_transfer_expected": True,
            "gpu_resident_path_explicit_hwdownload_present": False,
            "gpu_resident_path_explicit_hwupload_present": False,
        },
        "quality": {
            "status": "PASS",
            "fixture_profile": "REAL_MEDIA_SDR_BT709_GOLDEN_FIXTURE",
            "vmaf": 96.0,
            "ssim": 0.995,
            "psnr_db": 42.0,
            "av_duration_delta_seconds": 0.01,
            "timestamps_monotonic": True,
            "expected_color": {"primaries": "bt709", "transfer": "bt709", "space": "bt709"},
            "observed_color": {"primaries": "bt709", "transfer": "bt709", "space": "bt709"},
            "hdr_expected": False,
            "hdr_observed": False,
            "fixture_profile_is_evidence_only_not_provider_limit": True,
        },
        "negative_tests": {
            "missing_hrb_lease_denied": True,
            "uuid_bdf_mismatch_denied": True,
            "invalid_hrb_signature_descriptor_denied": True,
            "missing_broker_validation_denied": True,
            "synthetic_production_input_denied": True,
            "missing_real_media_provenance_denied": True,
            "silent_cuda_to_cpu_fallback_denied": True,
            "zero_copy_claim_without_stable_capability_denied": True,
            "missing_quality_metrics_denied": True,
            "build_trust_without_ffprobe_binding_denied": True,
            "reference_host_identity_not_required": True,
        },
        "rollback": {
            "status": "PASS",
            "persistent_environment_mutation": False,
            "persistent_system_configuration_mutation": False,
            "network_model_fetch_performed": False,
            "temporary_workspace_cleanable": True,
            "failure_injection_cleanup_pass": True,
        },
        "vs_mlrt_runtime": "DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_THIS_FFMPEG_PRIMARY_E2E",
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
        "global_promotion_claim": False,
    }
