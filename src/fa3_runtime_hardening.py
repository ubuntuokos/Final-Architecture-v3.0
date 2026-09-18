#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CAPABILITY_COUNT = 143
PRODUCTION_ACCEPTANCE_TOTAL = 19

ALLOWED_SANDBOX_BACKENDS = {"GVISOR", "WASMTIME_WASI", "HARDENED_ROOTLESS_OCI"}
SHADOW_INPUT_MODES = {"SYNTHETIC", "READ_ONLY_MIRROR", "SANITIZED_MIRROR"}
SHADOW_NETWORK_MODES = {"DENY", "LEASE_SCOPED"}


def runtime_isolation_valid(
    *,
    execution_class: str,
    runtime_backend: str,
    hrb_lease_valid: bool,
    accelerator_requested: bool,
    stable_accelerator_identity: bool,
    cgroup_v2_projected: bool,
    device_projection_from_hrb: bool,
    environment_is_authority: bool = False,
    runtime_reselected_resources: bool = False,
    immutable_runtime: bool = True,
    sbom_present: bool = True,
) -> bool:
    execution_class = execution_class.upper()
    runtime_backend = runtime_backend.upper()
    if environment_is_authority or runtime_reselected_resources:
        return False
    if accelerator_requested and not (
        hrb_lease_valid and stable_accelerator_identity and device_projection_from_hrb
    ):
        return False
    if execution_class == "SERVICE_PROVIDER":
        if runtime_backend not in {"ROOTLESS_OCI", "NATIVE_VERSIONED_PROVIDER"}:
            return False
        if not immutable_runtime or not sbom_present:
            return False
        if runtime_backend == "ROOTLESS_OCI" and not cgroup_v2_projected:
            return False
    elif execution_class == "DESKTOP_GUI":
        if runtime_backend == "HOST_SUBPROCESS_UNTRUSTED":
            return False
    elif execution_class == "UNTRUSTED_AGENT":
        return False
    else:
        return False
    return True


def agent_sandbox_valid(
    *,
    backend: str,
    arbitrary_code: bool,
    explicit_admission: bool,
    ephemeral_overlay: bool,
    host_home_visible: bool,
    host_processes_visible: bool,
    network_mode: str,
    direct_mcp_bypass: bool,
    compatibility_evidence: bool,
) -> bool:
    backend = backend.upper()
    network_mode = network_mode.upper()
    if backend == "HOST_SUBPROCESS":
        return False
    if backend not in ALLOWED_SANDBOX_BACKENDS:
        return False
    if not (explicit_admission and ephemeral_overlay and compatibility_evidence):
        return False
    if host_home_visible or host_processes_visible or direct_mcp_bypass:
        return False
    if network_mode not in SHADOW_NETWORK_MODES:
        return False
    if arbitrary_code and backend == "HARDENED_ROOTLESS_OCI":
        return False
    return True


def zero_host_round_trip_valid(
    *,
    requested_backend: str,
    observed_backend: str,
    hrb_lease_valid: bool,
    stable_accelerator_identity: bool,
    host_frame_round_trips: int,
    copy_telemetry_present: bool,
    dlp_shared_gpu_memory: bool,
    full_pipeline_zero_copy_claim: bool = False,
    full_pipeline_zero_copy_proven: bool = False,
) -> bool:
    if requested_backend != observed_backend:
        return False
    if not (hrb_lease_valid and stable_accelerator_identity and copy_telemetry_present):
        return False
    if host_frame_round_trips != 0 or not dlp_shared_gpu_memory:
        return False
    if full_pipeline_zero_copy_claim and not full_pipeline_zero_copy_proven:
        return False
    return True


@dataclass(frozen=True)
class HungarianAQCThresholds:
    language_confidence_min: float = 0.98
    grammar_score_min: float = 0.90
    toxicity_score_max: float = 0.05
    asr_cer_max: float = 0.04
    asr_wer_max: float = 0.08
    perceptual_quality_min: float = 0.75
    speaker_similarity_min_if_cloning: float = 0.75
    clipping_ratio_max: float = 0.001
    silence_ratio_max: float = 0.20


def evaluate_hungarian_aqc(
    metrics: dict[str, Any],
    *,
    cloning: bool,
    scorer_license_admitted: bool,
    thresholds: HungarianAQCThresholds | None = None,
) -> dict[str, Any]:
    t = thresholds or HungarianAQCThresholds()
    dimensions = {
        "text_language": float(metrics.get("language_confidence", -1)) >= t.language_confidence_min,
        "grammar_style": float(metrics.get("grammar_score", -1)) >= t.grammar_score_min
        and bool(metrics.get("register_consistent", False)),
        "toxicity_policy": float(metrics.get("toxicity_score", 1)) <= t.toxicity_score_max,
        "intelligibility": float(metrics.get("asr_cer", 1)) <= t.asr_cer_max
        and float(metrics.get("asr_wer", 1)) <= t.asr_wer_max,
        "naturalness": scorer_license_admitted
        and float(metrics.get("perceptual_quality", -1)) >= t.perceptual_quality_min,
        "signal_integrity": bool(metrics.get("finite_audio", False))
        and float(metrics.get("clipping_ratio", 1)) <= t.clipping_ratio_max
        and float(metrics.get("silence_ratio", 1)) <= t.silence_ratio_max,
        "speaker_identity": (
            not cloning
            or float(metrics.get("speaker_similarity", -1))
            >= t.speaker_similarity_min_if_cloning
        ),
    }
    return {
        "schema": "fa3.hu-aqc-receipt.v1",
        "locale": "hu-HU",
        "cloning": cloning,
        "dimensions": dimensions,
        "passed": all(dimensions.values()),
        "single_metric_authority": False,
        "scorer_license_admitted": scorer_license_admitted,
    }


def shadow_execution_valid(
    *,
    current_host_evidence: str,
    execution_mode: str,
    input_mode: str,
    production_data: bool,
    data_governance_admitted: bool,
    authoritative_output: bool,
    external_side_effects: bool,
    output_quarantined: bool,
    evidence_collection: bool,
    workspace_ephemeral: bool,
    network_mode: str,
    acceptance_criteria_passed: int = 0,
    acceptance_criteria_total: int = PRODUCTION_ACCEPTANCE_TOTAL,
    canonical_promotion_gate_pass: bool = False,
) -> bool:
    evidence = current_host_evidence.upper()
    mode = execution_mode.upper()
    input_mode = input_mode.upper()
    network_mode = network_mode.upper()

    if mode == "PRODUCTION":
        return (
            evidence == "PASS"
            and acceptance_criteria_passed == PRODUCTION_ACCEPTANCE_TOTAL
            and acceptance_criteria_total == PRODUCTION_ACCEPTANCE_TOTAL
            and canonical_promotion_gate_pass
        )

    if mode == "SHADOW":
        if evidence == "FAIL":
            return False
        if input_mode not in SHADOW_INPUT_MODES or network_mode not in SHADOW_NETWORK_MODES:
            return False
        if production_data and not data_governance_admitted:
            return False
        return (
            not authoritative_output
            and not external_side_effects
            and output_quarantined
            and evidence_collection
            and workspace_ephemeral
        )

    if mode == "DEV":
        return not authoritative_output

    return False


def shadow_receipt(**kwargs: Any) -> dict[str, Any]:
    allowed = shadow_execution_valid(**kwargs)
    mode = str(kwargs.get("execution_mode", "")).upper()
    return {
        "schema": "fa3.shadow-execution-receipt.v1",
        "execution_mode": mode,
        "allowed": allowed,
        "authoritative": mode == "PRODUCTION" and allowed,
        "promotion_authority": False,
        "may_assign_promoted": False,
    }
