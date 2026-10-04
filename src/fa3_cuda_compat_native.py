#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fa3_cuda_compat_backends import lower_amd_hip, lower_intel_opencl, lower_intel_sycl
from fa3_cuda_compat_frontend import SOURCE_KIND, parse_cuda_translation_unit
from fa3_cuda_compat_runtime import runtime_api_support

NATIVE_BACKEND_NAME = "cfa3-cuda-compat"
EXTERNAL_SCALE_RUNTIME_DEPENDENCY = False

_TARGETS = {
    "AMD": {
        "default_target_backend": "hip",
        "target_language": "HIP_CPP",
        "required_device_backends": ("rocm",),
        "alternative_target_backends": (),
    },
    "INTEL": {
        "default_target_backend": "sycl",
        "target_language": "SYCL_CPP",
        "required_device_backends": ("level-zero",),
        "alternative_target_backends": ("opencl",),
    },
}
_INTEL_COMMON_UNSUPPORTED = {"WARP_INTRINSICS","CUDA_ATOMICS","CUDA_HALF_TYPES","CUDA_CONSTANT_MEMORY"}


@dataclass(frozen=True)
class TranslationArtifact:
    target_vendor: str
    target_backend: str
    target_language: str
    source: str
    source_sha256: str
    translated_sha256: str
    compatibility_result: str
    detected_features: tuple[str, ...]
    limitations: tuple[str, ...]


def _vendor(value: str) -> str:
    return str(value or "").strip().upper()


def _backend(value: str | None) -> str:
    return str(value or "").strip().lower()


def target_descriptor(target_vendor: str, *, target_backend: str | None = None) -> dict[str, Any] | None:
    vendor = _vendor(target_vendor)
    row = _TARGETS.get(vendor)
    if not row: return None
    requested = _backend(target_backend) or row["default_target_backend"]
    if vendor == "AMD" and requested != "hip": return None
    if vendor == "INTEL" and requested not in {"sycl","opencl"}: return None
    if vendor == "INTEL" and requested == "opencl":
        return {"target_backend":"opencl","target_language":"OPENCL_C","required_device_backends":("opencl","level-zero"),"alternative_target_backends":("sycl",)}
    return {"target_backend":requested,"target_language":row["target_language"],"required_device_backends":row["required_device_backends"],"alternative_target_backends":row["alternative_target_backends"]}


def analyze_cuda_source(source: str, *, target_vendor: str, source_kind: str = SOURCE_KIND, target_backend: str | None = None) -> dict[str, Any]:
    vendor = _vendor(target_vendor)
    target = target_descriptor(vendor, target_backend=target_backend)
    ir = parse_cuda_translation_unit(source, source_kind=source_kind)
    findings = set(ir.unsupported_features)
    limitations: set[str] = set()
    if target is None:
        findings.add("TARGET_VENDOR_OR_BACKEND_UNSUPPORTED")
    elif vendor == "INTEL":
        for feature in _INTEL_COMMON_UNSUPPORTED:
            if feature in ir.detected_features: findings.add(feature)
        if target["target_backend"] == "sycl" and "SHARED_MEMORY" in ir.detected_features:
            findings.add("CUDA_SHARED_MEMORY_REQUIRES_SYCL_LOCAL_ACCESSOR_ADAPTER")
        if ir.runtime_calls: findings.add("CUDA_RUNTIME_API_REQUIRES_HOST_ADAPTER")
        limitations.add("HOST_LAUNCH_ADAPTER_REQUIRED")
        limitations.add("SYCL_QUEUE_AND_CONTEXT_BINDING_REQUIRED" if target["target_backend"]=="sycl" else "OPENCL_HOST_LAUNCH_BINDING_REQUIRED")
    elif vendor == "AMD":
        runtime = runtime_api_support(ir.runtime_calls,target_vendor="AMD",target_backend="hip")
        for symbol in runtime["unsupported_symbols"]: findings.add(f"UNSUPPORTED_RUNTIME_SYMBOL:{symbol}")
    findings_list=sorted(findings)
    supported=not findings_list
    compatibility="UNAVAILABLE" if not supported else ("FULL_EQUIVALENCE" if vendor=="AMD" else "FUNCTIONALLY_REDUCED")
    return {
        "schema":"fa3.cuda-compat-source-analysis.v2","implementation":"CFA3_NATIVE","frontend":"CFA3_STRUCTURED_CUDA_FRONTEND_IR",
        "external_scale_runtime_dependency":False,"source_kind":source_kind,"source_sha256":ir.source_sha256,
        "target_vendor":vendor,"target_backend":target.get("target_backend") if target else None,
        "target_language":target.get("target_language") if target else None,
        "required_device_backends":list(target.get("required_device_backends",())) if target else [],
        "alternative_target_backends":list(target.get("alternative_target_backends",())) if target else [],
        "detected_features":list(ir.detected_features),"runtime_calls":list(ir.runtime_calls),"driver_calls":list(ir.driver_calls),"math_calls":list(ir.math_calls),
        "kernel_count":len(ir.kernels),"ir":ir.as_dict(),"unsupported_features":findings_list,"known_limitations":sorted(limitations),
        "result":compatibility,"compatibility_result":compatibility,"supported":supported,
        "full_cuda_parity_claimed":False,"closed_binary_compatibility_claimed":False,
    }


def translate_cuda_kernel_source(source: str, *, target_vendor: str, source_kind: str = SOURCE_KIND, target_backend: str | None = None) -> dict[str, Any]:
    analysis=analyze_cuda_source(source,target_vendor=target_vendor,source_kind=source_kind,target_backend=target_backend)
    if not analysis["supported"]:
        return {"schema":"fa3.cuda-compat-translation.v2","result":"DENY","compatibility_result":"UNAVAILABLE","analysis":analysis,"artifact":None,"execution_authorized":False}
    ir=parse_cuda_translation_unit(source,source_kind=source_kind)
    vendor,backend=analysis["target_vendor"],analysis["target_backend"]
    if vendor=="AMD" and backend=="hip": lowered=lower_amd_hip(source,ir)
    elif vendor=="INTEL" and backend=="sycl": lowered=lower_intel_sycl(source,ir)
    elif vendor=="INTEL" and backend=="opencl": lowered=lower_intel_opencl(source,ir)
    else: lowered={"result":"DENY","classification":"UNAVAILABLE","limitations":["NO_LOWERER_FOR_TARGET"],"source":None,"target_backend":backend,"target_language":analysis["target_language"]}
    if lowered["result"]!="PASS" or lowered.get("source") is None:
        denied=dict(analysis); denied["supported"]=False; denied["result"]="UNAVAILABLE"; denied["compatibility_result"]="UNAVAILABLE"
        denied["unsupported_features"]=sorted(set(denied["unsupported_features"])|set(lowered.get("limitations",())))
        return {"schema":"fa3.cuda-compat-translation.v2","result":"DENY","compatibility_result":"UNAVAILABLE","analysis":denied,"artifact":None,"execution_authorized":False}
    artifact=TranslationArtifact(target_vendor=vendor,target_backend=lowered["target_backend"],target_language=lowered["target_language"],source=lowered["source"],source_sha256=analysis["source_sha256"],translated_sha256=lowered["translated_sha256"],compatibility_result=lowered["classification"],detected_features=tuple(analysis["detected_features"]),limitations=tuple(lowered.get("limitations",())))
    return {
        "schema":"fa3.cuda-compat-translation.v2","result":"PASS","compatibility_result":artifact.compatibility_result,"analysis":analysis,
        "artifact":{"target_vendor":artifact.target_vendor,"target_backend":artifact.target_backend,"target_language":artifact.target_language,"source":artifact.source,"source_sha256":artifact.source_sha256,"translated_sha256":artifact.translated_sha256,"compatibility_result":artifact.compatibility_result,"detected_features":list(artifact.detected_features),"limitations":list(artifact.limitations)},
        "execution_authorized":False,
    }
