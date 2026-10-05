#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from fa3_release_baseline import module_active_capability_count

CAPABILITY_COUNT = module_active_capability_count(__file__)
SHARED_APPLICATION_SCOPE = "ALL_CAPABILITY_COMPATIBLE_CFA3_APPLICATIONS"
TRACE_MODES = frozenset({"RAY_TRACING", "PATH_TRACING"})
HARDWARE_POLICIES = frozenset({"REQUIRED", "PREFERRED", "DISABLED"})
COMPATIBILITY_CLASSES = frozenset({"NATIVE", "PORTABLE", "SOFTWARE_CPU", "FUNCTIONALLY_REDUCED", "UNAVAILABLE"})


@dataclass(frozen=True)
class RayTracingBackendDescriptor:
    backend_id: str
    vendor: str
    api: str
    available: bool
    device_bound: bool
    supported_modes: tuple[str, ...]
    hardware_traversal: bool
    compatibility_class: str
    provider_admitted: bool
    runtime_admitted: bool
    cpu_software: bool = False
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.backend_id.strip() or not self.vendor.strip() or not self.api.strip():
            raise ValueError("backend_id, vendor and api are required")
        if self.compatibility_class not in COMPATIBILITY_CLASSES:
            raise ValueError("unsupported compatibility_class")
        unknown = set(self.supported_modes) - TRACE_MODES
        if unknown:
            raise ValueError(f"unsupported trace modes: {sorted(unknown)}")
        if self.cpu_software and self.vendor != "CPU":
            raise ValueError("cpu_software descriptor must use vendor CPU")
        if self.cpu_software and self.hardware_traversal:
            raise ValueError("CPU software path cannot claim hardware traversal")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def cpu_software_reference_descriptor(
    *,
    backend_id: str = "cfa3-cpu-software-ray-reference",
    provider_admitted: bool = False,
    runtime_admitted: bool = False,
) -> RayTracingBackendDescriptor:
    return RayTracingBackendDescriptor(
        backend_id=backend_id,
        vendor="CPU",
        api="CFA3_SOFTWARE_REFERENCE",
        available=True,
        device_bound=True,
        supported_modes=("RAY_TRACING", "PATH_TRACING"),
        hardware_traversal=False,
        compatibility_class="SOFTWARE_CPU",
        provider_admitted=provider_admitted,
        runtime_admitted=runtime_admitted,
        cpu_software=True,
        evidence=("canonical-cpu-software-path:declared",),
    )


def resolve_ray_path_tracing(
    backends: Iterable[RayTracingBackendDescriptor],
    *,
    application_id: str,
    workload_id: str,
    trace_mode: str,
    hardware_traversal: str = "PREFERRED",
    requested_backend_id: str | None = None,
    neural_denoise: bool = False,
) -> dict[str, Any]:
    app = str(application_id or "").strip()
    workload = str(workload_id or "").strip()
    mode = str(trace_mode or "").strip().upper()
    hw = str(hardware_traversal or "").strip().upper()
    requested = str(requested_backend_id or "").strip() or None
    base = {
        "schema": "fa3.ray-path-tracing-resolution.v1",
        "fabric_id": "FA3-SHARED-RAY-PATH-TRACING-001",
        "capability_count": CAPABILITY_COUNT,
        "application_scope": SHARED_APPLICATION_SCOPE,
        "execution_authorized": False,
        "automatic_backend_selection": False,
        "silent_fallback": False,
        "hrb_lease_required_before_execution": True,
        "engine_selection_required_before_execution": True,
        "model_router_required_for_neural_denoise": bool(neural_denoise),
        "cpu_software_path_required": True,
    }
    if not app or not workload:
        return {**base, "result": "DENY", "reason": "APPLICATION_AND_WORKLOAD_ID_REQUIRED", "candidates": [], "blocked_candidates": []}
    if mode not in TRACE_MODES:
        return {**base, "result": "DENY", "reason": "UNSUPPORTED_TRACE_MODE", "candidates": [], "blocked_candidates": []}
    if hw not in HARDWARE_POLICIES:
        return {**base, "result": "DENY", "reason": "UNSUPPORTED_HARDWARE_TRAVERSAL_POLICY", "candidates": [], "blocked_candidates": []}

    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    matched_explicit = False
    for descriptor in backends:
        if requested is not None and descriptor.backend_id != requested:
            continue
        if requested is not None:
            matched_explicit = True
        reasons: list[str] = []
        if not descriptor.available:
            reasons.append("BACKEND_NOT_AVAILABLE")
        if not descriptor.device_bound:
            reasons.append("EXACT_DEVICE_OR_CPU_HOST_BINDING_REQUIRED")
        if mode not in descriptor.supported_modes:
            reasons.append("TRACE_MODE_UNSUPPORTED")
        if hw == "REQUIRED" and not descriptor.hardware_traversal:
            reasons.append("HARDWARE_TRAVERSAL_REQUIRED")
        if hw == "DISABLED" and descriptor.hardware_traversal and not descriptor.cpu_software:
            reasons.append("HARDWARE_TRAVERSAL_DISABLED")
        if descriptor.compatibility_class == "UNAVAILABLE":
            reasons.append("COMPATIBILITY_UNAVAILABLE")
        if not descriptor.provider_admitted:
            reasons.append("PROVIDER_NOT_ADMITTED")
        if not descriptor.runtime_admitted:
            reasons.append("RUNTIME_NOT_ADMITTED")

        row = descriptor.as_dict()
        row.update({
            "trace_mode": mode,
            "requested_hardware_traversal": hw,
            "execution_authorized": False,
            "neural_denoise_handoff_required": bool(neural_denoise),
        })
        if reasons:
            row["blocking_reasons"] = sorted(set(reasons))
            blocked.append(row)
        else:
            candidates.append(row)

    if requested is not None and not matched_explicit:
        return {
            **base, "result": "UNAVAILABLE", "reason": "EXPLICIT_BACKEND_NOT_FOUND",
            "application_id": app, "workload_id": workload, "trace_mode": mode,
            "requested_backend_id": requested, "candidates": [], "blocked_candidates": blocked,
        }
    return {
        **base,
        "result": "CANDIDATE_AVAILABLE" if candidates else "UNAVAILABLE",
        "application_id": app,
        "workload_id": workload,
        "trace_mode": mode,
        "requested_backend_id": requested,
        "hardware_traversal": hw,
        "path_tracing_progressive_accumulation_required": mode == "PATH_TRACING",
        "candidates": candidates,
        "blocked_candidates": blocked,
    }
