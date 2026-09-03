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
EVIDENCE_LEVEL = "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_E2E_PASS"
HRB_AUTHORITY_ID = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
EXPECTED_MACHINE = "Dell Precision Tower 7910"
EXPECTED_CPU_TOKEN = "E5-2696 v4"
REFERENCE_PHYSICAL_CORES = 44
REFERENCE_LOGICAL_CPUS = 88
REFERENCE_NUMA_DOMAINS = 2

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
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
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


def build_identity_onnx(width: int = 64, height: int = 64) -> bytes:
    """Return a dependency-free ONNX Identity model: FLOAT NCHW [1,3,H,W]."""
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
    graph = (
        _b(1, node)
        + _s(2, "fa3_ffmpeg_identity_graph")
        + _b(11, value_info("input"))
        + _b(12, value_info("output"))
    )
    opset = _v(2, 13)
    model = (
        _v(1, 8)
        + _s(2, "fa3")
        + _s(3, "1.0")
        + _b(7, graph)
        + _b(8, opset)
    )
    return model


def normalize_bdf(value: str) -> str:
    value = str(value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", value):
        value = "0000:" + value
    return value


def valid_bdf(value: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", normalize_bdf(value)) is not None


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", value) is not None


def parse_ffmpeg_version(text: str) -> str | None:
    m = re.search(r"^ffmpeg version\s+([^\s]+)", text or "", flags=re.MULTILINE)
    return m.group(1) if m else None


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
        feature.get("ffmpeg_binary_sha256")
        and valid_digest(feature.get("ffmpeg_binary_sha256"))
        and feature.get("ffprobe_binary_sha256")
        and valid_digest(feature.get("ffprobe_binary_sha256"))
        and REQUIRED_BUILD_FLAGS.issubset(set(feature.get("build_flags", [])))
        and REQUIRED_FILTERS.issubset(set(feature.get("filters", [])))
        and REQUIRED_ENCODERS.issubset(set(feature.get("encoders", [])))
        and REQUIRED_HWACCELS.issubset(set(feature.get("hwaccels", [])))
    )


def build_trust_receipt_valid(value: dict[str, Any], binary_sha256: str) -> bool:
    return bool(
        value.get("schema") == "fa3.ffmpeg-build-trust-receipt.v1"
        and value.get("status") == "PASS"
        and value.get("trust_mode") in {"UPSTREAM_SIGNED_RELEASE", "DISTRIBUTION_SIGNED_PACKAGE"}
        and value.get("signature_verified") is True
        and valid_digest(value.get("source_or_package_sha256"))
        and value.get("installed_ffmpeg_binary_sha256") == binary_sha256
        and value.get("immutable_version_identity")
        and value.get("floating_master_or_nightly") is False
    )


def hrb_receipt_valid(value: dict[str, Any], live_gpus: list[dict[str, Any]], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if not (
        value.get("schema") == "fa3.hrb-placement-receipt.v1"
        and value.get("authority_id") == HRB_AUTHORITY_ID
        and value.get("status") in {"ADMITTED", "ACTIVE"}
        and value.get("lease_id")
        and value.get("workload_class") == "NEURAL_MEDIA"
        and value.get("device_uuid")
        and valid_bdf(value.get("pci_bdf", ""))
        and value.get("placement_source") == "LIVE_TOPOLOGY"
        and value.get("static_runtime_ordinal_as_identity") is False
    ):
        return False
    expiry = value.get("expires_at")
    if not expiry:
        return False
    try:
        expires = datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        return False
    target_uuid = str(value["device_uuid"]).strip()
    target_bdf = normalize_bdf(value["pci_bdf"])
    matches = [
        gpu for gpu in live_gpus
        if str(gpu.get("uuid", "")).strip() == target_uuid
        and normalize_bdf(gpu.get("pci_bdf", "")) == target_bdf
    ]
    return len(matches) == 1


def resolved_runtime_index(value: dict[str, Any], live_gpus: list[dict[str, Any]]) -> int | None:
    if not hrb_receipt_valid(value, live_gpus):
        return None
    target_uuid = str(value["device_uuid"]).strip()
    target_bdf = normalize_bdf(value["pci_bdf"])
    for gpu in live_gpus:
        if str(gpu.get("uuid", "")).strip() == target_uuid and normalize_bdf(gpu.get("pci_bdf", "")) == target_bdf:
            try:
                return int(gpu["index"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def quality_valid(q: dict[str, Any]) -> bool:
    try:
        return bool(
            q.get("status") == "PASS"
            and float(q.get("vmaf", -1)) >= QUALITY_THRESHOLDS["vmaf_min"]
            and float(q.get("ssim", -1)) >= QUALITY_THRESHOLDS["ssim_min"]
            and float(q.get("psnr_db", -1)) >= QUALITY_THRESHOLDS["psnr_min_db"]
            and float(q.get("av_duration_delta_seconds", 999)) <= QUALITY_THRESHOLDS["av_duration_delta_max_seconds"]
            and q.get("timestamps_monotonic") is True
            and q.get("color_primaries") == "bt709"
            and q.get("color_transfer") == "bt709"
            and q.get("color_space") == "bt709"
            and q.get("hdr_expected") is False
            and q.get("hdr_absence_validated") is True
        )
    except (TypeError, ValueError):
        return False


def validate_current_host_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    fs: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        fs.append({"code": code, "severity": "P0", "message": message})

    if not (
        receipt.get("schema") == "fa3.ffmpeg-ai-current-host-receipt.v1"
        and receipt.get("conformance_id") == CURRENT_HOST_CONFORMANCE_ID
        and receipt.get("status") == "PASS"
        and receipt.get("evidence_level") == EVIDENCE_LEVEL
    ):
        fail("FFMPEG-AI-HOST-001", "current-host receipt identity/status/evidence level mismatch")

    hw = receipt.get("hardware", {})
    if not (
        hw.get("source") == "LIVE_SYSFS_PROCFS_NVML"
        and hw.get("machine") == EXPECTED_MACHINE
        and hw.get("cpu_model_match") is True
        and hw.get("packages") == 2
        and hw.get("physical_cores") == REFERENCE_PHYSICAL_CORES
        and hw.get("logical_cpus") == REFERENCE_LOGICAL_CPUS
        and hw.get("numa_domains") == REFERENCE_NUMA_DOMAINS
        and valid_digest(hw.get("fingerprint_sha256"))
        and hw.get("hardware_semantics") == "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT"
    ):
        fail("FFMPEG-AI-HOST-002", "live T7910 hardware evidence mismatch")

    feature = receipt.get("ffmpeg_feature_manifest", {})
    if not feature_manifest_valid(feature):
        fail("FFMPEG-AI-HOST-003", "FFmpeg build/filter/codec capability manifest incomplete")

    if not build_trust_receipt_valid(receipt.get("ffmpeg_build_trust", {}), feature.get("ffmpeg_binary_sha256", "")):
        fail("FFMPEG-AI-HOST-004", "immutable signed FFmpeg build trust receipt missing or invalid")

    live_gpus = receipt.get("live_gpus", [])
    hrb = receipt.get("hrb_placement", {})
    if not hrb_receipt_valid(hrb, live_gpus):
        fail("FFMPEG-AI-HOST-005", "HRB lease is absent, expired, or does not match live GPU UUID/BDF")
    resolved = receipt.get("accelerator_resolution", {})
    if not (
        resolved.get("canonical_identity") == "UUID_PLUS_PCI_BDF"
        and resolved.get("ordinal_is_ephemeral") is True
        and resolved.get("runtime_index_resolved_from_uuid_bdf") is True
        and resolved.get("runtime_index") == resolved_runtime_index(hrb, live_gpus)
    ):
        fail("FFMPEG-AI-HOST-006", "runtime CUDA ordinal was not derived from canonical UUID/BDF identity")

    dnn = receipt.get("onnx_cuda_dnn", {})
    if not (
        dnn.get("status") == "PASS"
        and dnn.get("requested_provider") == "cuda"
        and dnn.get("observed_provider") == "cuda"
        and dnn.get("silent_cpu_fallback_observed") is False
        and dnn.get("identity_model_generated_locally") is True
        and valid_digest(dnn.get("model_sha256"))
        and dnn.get("model_contract") == "4D_NCHW_FLOAT32_SINGLE_INPUT"
        and valid_digest(dnn.get("cpu_framemd5_sha256"))
        and dnn.get("cpu_framemd5_sha256") == dnn.get("cuda_framemd5_sha256")
    ):
        fail("FFMPEG-AI-HOST-007", "ONNX CUDA execution/provider proof incomplete or CPU fallback detected")

    media = receipt.get("gpu_media_e2e", {})
    if not (
        media.get("status") == "PASS"
        and media.get("hardware_decode_requested") is True
        and media.get("cuda_filter_executed") is True
        and media.get("nvenc_encode_executed") is True
        and media.get("gpu_uuid") == hrb.get("device_uuid")
        and normalize_bdf(media.get("pci_bdf", "")) == normalize_bdf(hrb.get("pci_bdf", ""))
        and valid_digest(media.get("source_sha256"))
        and valid_digest(media.get("output_sha256"))
    ):
        fail("FFMPEG-AI-HOST-008", "real GPU decode/filter/encode/mux E2E evidence incomplete")

    copies = receipt.get("copy_boundary_evidence", {})
    if not (
        copies.get("zero_copy_claimed") is False
        and copies.get("stable_ffmpeg_dnn_cuda_hwframe_baseline") is False
        and copies.get("dnn_cpu_gpu_transfer_expected") is True
        and copies.get("gpu_media_pipeline_hwdownload_present") is False
        and copies.get("gpu_media_pipeline_hwupload_present") is False
    ):
        fail("FFMPEG-AI-HOST-009", "copy-boundary evidence improperly claims zero-copy or loses stable-release semantics")

    if not quality_valid(receipt.get("quality", {})):
        fail("FFMPEG-AI-HOST-010", "VMAF/SSIM/PSNR/A-V/timestamp/color validation failed")

    neg = receipt.get("negative_tests", {})
    required_neg = {
        "missing_hrb_denied",
        "uuid_bdf_mismatch_denied",
        "silent_cuda_to_cpu_fallback_denied",
        "static_cuda_ordinal_identity_denied",
        "zero_copy_claim_without_stable_capability_denied",
        "missing_quality_metrics_denied",
    }
    if set(neg) != required_neg or not all(neg.values()):
        fail("FFMPEG-AI-HOST-011", "required fail-closed negative tests incomplete")

    rollback = receipt.get("rollback", {})
    if not (
        rollback.get("status") == "PASS"
        and rollback.get("persistent_environment_mutation") is False
        and rollback.get("persistent_system_configuration_mutation") is False
        and rollback.get("network_model_fetch_performed") is False
        and rollback.get("temporary_workspace_cleanable") is True
        and rollback.get("failure_injection_cleanup_pass") is True
    ):
        fail("FFMPEG-AI-HOST-012", "rollback/cleanup evidence incomplete")

    if not (
        receipt.get("vs_mlrt_runtime") == "DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_THIS_FFMPEG_PRIMARY_E2E"
        and receipt.get("new_capabilities") == 0
        and receipt.get("new_architectural_authorities") == 0
        and receipt.get("capability_count_after") == CAPABILITY_COUNT
        and receipt.get("global_promotion_claim") is False
    ):
        fail("FFMPEG-AI-HOST-013", "authority/capability/provider/promotion invariant drift")
    return fs


def make_reference_receipt() -> dict[str, Any]:
    """Synthetic PASS fixture for unit tests only; never current-host evidence."""
    now = datetime.now(timezone.utc)
    future = now.replace(year=now.year + 1).isoformat().replace("+00:00", "Z")
    gpus = [{"index": 1, "uuid": "GPU-test", "pci_bdf": "0000:a5:00.0", "name": "NVIDIA Test GPU"}]
    ffhash = "a" * 64
    h = "b" * 64
    return {
        "schema": "fa3.ffmpeg-ai-current-host-receipt.v1",
        "conformance_id": CURRENT_HOST_CONFORMANCE_ID,
        "status": "PASS",
        "evidence_level": EVIDENCE_LEVEL,
        "fixture_semantics": "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST",
        "hardware": {
            "source": "LIVE_SYSFS_PROCFS_NVML",
            "machine": EXPECTED_MACHINE,
            "cpu_model_match": True,
            "packages": 2,
            "physical_cores": 44,
            "logical_cpus": 88,
            "numa_domains": 2,
            "fingerprint_sha256": h,
            "hardware_semantics": "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT",
        },
        "ffmpeg_feature_manifest": {
            "ffmpeg_binary_sha256": ffhash,
            "ffprobe_binary_sha256": "c" * 64,
            "build_flags": sorted(REQUIRED_BUILD_FLAGS),
            "filters": sorted(REQUIRED_FILTERS),
            "encoders": sorted(REQUIRED_ENCODERS),
            "hwaccels": sorted(REQUIRED_HWACCELS),
        },
        "ffmpeg_build_trust": {
            "schema": "fa3.ffmpeg-build-trust-receipt.v1",
            "status": "PASS",
            "trust_mode": "UPSTREAM_SIGNED_RELEASE",
            "signature_verified": True,
            "source_or_package_sha256": "d" * 64,
            "installed_ffmpeg_binary_sha256": ffhash,
            "immutable_version_identity": "n9.0.1",
            "floating_master_or_nightly": False,
        },
        "live_gpus": gpus,
        "hrb_placement": {
            "schema": "fa3.hrb-placement-receipt.v1",
            "authority_id": HRB_AUTHORITY_ID,
            "status": "ACTIVE",
            "lease_id": "lease-test",
            "workload_class": "NEURAL_MEDIA",
            "device_uuid": "GPU-test",
            "pci_bdf": "0000:a5:00.0",
            "placement_source": "LIVE_TOPOLOGY",
            "static_runtime_ordinal_as_identity": False,
            "expires_at": future,
        },
        "accelerator_resolution": {
            "canonical_identity": "UUID_PLUS_PCI_BDF",
            "ordinal_is_ephemeral": True,
            "runtime_index_resolved_from_uuid_bdf": True,
            "runtime_index": 1,
        },
        "onnx_cuda_dnn": {
            "status": "PASS",
            "requested_provider": "cuda",
            "observed_provider": "cuda",
            "silent_cpu_fallback_observed": False,
            "identity_model_generated_locally": True,
            "model_sha256": "e" * 64,
            "model_contract": "4D_NCHW_FLOAT32_SINGLE_INPUT",
            "cpu_framemd5_sha256": "f" * 64,
            "cuda_framemd5_sha256": "f" * 64,
        },
        "gpu_media_e2e": {
            "status": "PASS",
            "hardware_decode_requested": True,
            "cuda_filter_executed": True,
            "nvenc_encode_executed": True,
            "gpu_uuid": "GPU-test",
            "pci_bdf": "0000:a5:00.0",
            "source_sha256": "1" * 64,
            "output_sha256": "2" * 64,
        },
        "copy_boundary_evidence": {
            "zero_copy_claimed": False,
            "stable_ffmpeg_dnn_cuda_hwframe_baseline": False,
            "dnn_cpu_gpu_transfer_expected": True,
            "gpu_media_pipeline_hwdownload_present": False,
            "gpu_media_pipeline_hwupload_present": False,
        },
        "quality": {
            "status": "PASS",
            "vmaf": 95.0,
            "ssim": 0.99,
            "psnr_db": 40.0,
            "av_duration_delta_seconds": 0.01,
            "timestamps_monotonic": True,
            "color_primaries": "bt709",
            "color_transfer": "bt709",
            "color_space": "bt709",
            "hdr_expected": False,
            "hdr_absence_validated": True,
        },
        "negative_tests": {
            "missing_hrb_denied": True,
            "uuid_bdf_mismatch_denied": True,
            "silent_cuda_to_cpu_fallback_denied": True,
            "static_cuda_ordinal_identity_denied": True,
            "zero_copy_claim_without_stable_capability_denied": True,
            "missing_quality_metrics_denied": True,
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
