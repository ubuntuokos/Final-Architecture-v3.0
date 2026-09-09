#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

GATE_ID = "FA3-STABLE-AUDIO-3-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-STABLE-AUDIO-3-001"
PROVIDER_ID = "FA3-PROVIDER-STABLE-AUDIO-3-001"
PROFILE_ID = "FA3-MUSIC-001"
CONTRACT_ID = "FA3-MUSIC-GENERATION-CONTRACTS-001"
UPSTREAM_PIN = "779434a908193105335fd8d833418603625b2859"
CAPABILITY_COUNT = 143

P0_INVARIANTS = [
    "STABLE_AUDIO_3_REQUIRED_SUPPORTED_PROVIDER",
    "STABLE_AUDIO_3_NOT_ARCHITECTURAL_AUTHORITY",
    "STABLE_AUDIO_3_CAPABILITY_COUNT_REMAINS_143",
    "MUSIC_PROFILE_BIDIRECTIONAL_PROVIDER_BINDING_REQUIRED",
    "STABLE_AUDIO_3_IMMUTABLE_UPSTREAM_REFERENCE_REQUIRED",
    "PROVIDER_NEUTRAL_MUSIC_RUNTIME_CONTRACT_REQUIRED",
    "STABLE_AUDIO_3_RUNTIME_IDENTITY_COMPLETE_AND_IMMUTABLE",
    "AUDIO_AFFECTING_RUNTIME_SEMANTICS_PROVENANCE_REQUIRED",
    "NO_SILENT_MODEL_BACKEND_DEVICE_PRECISION_OR_CLOUD_FALLBACK",
    "ACCELERATOR_EXECUTION_REQUIRES_HRB_LEASE",
    "SMALL_MUSIC_AND_SFX_CPU_LOCAL_CANDIDATES",
    "MEDIUM_LOCAL_ACCELERATED_ROUTE_REQUIRES_REAL_E2E",
    "LARGE_ROUTE_REMAINS_REMOTE_API_OR_ENTERPRISE",
    "MEDIUM_BF16_RETIRED_FAIL_CLOSED",
    "FLASH_ATTENTION_PRODUCTION_ARTIFACT_IMMUTABLE_HASHED_PROVENANCED",
    "SAFETENSORS_PREFERRED_WHEN_UPSTREAM_AVAILABLE",
    "CODE_MODEL_AND_OUTPUT_LICENSE_DIMENSIONS_SEPARATE",
    "CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E",
    "LOSSLESS_44K1_STEREO_MASTER_REQUIRED",
    "LIMITER_AND_PCM_CONVERSION_ARE_RUNTIME_IDENTITY",
    "TENSORRT_ENGINE_COMPUTE_CAPABILITY_BINDING_REQUIRED",
    "CURRENT_HOST_PROMOTION_STAGE_SEQUENCE_REQUIRED",
]

RUNTIME_IDENTITY_FIELDS = {
    "backend", "model_revision", "model_variant", "decoder_variant", "precision",
    "engine_compute_capability", "chunking_mode", "limiter_identity", "codec_revision",
    "seed", "runtime_revision", "quantization", "pcm_conversion_semantics",
}

CURRENT_HOST_CASES = {
    "SA3-CH-001-small-sfx-cpu-text-to-audio",
    "SA3-CH-002-small-music-cpu-text-to-audio",
    "SA3-CH-003-medium-pytorch-cuda-hrb",
    "SA3-CH-004-medium-tensorrt-live-sm-pinned-engine",
    "SA3-CH-005-audio-to-audio",
    "SA3-CH-006-inpainting-and-continuation",
    "SA3-CH-007-wav-44k1-stereo-limiter-metadata",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def immutable_pin(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def runtime_identity_contract_valid(contract: dict[str, Any], provider: dict[str, Any]) -> bool:
    rc = contract.get("runtime_identity_contract", {})
    pc = provider.get("runtime_identity", {})
    return (
        RUNTIME_IDENTITY_FIELDS <= set(rc.get("required_fields", []))
        and RUNTIME_IDENTITY_FIELDS <= set(pc.get("required_fields", []))
        and rc.get("identity_change_requires_new_provenance") is True
        and rc.get("silent_runtime_identity_mutation_forbidden") is True
        and pc.get("immutable_for_production_receipt") is True
        and pc.get("silent_mutation_forbidden") is True
    )


def precision_policy_valid(provider: dict[str, Any]) -> bool:
    p = provider.get("precision_policy", {})
    return (
        p.get("medium_default") == "fp16"
        and set(p.get("allowed_medium", [])) == {"fp16", "fp8", "fp32"}
        and "bf16" in p.get("retired_medium", [])
        and p.get("silent_precision_fallback") is False
        and p.get("legacy_alias_normalization_requires_provenance") is True
    )


def supply_chain_valid(provider: dict[str, Any]) -> bool:
    s = provider.get("supply_chain", {})
    f = s.get("flash_attention", {})
    w = s.get("weight_loading", {})
    return (
        s.get("code_license") == "MIT"
        and s.get("code_license_does_not_admit_weights_or_outputs") is True
        and s.get("model_license_and_output_rights_require_separate_admission") is True
        and f.get("floating_community_wheel_url_for_production_forbidden") is True
        and f.get("immutable_version_sha256_and_provenance_required") is True
        and f.get("source_build_with_immutable_inputs_allowed") is True
        and w.get("safetensors_preferred_when_upstream_available") is True
        and w.get("unsafe_pickle_is_not_default_admission_route") is True
        and s.get("production_runtime_network_model_fetch") is False
    )


def reference_check(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-MUSIC-001.json",
        "contract": root / "canonical/contracts/FA3-MUSIC-GENERATION-CONTRACTS-001.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-STABLE-AUDIO-3-HARDENING-2026-09-08.json",
        "enforcement": root / "canonical/stable-audio-3-enforcement.json",
        "gate": root / "canonical/FA3-GATE-STABLE-AUDIO-3-001.json",
        "runtime": root / "canonical/FA3-STABLE-AUDIO-3-RUNTIME-CONFORMANCE-001.json",
        "evidence": root / "evidence/reference/stable-audio-3-ci-2026-09-08.json",
    }
    for name, path in paths.items():
        if not path.is_file():
            findings.append(finding("SA3-REF-001", "required Stable Audio 3 artifact missing", record=name, path=str(path)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    r = {name: loadj(path) for name, path in paths.items()}
    profile, contract, provider = r["profile"], r["contract"], r["provider"]

    if profile.get("id") != PROFILE_ID or profile.get("capability_count") != CAPABILITY_COUNT:
        findings.append(finding("SA3-PROFILE-001", "music profile identity/capability invariant drift"))
    if PROVIDER_ID not in profile.get("providers", []) or "FA3-PROVIDER-ACE-STEP-001" not in profile.get("providers", []):
        findings.append(finding("SA3-PROFILE-002", "music profile provider reconciliation drift"))
    if provider.get("id") != PROVIDER_ID or PROFILE_ID not in provider.get("profiles", []):
        findings.append(finding("SA3-PROV-001", "provider/profile bidirectional binding drift"))
    if provider.get("status") != "REQUIRED_SUPPORTED_REFERENCE":
        findings.append(finding("SA3-PROV-002", "provider required-supported status drift"))
    if provider.get("immutable_reference") != UPSTREAM_PIN or not immutable_pin(provider.get("immutable_reference", "")):
        findings.append(finding("SA3-PIN-001", "upstream immutable pin drift"))
    if any(provider.get(k) is not False for k in ("canonical_root", "architectural_authority", "new_capability", "new_architectural_authority")):
        findings.append(finding("SA3-AUTH-001", "Stable Audio 3 escalated to forbidden authority/root/capability"))
    if provider.get("capability_count") != CAPABILITY_COUNT:
        findings.append(finding("SA3-CAP-001", "capability count changed"))

    if contract.get("id") != CONTRACT_ID or contract.get("provider_neutral") is not True:
        findings.append(finding("SA3-CONTRACT-001", "music contract is not provider neutral"))
    rules = contract.get("rules", {})
    for key in (
        "accelerator_execution_requires_host_resource_broker_lease",
        "model_variant_and_runtime_identity_must_be_immutable",
        "audio_affecting_runtime_semantics_must_be_provenance_bearing",
        "silent_backend_device_precision_or_cloud_fallback_forbidden",
        "current_host_evidence_required_for_runtime_promotion",
    ):
        if rules.get(key) is not True:
            findings.append(finding("SA3-CONTRACT-002", f"required runtime rule disabled: {key}"))
    if not runtime_identity_contract_valid(contract, provider):
        findings.append(finding("SA3-IDENT-001", "runtime identity/provenance contract incomplete"))

    routes = provider.get("routes", {})
    if routes.get("small_music") != "CPU_LOCAL_CANDIDATE" or routes.get("small_sfx") != "CPU_LOCAL_CANDIDATE":
        findings.append(finding("SA3-ROUTE-001", "Small CPU route drift"))
    if routes.get("medium") != "CUDA_LOCAL_CANDIDATE_SUBJECT_TO_HRB_E2E":
        findings.append(finding("SA3-ROUTE-002", "Medium local accelerated route lost E2E gate"))
    if routes.get("large") != "REMOTE_API_OR_ENTERPRISE_SELF_HOST":
        findings.append(finding("SA3-ROUTE-003", "Large remote/API route drift"))
    if not precision_policy_valid(provider):
        findings.append(finding("SA3-PREC-001", "Medium precision retirement/selection policy drift"))

    trt = provider.get("tensorrt_policy", {})
    if not all(trt.get(k) is True for k in (
        "engine_compute_capability_binding_required",
        "live_gpu_compute_capability_discovery_required",
        "self_built_engine_requires_onnx_and_build_provenance",
        "chunking_mode_must_be_recorded",
    )) or trt.get("non_matching_engine_download_for_production_forbidden") is not True:
        findings.append(finding("SA3-TRT-001", "TensorRT architecture/provenance admission drift"))

    audio = provider.get("audio_output_semantics", {})
    limiter = audio.get("limiter", {})
    if audio.get("canonical_sample_rate_hz") != 44100 or audio.get("canonical_channels") != 2 or audio.get("canonical_master") != "lossless":
        findings.append(finding("SA3-AUDIO-001", "canonical lossless 44.1kHz stereo output drift"))
    if limiter.get("sample_peak_ceiling") != 0.977 or limiter.get("provenance_required") is not True or audio.get("pcm_int16_conversion") != "ROUND_TO_NEAREST":
        findings.append(finding("SA3-AUDIO-002", "limiter/PCM runtime identity drift"))
    if not supply_chain_valid(provider):
        findings.append(finding("SA3-SCS-001", "Stable Audio 3 supply-chain admission drift"))

    enforcement = r["enforcement"]
    if enforcement.get("gate_id") != GATE_ID or enforcement.get("p0_invariants") != P0_INVARIANTS or enforcement.get("fail_closed") is not True:
        findings.append(finding("SA3-GATE-001", "Stable Audio 3 enforcement/P0 set drift"))
    gate_rec = r["gate"]
    if gate_rec.get("id") != EXECUTABLE_GATE_ID or gate_rec.get("gateset") != GATE_ID or gate_rec.get("parent_gateset") != "FA3-STABILITY-PORTFOLIO-GATESET-001":
        findings.append(finding("SA3-GATE-002", "executable gate parent/binding drift"))

    decision = r["decision"]
    if decision.get("status") != "CANONICAL_CLOSED" or decision.get("capability_count_after") != CAPABILITY_COUNT or decision.get("new_capabilities") != 0 or decision.get("new_architectural_authorities") != 0:
        findings.append(finding("SA3-DEC-001", "Stable Audio 3 decision changed baseline semantics"))

    runtime = r["runtime"]
    if set(runtime.get("required_cases", [])) != CURRENT_HOST_CASES or runtime.get("current_host_status") != "PENDING_REAL_HOST_EXECUTION" or runtime.get("production_promotion_claim") is not False:
        findings.append(finding("SA3-CH-001", "current-host admission contract overclaims or lost required cases"))
    if provider.get("promotion_sequence") != runtime.get("promotion_sequence"):
        findings.append(finding("SA3-CH-002", "current-host promotion stage sequence drift"))

    evidence = r["evidence"]
    if evidence.get("status") != "PASS" or evidence.get("mandatory_rules_passed") != len(P0_INVARIANTS) or evidence.get("current_host_runtime_evidence") is not False or evidence.get("production_promotion_claim") is not False:
        findings.append(finding("SA3-EVID-001", "reference evidence invalid or overclaims current-host promotion"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def current_host_gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    receipt_path = root / "evidence/receipts/stable-audio-3-current-host.json"
    findings: list[dict[str, Any]] = []
    if not receipt_path.is_file():
        findings.append(finding("SA3-CH-EVID-001", "real current-host Stable Audio 3 receipt missing"))
    else:
        receipt = loadj(receipt_path)
        if receipt.get("status") != "CURRENT_HOST_STABLE_AUDIO_3_E2E_PASS" or receipt.get("current_host") is not True or receipt.get("production_e2e") is not True:
            findings.append(finding("SA3-CH-EVID-002", "receipt does not prove current-host production E2E"))
        cases = receipt.get("cases", [])
        ids = {c.get("case_id") for c in cases if c.get("status") == "PASS"}
        if ids != CURRENT_HOST_CASES:
            findings.append(finding("SA3-CH-EVID-003", "required current-host case set incomplete", passed=sorted(ids)))
        if receipt.get("upstream_immutable_reference") != UPSTREAM_PIN:
            findings.append(finding("SA3-CH-EVID-004", "current-host receipt upstream pin mismatch"))
        if receipt.get("sample_rate_hz") != 44100 or receipt.get("channels") != 2 or receipt.get("limiter_ceiling") != 0.977:
            findings.append(finding("SA3-CH-EVID-005", "current-host audio contract mismatch"))
    report = {
        "schema": "fa3.stable-audio-3-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "current_host_runtime_evidence": not findings,
        "production_promotion_claim": not findings,
        "findings": findings,
    }
    out = root / "reports/stable-audio-3-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def gate(root: Path) -> dict[str, Any]:
    ref = reference_check(root)
    report = {
        "schema": "fa3.stable-audio-3-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "result": ref["result"],
        "blocking_findings": len(ref["findings"]),
        "findings": ref["findings"],
        "mandatory_rules": len(P0_INVARIANTS),
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "current_host_runtime_evidence": False,
        "production_promotion_claim": False,
    }
    out = Path(root).resolve() / "reports/stable-audio-3-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Stable Audio 3 fail-closed gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--current-host", action="store_true")
    args = ap.parse_args()
    report = current_host_gate(Path(args.root)) if args.current_host else gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
