#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable


BACKEND_CLASSES = {"native", "portable", "translation"}


@dataclass(frozen=True)
class KernelRequest:
    request_id: str
    hrb_lease_id: str
    accelerator_id: str
    topology_binding: str
    accelerator_arch: str
    compute_backend: str
    backend_class: str
    framework_backend: str
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
    supported_backends: tuple[str, ...]
    supported_backend_classes: tuple[str, ...]
    supported_arches: tuple[str, ...]
    supported_dtypes: tuple[str, ...]
    supported_ops: tuple[str, ...]
    custom_kernel: bool
    correctness_pass: bool
    benchmark_ms: float | None
    workspace_bytes: int = 0
    available_accelerator_memory_bytes: int | None = None
    compatibility_pass: bool = True
    supported_framework_backends: tuple[str, ...] = ()


def _norm(value: str) -> str:
    return str(value or "").strip().lower()


def request_valid(req: KernelRequest) -> bool:
    return bool(
        req.request_id
        and req.hrb_lease_id
        and req.accelerator_id
        and req.topology_binding
        and req.accelerator_arch
        and req.compute_backend
        and _norm(req.backend_class) in BACKEND_CLASSES
        and req.framework_backend
        and req.operation
        and req.dtype
        and req.layout
        and req.m > 0
        and req.n > 0
        and req.k > 0
        and req.batch > 0
    )


def provider_arch_eligible(accelerator_arch: str, supported_arches: Iterable[str]) -> bool:
    arch = _norm(accelerator_arch)
    return bool(arch) and arch in {_norm(x) for x in supported_arches}


def provider_backend_eligible(req: KernelRequest, candidate: KernelCandidate) -> bool:
    backend = _norm(req.compute_backend)
    backend_class = _norm(req.backend_class)
    if backend not in {_norm(x) for x in candidate.supported_backends}:
        return False
    if backend_class not in {_norm(x) for x in candidate.supported_backend_classes}:
        return False
    if backend_class == "translation":
        return False
    if candidate.supported_framework_backends:
        if _norm(req.framework_backend) not in {_norm(x) for x in candidate.supported_framework_backends}:
            return False
    return True


def candidate_eligible(req: KernelRequest, candidate: KernelCandidate) -> bool:
    if not request_valid(req) or not candidate.compatibility_pass:
        return False
    if not provider_backend_eligible(req, candidate):
        return False
    if not provider_arch_eligible(req.accelerator_arch, candidate.supported_arches):
        return False
    if req.dtype not in candidate.supported_dtypes or req.operation not in candidate.supported_ops:
        return False
    if not candidate.correctness_pass or candidate.benchmark_ms is None or candidate.benchmark_ms <= 0:
        return False
    if (
        candidate.available_accelerator_memory_bytes is not None
        and candidate.workspace_bytes > candidate.available_accelerator_memory_bytes
    ):
        return False
    return True


def choose_candidate(req: KernelRequest, candidates: Iterable[KernelCandidate]) -> KernelCandidate:
    eligible = [candidate for candidate in candidates if candidate_eligible(req, candidate)]
    if req.requested_provider:
        exact = [candidate for candidate in eligible if candidate.provider_id == req.requested_provider]
        if not exact:
            raise ValueError("requested provider is ineligible; silent fallback is forbidden")
        return min(exact, key=lambda candidate: candidate.benchmark_ms)
    if not eligible:
        raise ValueError("no eligible kernel candidate")
    return min(eligible, key=lambda candidate: candidate.benchmark_ms)


def autotune_key(req: KernelRequest, versions: dict[str, str]) -> dict:
    return {
        "operation": req.operation,
        "m": req.m,
        "n": req.n,
        "k": req.k,
        "batch": req.batch,
        "dtype": req.dtype,
        "layout": req.layout,
        "accelerator_id": req.accelerator_id,
        "accelerator_arch": req.accelerator_arch,
        "compute_backend": req.compute_backend,
        "backend_class": req.backend_class,
        "framework_backend": req.framework_backend,
        **{key: versions[key] for key in sorted(versions)},
    }


def cache_fingerprint(key: dict) -> str:
    return sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def deepgemm_arch_eligible(accelerator_arch: str, supported_arches: Iterable[str] = ("sm90", "sm100")) -> bool:
    # Provider-scoped default from the immutable DeepGEMM snapshot; never a global FA3 rule.
    return provider_arch_eligible(accelerator_arch, supported_arches)
