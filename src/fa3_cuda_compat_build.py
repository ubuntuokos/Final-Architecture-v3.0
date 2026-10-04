#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Iterable

_VALUE_FLAGS = {"-I", "-D", "-U", "-include", "-isystem", "-o", "-x", "--std", "-std", "-arch", "--gpu-architecture", "-gencode", "--generate-code"}
_PREFIX_FLAGS = ("-I", "-D", "-U", "-std=", "--std=", "-O")
_EXACT_FLAGS = {
    "-g", "-G", "-lineinfo", "--use_fast_math",
    "--relocatable-device-code=true", "--relocatable-device-code=false",
    "-rdc=true", "-rdc=false", "-c",
}


def normalize_nvcc_options(args: Iterable[str]) -> dict[str, Any]:
    tokens = [str(x) for x in args]
    normalized: list[str] = []
    unsupported: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _VALUE_FLAGS:
            if i + 1 >= len(tokens):
                unsupported.append(f"MISSING_VALUE:{token}")
                i += 1
                continue
            normalized.extend([token, tokens[i + 1]])
            i += 2
            continue
        if token in _EXACT_FLAGS or any(token.startswith(prefix) for prefix in _PREFIX_FLAGS):
            normalized.append(token)
            i += 1
            continue
        if token.endswith((".cu", ".cuh", ".cpp", ".cc", ".cxx", ".o", ".a")):
            normalized.append(token)
            i += 1
            continue
        if token.startswith(("-gencode", "--generate-code", "-arch=", "--gpu-architecture=")):
            normalized.append(token)
            i += 1
            continue
        unsupported.append(token)
        i += 1
    return {
        "schema": "fa3.cuda-compat-nvcc-options.v1",
        "normalized": normalized,
        "unsupported": unsupported,
        "result": "PASS" if not unsupported else "DENY",
        "unknown_option_policy": "FAIL_CLOSED",
        "execution_authorized": False,
    }


def make_build_plan(
    *,
    sources: Iterable[str],
    nvcc_args: Iterable[str],
    target_vendor: str,
    target_backend: str | None = None,
) -> dict[str, Any]:
    source_list = [str(x) for x in sources]
    options = normalize_nvcc_options(nvcc_args)
    findings: list[str] = []
    if not source_list:
        findings.append("NO_SOURCE_FILES")
    bad_ext = [x for x in source_list if not x.endswith((".cu", ".cuh", ".cpp", ".cc", ".cxx"))]
    if bad_ext:
        findings.extend(f"UNSUPPORTED_SOURCE_EXTENSION:{x}" for x in bad_ext)
    findings.extend(f"UNSUPPORTED_NVCC_OPTION:{x}" for x in options["unsupported"])
    return {
        "schema": "fa3.cuda-compat-build-plan.v1",
        "result": "PASS" if not findings else "DENY",
        "target_vendor": str(target_vendor or "").strip().upper(),
        "target_backend": str(target_backend or "").strip().lower() or None,
        "sources": source_list,
        "normalized_nvcc_options": options["normalized"],
        "findings": findings,
        "compiler_execution_authorized": False,
        "artifact_execution_authorized": False,
        "hrb_lease_required_before_accelerator_execution": True,
        "silent_option_drop": False,
        "silent_backend_fallback": False,
    }
