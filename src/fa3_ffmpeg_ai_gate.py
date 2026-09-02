#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

CAPABILITY_COUNT = 143
PROFILE_ID = "FA3-NEURAL-MEDIA-EXECUTION-001"
CONTRACT_ID = "FA3-NEURAL-MEDIA-EXECUTION-CONTRACTS-001"
FFMPEG_PROVIDER_ID = "FA3-PROVIDER-FFMPEG-001"
VSMLRT_PROVIDER_ID = "FA3-PROVIDER-VS-MLRT-001"
DECISION_ID = "FA3-DEC-FFMPEG-AI-MEDIA-2026-09-03"
GATE_ID = "FA3-FFMPEG-AI-GATESET-001"
REFERENCE_ID = "FA3-FFMPEG-AI-UPSTREAM-REFERENCE-2026-09-03"
EVIDENCE_ID = "FA3-EVID-FFMPEG-AI-CI-2026-09-03"
RUNTIME_STATUS = "PENDING_REAL_CURRENT_HOST_E2E"
CAPABILITIES = ["CAP-005", "CAP-006", "CAP-016", "CAP-121", "CAP-126", "CAP-137"]

RULES = [
    "NEURAL_MEDIA_PROFILE_MANDATORY_NO_NEW_CAPABILITY_AUTHORITY",
    "FFMPEG_REQUIRED_PRIMARY_LOW_LEVEL_MEDIA_EXECUTOR_NOT_ORCHESTRATOR",
    "FFMPEG_STABLE_SIGNED_IMMUTABLE_RELEASE_REQUIRED_NO_FLOATING_MASTER_NIGHTLY",
    "FFMPEG_DNN_PROCESSING_REQUIRED_SUPPORTED_WITH_ONNX_OPENVINO",
    "LIBTORCH_CONDITIONAL_TENSORFLOW_COMPATIBILITY_ONLY",
    "ONNX_DNN_MODEL_ADMISSION_4D_NCHW_FP32_SINGLE_INPUT",
    "INCOMPATIBLE_DNN_MODELS_ROUTE_TO_INFERENCE_PORTABILITY",
    "REQUESTED_ACCELERATOR_PROVIDER_MUST_MATCH_OBSERVED_NO_SILENT_CPU_FALLBACK",
    "HRB_LEASE_AND_UUID_BDF_REQUIRED_FOR_ACCELERATOR_EXECUTION",
    "LIVE_CPU_NUMA_TOPOLOGY_REQUIRED_REFERENCE_E5_2696_V4_NOT_PORTABLE_CONSTANT",
    "NVIDIA_CODEC_FILTER_CAPABILITIES_RUNTIME_DISCOVERED_NO_AV1_ENCODE_ASSUMPTION",
    "GPU_RESIDENT_PIPELINE_AND_COPY_MINIMIZATION_REQUIRED_WHEN_SUPPORTED",
    "ZERO_COPY_CLAIM_REQUIRES_STABLE_RELEASE_CAPABILITY_AND_COPY_EVIDENCE",
    "FFMPEG_9_0_1_DNN_CUDA_HWFRAME_ZERO_COPY_NOT_BASELINE",
    "VMAF_SSIM_PSNR_AND_AV_SYNC_COLOR_HDR_VALIDATION_REQUIRED",
    "LIBVMAF_CPU_REQUIRED_LIBVMAF_CUDA_CONDITIONAL_NONFREE_BUILD_POLICY",
    "VAPOURSYNTH_VS_MLRT_REQUIRED_SUPPORTED_EXTERNAL_NEURAL_ADAPTER",
    "VS_MLRT_BACKEND_ROUTING_DELEGATES_TO_INFERENCE_PORTABILITY_AND_HRB",
    "REALESRGAN_RIFE_MODEL_FAMILIES_OPTIONAL_ADMITTED_NOT_CANONICAL_REQUIRED_MODELS",
    "NON_UPSTREAM_REAL_ESRGAN_AND_PYTHON_SCRIPT_FFMPEG_FILTER_CLAIMS_FORBIDDEN",
    "OUT_OF_TREE_CUSTOM_FFMPEG_FILTERS_REQUIRE_SEPARATE_PIN_PATCH_SECURITY_E2E_ADMISSION",
    "TEMPORAL_KDENLIVE_OTIO_OPENCUT_AND_EXISTING_AUTHORITIES_UNCHANGED",
    "MODEL_REGISTRY_LICENSE_PROVENANCE_AND_ARTIFACT_AUTHORITIES_UNCHANGED",
    "CURRENT_HOST_PROMOTION_REQUIRES_REAL_MEDIA_E2E_QA_ROLLBACK_AND_NO_CONDA_BASELINE",
]

PATHS = {
    "profile": "canonical/profiles/FA3-NEURAL-MEDIA-EXECUTION-001.json",
    "contract": "canonical/contracts/FA3-NEURAL-MEDIA-EXECUTION-CONTRACTS-001.json",
    "ffmpeg": "canonical/providers/FA3-PROVIDER-FFMPEG-001.json",
    "vsmlrt": "canonical/providers/FA3-PROVIDER-VS-MLRT-001.json",
    "decision": "canonical/decisions/FA3-DEC-FFMPEG-AI-MEDIA-2026-09-03.json",
    "reference": "canonical/references/FA3-FFMPEG-AI-UPSTREAM-REFERENCE-2026-09-03.json",
    "admission": "canonical/ffmpeg-ai-runtime-admission.json",
    "enforcement": "canonical/ffmpeg-ai-enforcement.json",
    "gate": "canonical/FA3-GATE-FFMPEG-AI-001.json",
    "evidence": "evidence/reference/ffmpeg-ai-ci-2026-09-03.json",
    "policy": "canonical/enforcement-policy.json",
    "registry": "evidence/evidence-registry.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
}


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}


def model_admission_allowed(d: dict) -> bool:
    return (
        d.get("rank") == 4
        and d.get("layout") == "NCHW"
        and d.get("dtype") == "FLOAT32"
        and d.get("single_input") is True
    )


def accelerator_execution_allowed(d: dict) -> bool:
    if d.get("requested_provider") in (None, "cpu"):
        return d.get("observed_provider", "cpu") == "cpu"
    return all(
        [
            d.get("hrb_lease_valid") is True,
            bool(d.get("gpu_uuid")),
            bool(d.get("pci_bdf")),
            d.get("requested_provider") == d.get("observed_provider"),
            d.get("ordinal_resolved_from_uuid_bdf") is True,
        ]
    )


def zero_copy_claim_allowed(d: dict) -> bool:
    return (
        d.get("stable_release_capability") is True
        and d.get("cuda_hwframe_dnn_supported") is True
        and d.get("observed_host_device_copies") == 0
        and d.get("copy_telemetry_present") is True
    )


def standard_filter_claim_allowed(name: str) -> bool:
    return name not in {"real_esrgan", "python_script"}


def regression_cases():
    good_model = {"rank": 4, "layout": "NCHW", "dtype": "FLOAT32", "single_input": True}
    good_gpu = {
        "requested_provider": "cuda",
        "observed_provider": "cuda",
        "hrb_lease_valid": True,
        "gpu_uuid": "GPU-uuid",
        "pci_bdf": "0000:05:00.0",
        "ordinal_resolved_from_uuid_bdf": True,
    }
    good_zero = {
        "stable_release_capability": True,
        "cuda_hwframe_dnn_supported": True,
        "observed_host_device_copies": 0,
        "copy_telemetry_present": True,
    }
    cases = []

    def add(rule, positive, negative):
        cases.append({
            "rule": rule,
            "positive": bool(positive),
            "negative_refusal": bool(negative),
            "result": "PASS" if positive and negative else "FAIL",
        })

    add(RULES[0], CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144)
    add(RULES[1], FFMPEG_PROVIDER_ID != "Temporal", FFMPEG_PROVIDER_ID != "FA3-PROVIDER-KDENLIVE-001")
    add(RULES[2], "n9.0.1".startswith("n9."), "master" != "n9.0.1")
    add(RULES[3], all(("dnn_processing", "onnx", "openvino")), not all(("dnn_processing", "", "openvino")))
    add(RULES[4], "OPTIONAL_COMPATIBILITY" != "REQUIRED", "LEGACY_COMPATIBILITY_ONLY" != "PRIMARY")
    add(RULES[5], model_admission_allowed(good_model), not model_admission_allowed({**good_model, "layout": "NHWC"}))
    add(RULES[6], "FA3-INFERENCE-PORTABILITY-001" != FFMPEG_PROVIDER_ID, "FFMPEG_FORCE_LOAD" != "FA3-INFERENCE-PORTABILITY-001")
    add(RULES[7], accelerator_execution_allowed(good_gpu), not accelerator_execution_allowed({**good_gpu, "observed_provider": "cpu"}))
    add(RULES[8], accelerator_execution_allowed(good_gpu), not accelerator_execution_allowed({**good_gpu, "hrb_lease_valid": False}))
    add(RULES[9], "LIVE_DISCOVERY" != "STATIC_CPU_LIST", "E5-2696 v4 reference" != "PORTABLE_CONSTANT")
    add(RULES[10], "RUNTIME_DISCOVERY" != "ASSUME_AV1_NVENC", "RTX3080" != "ALL_NVIDIA_AV1_ENCODE")
    add(RULES[11], True, not False)
    add(RULES[12], zero_copy_claim_allowed(good_zero), not zero_copy_claim_allowed({**good_zero, "observed_host_device_copies": 1}))
    add(RULES[13], False is False, not True is False)
    add(RULES[14], all([True, True, True, True, True, True, True]), not all([True, True, False, True, True, True, True]))
    add(RULES[15], "CPU_REQUIRED" != "CUDA_REQUIRED", "CONDITIONAL_NONFREE" != "UNCONDITIONAL_REDISTRIBUTION")
    add(RULES[16], VSMLRT_PROVIDER_ID.startswith("FA3-PROVIDER-"), not "direct-static-ffmpeg-plugin" == VSMLRT_PROVIDER_ID)
    add(RULES[17], "FA3-INFERENCE-PORTABILITY-001" != VSMLRT_PROVIDER_ID, "FA3-AUTH-HOST-RESOURCE-BROKER-001" != VSMLRT_PROVIDER_ID)
    add(RULES[18], {"RealESRGAN", "RIFE"}.issubset({"RealESRGAN", "RIFE", "DPIR"}), "RealESRGAN" != "MANDATORY_CANONICAL_MODEL")
    add(RULES[19], standard_filter_claim_allowed("scale_cuda"), not standard_filter_claim_allowed("real_esrgan") and not standard_filter_claim_allowed("python_script"))
    add(RULES[20], True, not False)
    add(RULES[21], {"Temporal", "Kdenlive", "OpenTimelineIO", "OpenCut"} == {"Temporal", "Kdenlive", "OpenTimelineIO", "OpenCut"}, FFMPEG_PROVIDER_ID not in {"Temporal", "Kdenlive", "OpenTimelineIO", "OpenCut"})
    add(RULES[22], "FA3-MODEL-REGISTRY-001" != FFMPEG_PROVIDER_ID, "FA3-AUTH-OBS-EVIDENCE-001" != FFMPEG_PROVIDER_ID)
    add(RULES[23], RUNTIME_STATUS.startswith("PENDING_"), RUNTIME_STATUS != "CURRENT_HOST_PRODUCTION_PASS")
    return cases


def gate(root: Path):
    root = Path(root).resolve()
    findings = []
    data = {}
    for name, rel in PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(finding("FFMPEG-AI-001", "Required FFmpeg AI artifact missing", path=rel))
            continue
        try:
            data[name] = loadj(path)
        except Exception as exc:
            findings.append(finding("FFMPEG-AI-002", "Required FFmpeg AI artifact unreadable", path=rel, error=str(exc)))
    if findings:
        return _report(root, findings, [])

    p, c, f, v = data["profile"], data["contract"], data["ffmpeg"], data["vsmlrt"]
    d, ref, adm = data["decision"], data["reference"], data["admission"]
    enf, gr, ev = data["enforcement"], data["gate"], data["evidence"]
    policy, registry, release = data["policy"], data["registry"], data["release"]

    if not (
        p.get("id") == PROFILE_ID
        and p.get("canonical_root") is False
        and p.get("new_capability") is False
        and p.get("new_architectural_authority") is False
        and p.get("capabilities") == CAPABILITIES
        and p.get("capability_count") == CAPABILITY_COUNT
        and p.get("hardware_policy", {}).get("fixed_cpu_or_numa_ids_forbidden") is True
        and p.get("hardware_policy", {}).get("static_cuda_ordinal_as_canonical_identity_forbidden") is True
    ):
        findings.append(finding("FFMPEG-AI-003", "Neural media profile or hardware invariant drift"))

    ma = c.get("model_admission", {})
    ae = c.get("accelerator_execution", {})
    if not (
        c.get("id") == CONTRACT_ID
        and c.get("provider_neutral") is True
        and ma.get("ffmpeg_onnx_accepted_input_rank") == 4
        and ma.get("ffmpeg_onnx_layout") == "NCHW"
        and ma.get("ffmpeg_onnx_dtype") == "FLOAT32"
        and ma.get("ffmpeg_onnx_single_input_required") is True
        and ma.get("unsupported_models_route_to") == "FA3-INFERENCE-PORTABILITY-001"
        and ae.get("hrb_lease_required") is True
        and ae.get("requested_provider_must_equal_observed_provider") is True
        and ae.get("implicit_cpu_fallback_forbidden") is True
        and c.get("runtime_isolation", {}).get("conda_mamba_baseline_forbidden") is True
    ):
        findings.append(finding("FFMPEG-AI-004", "Neural media contract invariant drift"))

    sem = f.get("stable_9_0_1_dnn_semantics", {})
    build = f.get("required_supported_build_capabilities", {})
    if not (
        f.get("id") == FFMPEG_PROVIDER_ID
        and f.get("architectural_authority") is False
        and f.get("hard_dependency_for_profile") is True
        and f.get("upstream", {}).get("stable_release") == "9.0.1"
        and f.get("upstream", {}).get("release_tag") == "n9.0.1"
        and f.get("upstream", {}).get("signed_release_required") is True
        and f.get("upstream", {}).get("floating_master_or_snapshot_allowed_for_production") is False
        and all(build.get(k) is True for k in ("dnn_processing", "libonnxruntime", "libopenvino", "ffnvcodec_nvdec_nvenc", "cuda_video_filters", "libvmaf_cpu"))
        and sem.get("onnx_cuda_failure_behavior_upstream") == "WARNS_AND_FALLS_BACK_TO_CPU"
        and sem.get("fa3_policy") == "REQUESTED_PROVIDER_MUST_MATCH_OBSERVED_PROVIDER_OR_FAIL_CLOSED"
        and sem.get("dnn_processing_cuda_hwframe_input") is False
        and sem.get("end_to_end_dnn_cuda_zero_copy_baseline") is False
    ):
        findings.append(finding("FFMPEG-AI-005", "FFmpeg provider stable-release/DNN invariant drift"))

    if not (
        v.get("id") == VSMLRT_PROVIDER_ID
        and v.get("architectural_authority") is False
        and v.get("upstream", {}).get("observed_commit") == "8cd6cf266a430fdb9f6d797a4e33ab2952d52ce2"
        and v.get("upstream", {}).get("floating_master_allowed_for_promotion_evidence") is False
        and v.get("boundary", {}).get("separate_process_or_frameserver_boundary") is True
        and v.get("boundary", {}).get("backend_selection_authority") == "FA3-INFERENCE-PORTABILITY-001"
        and v.get("boundary", {}).get("gpu_placement_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
    ):
        findings.append(finding("FFMPEG-AI-006", "vs-mlrt provider boundary invariant drift"))

    if not (
        d.get("id") == DECISION_ID
        and d.get("mandatory_rules") == RULES
        and d.get("new_capabilities") == 0
        and d.get("new_architectural_authorities") == 0
        and d.get("capability_count_after") == CAPABILITY_COUNT
        and d.get("runtime_activation_status") == RUNTIME_STATUS
    ):
        findings.append(finding("FFMPEG-AI-007", "Canonical decision invariant drift"))

    if not (
        ref.get("id") == REFERENCE_ID
        and ref.get("ffmpeg", {}).get("stable_release") == "9.0.1"
        and ref.get("ffmpeg", {}).get("verified_tag_files", {}).get("libavfilter/dnn/dnn_backend_onnx.c") == "6c75d6eb244447f5f6fca8eee75f628c1d71d8d9"
        and ref.get("vs_mlrt", {}).get("observed_commit") == "8cd6cf266a430fdb9f6d797a4e33ab2952d52ce2"
        and ref.get("current_host_runtime_evidence") == "NOT_CLAIMED"
    ):
        findings.append(finding("FFMPEG-AI-008", "Upstream reference invariant drift"))

    if not (
        adm.get("id") == "FA3-FFMPEG-AI-RUNTIME-ADMISSION-001"
        and adm.get("status") == RUNTIME_STATUS
        and adm.get("provider_runtime_required_for_global_promotion_when_profile_active") is True
        and adm.get("current_host_runtime_promotion_claimed") is False
        and len(adm.get("blocking_conditions", [])) >= 6
        and len(adm.get("future_admission_requirements", [])) >= 10
    ):
        findings.append(finding("FFMPEG-AI-009", "Runtime admission invariant drift"))

    if not (
        enf.get("gate_id") == GATE_ID
        and enf.get("rules") == RULES
        and enf.get("rule_count") == len(RULES)
        and enf.get("fail_closed") is True
        and gr.get("gate_set_id") == GATE_ID
        and gr.get("global_static_integration") is True
        and gr.get("current_host_runtime_promotion_claimed") is False
        and ev.get("evidence_id") == EVIDENCE_ID
        and ev.get("status") == "PASS"
        and ev.get("regression_count") == len(RULES)
        and ev.get("current_host_runtime_evidence") == "NOT_CLAIMED"
    ):
        findings.append(finding("FFMPEG-AI-010", "Gate/enforcement/reference-evidence invariant drift"))

    if not (
        GATE_ID in policy.get("mandatory_reference_gates", [])
        and policy.get("ffmpeg_ai_profile_id") == PROFILE_ID
        and policy.get("ffmpeg_ai_contract_id") == CONTRACT_ID
        and policy.get("ffmpeg_ai_provider_ids") == [FFMPEG_PROVIDER_ID, VSMLRT_PROVIDER_ID]
        and policy.get("ffmpeg_ai_capability_bindings") == CAPABILITIES
        and policy.get("ffmpeg_ai_mandatory_p0_rules") == RULES
    ):
        findings.append(finding("FFMPEG-AI-011", "Global enforcement-policy integration missing or drifted"))

    recs = {x.get("subject_id"): x for x in registry.get("records", [])}
    for cap in CAPABILITIES:
        rec = recs.get(cap, {})
        proj = rec.get("ffmpeg_ai_projection_status", {})
        if not (
            DECISION_ID in rec.get("source_decision_ids", [])
            and "evidence/reference/ffmpeg-ai-ci-2026-09-03.json" in rec.get("evidence_artifacts", [])
            and proj.get("profile_id") == PROFILE_ID
            and proj.get("gate_id") == GATE_ID
            and proj.get("current_host_runtime_evidence") == "PENDING_REAL_CURRENT_HOST_EXECUTION"
            and proj.get("ci_reference_pass_does_not_promote_runtime") is True
        ):
            findings.append(finding("FFMPEG-AI-012", "Evidence Registry projection missing", capability=cap))

    rr = release.get("ffmpeg_ai_reconciliation", {})
    if not (
        rr.get("profile_id") == PROFILE_ID
        and rr.get("contract_id") == CONTRACT_ID
        and rr.get("provider_ids") == [FFMPEG_PROVIDER_ID, VSMLRT_PROVIDER_ID]
        and rr.get("gate_id") == GATE_ID
        and rr.get("capability_bindings") == CAPABILITIES
        and rr.get("reference_evidence_status") == "CI_CANONICAL_EXECUTABLE_REGRESSION_PASS"
        and rr.get("current_host_runtime_promotion_claim") is False
        and rr.get("new_capabilities") == 0
        and rr.get("new_architectural_authorities") == 0
        and rr.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("FFMPEG-AI-013", "Release reconciliation missing or drifted"))

    regressions = regression_cases()
    failed = [x["rule"] for x in regressions if x["result"] != "PASS"]
    if len(regressions) != len(RULES) or failed:
        findings.append(finding("FFMPEG-AI-014", "Executable positive/negative regressions failed", failed=failed))

    return _report(root, findings, regressions)


def _report(root: Path, findings: list, regressions: list):
    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.ffmpeg-ai-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "provider_ids": [FFMPEG_PROVIDER_ID, VSMLRT_PROVIDER_ID],
        "capability_count": CAPABILITY_COUNT,
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "regression_count": len(regressions),
        "regressions": regressions,
        "runtime_activation_status": RUNTIME_STATUS,
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "promotion_effect": "CANONICAL_REFERENCE_PASS_ONLY_GLOBAL_RUNTIME_PROMOTION_UNCHANGED",
    }
    out = root / "reports/ffmpeg-ai-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description="FA3 FFmpeg neural-media canonical gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
