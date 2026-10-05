#!/usr/bin/env python3
"""UAF provider adapters for the FA3 marketing projection surface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fa3_marketing_decision_fabric import DecisionRequest, decide
from fa3_uaf import ActionRequest, CallableProvider, ProviderDescriptor, ProviderRegistry, UafError

PROVIDER_ACTIONS: dict[str, tuple[str, ...]] = {
    "FA3-PROVIDER-TWENTY-001": (
        "marketing.contact.project", "marketing.contact.reconcile",
    ),
    "FA3-PROVIDER-MAUTIC-001": (
        "marketing.segment.preview", "marketing.campaign.draft",
        "marketing.campaign.schedule", "marketing.campaign.pause",
    ),
    "FA3-PROVIDER-LISTMONK-001": (
        "marketing.newsletter.prepare", "marketing.newsletter.dispatch",
    ),
    "FA3-MARKETING-CANONICAL-ADAPTER-001": (
        "marketing.consent.record", "marketing.suppression.apply",
        "marketing.campaign.validate", "marketing.campaign.approve",
        "marketing.delivery.reconcile", "marketing.experiment.record",
        "marketing.analytics.project",
    ),
}


@dataclass(frozen=True)
class AdapterMode:
    name: str
    external_mutation: bool
    current_host_admitted: bool


REFERENCE_MODE = AdapterMode("REFERENCE_ONLY", False, False)


def _candidates(request: ActionRequest) -> tuple[dict[str, Any], ...]:
    values = request.arguments.get("candidate_ids", [])
    return tuple({"id": str(value), "eligible": True} for value in values)


def register_marketing_provider(
    providers: ProviderRegistry,
    provider_id: str,
    *,
    transport: Callable[[ActionRequest, tuple[Any, ...]], dict[str, Any]] | None = None,
    mode: AdapterMode = REFERENCE_MODE,
    advisory: Callable[[tuple[str, ...], dict[str, Any]], list[str]] | None = None,
) -> None:
    action_ids = PROVIDER_ACTIONS.get(provider_id)
    if action_ids is None:
        raise UafError("MKT-PROVIDER-UNKNOWN", f"unknown marketing provider: {provider_id}")
    if mode.external_mutation and (not mode.current_host_admitted or transport is None):
        raise UafError(
            "MKT-PROVIDER-NOT-ADMITTED",
            "external mutation requires an admitted current-host transport",
        )

    def execute(
        request: ActionRequest, _resource_lease: Any, secret_leases: tuple[Any, ...]
    ) -> dict[str, Any]:
        receipt = decide(DecisionRequest(
            decision_id=f"{request.trace_id}:{request.action_id}",
            kind="CANDIDATE_RANKING",
            scope=request.action_id,
            candidates=_candidates(request),
            context=tuple(
                {"id": str(value), "relevance": 1.0}
                for value in request.arguments.get("context_refs", [])
            ),
            signals={"evidence_refs": [f"uaf:{request.request_id}"]},
        ), advisory=advisory)
        if receipt["outcome"] != "CONTINUE":
            raise UafError("MKT-DECISION-BLOCKED", receipt["reason"])
        if mode.external_mutation:
            if provider_id.startswith("FA3-PROVIDER-") and not secret_leases:
                raise UafError(
                    "UAF-SECRET-DENIED",
                    "external marketing provider requires Secret Broker lease",
                )
            provider_output = transport(request, secret_leases) if transport else {}
            status = str(provider_output.get("status", "PROVIDER_APPLIED"))
            evidence_refs = list(provider_output.get("evidence_refs", []))
        else:
            status = "REFERENCE_ONLY_NO_PROVIDER_MUTATION"
            evidence_refs = [f"reference:{request.request_id}"]
        return {
            "status": status,
            "provider_id": provider_id,
            "decision_receipt": receipt,
            "evidence_refs": evidence_refs,
        }

    providers.register(CallableProvider(
        ProviderDescriptor(
            provider_id=provider_id,
            action_ids=action_ids,
            capabilities=("marketing.projection", "marketing.decision-receipt"),
            priority=20,
            state="CONNECTED",
            metadata={
                "authority": "NON_AUTHORITY_ADAPTER",
                "mode": mode.name,
                "current_host_admitted": mode.current_host_admitted,
            },
        ),
        execute,
    ))


def register_reference_marketing_providers(providers: ProviderRegistry) -> None:
    for provider_id in PROVIDER_ACTIONS:
        register_marketing_provider(providers, provider_id)
