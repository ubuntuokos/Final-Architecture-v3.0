#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Iterable

AMD_RUNTIME_MAP = {
    "cudaGetDevice": "hipGetDevice",
    "cudaSetDevice": "hipSetDevice",
    "cudaGetDeviceCount": "hipGetDeviceCount",
    "cudaMalloc": "hipMalloc",
    "cudaFree": "hipFree",
    "cudaMemcpy": "hipMemcpy",
    "cudaMemcpyAsync": "hipMemcpyAsync",
    "cudaMemset": "hipMemset",
    "cudaMemsetAsync": "hipMemsetAsync",
    "cudaDeviceSynchronize": "hipDeviceSynchronize",
    "cudaStreamCreate": "hipStreamCreate",
    "cudaStreamDestroy": "hipStreamDestroy",
    "cudaStreamSynchronize": "hipStreamSynchronize",
    "cudaEventCreate": "hipEventCreate",
    "cudaEventDestroy": "hipEventDestroy",
    "cudaEventRecord": "hipEventRecord",
    "cudaEventSynchronize": "hipEventSynchronize",
    "cudaGetLastError": "hipGetLastError",
    "cudaPeekAtLastError": "hipPeekAtLastError",
}


AMD_RUNTIME_TYPE_CONSTANT_MAP = {
    "cudaError_t": "hipError_t",
    "cudaStream_t": "hipStream_t",
    "cudaEvent_t": "hipEvent_t",
    "cudaMemcpyKind": "hipMemcpyKind",
    "cudaDeviceProp": "hipDeviceProp_t",
    "cudaSuccess": "hipSuccess",
    "cudaMemcpyHostToHost": "hipMemcpyHostToHost",
    "cudaMemcpyHostToDevice": "hipMemcpyHostToDevice",
    "cudaMemcpyDeviceToHost": "hipMemcpyDeviceToHost",
    "cudaMemcpyDeviceToDevice": "hipMemcpyDeviceToDevice",
    "cudaMemcpyDefault": "hipMemcpyDefault",
}

AMD_RUNTIME_TOKEN_MAP = {**AMD_RUNTIME_MAP, **AMD_RUNTIME_TYPE_CONSTANT_MAP}

INTEL_SYCL_RUNTIME_MAP = {
    "cudaMalloc": "sycl::malloc_device",
    "cudaFree": "sycl::free",
    "cudaMemcpy": "sycl::queue::memcpy",
    "cudaMemcpyAsync": "sycl::queue::memcpy",
    "cudaMemset": "sycl::queue::memset",
    "cudaMemsetAsync": "sycl::queue::memset",
    "cudaDeviceSynchronize": "sycl::queue::wait",
}


def runtime_api_support(
    symbols: Iterable[str],
    *,
    target_vendor: str,
    target_backend: str | None = None,
) -> dict[str, Any]:
    vendor = str(target_vendor or "").strip().upper()
    backend = str(target_backend or "").strip().lower()
    requested = tuple(sorted(set(str(x) for x in symbols if str(x).strip())))
    mappings: dict[str, str] = {}
    unsupported: list[str] = []

    if vendor == "AMD":
        for symbol in requested:
            target = AMD_RUNTIME_MAP.get(symbol)
            if target:
                mappings[symbol] = target
            else:
                unsupported.append(symbol)
        classification = "FULL_EQUIVALENCE" if requested and not unsupported else (
            "UNAVAILABLE" if unsupported else "FULL_EQUIVALENCE"
        )
        semantics = "DIRECT_HIP_RUNTIME_MAPPING_WITH_SEPARATE_EXECUTION_ADMISSION"
    elif vendor == "INTEL" and backend in {"", "sycl"}:
        for symbol in requested:
            target = INTEL_SYCL_RUNTIME_MAP.get(symbol)
            if target:
                mappings[symbol] = target
            else:
                unsupported.append(symbol)
        classification = "FUNCTIONALLY_REDUCED" if requested and not unsupported else (
            "UNAVAILABLE" if unsupported else "FUNCTIONALLY_REDUCED"
        )
        semantics = "SYCL_HOST_ADAPTER_REQUIRED_QUEUE_AND_CONTEXT_SEMANTICS_NOT_IMPLICIT"
    else:
        unsupported.extend(requested)
        classification = "UNAVAILABLE" if requested else "FULL_EQUIVALENCE"
        semantics = "NO_RUNTIME_COMPATIBILITY_MAPPING"

    return {
        "schema": "fa3.cuda-compat-runtime-map.v1",
        "target_vendor": vendor,
        "target_backend": backend or None,
        "requested_symbols": list(requested),
        "mappings": mappings,
        "unsupported_symbols": unsupported,
        "classification": classification,
        "semantics": semantics,
        "runtime_execution_authorized": False,
        "hrb_lease_required_before_accelerator_execution": True,
        "silent_fallback": False,
    }
