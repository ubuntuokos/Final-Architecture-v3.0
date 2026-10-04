#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Iterable, Mapping

from fa3_accelerator_backend_probe import enrich_accelerator_backends
from fa3_hardware_discovery import AcceleratorDeviceDescriptor

SHARED_APPLICATION_SCOPE = "ALL_CURRENT_AND_FUTURE_CFA3_APPLICATIONS"
CUDA_COMPAT_BACKENDS = frozenset({"cuda", "scale-cuda", "zluda"})


def _identity(value: str | None) -> str:
    return str(value or "").strip()


def resolve_cuda_compatibility(
    devices: Iterable[AcceleratorDeviceDescriptor],
    *,
    application_id: str,
    workload_id: str,
    requested_backend: str | None = None,
    allow_translation: bool = False,
    include_framework_probes: bool = False,
    environ: Mapping[str, str] | None = None,
    scale_rights_receipt: Mapping[str, Any] | None = None,
    commercial_context: bool = True,
) -> dict[str, Any]:
    """Resolve centrally visible CUDA-compatible candidates without authorizing execution.

    The API is intentionally application-agnostic: every current or future CFA3
    application uses this same entry point. application_id is provenance/audit
    context only and is never an allowlist key. HRB remains the execution
    placement/lease authority.
    """
    app = _identity(application_id)
    workload = _identity(workload_id)
    requested = _identity(requested_backend) or None

    if not app or not workload:
        return {
            "schema": "fa3.cuda-compat-shared-resolution.v1",
            "result": "DENY",
            "reason": "APPLICATION_AND_WORKLOAD_ID_REQUIRED",
            "application_scope": SHARED_APPLICATION_SCOPE,
            "application_allowlist": False,
            "execution_authorized": False,
            "candidates": [],
            "blocked_candidates": [],
        }

    if requested is not None and requested not in CUDA_COMPAT_BACKENDS:
        return {
            "schema": "fa3.cuda-compat-shared-resolution.v1",
            "result": "DENY",
            "reason": "UNSUPPORTED_EXPLICIT_BACKEND",
            "application_scope": SHARED_APPLICATION_SCOPE,
            "application_id": app,
            "workload_id": workload,
            "requested_backend": requested,
            "application_allowlist": False,
            "automatic_backend_selection": False,
            "execution_authorized": False,
            "candidates": [],
            "blocked_candidates": [],
        }

    enriched = enrich_accelerator_backends(
        devices,
        include_framework_probes=include_framework_probes,
        environ=environ,
        scale_rights_receipt=scale_rights_receipt,
        commercial_context=commercial_context,
    )

    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for device in enriched:
        for backend in device.backends:
            if backend.name not in CUDA_COMPAT_BACKENDS:
                continue
            if requested is not None and backend.name != requested:
                continue

            reasons: list[str] = []
            if not backend.detected:
                reasons.append("BACKEND_NOT_DETECTED")
            if not backend.available:
                reasons.append("BACKEND_NOT_AVAILABLE")
            if backend.binding_scope != "DEVICE":
                reasons.append("EXACT_DEVICE_BINDING_REQUIRED")
            if backend.backend_class == "translation" and not allow_translation:
                reasons.append("TRANSLATION_NOT_EXPLICITLY_ALLOWED")

            row = {
                "device_id": device.discovery_id,
                "stable_device_id": device.stable_device_id,
                "pci_bdf": device.pci_bdf,
                "vendor": device.vendor,
                "backend": backend.name,
                "backend_class": backend.backend_class,
                "runtime_version": backend.runtime_version,
                "experimental": backend.experimental,
                "framework_backends": list(backend.framework_backends),
                "evidence_sources": list(backend.evidence_sources),
            }
            if reasons:
                row["blocking_reasons"] = reasons
                blocked.append(row)
            else:
                candidates.append(row)

    return {
        "schema": "fa3.cuda-compat-shared-resolution.v1",
        "result": "CANDIDATE_AVAILABLE" if candidates else "UNAVAILABLE",
        "application_scope": SHARED_APPLICATION_SCOPE,
        "application_id": app,
        "workload_id": workload,
        "requested_backend": requested,
        "application_allowlist": False,
        "application_identity_is_provenance_only": True,
        "automatic_backend_selection": False,
        "application_provider_selection_authority": False,
        "translation_explicitly_allowed": bool(allow_translation),
        "execution_authorized": False,
        "execution_requires_authorized_hrb_lease": True,
        "silent_fallback": False,
        "candidates": candidates,
        "blocked_candidates": blocked,
    }
