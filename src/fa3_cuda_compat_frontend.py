#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re

from fa3_cuda_compat_ir import CudaKernelIR, CudaParameterIR, CudaTranslationUnitIR

SOURCE_KIND = "CUDA_KERNEL_SOURCE"

_FEATURE_PATTERNS = {
    "KERNEL_ENTRY": re.compile(r"\b__global__\s+(?:__launch_bounds__\s*\([^)]*\)\s*)?void\s+[A-Za-z_]\w*\s*\("),
    "DEVICE_FUNCTION": re.compile(r"\b__device__\b"),
    "SHARED_MEMORY": re.compile(r"\b__shared__\b"),
    "BLOCK_BARRIER": re.compile(r"\b__syncthreads\s*\(\s*\)"),
    "THREAD_INDEX": re.compile(r"\bthreadIdx\.[xyz]\b"),
    "BLOCK_INDEX": re.compile(r"\bblockIdx\.[xyz]\b"),
    "BLOCK_DIMENSION": re.compile(r"\bblockDim\.[xyz]\b"),
    "GRID_DIMENSION": re.compile(r"\bgridDim\.[xyz]\b"),
    "CUDA_ATOMICS": re.compile(r"\batomic(?:Add|Sub|Exch|Min|Max|Inc|Dec|CAS|And|Or|Xor)\s*\("),
    "CUDA_HALF_TYPES": re.compile(r"\b(?:__half|half2|__nv_bfloat16)\b"),
    "CUDA_CONSTANT_MEMORY": re.compile(r"\b__constant__\b"),
    "WARP_INTRINSICS": re.compile(r"\b__(?:shfl|ballot|activemask|syncwarp|match|reduce)_\w+\b"),
}
_KERNEL_PREFIX = re.compile(r"\b__global__\s+(?:__launch_bounds__\s*\([^)]*\)\s*)?void\s+([A-Za-z_]\w*)\s*\(")
_RUNTIME_CALL = re.compile(r"\b(cuda[A-Z][A-Za-z0-9_]*)\s*\(")
_DRIVER_CALL = re.compile(r"\b(cu[A-Z][A-Za-z0-9_]*)\s*\(")
_MATH_CALL = re.compile(r"\b(sinf|cosf|tanf|expf|logf|sqrtf|rsqrtf|fabsf|fmaf|sin|cos|tan|exp|log|sqrt|fabs|fma)\s*\(")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mask_comments_and_strings(text: str) -> str:
    out = list(text)
    i = 0
    n = len(text)
    state = "code"
    quote = ""
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                out[i] = out[i + 1] = " "; i += 2; state = "line"; continue
            if ch == "/" and nxt == "*":
                out[i] = out[i + 1] = " "; i += 2; state = "block"; continue
            if ch in ('"', "'"):
                quote = ch; out[i] = " "; i += 1; state = "string"; continue
            i += 1; continue
        if state == "line":
            if ch == "\n": state = "code"
            else: out[i] = " "
            i += 1; continue
        if state == "block":
            if ch == "*" and nxt == "/":
                out[i] = out[i + 1] = " "; i += 2; state = "code"
            else:
                if ch != "\n": out[i] = " "
                i += 1
            continue
        if state == "string":
            if ch == "\\" and i + 1 < n:
                out[i] = " "
                if text[i + 1] != "\n": out[i + 1] = " "
                i += 2; continue
            if ch == quote:
                out[i] = " "; i += 1; state = "code"
            else:
                if ch != "\n": out[i] = " "
                i += 1
    return "".join(out)


def _matching(masked: str, start: int, open_char: str, close_char: str) -> int | None:
    if start < 0 or start >= len(masked) or masked[start] != open_char:
        return None
    depth = 0
    for i in range(start, len(masked)):
        ch = masked[i]
        if ch == open_char: depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0: return i
    return None


def _split_parameters(text: str) -> list[str]:
    if not text.strip() or text.strip() == "void": return []
    out, start = [], 0
    depths = {"(": 0, "[": 0, "<": 0}
    pairs = {")": "(", "]": "[", ">": "<"}
    for i, ch in enumerate(text):
        if ch in depths: depths[ch] += 1
        elif ch in pairs and depths[pairs[ch]] > 0: depths[pairs[ch]] -= 1
        elif ch == "," and not any(depths.values()):
            out.append(text[start:i].strip()); start = i + 1
    out.append(text[start:].strip())
    return [x for x in out if x]


def _parameter_ir(declaration: str) -> CudaParameterIR:
    decl = declaration.strip()
    cleaned = re.sub(r"\b(?:__restrict__|restrict|const|volatile)\b", " ", decl)
    cleaned = re.sub(r"\[[^\]]*\]\s*$", "", cleaned).strip()
    names = re.findall(r"[A-Za-z_]\w*", cleaned)
    return CudaParameterIR(declaration=decl,name=names[-1] if names else "",pointer="*" in decl or "[" in decl,const=bool(re.search(r"\bconst\b", decl)))


def _features(text: str) -> tuple[str, ...]:
    return tuple(sorted(name for name, pattern in _FEATURE_PATTERNS.items() if pattern.search(text)))


def _extract_kernels(source: str, masked: str) -> tuple[CudaKernelIR, ...]:
    kernels, pos = [], 0
    while True:
        m = _KERNEL_PREFIX.search(masked, pos)
        if not m: break
        open_paren = masked.find("(", m.start())
        close_paren = _matching(masked, open_paren, "(", ")")
        if close_paren is None: break
        open_brace = masked.find("{", close_paren + 1)
        if open_brace < 0:
            pos = close_paren + 1; continue
        if ";" in masked[close_paren + 1:open_brace]:
            pos = close_paren + 1; continue
        close_brace = _matching(masked, open_brace, "{", "}")
        if close_brace is None: break
        params_text = source[open_paren + 1:close_paren]
        body = source[open_brace + 1:close_brace]
        kernels.append(CudaKernelIR(name=m.group(1),parameters=tuple(_parameter_ir(p) for p in _split_parameters(params_text)),body=body,detected_features=_features(source[m.start():close_brace + 1])))
        pos = close_brace + 1
    return tuple(kernels)


def parse_cuda_translation_unit(source: str, *, source_kind: str = SOURCE_KIND) -> CudaTranslationUnitIR:
    text = str(source or "")
    masked = _mask_comments_and_strings(text)
    kernels = _extract_kernels(text, masked)
    detected = set(_features(masked))
    runtime_calls = tuple(sorted(set(_RUNTIME_CALL.findall(masked))))
    driver_calls = tuple(sorted(set(_DRIVER_CALL.findall(masked))))
    math_calls = tuple(sorted(set(_MATH_CALL.findall(masked))))
    if runtime_calls: detected.add("CUDA_RUNTIME_CALLS")
    if driver_calls: detected.add("CUDA_DRIVER_CALLS")
    if math_calls: detected.add("CUDA_MATH_CALLS")
    unsupported = set()
    if source_kind != SOURCE_KIND: unsupported.add("SOURCE_KIND_UNSUPPORTED")
    if not text.strip(): unsupported.add("SOURCE_EMPTY")
    if text.strip() and not kernels: unsupported.add("CUDA_KERNEL_ENTRY_NOT_FOUND")
    if re.search(r"<<<|>>>", masked): unsupported.add("CUDA_HOST_LAUNCH_SYNTAX")
    if driver_calls: unsupported.add("CUDA_DRIVER_API")
    if any("<<<" in _mask_comments_and_strings(k.body) for k in kernels): unsupported.add("DYNAMIC_PARALLELISM")
    if re.search(r"\b(?:texture|surface|tex[123]D|surf[123]D)\b", masked): unsupported.add("TEXTURE_SURFACE_API")
    if re.search(r"\bcooperative_groups\b|\bcg::", masked): unsupported.add("COOPERATIVE_GROUPS")
    if re.search(r'\basm\s*(?:volatile\s*)?\(\s*"', text): unsupported.add("INLINE_PTX")
    return CudaTranslationUnitIR(source_kind=source_kind,source_sha256=sha256_text(text),kernels=kernels,runtime_calls=runtime_calls,driver_calls=driver_calls,math_calls=math_calls,detected_features=tuple(sorted(detected)),unsupported_features=tuple(sorted(unsupported)))
