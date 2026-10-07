#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Iterable, Mapping

from fa3_accelerator_backend_probe import enrich_accelerator_backends
from fa3_cuda_compat_build import make_build_plan
from fa3_cuda_compat_native import NATIVE_BACKEND_NAME, SOURCE_KIND, analyze_cuda_source, translate_cuda_kernel_source
from fa3_cuda_compat_runtime import runtime_api_support
from fa3_hardware_discovery import AcceleratorDeviceDescriptor

SHARED_APPLICATION_SCOPE = "ALL_CURRENT_AND_FUTURE_CFA3_APPLICATIONS"
CUDA_COMPAT_BACKENDS = frozenset({"cuda", NATIVE_BACKEND_NAME, "zluda"})


def _identity(value: str | None) -> str:
    return str(value or "").strip()


def resolve_cuda_compatibility(
    devices: Iterable[AcceleratorDeviceDescriptor],
    *,
    application_id: str,
    workload_id: str,
    requested_backend: str | None = None,
    requested_translation_target: str | None = None,
    allow_translation: bool = False,
    cuda_source: str | None = None,
    source_kind: str = SOURCE_KIND,
    include_framework_probes: bool = False,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    app=_identity(application_id); workload=_identity(workload_id)
    requested=_identity(requested_backend) or None
    translation_target=_identity(requested_translation_target).lower() or None
    base={"schema":"fa3.cuda-compat-shared-resolution.v3","implementation":"CFA3_NATIVE_SHARED","external_scale_runtime_dependency":False,"application_scope":SHARED_APPLICATION_SCOPE,"application_allowlist":False,"execution_authorized":False}
    if not app or not workload:
        return {**base,"result":"DENY","reason":"APPLICATION_AND_WORKLOAD_ID_REQUIRED","candidates":[],"blocked_candidates":[]}
    if requested is not None and requested not in CUDA_COMPAT_BACKENDS:
        return {**base,"result":"DENY","reason":"UNSUPPORTED_EXPLICIT_BACKEND","application_id":app,"workload_id":workload,"requested_backend":requested,"automatic_backend_selection":False,"candidates":[],"blocked_candidates":[]}
    enriched=enrich_accelerator_backends(devices,include_framework_probes=include_framework_probes,environ=environ)
    candidates=[]; blocked=[]
    for device in enriched:
        for backend in device.backends:
            if backend.name not in CUDA_COMPAT_BACKENDS: continue
            if requested is not None and backend.name!=requested: continue
            reasons=[]; source_analysis=None
            if not backend.detected: reasons.append("BACKEND_NOT_DETECTED")
            if not backend.available: reasons.append("BACKEND_NOT_AVAILABLE")
            if backend.binding_scope!="DEVICE": reasons.append("EXACT_DEVICE_BINDING_REQUIRED")
            if backend.backend_class=="translation" and not allow_translation: reasons.append("TRANSLATION_NOT_EXPLICITLY_ALLOWED")
            if backend.name==NATIVE_BACKEND_NAME and cuda_source is not None:
                source_analysis=analyze_cuda_source(cuda_source,target_vendor=device.vendor,source_kind=source_kind,target_backend=translation_target)
                if not source_analysis["supported"]: reasons.append("CUDA_SOURCE_SUBSET_UNSUPPORTED")
            row={"device_id":device.discovery_id,"stable_device_id":device.stable_device_id,"pci_bdf":device.pci_bdf,"vendor":device.vendor,"backend":backend.name,"backend_class":backend.backend_class,"runtime_version":backend.runtime_version,"experimental":backend.experimental,"framework_backends":list(backend.framework_backends),"evidence_sources":list(backend.evidence_sources),"requested_translation_target":translation_target}
            if source_analysis is not None:
                row["source_analysis"]=source_analysis; row["compatibility_result"]=source_analysis["compatibility_result"]; row["known_limitations"]=source_analysis["known_limitations"]
            if reasons:
                row["blocking_reasons"]=sorted(set(reasons)); blocked.append(row)
            else: candidates.append(row)
    return {**base,"result":"CANDIDATE_AVAILABLE" if candidates else "UNAVAILABLE","application_id":app,"workload_id":workload,"requested_backend":requested,"requested_translation_target":translation_target,"application_identity_is_provenance_only":True,"automatic_backend_selection":False,"application_provider_selection_authority":False,"translation_explicitly_allowed":bool(allow_translation),"execution_requires_authorized_hrb_lease":True,"silent_fallback":False,"candidates":candidates,"blocked_candidates":blocked}


def prepare_cuda_compat_translation(*,application_id:str,workload_id:str,cuda_source:str,target_vendor:str,target_backend:str|None=None,source_kind:str=SOURCE_KIND)->dict[str,Any]:
    app=_identity(application_id); workload=_identity(workload_id)
    if not app or not workload:
        return {"schema":"fa3.cuda-compat-shared-translation.v2","result":"DENY","reason":"APPLICATION_AND_WORKLOAD_ID_REQUIRED","application_scope":SHARED_APPLICATION_SCOPE,"application_allowlist":False,"external_scale_runtime_dependency":False,"execution_authorized":False}
    translated=translate_cuda_kernel_source(cuda_source,target_vendor=target_vendor,target_backend=target_backend,source_kind=source_kind)
    return {"schema":"fa3.cuda-compat-shared-translation.v2","result":translated["result"],"compatibility_result":translated.get("compatibility_result","UNAVAILABLE"),"application_scope":SHARED_APPLICATION_SCOPE,"application_allowlist":False,"application_id":app,"workload_id":workload,"implementation":"CFA3_NATIVE_SHARED","external_scale_runtime_dependency":False,"translation":translated,"execution_authorized":False,"execution_requires_authorized_hrb_lease":True,"silent_fallback":False}


def prepare_cuda_compat_build(*,application_id:str,workload_id:str,sources:Iterable[str],nvcc_args:Iterable[str],target_vendor:str,target_backend:str|None=None)->dict[str,Any]:
    app=_identity(application_id); workload=_identity(workload_id)
    if not app or not workload:
        return {"schema":"fa3.cuda-compat-shared-build.v1","result":"DENY","reason":"APPLICATION_AND_WORKLOAD_ID_REQUIRED","application_scope":SHARED_APPLICATION_SCOPE,"execution_authorized":False}
    plan=make_build_plan(sources=sources,nvcc_args=nvcc_args,target_vendor=target_vendor,target_backend=target_backend)
    return {"schema":"fa3.cuda-compat-shared-build.v1","result":plan["result"],"application_scope":SHARED_APPLICATION_SCOPE,"application_allowlist":False,"application_id":app,"workload_id":workload,"build_plan":plan,"compiler_execution_authorized":False,"artifact_execution_authorized":False,"silent_fallback":False}


def inspect_cuda_runtime_compatibility(*,application_id:str,workload_id:str,symbols:Iterable[str],target_vendor:str,target_backend:str|None=None)->dict[str,Any]:
    app=_identity(application_id); workload=_identity(workload_id)
    if not app or not workload:
        return {"schema":"fa3.cuda-compat-shared-runtime-map.v1","result":"DENY","reason":"APPLICATION_AND_WORKLOAD_ID_REQUIRED","application_scope":SHARED_APPLICATION_SCOPE,"execution_authorized":False}
    mapping=runtime_api_support(symbols,target_vendor=target_vendor,target_backend=target_backend)
    return {"schema":"fa3.cuda-compat-shared-runtime-map.v1","result":"PASS" if mapping["classification"]!="UNAVAILABLE" else "DENY","application_scope":SHARED_APPLICATION_SCOPE,"application_allowlist":False,"application_id":app,"workload_id":workload,"runtime_map":mapping,"execution_authorized":False,"silent_fallback":False}
