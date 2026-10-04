#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from fa3_voice_workspace import VoiceWorkspaceDenied, VoiceWorkspaceStore


class VoiceProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class VoiceProviderDescriptor:
    provider_id: str
    capabilities: tuple[str, ...]
    languages: tuple[str, ...]
    current_host_admitted: bool
    cpu_supported: bool


class VoiceProviderAdapter(Protocol):
    descriptor: VoiceProviderDescriptor

    def synthesize(
        self,
        request: dict[str, Any],
        *,
        resource_admission: Any,
        provider_decision: dict[str, Any],
    ) -> dict[str, Any]: ...


class VoiceProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, VoiceProviderAdapter] = {}

    def register(self, provider: VoiceProviderAdapter) -> None:
        pid = provider.descriptor.provider_id.strip()
        if not pid:
            raise VoiceProviderError("provider id required")
        if pid in self._providers:
            raise VoiceProviderError(f"duplicate voice provider adapter: {pid}")
        self._providers[pid] = provider

    def resolve_exact(self, provider_id: str) -> VoiceProviderAdapter:
        provider = self._providers.get(provider_id)
        if provider is None:
            raise VoiceProviderError(f"no runtime adapter for routed provider: {provider_id}")
        if provider.descriptor.current_host_admitted is not True:
            raise VoiceProviderError(f"voice provider is not current-host admitted: {provider_id}")
        return provider

    def descriptors(self) -> list[VoiceProviderDescriptor]:
        return [self._providers[key].descriptor for key in sorted(self._providers)]


def execute_dispatched_job(
    store: VoiceWorkspaceStore,
    registry: VoiceProviderRegistry,
    job_id: str,
    *,
    resource_admission: Any,
) -> dict[str, Any]:
    job = store.status(job_id).get("job")
    if not isinstance(job, dict) or not job:
        raise VoiceWorkspaceDenied("unknown dispatched voice job")
    if job.get("status") != "DISPATCHED":
        raise VoiceWorkspaceDenied("voice provider execution requires DISPATCHED job")
    decision = job.get("provider_decision")
    if not isinstance(decision, dict):
        raise VoiceWorkspaceDenied("dispatched job lacks provider decision")
    provider_id = str(decision.get("selected_provider_id") or "").strip()
    if not provider_id:
        raise VoiceWorkspaceDenied("dispatched job lacks selected provider")
    if not resource_admission:
        raise VoiceWorkspaceDenied("fresh resource admission is required for voice provider execution")

    adapter = registry.resolve_exact(provider_id)
    request = job.get("request")
    if not isinstance(request, dict):
        raise VoiceWorkspaceDenied("voice generation request missing")

    language = str(request.get("language") or "").strip()
    mode = str(request.get("mode") or "").strip()
    if language not in adapter.descriptor.languages:
        raise VoiceProviderError(f"routed language not supported by adapter: {language}")
    required_capability = "voice_clone" if mode in {"voice_clone", "zero_shot"} else "plain_tts"
    if required_capability not in adapter.descriptor.capabilities:
        raise VoiceProviderError(f"routed capability not supported by adapter: {required_capability}")

    result = adapter.synthesize(
        request,
        resource_admission=resource_admission,
        provider_decision=decision,
    )
    if not isinstance(result, dict):
        raise VoiceProviderError("voice provider result must be an object")
    if result.get("provider_id") != provider_id:
        raise VoiceProviderError("voice provider result identity mismatch")
    return store.accept_generation_result(job_id, result)
