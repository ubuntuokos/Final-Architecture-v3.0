#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_runtime_hardening import (
    CAPABILITY_COUNT,
    agent_sandbox_valid,
    evaluate_hungarian_aqc,
    runtime_isolation_valid,
    shadow_execution_valid,
    zero_host_round_trip_valid,
)

GATE_ID = "FA3-RUNTIME-HARDENING-GATESET-001"
PROFILE_IDS = (
    "FA3-RUNTIME-ISOLATION-001",
    "FA3-AGENT-SANDBOX-001",
    "FA3-MEDIA-GPU-ZEROCOPY-001",
    "FA3-HU-AQC-001",
    "FA3-PROMOTION-SHADOW-001",
)

PATHS = {
    "runtime_isolation": "canonical/profiles/FA3-RUNTIME-ISOLATION-001.json",
    "agent_sandbox": "canonical/profiles/FA3-AGENT-SANDBOX-001.json",
    "media_zero": "canonical/profiles/FA3-MEDIA-GPU-ZEROCOPY-001.json",
    "hu_aqc": "canonical/profiles/FA3-HU-AQC-001.json",
    "shadow": "canonical/profiles/FA3-PROMOTION-SHADOW-001.json",
    "contract": "canonical/contracts/FA3-RUNTIME-HARDENING-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-PYNVVIDEOCODEC-001.json",
    "vapoursynth_provider": "canonical/providers/FA3-PROVIDER-VAPOURSYNTH-R80-001.json",
    "vapoursynth_reference": "canonical/references/FA3-VAPOURSYNTH-R80-UPSTREAM-REFERENCE-2026-09-19.json",
    "vapoursynth_decision": "canonical/decisions/FA3-DEC-VAPOURSYNTH-R80-RUNTIME-HARDENING-2026-09-19.json",
    "neural_contract": "canonical/contracts/FA3-NEURAL-MEDIA-EXECUTION-CONTRACTS-001.json",
    "vsmlrt": "canonical/providers/FA3-PROVIDER-VS-MLRT-001.json",
    "upstream_locks": "canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json",
    "decision": "canonical/decisions/FA3-DEC-RUNTIME-HARDENING-SHADOW-2026-09-19.json",
    "gate": "canonical/FA3-GATE-RUNTIME-HARDENING-001.json",
    "enforcement": "canonical/runtime-hardening-enforcement.json",
    "hrb": "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json",
    "agent_exec": "canonical/profiles/FA3-AGENT-EXEC-001.json",
    "closed_loop": "canonical/profiles/FA3-CLOSED-LOOP-AGENT-OPERATIONS-001.json",
    "media": "canonical/profiles/FA3-NEURAL-MEDIA-EXECUTION-001.json",
    "voice": "canonical/profiles/FA3-VOICE-001.json",
    "voice_routing": "canonical/FA3-VOICE-QUALITY-ROUTING-001.json",
    "policy": "canonical/enforcement-policy.json",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def _good_aqc() -> dict[str, Any]:
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


def regressions() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(name: str, positive: bool, negative_refusal: bool) -> None:
        cases.append({
            "name": name,
            "positive": bool(positive),
            "negative_refusal": bool(negative_refusal),
            "result": "PASS" if positive and negative_refusal else "FAIL",
        })

    service = dict(
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
    add(
        "runtime-isolation-hrb-authority",
        runtime_isolation_valid(**service),
        not runtime_isolation_valid(**{**service, "runtime_reselected_resources": True}),
    )

    sandbox = dict(
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
    add(
        "agent-sandbox-no-host-subprocess",
        agent_sandbox_valid(**sandbox),
        not agent_sandbox_valid(**{**sandbox, "backend": "HOST_SUBPROCESS"}),
    )

    media = dict(
        requested_backend="cuda",
        observed_backend="cuda",
        hrb_lease_valid=True,
        stable_accelerator_identity=True,
        host_frame_round_trips=0,
        copy_telemetry_present=True,
        dlp_shared_gpu_memory=True,
    )
    add(
        "media-zero-host-round-trip",
        zero_host_round_trip_valid(**media),
        not zero_host_round_trip_valid(**{**media, "host_frame_round_trips": 1}),
    )

    good_aqc = _good_aqc()
    add(
        "hu-aqc-multi-signal",
        evaluate_hungarian_aqc(good_aqc, cloning=True, scorer_license_admitted=True)["passed"],
        not evaluate_hungarian_aqc(
            {**good_aqc, "asr_wer": 0.31}, cloning=True, scorer_license_admitted=True
        )["passed"],
    )
    add(
        "hu-aqc-license-admission",
        evaluate_hungarian_aqc(good_aqc, cloning=False, scorer_license_admitted=True)["passed"],
        not evaluate_hungarian_aqc(good_aqc, cloning=False, scorer_license_admitted=False)["passed"],
    )

    shadow = dict(
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
    add(
        "shadow-non-authoritative",
        shadow_execution_valid(**shadow),
        not shadow_execution_valid(**{**shadow, "external_side_effects": True}),
    )
    add(
        "production-22-of-22",
        shadow_execution_valid(
            **{
                **shadow,
                "current_host_evidence": "PASS",
                "execution_mode": "PRODUCTION",
                "acceptance_criteria_passed": 22,
                "acceptance_criteria_total": 22,
                "canonical_promotion_gate_pass": True,
            }
        ),
        not shadow_execution_valid(
            **{
                **shadow,
                "current_host_evidence": "PENDING_CURRENT_HOST",
                "execution_mode": "PRODUCTION",
                "acceptance_criteria_passed": 22,
                "acceptance_criteria_total": 22,
                "canonical_promotion_gate_pass": True,
            }
        ),
    )
    return cases


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    data: dict[str, dict[str, Any]] = {}
    for key, rel in PATHS.items():
        try:
            data[key] = loadj(root / rel)
        except Exception as exc:
            findings.append(finding("HARDEN-000", "Required materialization unreadable", path=rel, error=repr(exc)))

    if findings:
        return _report(root, findings, [])

    for key in ("runtime_isolation", "agent_sandbox", "media_zero", "hu_aqc", "shadow"):
        record = data[key]
        if (
            record.get("id") not in PROFILE_IDS
            or record.get("canonical_root") is not False
            or record.get("new_capability") is not False
            or record.get("new_architectural_authority") is not False
            or record.get("capability_count") != CAPABILITY_COUNT
        ):
            findings.append(finding("HARDEN-001", "Profile capability/authority invariant drift", profile=record.get("id")))

    if data["contract"].get("capability_count") != CAPABILITY_COUNT:
        findings.append(finding("HARDEN-002", "Runtime hardening contract capability count drift"))

    provider = data["provider"]
    if (
        provider.get("id") != "FA3-PROVIDER-PYNVVIDEOCODEC-001"
        or provider.get("architectural_authority") is not False
        or provider.get("new_capability") is not False
        or provider.get("new_architectural_authority") is not False
        or provider.get("capability_count") != CAPABILITY_COUNT
        or provider.get("runtime_activation", {}).get("current_host_runtime_promotion_claimed") is not False
    ):
        findings.append(finding("HARDEN-003", "PyNvVideoCodec provider authority/promotion invariant drift"))

    vapoursynth = data["vapoursynth_provider"]
    if (
        vapoursynth.get("id") != "FA3-PROVIDER-VAPOURSYNTH-R80-001"
        or vapoursynth.get("upstream", {}).get("release") != "R80"
        or vapoursynth.get("upstream", {}).get("immutable_commit") != "732845793a1caf5838d4f7b94f6ce668a19c908e"
        or vapoursynth.get("architectural_authority") is not False
        or vapoursynth.get("new_capability") is not False
        or vapoursynth.get("capability_count") != CAPABILITY_COUNT
        or vapoursynth.get("current_host", {}).get("runtime_promotion_claimed") is not False
    ):
        findings.append(finding("HARDEN-018", "VapourSynth R80 provider pin/authority/promotion invariant drift"))

    reference = data["vapoursynth_reference"]
    if (
        reference.get("release") != "R80"
        or reference.get("immutable_commit") != "732845793a1caf5838d4f7b94f6ce668a19c908e"
        or reference.get("license_spdx") != "LGPL-2.1"
        or reference.get("current_host_runtime_evidence") != "NOT_CLAIMED"
    ):
        findings.append(finding("HARDEN-019", "VapourSynth R80 upstream reference invariant drift"))

    vapour_decision = data["vapoursynth_decision"]
    if (
        vapour_decision.get("new_capabilities") != 0
        or vapour_decision.get("new_architectural_authorities") != 0
        or vapour_decision.get("capability_count_after") != CAPABILITY_COUNT
        or vapour_decision.get("acceptance_criteria_after") != 22
        or vapour_decision.get("current_host_runtime_promotion_claim") is not False
    ):
        findings.append(finding("HARDEN-020", "VapourSynth runtime-hardening decision invariant drift"))

    decision = data["decision"]
    if (
        decision.get("new_capabilities") != 0
        or decision.get("new_architectural_authorities") != 0
        or decision.get("capability_count_after") != CAPABILITY_COUNT
        or decision.get("current_host_runtime_promotion_claim") is not False
    ):
        findings.append(finding("HARDEN-004", "Decision changes capability/authority/promotion baseline"))

    enforcement = data["enforcement"]
    rules = enforcement.get("rules", {})
    expected = {
        "hrb_resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001_ONLY",
        "runtime_launcher_resource_authority": "DENY",
        "environment_variable_resource_authority": "DENY",
        "arbitrary_agent_host_subprocess": "DENY",
        "accelerated_neural_media_claim": "ZERO_HOST_ROUND_TRIP",
        "shadow_can_assign_promoted": "DENY",
        "production_acceptance_criteria": "22_OF_22_PLUS_CURRENT_HOST_PASS",
        "rootless_provider_quadlet_materialization": "HRB_LEASE_BOUND_IMMUTABLE_TEMPLATE",
        "canonical_quadlet_template_mutation_per_lease": "DENY",
        "host_impact_agent_default_backend": "GVISOR_RUNSC_IF_COMPATIBLE",
        "direct_agent_container_runtime_socket": "DENY",
        "agent_default_tool_channel": "CENTRAL_MCP_GATEWAY_AUTHENTICATED_UNIX_SOCKET",
        "portable_gpu_frame_fabric": "FA3-PROVIDER-VAPOURSYNTH-R80-001",
        "vs_mlrt_role": "SEPARATE_NEURAL_RUNTIME_ADAPTER",
        "vspipe_y4m_ffmpeg_zero_host_round_trip_evidence": "DENY",
        "pcie_fixed_percent_zero_copy_proof": "DENY",
        "pcie_nvml_telemetry_role": "CORROBORATING_ONLY",
    }
    for key, value in expected.items():
        if rules.get(key) != value:
            findings.append(finding("HARDEN-005", "Runtime-hardening enforcement rule drift", rule=key))

    hrb = data["hrb"]
    quadlet = hrb.get("quadlet_runtime_projection", {})
    if (
        quadlet.get("canonical_template_mutation_forbidden") is not True
        or quadlet.get("rootless_required") is not True
        or quadlet.get("materialization_root") != "$XDG_RUNTIME_DIR/containers/systemd"
        or quadlet.get("runtime_ordinal_is_noncanonical") is not True
    ):
        findings.append(finding("HARDEN-021", "HRB Quadlet lease materialization policy missing/drifted"))
    projection = hrb.get("runtime_isolation_projection_policy", {})
    if (
        projection.get("profile_id") != "FA3-RUNTIME-ISOLATION-001"
        or projection.get("resource_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        or projection.get("launcher_authority") is not False
        or projection.get("environment_variable_authority") is not False
    ):
        findings.append(finding("HARDEN-006", "HRB runtime-isolation authority binding missing/drifted"))

    agent_exec = data["agent_exec"]
    closed_loop = data["closed_loop"]
    sandbox_profile = data["agent_sandbox"]
    host_impact = sandbox_profile.get("host_impact_policy", {})
    if (
        host_impact.get("preferred_backend") != "GVISOR_RUNSC"
        or host_impact.get("direct_container_runtime_socket") != "DENY"
        or host_impact.get("default_tool_channel") != "CENTRAL_MCP_GATEWAY_AUTHENTICATED_UNIX_SOCKET"
        or host_impact.get("workspace_destruction_receipt_required") is not True
    ):
        findings.append(finding("HARDEN-022", "Host-impact agent sandbox policy missing/drifted"))
    if agent_exec.get("sandbox_profile") != "FA3-AGENT-SANDBOX-001":
        findings.append(finding("HARDEN-007", "Agent execution profile is not bound to mandatory sandbox"))
    if "HOST_SUBPROCESS_ARBITRARY_AGENT_EXECUTION_FORBIDDEN" not in agent_exec.get("invariants", []):
        findings.append(finding("HARDEN-008", "Agent host-subprocess prohibition missing"))
    if closed_loop.get("sandbox_profile") != "FA3-AGENT-SANDBOX-001":
        findings.append(finding("HARDEN-009", "Closed-loop operations missing sandbox binding"))

    media_profile = data["media"]
    zero_profile = data["media_zero"]
    zero_roles = zero_profile.get("provider_roles", {})
    zero_evidence = zero_profile.get("evidence_policy", {})
    if (
        zero_roles.get("portable_gpu_frame_fabric") != "FA3-PROVIDER-VAPOURSYNTH-R80-001"
        or zero_roles.get("primary_nvidia_ai_frame_executor") != "FA3-PROVIDER-PYNVVIDEOCODEC-001"
        or zero_roles.get("neural_runtime_adapter") != "FA3-PROVIDER-VS-MLRT-001"
        or zero_evidence.get("vspipe_y4m_ffmpeg_zero_host_round_trip_claim") != "FORBIDDEN"
        or zero_evidence.get("pcie_nvml_telemetry_role") != "CORROBORATING_ONLY"
    ):
        findings.append(finding("HARDEN-023", "Portable GPU frame fabric or zero-host evidence semantics drift"))

    neural_contract = data["neural_contract"]
    frame_policy = neural_contract.get("frame_memory_policy", {})
    if (
        frame_policy.get("portable_gpu_frame_fabric") != "FA3-PROVIDER-VAPOURSYNTH-R80-001"
        or frame_policy.get("residency_trace_required") is not True
        or frame_policy.get("vspipe_y4m_ffmpeg_zero_host_roundtrip_claim_forbidden") is not True
        or frame_policy.get("pcie_telemetry_is_primary_zero_copy_proof") is not False
    ):
        findings.append(finding("HARDEN-024", "Neural-media residency contract drift"))

    vsmlrt = data["vsmlrt"]
    if (
        vsmlrt.get("vapoursynth_frame_fabric_provider") != "FA3-PROVIDER-VAPOURSYNTH-R80-001"
        or vsmlrt.get("residency_policy", {}).get("native_gpu_residency_assumed") is not False
        or vsmlrt.get("residency_policy", {}).get("backend_specific_current_host_e2e_required") is not True
    ):
        findings.append(finding("HARDEN-025", "vs-mlrt adapter separation/residency policy drift"))

    upstream_lock = data["upstream_locks"].get("locks", {}).get("vapoursynth_r80", {})
    if (
        upstream_lock.get("version") != "R80"
        or upstream_lock.get("revision") != "732845793a1caf5838d4f7b94f6ce668a19c908e"
    ):
        findings.append(finding("HARDEN-026", "VapourSynth R80 upstream lock missing/drifted"))

    media_policy = media_profile.get("accelerated_ai_frame_policy", {})
    if (
        media_profile.get("zero_host_roundtrip_profile_id") != "FA3-MEDIA-GPU-ZEROCOPY-001"
        or media_policy.get("claim_semantics") != "ZERO_HOST_ROUND_TRIP"
        or media_policy.get("primary_nvidia_ai_frame_executor") != "FA3-PROVIDER-PYNVVIDEOCODEC-001"
        or media_profile.get("primary_low_level_executor") != "FA3-PROVIDER-FFMPEG-001"
    ):
        findings.append(finding("HARDEN-010", "Neural-media executor roles or residency semantics drift"))

    voice = data["voice"]
    voice_routing = data["voice_routing"]
    if voice.get("hu_aqc_profile_id") != "FA3-HU-AQC-001":
        findings.append(finding("HARDEN-011", "Voice profile is not bound to Hungarian AQC"))
    aqc_policy = voice_routing.get("aqc_policy", {})
    if (
        aqc_policy.get("profile_id") != "FA3-HU-AQC-001"
        or aqc_policy.get("single_metric_authority") is not False
        or aqc_policy.get("fail_closed") is not True
    ):
        findings.append(finding("HARDEN-012", "Voice routing Hungarian AQC policy missing/drifted"))

    shadow = data["shadow"]
    prod = shadow.get("production_requirements", {})
    if (
        prod.get("acceptance_criteria_passed") != 22
        or prod.get("acceptance_criteria_total") != 22
        or shadow.get("shadow_may_never_assign") != ["PROMOTED"]
    ):
        findings.append(finding("HARDEN-013", "Shadow execution weakens canonical promotion gate"))

    policy = data["policy"]
    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(finding("HARDEN-014", "Runtime hardening gate not bound into permanent policy"))
    if policy.get("runtime_hardening_gate_id") != GATE_ID:
        findings.append(finding("HARDEN-015", "Runtime hardening policy binding missing"))
    if policy.get("canonical_capability_count") != CAPABILITY_COUNT:
        findings.append(finding("HARDEN-016", "Global capability count drift"))

    regression_rows = regressions()
    failed = [x["name"] for x in regression_rows if x["result"] != "PASS"]
    if failed:
        findings.append(finding("HARDEN-017", "Executable hardening regressions failed", failed=failed))

    return _report(root, findings, regression_rows)


def _report(root: Path, findings: list[dict[str, Any]], regression_rows: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "schema": "fa3.runtime-hardening-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_ids": list(PROFILE_IDS),
        "capability_count": CAPABILITY_COUNT,
        "authority_delta": 0,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "regression_count": len(regression_rows),
        "regressions": regression_rows,
        "current_host_runtime_promotion_claim": False,
        "production_promotion_gate_bypassed": False,
    }
    out = root / "reports/runtime-hardening-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 cross-cutting runtime hardening gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
