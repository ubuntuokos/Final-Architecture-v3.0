#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from typing import Any

from fa3_cuda_compat_ir import CudaTranslationUnitIR
from fa3_cuda_compat_runtime import AMD_RUNTIME_TOKEN_MAP, runtime_api_support


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rewrite_runtime_calls(source: str, mapping: dict[str, str]) -> str:
    out = source
    for old, new in sorted(mapping.items(), key=lambda item: -len(item[0])):
        out = re.sub(rf"\b{re.escape(old)}\b", new, out)
    return out


def lower_amd_hip(source: str, ir: CudaTranslationUnitIR) -> dict[str, Any]:
    runtime = runtime_api_support(ir.runtime_calls, target_vendor="AMD", target_backend="hip")
    if runtime["unsupported_symbols"]:
        return {"result":"DENY","classification":"UNAVAILABLE","limitations":[f"UNSUPPORTED_RUNTIME_SYMBOL:{x}" for x in runtime["unsupported_symbols"]],"source":None,"target_backend":"hip","target_language":"HIP_CPP"}
    translated = re.sub(r'^\s*#\s*include\s*[<"]cuda_runtime\.h[>"]\s*$', "#include <hip/hip_runtime.h>", source, flags=re.MULTILINE)
    if "hip/hip_runtime.h" not in translated: translated = "#include <hip/hip_runtime.h>\n" + translated
    translated = _rewrite_runtime_calls(translated, AMD_RUNTIME_TOKEN_MAP)
    return {"result":"PASS","classification":"FULL_EQUIVALENCE","limitations":[],"source":translated,"target_backend":"hip","target_language":"HIP_CPP","runtime_map":runtime,"translated_sha256":_sha256(translated)}


def _opencl_pointer_parameter(param: str) -> str:
    value = param.strip()
    if "*" not in value or re.search(r"\b__(?:global|local|constant|private)\b", value): return value
    return "__global " + value


def _rewrite_opencl_kernel_signatures(source: str) -> str:
    pattern = re.compile(r"\b__global__\s+void\s+([A-Za-z_]\w*)\s*\(([^(){}]*)\)")
    def repl(match: re.Match[str]) -> str:
        raw = match.group(2).strip()
        params = "" if not raw else ", ".join(_opencl_pointer_parameter(part) for part in raw.split(","))
        return f"__kernel void {match.group(1)}({params})"
    return pattern.sub(repl, source)


def lower_intel_opencl(source: str, ir: CudaTranslationUnitIR) -> dict[str, Any]:
    if ir.runtime_calls:
        return {"result":"DENY","classification":"UNAVAILABLE","limitations":["CUDA_RUNTIME_API_REQUIRES_HOST_ADAPTER"],"source":None,"target_backend":"opencl","target_language":"OPENCL_C"}
    translated = re.sub(r'^\s*#\s*include\s*[<"]cuda_runtime\.h[>"]\s*$', "", source, flags=re.MULTILINE)
    translated = _rewrite_opencl_kernel_signatures(translated)
    translated = re.sub(r"\b__device__\b", "", translated)
    translated = re.sub(r"\b__host__\b", "", translated)
    translated = re.sub(r"\b__forceinline__\b", "inline", translated)
    translated = re.sub(r"\b__shared__\b", "__local", translated)
    replacements={"threadIdx.x":"get_local_id(0)","threadIdx.y":"get_local_id(1)","threadIdx.z":"get_local_id(2)","blockIdx.x":"get_group_id(0)","blockIdx.y":"get_group_id(1)","blockIdx.z":"get_group_id(2)","blockDim.x":"get_local_size(0)","blockDim.y":"get_local_size(1)","blockDim.z":"get_local_size(2)","gridDim.x":"get_num_groups(0)","gridDim.y":"get_num_groups(1)","gridDim.z":"get_num_groups(2)"}
    for old,new in replacements.items(): translated=translated.replace(old,new)
    translated=re.sub(r"\b__syncthreads\s*\(\s*\)","barrier(CLK_LOCAL_MEM_FENCE)",translated)
    return {"result":"PASS","classification":"FUNCTIONALLY_REDUCED","limitations":["HOST_LAUNCH_ADAPTER_REQUIRED","CUDA_RUNTIME_API_NOT_EMITTED"],"source":translated,"target_backend":"opencl","target_language":"OPENCL_C","translated_sha256":_sha256(translated)}


def _rewrite_sycl_kernel_signatures(source: str) -> str:
    pattern=re.compile(r"\b__global__\s+void\s+([A-Za-z_]\w*)\s*\(([^(){}]*)\)")
    def repl(m: re.Match[str]) -> str:
        raw=m.group(2).strip(); params="sycl::nd_item<3> item" if not raw else f"{raw}, sycl::nd_item<3> item"
        return f"inline void {m.group(1)}({params})"
    return pattern.sub(repl,source)


def lower_intel_sycl(source: str, ir: CudaTranslationUnitIR) -> dict[str, Any]:
    runtime=runtime_api_support(ir.runtime_calls,target_vendor="INTEL",target_backend="sycl")
    if ir.runtime_calls:
        return {"result":"DENY","classification":"UNAVAILABLE","limitations":["CUDA_RUNTIME_API_REQUIRES_HOST_ADAPTER"],"source":None,"target_backend":"sycl","target_language":"SYCL_CPP","runtime_map":runtime}
    translated=re.sub(r'^\s*#\s*include\s*[<"]cuda_runtime\.h[>"]\s*$',"",source,flags=re.MULTILINE)
    if "#include <sycl/sycl.hpp>" not in translated: translated="#include <sycl/sycl.hpp>\n"+translated
    translated=_rewrite_sycl_kernel_signatures(translated)
    translated=re.sub(r"\b__device__\b","inline",translated)
    translated=re.sub(r"\b__host__\b","",translated)
    translated=re.sub(r"\b__forceinline__\b","inline",translated)
    replacements={"threadIdx.x":"item.get_local_id(2)","threadIdx.y":"item.get_local_id(1)","threadIdx.z":"item.get_local_id(0)","blockIdx.x":"item.get_group(2)","blockIdx.y":"item.get_group(1)","blockIdx.z":"item.get_group(0)","blockDim.x":"item.get_local_range(2)","blockDim.y":"item.get_local_range(1)","blockDim.z":"item.get_local_range(0)","gridDim.x":"item.get_group_range(2)","gridDim.y":"item.get_group_range(1)","gridDim.z":"item.get_group_range(0)"}
    for old,new in replacements.items(): translated=translated.replace(old,new)
    translated=re.sub(r"\b__syncthreads\s*\(\s*\)","item.barrier(sycl::access::fence_space::local_space)",translated)
    return {"result":"PASS","classification":"FUNCTIONALLY_REDUCED","limitations":["SYCL_HOST_QUEUE_LAUNCH_WRAPPER_REQUIRED","CUDA_STREAM_EVENT_SEMANTICS_REQUIRE_EXPLICIT_HOST_ADAPTER"],"source":translated,"target_backend":"sycl","target_language":"SYCL_CPP","runtime_map":runtime,"translated_sha256":_sha256(translated)}
