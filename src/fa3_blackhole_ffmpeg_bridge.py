#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

BRIDGE_ID = "FA3-BLACKHOLE-FFMPEG-BRIDGE-001"
GATESET_ID = "FA3-BLACKHOLE-FFMPEG-BRIDGE-GATESET-001"
HARDWARE_POLICY_ID = "FA3-HARDWARE-BASELINE-001"
STT_MEDIA_PROFILE_ID = "FA3-STT-MEDIA-001"

REQUIRED_CAPABILITIES = {
    "cuda",
    "onnxruntime_cuda",
    "ffmpeg_cuda_hwframes",
    "nvenc",
}
REQUIRED_STAGE_ORDER = [
    "ZERO_COPY_NEURAL_PROCESSING",
    "BLACKHOLE_TRANSCRIPTION",
    "CANONICAL_EVIDENCE_GENERATION",
]


class BridgePolicyDenied(PermissionError):
    pass


def _parse_utc(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise BridgePolicyDenied("FAIL-CLOSED: malformed UTC timestamp") from exc
    if dt.tzinfo is None:
        raise BridgePolicyDenied("FAIL-CLOSED: timestamp must include timezone")
    return dt.astimezone(timezone.utc)


def _deny(message: str) -> None:
    raise BridgePolicyDenied(f"FAIL-CLOSED: {message}")


def validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        _deny("bridge payload must be an object")
    if payload.get("$schema") != "fa3.blackhole-ffmpeg-bridge-request.v1":
        _deny("Blackhole bridge schema mismatch")

    metadata = payload.get("job_metadata")
    if not isinstance(metadata, dict) or not metadata.get("job_id") or not metadata.get("owner"):
        _deny("job metadata is incomplete")

    constraints = payload.get("hardware_constraints")
    if not isinstance(constraints, dict):
        _deny("hardware constraints are missing")
    if constraints.get("hardware_policy_ref") != HARDWARE_POLICY_ID:
        _deny("portable hardware policy reference is missing")
    if "host_resource_broker_lease_id" in constraints:
        _deny("static HRB lease IDs are forbidden in canonical payloads")
    static_sms = constraints.get("allowed_sm_architectures")
    if static_sms not in (None, [], ()):
        _deny("static SM architecture allowlists are forbidden as canonical admission")
    capabilities = set(constraints.get("required_capabilities") or [])
    if not REQUIRED_CAPABILITIES.issubset(capabilities):
        _deny("required accelerator/media capabilities are incomplete")
    hrb = constraints.get("host_resource_broker")
    if not isinstance(hrb, dict):
        _deny("Host Resource Broker policy is missing")
    if hrb.get("lease_required") is not True or hrb.get("lease_source") != "runtime":
        _deny("HRB lease must be acquired dynamically at runtime")
    if hrb.get("require_same_gpu_for_pipeline") is not True:
        _deny("same-GPU binding is mandatory for the accelerated pipeline")

    runtime = payload.get("runtime_environment")
    if not isinstance(runtime, dict):
        _deny("runtime environment is missing")
    if not runtime.get("ffmpeg_binary_override"):
        _deny("FFmpeg binary must be explicit")
    if runtime.get("require_binary_integrity_verification") is not True:
        _deny("FFmpeg binary integrity verification is mandatory")
    if runtime.get("use_gpu_resident_zero_copy") is not True:
        _deny("GPU-resident zero-copy intent must be explicit")
    profile = runtime.get("profile", "PRODUCTION")
    if profile not in {"PRODUCTION", "DIAGNOSTIC"}:
        _deny("unsupported runtime profile")
    env = runtime.get("environment_variables") or {}
    if not isinstance(env, dict):
        _deny("environment_variables must be an object")
    if env.get("CUDA_LAUNCH_BLOCKING") == "1" and profile != "DIAGNOSTIC":
        _deny("CUDA_LAUNCH_BLOCKING=1 is diagnostic-only and forbidden in production")

    stages = payload.get("pipeline_stages")
    if not isinstance(stages, list):
        _deny("pipeline stages are missing")
    names = [stage.get("stage_name") for stage in stages if isinstance(stage, dict)]
    if names != REQUIRED_STAGE_ORDER:
        _deny("pipeline must contain neural processing, transcription and evidence stages in canonical order")

    neural = stages[0]
    neural_params = neural.get("parameters") or {}
    if neural_params.get("zero_copy_claim_scope") != "FRAME_TO_TENSOR_ONLY":
        _deny("zero-copy claim must be scoped to measured frame-to-tensor mapping")
    if neural_params.get("end_to_end_gpu_resident_claim") is not False:
        _deny("end-to-end GPU-resident execution is not an admitted baseline claim")

    transcription = stages[1]
    trans_params = transcription.get("parameters") or {}
    if trans_params.get("stt_profile_ref") != STT_MEDIA_PROFILE_ID:
        _deny("transcription stage must delegate to FA3-STT-MEDIA-001")
    if trans_params.get("target_locale") != "hu-HU":
        _deny("Marketing bridge transcription target must be hu-HU")
    if not trans_params.get("output_transcript") or not trans_params.get("output_subtitles"):
        _deny("transcription artifacts are incomplete")

    evidence_params = (stages[2].get("parameters") or {})
    if evidence_params.get("sha256_verification_mandatory") is not True:
        _deny("output SHA-256 verification is mandatory")
    if evidence_params.get("zero_copy_evidence_mandatory") is not True:
        _deny("measured zero-copy evidence is mandatory")
    if evidence_params.get("lease_binding_evidence_mandatory") is not True:
        _deny("HRB lease binding evidence is mandatory")

    acceptance = payload.get("acceptance_policy")
    if not isinstance(acceptance, dict):
        _deny("acceptance policy is missing")
    if acceptance.get("required_final_status") != "CURRENT_HOST_PRODUCTION_E2E_PASS":
        _deny("production status target is not canonical")
    if acceptance.get("fail_closed") is not True:
        _deny("bridge acceptance must fail closed")
    if acceptance.get("zero_copy_promotion_requires_measured_evidence") is not True:
        _deny("zero-copy promotion must require measured evidence")
    if acceptance.get("end_to_end_gpu_resident_claim") is not False:
        _deny("unmeasured end-to-end GPU-resident claim is forbidden")


def validate_runtime_lease(lease: dict[str, Any], *, now: datetime | None = None) -> None:
    if not isinstance(lease, dict):
        _deny("runtime HRB lease is missing")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    if lease.get("status") != "VALID" or lease.get("broker_validation") != "VALID":
        _deny("HRB lease is not broker-validated VALID")
    for key in ("lease_id", "gpu_uuid", "pci_bdf", "expires_at"):
        if not lease.get(key):
            _deny(f"HRB lease field missing: {key}")
    purposes = set(lease.get("purpose_scope") or [])
    if "BLACKHOLE_NEURAL_MEDIA" not in purposes:
        _deny("HRB lease purpose scope does not authorize Blackhole neural media")
    if _parse_utc(lease["expires_at"]) <= now:
        _deny("HRB lease is expired")


def validate_zero_copy_evidence(evidence: dict[str, Any], lease: dict[str, Any]) -> None:
    if not isinstance(evidence, dict):
        _deny("measured zero-copy evidence is missing")
    expected_gpu = lease.get("gpu_uuid")
    for field in ("hrb_gpu_uuid", "ffmpeg_gpu_uuid", "onnx_gpu_uuid", "nvenc_gpu_uuid"):
        if evidence.get(field) != expected_gpu:
            _deny(f"GPU identity mismatch in zero-copy evidence: {field}")
    if evidence.get("onnx_execution_provider") != "CUDAExecutionProvider":
        _deny("ONNX CUDA execution was not observed")
    if evidence.get("frame_to_tensor_zero_copy_observed") is not True:
        _deny("frame-to-tensor zero-copy was not observed")
    for counter in ("hwdownload_count", "unexpected_host_transfer_count", "intermediate_reupload_count"):
        value = evidence.get(counter)
        if not isinstance(value, int) or value != 0:
            _deny(f"unexpected host/copy activity detected: {counter}")
    e2e_claim = evidence.get("end_to_end_gpu_resident_claim", False)
    if e2e_claim is True and evidence.get("measured_end_to_end_gpu_resident") is not True:
        _deny("end-to-end GPU-resident claim lacks measured evidence")


def evaluate_current_host_evidence(
    payload: dict[str, Any],
    lease: dict[str, Any],
    evidence: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_payload(payload)
    validate_runtime_lease(lease, now=now)
    zero_copy = evidence.get("zero_copy") if isinstance(evidence, dict) else None
    validate_zero_copy_evidence(zero_copy, lease)

    required_true = (
        "ffmpeg_build_trust_verified",
        "source_media_provenance_verified",
        "source_media_is_real_non_synthetic",
        "output_sha256_verified",
        "stt_result_hash_bound",
        "caption_qc_passed",
        "rollback_or_cleanup_verified",
    )
    missing = [name for name in required_true if evidence.get(name) is not True]
    if missing:
        _deny("current-host evidence incomplete: " + ",".join(missing))
    return {
        "status": "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "bridge_id": BRIDGE_ID,
        "lease_id": lease["lease_id"],
        "gpu_uuid": lease["gpu_uuid"],
        "zero_copy_claim_scope": "FRAME_TO_TENSOR_ONLY",
        "end_to_end_gpu_resident_claim": False,
    }


def reference_payload() -> dict[str, Any]:
    return {
        "$schema": "fa3.blackhole-ffmpeg-bridge-request.v1",
        "schema_version": "1.0.0",
        "job_metadata": {
            "job_id": "JOB-REFERENCE-BLACKHOLE-001",
            "owner": "FA3-MARKETING-STUDIO",
            "execution_priority": "CRITICAL",
        },
        "hardware_constraints": {
            "hardware_policy_ref": HARDWARE_POLICY_ID,
            "required_capabilities": sorted(REQUIRED_CAPABILITIES),
            "host_resource_broker": {
                "lease_required": True,
                "lease_source": "runtime",
                "require_same_gpu_for_pipeline": True,
            },
        },
        "runtime_environment": {
            "profile": "PRODUCTION",
            "ffmpeg_binary_override": "./bin/ffmpeg-custom/bin/ffmpeg",
            "require_binary_integrity_verification": True,
            "use_gpu_resident_zero_copy": True,
            "environment_variables": {"OMP_PROC_BIND": "close"},
        },
        "pipeline_stages": [
            {
                "stage_index": 1,
                "stage_name": "ZERO_COPY_NEURAL_PROCESSING",
                "input_file": "storage/raw_ingest/marketing_input_source.mp4",
                "output_file": "storage/processed/marketing_denoised_1080p.mp4",
                "parameters": {
                    "neural_model_ref": "media_enhancer_v3",
                    "video_codec": "h264_nvenc",
                    "neural_media_profile_ref": "FA3-NEURAL-MEDIA-EXECUTION-001",
                    "zero_copy_claim_scope": "FRAME_TO_TENSOR_ONLY",
                    "end_to_end_gpu_resident_claim": False,
                },
            },
            {
                "stage_index": 2,
                "stage_name": "BLACKHOLE_TRANSCRIPTION",
                "parameters": {
                    "stt_profile_ref": STT_MEDIA_PROFILE_ID,
                    "target_locale": "hu-HU",
                    "output_transcript": "storage/processed/marketing_input_source.transcript.json",
                    "output_subtitles": "storage/processed/marketing_input_source.hu-HU.srt",
                },
            },
            {
                "stage_index": 3,
                "stage_name": "CANONICAL_EVIDENCE_GENERATION",
                "parameters": {
                    "output_report_destination": "reports/blackhole-ffmpeg-bridge-telemetry.json",
                    "sha256_verification_mandatory": True,
                    "zero_copy_evidence_mandatory": True,
                    "lease_binding_evidence_mandatory": True,
                },
            },
        ],
        "acceptance_policy": {
            "required_final_status": "CURRENT_HOST_PRODUCTION_E2E_PASS",
            "fail_closed": True,
            "zero_copy_promotion_requires_measured_evidence": True,
            "end_to_end_gpu_resident_claim": False,
        },
    }


def reference_lease() -> dict[str, Any]:
    return {
        "status": "VALID",
        "broker_validation": "VALID",
        "lease_id": "runtime-lease-test-001",
        "gpu_uuid": "GPU-REFERENCE-001",
        "pci_bdf": "0000:01:00.0",
        "purpose_scope": ["BLACKHOLE_NEURAL_MEDIA"],
        "expires_at": "2099-01-01T00:00:00Z",
    }


def reference_zero_copy(lease: dict[str, Any] | None = None) -> dict[str, Any]:
    lease = lease or reference_lease()
    gpu = lease["gpu_uuid"]
    return {
        "hrb_gpu_uuid": gpu,
        "ffmpeg_gpu_uuid": gpu,
        "onnx_gpu_uuid": gpu,
        "nvenc_gpu_uuid": gpu,
        "onnx_execution_provider": "CUDAExecutionProvider",
        "frame_to_tensor_zero_copy_observed": True,
        "hwdownload_count": 0,
        "unexpected_host_transfer_count": 0,
        "intermediate_reupload_count": 0,
        "end_to_end_gpu_resident_claim": False,
        "measured_end_to_end_gpu_resident": False,
    }


def run_bridge_regressions() -> dict[str, Any]:
    now = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)
    payload = reference_payload()
    lease = reference_lease()
    zc = reference_zero_copy(lease)

    def rejects(fn) -> bool:
        try:
            fn()
        except BridgePolicyDenied:
            return True
        return False

    checks: list[tuple[str, bool]] = []
    checks.append(("BRIDGE-001", not rejects(lambda: validate_payload(payload))))

    bad = {**payload, "hardware_constraints": {**payload["hardware_constraints"], "host_resource_broker_lease_id": "STATIC"}}
    checks.append(("BRIDGE-002", rejects(lambda: validate_payload(bad))))

    bad = {**payload, "hardware_constraints": {**payload["hardware_constraints"], "allowed_sm_architectures": ["sm_86"]}}
    checks.append(("BRIDGE-003", rejects(lambda: validate_payload(bad))))

    bad = {**payload, "pipeline_stages": [payload["pipeline_stages"][0], payload["pipeline_stages"][2]]}
    checks.append(("BRIDGE-004", rejects(lambda: validate_payload(bad))))

    bad_runtime = {**payload["runtime_environment"], "environment_variables": {"CUDA_LAUNCH_BLOCKING": "1"}}
    bad = {**payload, "runtime_environment": bad_runtime}
    checks.append(("BRIDGE-005", rejects(lambda: validate_payload(bad))))

    diag_runtime = {**bad_runtime, "profile": "DIAGNOSTIC"}
    diag = {**payload, "runtime_environment": diag_runtime}
    checks.append(("BRIDGE-006", not rejects(lambda: validate_payload(diag))))

    checks.append(("BRIDGE-007", not rejects(lambda: validate_runtime_lease(lease, now=now))))
    expired = {**lease, "expires_at": "2026-09-14T05:00:00Z"}
    checks.append(("BRIDGE-008", rejects(lambda: validate_runtime_lease(expired, now=now))))

    wrong_gpu = {**zc, "onnx_gpu_uuid": "GPU-WRONG"}
    checks.append(("BRIDGE-009", rejects(lambda: validate_zero_copy_evidence(wrong_gpu, lease))))

    host_copy = {**zc, "unexpected_host_transfer_count": 1}
    checks.append(("BRIDGE-010", rejects(lambda: validate_zero_copy_evidence(host_copy, lease))))

    no_measurement = {**zc, "frame_to_tensor_zero_copy_observed": False}
    checks.append(("BRIDGE-011", rejects(lambda: validate_zero_copy_evidence(no_measurement, lease))))

    checks.append(("BRIDGE-012", not rejects(lambda: validate_zero_copy_evidence(zc, lease))))

    overclaim = {**zc, "end_to_end_gpu_resident_claim": True, "measured_end_to_end_gpu_resident": False}
    checks.append(("BRIDGE-013", rejects(lambda: validate_zero_copy_evidence(overclaim, lease))))

    evidence = {
        "zero_copy": zc,
        "ffmpeg_build_trust_verified": True,
        "source_media_provenance_verified": True,
        "source_media_is_real_non_synthetic": True,
        "output_sha256_verified": True,
        "stt_result_hash_bound": True,
        "caption_qc_passed": True,
        "rollback_or_cleanup_verified": True,
    }
    checks.append(("BRIDGE-014", not rejects(lambda: evaluate_current_host_evidence(payload, lease, evidence, now=now))))

    incomplete = {**evidence, "source_media_provenance_verified": False}
    checks.append(("BRIDGE-015", rejects(lambda: evaluate_current_host_evidence(payload, lease, incomplete, now=now))))

    synth = {**evidence, "source_media_is_real_non_synthetic": False}
    checks.append(("BRIDGE-016", rejects(lambda: evaluate_current_host_evidence(payload, lease, synth, now=now))))

    cases = [{"case_id": cid, "status": "PASS" if ok else "FAIL"} for cid, ok in checks]
    return {
        "result": "PASS" if all(ok for _, ok in checks) else "FAIL",
        "total": len(cases),
        "passed": sum(c["status"] == "PASS" for c in cases),
        "cases": cases,
        "current_host_runtime_claim": False,
    }
