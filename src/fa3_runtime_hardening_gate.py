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
    "FA3-PROVIDER-RUNTIME-001",
)

PATHS = {
    "runtime_isolation": "canonical/profiles/FA3-RUNTIME-ISOLATION-001.json",
    "agent_sandbox": "canonical/profiles/FA3-AGENT-SANDBOX-001.json",
    "media_zero": "canonical/profiles/FA3-MEDIA-GPU-ZEROCOPY-001.json",
    "hu_aqc": "canonical/profiles/FA3-HU-AQC-001.json",
    "shadow": "canonical/profiles/FA3-PROMOTION-SHADOW-001.json",
    "provider_runtime": "canonical/profiles/FA3-PROVIDER-RUNTIME-001.json",
    "contract": "canonical/contracts/FA3-RUNTIME-HARDENING-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-PYNVVIDEOCODEC-001.json",
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
    "current_host_conformance": "canonical/FA3-RUNTIME-HARDENING-CURRENT-HOST-CONFORMANCE-001.json",
    "current_host_gate": "canonical/FA3-GATE-RUNTIME-HARDENING-CURRENT-HOST-001.json",
    "current_host_enforcement": "canonical/runtime-hardening-current-host-enforcement.json",
    "current_host_decision": "canonical/decisions/FA3-DEC-RUNTIME-HARDENING-CURRENT-HOST-2026-09-19.json",
    "current_host_reference": "canonical/references/FA3-RUNTIME-HARDENING-CURRENT-HOST-UPSTREAM-REFERENCE-2026-09-19.json",
    "secret_broker_contract": "canonical/contracts/FA3-SECRET-BROKER-CONTRACTS-001.json",
    "reconciliation": "canonical/decisions/FA3-DEC-MODERNIZATION-RECONCILIATION-2026-09-20.json",
    "hardware_decision": "canonical/decisions/FA3-DEC-HARDWARE-AUDIT-2026-09-20.json",
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
        "production-19-of-19",
        shadow_execution_valid(
            **{
                **shadow,
                "current_host_evidence": "PASS",
                "execution_mode": "PRODUCTION",
                "acceptance_criteria_passed": 19,
                "acceptance_criteria_total": 19,
                "canonical_promotion_gate_pass": True,
            }
        ),
        not shadow_execution_valid(
            **{
                **shadow,
                "current_host_evidence": "PENDING_CURRENT_HOST",
                "execution_mode": "PRODUCTION",
                "acceptance_criteria_passed": 19,
                "acceptance_criteria_total": 19,
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

    for key in ("runtime_isolation", "agent_sandbox", "media_zero", "hu_aqc", "shadow", "provider_runtime"):
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

    decision = data["decision"]
    if (
        decision.get("new_capabilities") != 0
        or decision.get("new_architectural_authorities") != 0
        or not isinstance(decision.get("capability_count_after"), int) or decision.get("capability_count_after") > CAPABILITY_COUNT
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
        "accelerated_neural_media_claim": "CLASSIFIED_AS_ZERO_COPY_PROVEN_TRANSFER_MINIMIZED_OR_NOT_ZERO_COPY",
        "shadow_can_assign_promoted": "DENY",
        "production_acceptance_criteria": "19_OF_19_PLUS_CURRENT_HOST_PASS",
        "provider_runtime_class_explicit": "REQUIRED",
        "conda_mamba_baseline": "DENY",
        "oci_rootless_digest_pinned_when_selected": "REQUIRED",
    }
    for key, value in expected.items():
        if rules.get(key) != value:
            findings.append(finding("HARDEN-005", "Runtime-hardening enforcement rule drift", rule=key))

    hrb = data["hrb"]
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
    if agent_exec.get("sandbox_profile") != "FA3-AGENT-SANDBOX-001":
        findings.append(finding("HARDEN-007", "Agent execution profile is not bound to mandatory sandbox"))
    if "HOST_SUBPROCESS_ARBITRARY_AGENT_EXECUTION_FORBIDDEN" not in agent_exec.get("invariants", []):
        findings.append(finding("HARDEN-008", "Agent host-subprocess prohibition missing"))
    if closed_loop.get("sandbox_profile") != "FA3-AGENT-SANDBOX-001":
        findings.append(finding("HARDEN-009", "Closed-loop operations missing sandbox binding"))

    media_profile = data["media"]
    media_policy = media_profile.get("accelerated_ai_frame_policy", {})
    if (
        media_profile.get("zero_host_roundtrip_profile_id") != "FA3-MEDIA-GPU-ZEROCOPY-001"
        or media_policy.get("claim_semantics") != "CLASSIFIED_MEMORY_RESIDENCY_EVIDENCE"
        or media_policy.get("optional_nvidia_ai_frame_executor") != "FA3-PROVIDER-PYNVVIDEOCODEC-001"
        or media_policy.get("universal_pcie_percentage_threshold") != "FORBIDDEN"
        or media_policy.get("non_claiming_or_cpu_only_path") != "VALID_WITHOUT_ACCELERATOR_PROVIDER"
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
        prod.get("acceptance_criteria_passed") != 19
        or prod.get("acceptance_criteria_total") != 19
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

    current_host = data["current_host_conformance"]
    current_host_gate = data["current_host_gate"]
    current_host_enforcement = data["current_host_enforcement"]
    current_host_decision = data["current_host_decision"]
    current_host_reference = data["current_host_reference"]
    if not (
        current_host.get("id") == "FA3-RUNTIME-HARDENING-CURRENT-HOST-CONFORMANCE-001"
        and current_host.get("status") == "EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING"
        and current_host.get("capability_count") == CAPABILITY_COUNT
        and current_host.get("new_capabilities") == 0
        and current_host.get("new_architectural_authorities") == 0
        and current_host.get("global_promotion_claim") is False
        and len(current_host.get("surfaces", [])) == 4
    ):
        findings.append(finding("HARDEN-018", "Runtime hardening current-host conformance materialization drift"))
    if not (
        current_host_gate.get("gateset_id") == "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"
        and current_host_gate.get("conformance_id") == current_host.get("id")
        and current_host_gate.get("fail_closed") is True
        and current_host_gate.get("current_host_runner_required") is True
        and current_host_gate.get("global_promotion_claim") is False
    ):
        findings.append(finding("HARDEN-019", "Runtime hardening current-host gate materialization drift"))
    host_rules = current_host_enforcement.get("rules", {})
    if not (
        current_host_enforcement.get("gate_id") == "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"
        and current_host_enforcement.get("fail_closed") is True
        and host_rules.get("github_hosted_substitution") == "DENY"
        and host_rules.get("sandbox_compatibility_smoke_as_production_isolation") == "DENY"
        and host_rules.get("shadow_promotion_authority") == "DENY"
        and host_rules.get("universal_pcie_percentage_threshold") == "DENY"
        and host_rules.get("media_surface_applicability") == "CONDITIONAL_ON_ZERO_HOST_ROUND_TRIP_CLAIM"
    ):
        findings.append(finding("HARDEN-020", "Runtime hardening current-host enforcement drift"))
    if not (
        current_host_decision.get("status") == "CANONICAL_CLOSED"
        and current_host_decision.get("current_host_runtime_promotion_claim") is False
        and current_host_decision.get("global_promotion_claim") is False
        and current_host_reference.get("production_admission_effect") == "REFERENCE_ONLY_NOT_CURRENT_HOST_PASS"
    ):
        findings.append(finding("HARDEN-021", "Runtime hardening current-host decision/reference overclaim"))
    if not (
        policy.get("runtime_hardening_current_host_conformance_id") == current_host.get("id")
        and policy.get("runtime_hardening_current_host_gate_id") == "FA3-RUNTIME-HARDENING-CURRENT-HOST-GATESET-001"
        and policy.get("runtime_hardening_current_host_status") == "PENDING_REAL_SELF_HOSTED_EXECUTION"
        and policy.get("runtime_hardening_current_host_global_promotion_claim") is False
    ):
        findings.append(finding("HARDEN-022", "Global policy current-host hardening binding drift"))

    secret_broker = data["secret_broker_contract"]
    delivery = secret_broker.get("delivery", {})
    secret_evidence = secret_broker.get("evidence", {})
    if not (
        secret_broker.get("provider_neutral") is True
        and secret_broker.get("authority") == "FA3-AUTH-SECRETS-001"
        and secret_broker.get("capability_count") == CAPABILITY_COUNT
        and secret_broker.get("new_capabilities") == 0
        and secret_broker.get("new_architectural_authorities") == 0
        and delivery.get("world_writable_socket_forbidden") is True
        and delivery.get("peer_credential_validation_required") is True
        and delivery.get("nonce_and_replay_protection_required") is True
        and delivery.get("lease_ttl_bound_to_cgroup_and_pidfd_liveness") is True
        and delivery.get("production_test_secret_under_run_secrets_forbidden") is True
        and secret_evidence.get("durable_or_externally_verifiable_receipts") == "ASYMMETRIC_SIGNATURE_REQUIRED"
        and secret_evidence.get("hmac_as_external_evidence_authority_forbidden") is True
    ):
        findings.append(finding("HARDEN-023", "Provider-neutral secret broker contract drift"))

    reconciliation = data["reconciliation"]
    baseline = reconciliation.get("baseline", {})
    closure = reconciliation.get("closure_semantics", {})
    rejected = set(reconciliation.get("rejected", []))
    if not (
        reconciliation.get("status") == "ACCEPTED_MATERIALIZED"
        and isinstance(baseline.get("capability_count_before"), int) and baseline.get("capability_count_before") == baseline.get("capability_count_after") and baseline.get("capability_count_after") <= CAPABILITY_COUNT
        and baseline.get("acceptance_criteria_before") == baseline.get("acceptance_criteria_after") == 19
        and baseline.get("new_architectural_authorities") == 0
        and "GLOBAL_NVIDIA_CUDA_NVML_RTX_SM86_GPU_SKU_INDEX_UUID_OR_VRAM_BASELINE" in rejected
        and "EXPANDING_NINETEEN_ACCEPTANCE_CRITERIA_TO_TWENTY_TWO" in rejected
        and closure.get("global_promotion_claim") is False
        and closure.get("fabricated_current_host_pass_forbidden") is True
        and isinstance(data["hardware_decision"].get("capability_count_after"), int) and data["hardware_decision"].get("capability_count_after") <= CAPABILITY_COUNT
        and policy.get("secret_broker_contract_id") == secret_broker.get("id")
        and policy.get("modernization_reconciliation_decision_id") == reconciliation.get("id")
        and policy.get("modernization_acceptance_criteria_count") == 19
    ):
        findings.append(finding("HARDEN-024", "Modernization reconciliation invariant drift"))

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
