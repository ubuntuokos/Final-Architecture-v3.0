from pathlib import Path

from src.fa3_runtime_hardening import (
    agent_sandbox_valid,
    evaluate_hungarian_aqc,
    runtime_isolation_valid,
    shadow_execution_valid,
    zero_host_round_trip_valid,
)
from src.fa3_runtime_hardening_gate import gate


ROOT = Path(__file__).resolve().parents[1]


def test_rootless_service_runtime_must_follow_hrb_projection():
    good = dict(
        execution_class="SERVICE_PROVIDER",
        runtime_backend="ROOTLESS_OCI",
        hrb_lease_valid=True,
        accelerator_requested=True,
        stable_accelerator_identity=True,
        cgroup_v2_projected=True,
        device_projection_from_hrb=True,
        immutable_runtime=True,
        sbom_present=True,
    )
    assert runtime_isolation_valid(**good)
    assert not runtime_isolation_valid(**{**good, "environment_is_authority": True})
    assert not runtime_isolation_valid(**{**good, "runtime_reselected_resources": True})


def test_arbitrary_agent_never_runs_as_host_subprocess():
    good = dict(
        backend="GVISOR",
        arbitrary_code=True,
        explicit_admission=True,
        ephemeral_overlay=True,
        host_home_visible=False,
        host_processes_visible=False,
        network_mode="DENY",
        direct_mcp_bypass=False,
        compatibility_evidence=True,
    )
    assert agent_sandbox_valid(**good)
    assert not agent_sandbox_valid(**{**good, "backend": "HOST_SUBPROCESS"})
    assert not agent_sandbox_valid(**{**good, "backend": "HARDENED_ROOTLESS_OCI"})


def test_media_zero_host_round_trip_is_measured_not_marketing_claim():
    good = dict(
        requested_backend="cuda",
        observed_backend="cuda",
        hrb_lease_valid=True,
        stable_accelerator_identity=True,
        host_frame_round_trips=0,
        copy_telemetry_present=True,
        dlp_shared_gpu_memory=True,
    )
    assert zero_host_round_trip_valid(**good)
    assert not zero_host_round_trip_valid(**{**good, "host_frame_round_trips": 1})
    assert not zero_host_round_trip_valid(
        **{**good, "full_pipeline_zero_copy_claim": True, "full_pipeline_zero_copy_proven": False}
    )


def _aqc_good():
    return {
        "language_confidence": 0.995,
        "grammar_score": 0.97,
        "register_consistent": True,
        "toxicity_score": 0.01,
        "asr_cer": 0.01,
        "asr_wer": 0.03,
        "perceptual_quality": 0.91,
        "speaker_similarity": 0.89,
        "finite_audio": True,
        "clipping_ratio": 0.0001,
        "silence_ratio": 0.08,
    }


def test_hungarian_aqc_keeps_dimensions_independent_and_license_gated():
    good = _aqc_good()
    result = evaluate_hungarian_aqc(good, cloning=True, scorer_license_admitted=True)
    assert result["passed"]
    assert result["single_metric_authority"] is False
    assert not evaluate_hungarian_aqc(
        {**good, "asr_wer": 0.40}, cloning=True, scorer_license_admitted=True
    )["passed"]
    assert not evaluate_hungarian_aqc(
        {**good, "speaker_similarity": 0.20}, cloning=True, scorer_license_admitted=True
    )["passed"]
    assert not evaluate_hungarian_aqc(good, cloning=False, scorer_license_admitted=False)["passed"]


def test_pending_current_host_can_shadow_but_cannot_produce_authority():
    base = dict(
        current_host_evidence="PENDING_CURRENT_HOST",
        execution_mode="SHADOW",
        input_mode="SANITIZED_MIRROR",
        production_data=True,
        data_governance_admitted=True,
        authoritative_output=False,
        external_side_effects=False,
        output_quarantined=True,
        evidence_collection=True,
        workspace_ephemeral=True,
        network_mode="DENY",
    )
    assert shadow_execution_valid(**base)
    assert not shadow_execution_valid(**{**base, "authoritative_output": True})
    assert not shadow_execution_valid(**{**base, "external_side_effects": True})
    assert not shadow_execution_valid(**{**base, "data_governance_admitted": False})


def test_production_requires_current_host_pass_and_all_22_acceptance_criteria():
    base = dict(
        current_host_evidence="PASS",
        execution_mode="PRODUCTION",
        input_mode="SYNTHETIC",
        production_data=False,
        data_governance_admitted=False,
        authoritative_output=True,
        external_side_effects=True,
        output_quarantined=False,
        evidence_collection=True,
        workspace_ephemeral=False,
        network_mode="LEASE_SCOPED",
        acceptance_criteria_passed=22,
        acceptance_criteria_total=22,
        canonical_promotion_gate_pass=True,
    )
    assert shadow_execution_valid(**base)
    assert not shadow_execution_valid(**{**base, "current_host_evidence": "PENDING_CURRENT_HOST"})
    assert not shadow_execution_valid(**{**base, "acceptance_criteria_passed": 21})
    assert not shadow_execution_valid(**{**base, "canonical_promotion_gate_pass": False})


def test_runtime_hardening_canonical_gate_passes():
    report = gate(ROOT)
    assert report["result"] == "PASS", report
    assert report["capability_count"] == 143
    assert report["authority_delta"] == 0
    assert report["current_host_runtime_promotion_claim"] is False
