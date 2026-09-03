#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable

@dataclass(frozen=True)
class KernelRequest:
    request_id: str
    hrb_lease_id: str
    device_uuid: str
    pci_bdf: str
    gpu_arch: str
    operation: str
    m: int
    n: int
    k: int
    batch: int
    dtype: str
    layout: str
    requested_provider: str | None = None

@dataclass(frozen=True)
class KernelCandidate:
    provider_id: str
    supported_arches: tuple[str, ...]
    supported_dtypes: tuple[str, ...]
    supported_ops: tuple[str, ...]
    custom_kernel: bool
    correctness_pass: bool
    benchmark_ms: float | None
    workspace_bytes: int = 0
    available_vram_bytes: int | None = None
    compatibility_pass: bool = True
    compatibility_pass: bool = True

def _norm_arch(value: str) -> str:
    return str(value or "").strip().lower()

def request_valid(req: KernelRequest) -> bool:
    return bool(
        req.request_id and req.hrb_lease_id and req.device_uuid and req.pci_bdf
        and req.gpu_arch and req.operation and req.dtype and req.layout
        and req.m > 0 and req.n > 0 and req.k > 0 and req.batch > 0
    )

def provider_arch_eligible(gpu_arch: str, supported_arches: Iterable[str]) -> bool:
    arch=_norm_arch(gpu_arch)
    return bool(arch) and arch in {_norm_arch(x) for x in supported_arches}

def candidate_eligible(req: KernelRequest, c: KernelCandidate) -> bool:
    if not request_valid(req) or not c.compatibility_pass:
        return False
    if not provider_arch_eligible(req.gpu_arch, c.supported_arches):
        return False
    if req.dtype not in c.supported_dtypes or req.operation not in c.supported_ops:
        return False
    if not c.correctness_pass or c.benchmark_ms is None or c.benchmark_ms <= 0:
        return False
    if c.available_vram_bytes is not None and c.workspace_bytes > c.available_vram_bytes:
        return False
    return True

def choose_candidate(req: KernelRequest, candidates: Iterable[KernelCandidate]) -> KernelCandidate:
    eligible = [c for c in candidates if candidate_eligible(req, c)]
    if req.requested_provider:
        exact = [c for c in eligible if c.provider_id == req.requested_provider]
        if not exact:
            raise ValueError("requested provider is ineligible; silent fallback is forbidden")
        return min(exact, key=lambda c: c.benchmark_ms)
    if not eligible:
        raise ValueError("no eligible kernel candidate")
    return min(eligible, key=lambda c: c.benchmark_ms)

def autotune_key(req: KernelRequest, versions: dict[str, str]) -> dict:
    return {
        "operation": req.operation, "m": req.m, "n": req.n, "k": req.k, "batch": req.batch,
        "dtype": req.dtype, "layout": req.layout, "device_uuid": req.device_uuid, "gpu_arch": req.gpu_arch,
        **{k: versions[k] for k in sorted(versions)},
    }

def cache_fingerprint(key: dict) -> str:
    return sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def deepgemm_arch_eligible(gpu_arch: str, supported_arches: Iterable[str] = ("sm90", "sm100")) -> bool:
    # Default values mirror the immutable fw-ai/DeepGEMM snapshot pinned by FA3.
    # Callers admitting a different immutable provider revision must pass that
    # revision's declared architecture set instead of treating these as a global rule.
    return provider_arch_eligible(gpu_arch, supported_arches)
