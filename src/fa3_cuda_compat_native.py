#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any

NATIVE_BACKEND_NAME = "cfa3-cuda-compat"
EXTERNAL_SCALE_RUNTIME_DEPENDENCY = False
SOURCE_KIND = "CUDA_KERNEL_SOURCE"

_TARGETS = {
    "AMD": {
        "target_backend": "hip",
        "target_language": "HIP_CPP",
        "required_device_backends": ("rocm",),
    },
    "INTEL": {
        "target_backend": "opencl",
        "target_language": "OPENCL_C",
        "required_device_backends": ("level-zero", "opencl"),
    },
}

_COMMON_UNSUPPORTED = {
    "CUDA_HOST_LAUNCH_SYNTAX": re.compile(r"<<<|>>>"),
    "CUDA_RUNTIME_API": re.compile(r"\bcuda(?:Malloc|Free|Memcpy|Memset|Stream|Event|Graph|Launch|Device|GetDevice|SetDevice)\w*\b"),
    "CUDA_DRIVER_API": re.compile(r"\bcu(?:Init|Ctx|Mem|Module|Launch|Device|Stream|Event|Graph)\w*\b"),
    "DYNAMIC_PARALLELISM": re.compile(r"\b__global__\b[\s\S]*<<<"),
    "TEXTURE_SURFACE_API": re.compile(r"\b(?:texture|surface|tex[123]D|surf[123]D)\b"),
    "COOPERATIVE_GROUPS": re.compile(r"\bcooperative_groups\b|\bcg::"),
    "INLINE_PTX": re.compile(r"\basm\s*\(\s*\""),
}

_INTEL_UNSUPPORTED = {
    "WARP_INTRINSICS": re.compile(r"\b__(?:shfl|ballot|activemask|syncwarp|match|reduce)_\w+\b"),
    "CUDA_ATOMICS": re.compile(r"\batomic(?:Add|Sub|Exch|Min|Max|Inc|Dec|CAS|And|Or|Xor)\s*\("),
    "CUDA_HALF_TYPES": re.compile(r"\b(?:__half|half2|__nv_bfloat16)\b"),
    "CUDA_CONSTANT_MEMORY": re.compile(r"\b__constant__\b"),
}

_FEATURE_PATTERNS = {
    "KERNEL_ENTRY": re.compile(r"\b__global__\s+void\s+[A-Za-z_]\w*\s*\("),
    "DEVICE_FUNCTION": re.compile(r"\b__device__\b"),
    "SHARED_MEMORY": re.compile(r"\b__shared__\b"),
    "BLOCK_BARRIER": re.compile(r"\b__syncthreads\s*\(\s*\)"),
    "THREAD_INDEX": re.compile(r"\bthreadIdx\.[xyz]\b"),
    "BLOCK_INDEX": re.compile(r"\bblockIdx\.[xyz]\b"),
    "BLOCK_DIMENSION": re.compile(r"\bblockDim\.[xyz]\b"),
    "GRID_DIMENSION": re.compile(r"\bgridDim\.[xyz]\b"),
}


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


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vendor(value: str) -> str:
    return str(value or "").strip().upper()


def target_descriptor(target_vendor: str) -> dict[str, Any] | None:
    row = _TARGETS.get(_vendor(target_vendor))
    return dict(row) if row else None


def analyze_cuda_source(
    source: str,
    *,
    target_vendor: str,
    source_kind: str = SOURCE_KIND,
) -> dict[str, Any]:
    vendor = _vendor(target_vendor)
    target = _TARGETS.get(vendor)
    findings: list[str] = []
    if source_kind != SOURCE_KIND:
        findings.append("SOURCE_KIND_UNSUPPORTED")
    if target is None:
        findings.append("TARGET_VENDOR_UNSUPPORTED")
    text = str(source or "")
    if not text.strip():
        findings.append("SOURCE_EMPTY")

    detected = sorted(
        name for name, pattern in _FEATURE_PATTERNS.items() if pattern.search(text)
    )
    if text.strip() and "KERNEL_ENTRY" not in detected:
        findings.append("CUDA_KERNEL_ENTRY_NOT_FOUND")
    for name, pattern in _COMMON_UNSUPPORTED.items():
        if pattern.search(text):
            findings.append(name)
    if vendor == "INTEL":
        for name, pattern in _INTEL_UNSUPPORTED.items():
            if pattern.search(text):
                findings.append(name)

    findings = sorted(set(findings))
    return {
        "schema": "fa3.cuda-compat-source-analysis.v1",
        "implementation": "CFA3_NATIVE",
        "external_scale_runtime_dependency": False,
        "source_kind": source_kind,
        "source_sha256": _sha256(text),
        "target_vendor": vendor,
        "target_backend": target.get("target_backend") if target else None,
        "target_language": target.get("target_language") if target else None,
        "required_device_backends": list(target.get("required_device_backends", ())) if target else [],
        "detected_features": detected,
        "unsupported_features": findings,
        "result": "SUPPORTED_SUBSET" if not findings else "UNAVAILABLE",
        "supported": not findings,
        "full_cuda_parity_claimed": False,
        "closed_binary_compatibility_claimed": False,
    }


def _opencl_pointer_parameter(param: str) -> str:
    value = param.strip()
    if "*" not in value:
        return value
    if re.search(r"\b__(?:global|local|constant|private)\b", value):
        return value
    return "__global " + value


def _rewrite_opencl_kernel_signatures(source: str) -> str:
    pattern = re.compile(
        r"\b__global__\s+void\s+([A-Za-z_]\w*)\s*\(([^(){}]*)\)"
    )
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        raw_params = match.group(2).strip()
        params = "" if not raw_params else ", ".join(
            _opencl_pointer_parameter(part) for part in raw_params.split(",")
        )
        return f"__kernel void {name}({params})"
    return pattern.sub(repl, source)


def translate_cuda_kernel_source(
    source: str,
    *,
    target_vendor: str,
    source_kind: str = SOURCE_KIND,
) -> dict[str, Any]:
    analysis = analyze_cuda_source(
        source,
        target_vendor=target_vendor,
        source_kind=source_kind,
    )
    if not analysis["supported"]:
        return {
            "schema": "fa3.cuda-compat-translation.v1",
            "result": "DENY",
            "analysis": analysis,
            "artifact": None,
            "execution_authorized": False,
        }

    vendor = analysis["target_vendor"]
    translated = str(source)
    if vendor == "AMD":
        translated = re.sub(
            r"^\s*#\s*include\s*[<\"]cuda_runtime\.h[>\"]\s*$",
            "#include <hip/hip_runtime.h>",
            translated,
            flags=re.MULTILINE,
        )
        if "hip/hip_runtime.h" not in translated:
            translated = "#include <hip/hip_runtime.h>\n" + translated
    elif vendor == "INTEL":
        translated = re.sub(
            r"^\s*#\s*include\s*[<\"]cuda_runtime\.h[>\"]\s*$",
            "",
            translated,
            flags=re.MULTILINE,
        )
        translated = _rewrite_opencl_kernel_signatures(translated)
        translated = re.sub(r"\b__device__\b", "", translated)
        translated = re.sub(r"\b__host__\b", "", translated)
        translated = re.sub(r"\b__forceinline__\b", "inline", translated)
        translated = re.sub(r"\b__shared__\b", "__local", translated)
        replacements = {
            "threadIdx.x": "get_local_id(0)",
            "threadIdx.y": "get_local_id(1)",
            "threadIdx.z": "get_local_id(2)",
            "blockIdx.x": "get_group_id(0)",
            "blockIdx.y": "get_group_id(1)",
            "blockIdx.z": "get_group_id(2)",
            "blockDim.x": "get_local_size(0)",
            "blockDim.y": "get_local_size(1)",
            "blockDim.z": "get_local_size(2)",
            "gridDim.x": "get_num_groups(0)",
            "gridDim.y": "get_num_groups(1)",
            "gridDim.z": "get_num_groups(2)",
        }
        for old, new in replacements.items():
            translated = translated.replace(old, new)
        translated = re.sub(
            r"\b__syncthreads\s*\(\s*\)",
            "barrier(CLK_LOCAL_MEM_FENCE)",
            translated,
        )

    artifact = TranslationArtifact(
        target_vendor=vendor,
        target_backend=analysis["target_backend"],
        target_language=analysis["target_language"],
        source=translated,
        source_sha256=analysis["source_sha256"],
        translated_sha256=_sha256(translated),
        compatibility_result=analysis["result"],
        detected_features=tuple(analysis["detected_features"]),
    )
    return {
        "schema": "fa3.cuda-compat-translation.v1",
        "result": "PASS",
        "analysis": analysis,
        "artifact": {
            "target_vendor": artifact.target_vendor,
            "target_backend": artifact.target_backend,
            "target_language": artifact.target_language,
            "source": artifact.source,
            "source_sha256": artifact.source_sha256,
            "translated_sha256": artifact.translated_sha256,
            "compatibility_result": artifact.compatibility_result,
            "detected_features": list(artifact.detected_features),
        },
        "execution_authorized": False,
    }
