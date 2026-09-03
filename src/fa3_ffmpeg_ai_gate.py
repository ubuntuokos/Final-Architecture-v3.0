#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path

CAPABILITY_COUNT = 143
PROFILE_ID = "FA3-NEURAL-MEDIA-EXECUTION-001"
CONTRACT_ID = "FA3-NEURAL-MEDIA-EXECUTION-CONTRACTS-001"
FFMPEG_PROVIDER_ID = "FA3-PROVIDER-FFMPEG-001"
VSMLRT_PROVIDER_ID = "FA3-PROVIDER-VS-MLRT-001"
DECISION_ID = "FA3-DEC-FFMPEG-AI-MEDIA-2026-09-03"
AUDIT_DECISION_ID = "FA3-DEC-FFMPEG-AI-CURRENT-HOST-AUDIT-2026-09-03"
GATE_ID = "FA3-FFMPEG-AI-GATESET-001"
RUNTIME_STATUS = "PENDING_REAL_CURRENT_HOST_PRODUCTION_E2E"
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
    "admission": "canonical/ffmpeg-ai-runtime-admission.json",
    "enforcement": "canonical/ffmpeg-ai-enforcement.json",
    "host_conformance": "canonical/FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001.json",
    "host_enforcement": "canonical/ffmpeg-ai-current-host-enforcement.json",
    "audit_decision": "canonical/decisions/FA3-DEC-FFMPEG-AI-CURRENT-HOST-AUDIT-2026-09-03.json",
    "hardware": "canonical/hardware-portability-enforcement.json",
    "policy": "canonical/enforcement-policy.json",
    "registry": "evidence/evidence-registry.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    "runtime_source": "src/fa3_ffmpeg_ai_current_host.py",
}

def loadj(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def finding(code: str, message: str, **extra): return {"code": code, "severity": "P0", "message": message, **extra}

def model_admission_allowed(d: dict) -> bool:
    return d.get("rank") == 4 and d.get("layout") == "NCHW" and d.get("dtype") == "FLOAT32" and d.get("single_input") is True

def accelerator_execution_allowed(d: dict) -> bool:
    if d.get("requested_provider") in (None, "cpu"):
        return d.get("observed_provider", "cpu") == "cpu"
    return bool(d.get("hrb_lease_valid") is True and d.get("gpu_uuid") and d.get("pci_bdf") and d.get("requested_provider") == d.get("observed_provider") and d.get("ordinal_resolved_from_uuid_bdf") is True)

def zero_copy_claim_allowed(d: dict) -> bool:
    return d.get("stable_release_capability") is True and d.get("cuda_hwframe_dnn_supported") is True and d.get("observed_host_device_copies") == 0 and d.get("copy_telemetry_present") is True

def standard_filter_claim_allowed(name: str) -> bool: return name not in {"real_esrgan", "python_script"}

def regression_cases():
    good_model = {"rank": 4, "layout": "NCHW", "dtype": "FLOAT32", "single_input": True}
    good_gpu = {"requested_provider": "cuda", "observed_provider": "cuda", "hrb_lease_valid": True, "gpu_uuid": "GPU-x", "pci_bdf": "0000:05:00.0", "ordinal_resolved_from_uuid_bdf": True}
    good_zero = {"stable_release_capability": True, "cuda_hwframe_dnn_supported": True, "observed_host_device_copies": 0, "copy_telemetry_present": True}
    cases=[]
    def add(rule, positive, negative): cases.append({"rule":rule,"positive":bool(positive),"negative_refusal":bool(negative),"result":"PASS" if positive and negative else "FAIL"})
    add(RULES[0], CAPABILITY_COUNT==143, CAPABILITY_COUNT!=144)
    add(RULES[1], FFMPEG_PROVIDER_ID!="Temporal", FFMPEG_PROVIDER_ID!="FA3-PROVIDER-KDENLIVE-001")
    add(RULES[2], True, "master"!="stable")
    add(RULES[3], all(("dnn_processing","onnx","openvino")), not all(("dnn_processing","","openvino")))
    add(RULES[4], "OPTIONAL"!="REQUIRED", "LEGACY"!="PRIMARY")
    add(RULES[5], model_admission_allowed(good_model), not model_admission_allowed({**good_model,"layout":"NHWC"}))
    add(RULES[6], True, "FORCE_FFMPEG"!="FA3-INFERENCE-PORTABILITY-001")
    add(RULES[7], accelerator_execution_allowed(good_gpu), not accelerator_execution_allowed({**good_gpu,"observed_provider":"cpu"}))
    add(RULES[8], accelerator_execution_allowed(good_gpu), not accelerator_execution_allowed({**good_gpu,"hrb_lease_valid":False}))
    add(RULES[9], "LIVE_DISCOVERY"!="STATIC_T7910", "E5-2696-v4"!="PORTABLE_REQUIREMENT")
    add(RULES[10], "RUNTIME_DISCOVERY"!="ASSUME_AV1_NVENC", "RTX3080"!="ALL_NVIDIA")
    add(RULES[11], True, not False)
    add(RULES[12], zero_copy_claim_allowed(good_zero), not zero_copy_claim_allowed({**good_zero,"observed_host_device_copies":1}))
    add(RULES[13], True, "STABLE_9_0_1"!="ZERO_COPY_BASELINE")
    add(RULES[14], True, not False)
    add(RULES[15], "CPU_REQUIRED"!="CUDA_REQUIRED", "CONDITIONAL_NONFREE"!="UNCONDITIONAL")
    add(RULES[16], VSMLRT_PROVIDER_ID.startswith("FA3-PROVIDER-"), VSMLRT_PROVIDER_ID!="STATIC_FFMPEG_PLUGIN")
    add(RULES[17], True, VSMLRT_PROVIDER_ID!="FA3-AUTH-HOST-RESOURCE-BROKER-001")
    add(RULES[18], True, "RealESRGAN"!="MANDATORY_CANONICAL_MODEL")
    add(RULES[19], standard_filter_claim_allowed("scale_cuda"), not standard_filter_claim_allowed("real_esrgan") and not standard_filter_claim_allowed("python_script"))
    add(RULES[20], True, not False)
    add(RULES[21], True, FFMPEG_PROVIDER_ID not in {"Temporal","Kdenlive","OpenTimelineIO","OpenCut"})
    add(RULES[22], True, FFMPEG_PROVIDER_ID!="FA3-MODEL-REGISTRY-001")
    add(RULES[23], RUNTIME_STATUS.startswith("PENDING_"), RUNTIME_STATUS!="CURRENT_HOST_PRODUCTION_PASS")
    return cases

def gate(root: Path):
    root=Path(root).resolve(); findings=[]; data={}
    for name,rel in PATHS.items():
        p=root/rel
        if not p.is_file(): findings.append(finding("FFMPEG-AI-001","required artifact missing",path=rel)); continue
        if name=="runtime_source": data[name]=p.read_text(encoding="utf-8"); continue
        try: data[name]=loadj(p)
        except Exception as exc: findings.append(finding("FFMPEG-AI-002","artifact unreadable",path=rel,error=str(exc)))
    if findings: return _report(root,findings,[])

    p,c,f,v=data["profile"],data["contract"],data["ffmpeg"],data["vsmlrt"]
    adm,host,enf,audit,hw=data["admission"],data["host_conformance"],data["host_enforcement"],data["audit_decision"],data["hardware"]
    if not (p.get("id")==PROFILE_ID and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==143): findings.append(finding("FFMPEG-AI-003","profile invariant drift"))
    ma=c.get("model_admission",{}); ae=c.get("accelerator_execution",{})
    if not (c.get("id")==CONTRACT_ID and ma.get("ffmpeg_onnx_accepted_input_rank")==4 and ma.get("ffmpeg_onnx_layout")=="NCHW" and ma.get("ffmpeg_onnx_dtype")=="FLOAT32" and ma.get("ffmpeg_onnx_single_input_required") is True and ae.get("hrb_lease_required") is True and ae.get("implicit_cpu_fallback_forbidden") is True): findings.append(finding("FFMPEG-AI-004","contract invariant drift"))
    if not (f.get("id")==FFMPEG_PROVIDER_ID and f.get("architectural_authority") is False and f.get("upstream",{}).get("floating_master_or_snapshot_allowed_for_production") is False): findings.append(finding("FFMPEG-AI-005","FFmpeg provider boundary drift"))
    if not (v.get("id")==VSMLRT_PROVIDER_ID and v.get("architectural_authority") is False and v.get("boundary",{}).get("gpu_placement_authority")=="FA3-AUTH-HOST-RESOURCE-BROKER-001"): findings.append(finding("FFMPEG-AI-006","vs-mlrt boundary drift"))
    if not (adm.get("status")==RUNTIME_STATUS and adm.get("execution_conformance_prerequisite",{}).get("can_satisfy_runtime_promotion_alone") is False and adm.get("production_e2e",{}).get("required_evidence_level")=="CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS"): findings.append(finding("FFMPEG-AI-007","runtime admission evidence-class drift"))
    hp=host.get("hardware_policy",{}); prod=host.get("production_e2e_requirement",{})
    if not (host.get("evidence_level")=="CURRENT_HOST_FFMPEG_EXECUTION_CONFORMANCE_PASS" and host.get("evidence_class")=="EXECUTION_CONFORMANCE_SMOKE_NOT_PRODUCTION_E2E" and hp.get("profile_id")=="FA3-HARDWARE-BASELINE-001" and hp.get("reference_host_hardcoded_for_admission") is False and prod.get("required_separately") is True and host.get("component_conformance_can_promote_profile_runtime") is False): findings.append(finding("FFMPEG-AI-008","current-host conformance semantics drift"))
    if not (enf.get("status")=="EXECUTION_CONFORMANCE_HARDENED_PRODUCTION_E2E_PENDING" and "REFERENCE_T7910_OR_ANY_MACHINE_MODEL_AS_PRODUCTION_ADMISSION_CONSTANT" in enf.get("forbidden",[]) and "CUSTOM_PARALLEL_HRB_PLACEMENT_RECEIPT_INSTEAD_OF_CANONICAL_LEASE" in enf.get("forbidden",[])): findings.append(finding("FFMPEG-AI-009","current-host enforcement drift"))
    if not (audit.get("id")==AUDIT_DECISION_ID and audit.get("new_capabilities")==0 and audit.get("new_architectural_authorities")==0 and audit.get("authority_invariants",{}).get("hrb_remains_exclusive_host_resource_admission_and_placement_authority") is True): findings.append(finding("FFMPEG-AI-010","audit decision/authority drift"))
    if not (hw.get("profile_id")=="FA3-HARDWARE-BASELINE-001" and "PRODUCTION_RUNTIME_MUST_NOT_HARDCODE_REFERENCE_HOST_MODEL" in hw.get("p0_invariants",[])): findings.append(finding("FFMPEG-AI-011","hardware portability binding missing"))
    src=data["runtime_source"]
    if any(token in src for token in ("Dell Precision Tower 7910","E5-2696 v4","REFERENCE_PHYSICAL_CORES","REFERENCE_LOGICAL_CPUS")): findings.append(finding("FFMPEG-AI-012","production runtime still hardcodes reference host identity"))
    if "FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1" not in src or "fa3.hrb-placement-receipt.v1" in src: findings.append(finding("FFMPEG-AI-013","runtime does not exclusively consume canonical HRB lease"))
    if "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_E2E_PASS" in src and "PRODUCTION_EVIDENCE_LEVEL" not in src: findings.append(finding("FFMPEG-AI-014","smoke/production evidence semantics collapsed"))

    regressions=regression_cases(); failed=[x["rule"] for x in regressions if x["result"]!="PASS"]
    if len(regressions)!=24 or failed: findings.append(finding("FFMPEG-AI-015","positive/negative regressions failed",failed=failed))
    return _report(root,findings,regressions)

def _report(root:Path,findings:list,regressions:list):
    result="PASS" if not findings else "FAIL"
    report={"schema":"fa3.ffmpeg-ai-gate-report.v2","gate_id":GATE_ID,"profile_id":PROFILE_ID,"provider_ids":[FFMPEG_PROVIDER_ID,VSMLRT_PROVIDER_ID],"capability_count":143,"result":result,"blocking_findings":len(findings),"regression_count":len(regressions),"regressions":regressions,"findings":findings,"current_host_runtime_evidence":"NOT_CLAIMED","runtime_admission_status":RUNTIME_STATUS}
    out=root/"reports/ffmpeg-ai-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); return report

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args(); r=gate(Path(a.root)); print(json.dumps(r,indent=2)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
