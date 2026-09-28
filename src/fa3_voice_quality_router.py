#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_decision_fabric import DecisionError

POLICY_PATH = Path("canonical/FA3-VOICE-QUALITY-ROUTING-001.json")


class VoiceQualityRoutingDenied(RuntimeError):
    pass


def load_policy(root: Path) -> dict[str, Any]:
    return json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))


def normalize_locale(value: str) -> str:
    value = value.strip().replace("_", "-")
    if not value:
        raise VoiceQualityRoutingDenied("language/locale is required")
    parts = value.split("-")
    if len(parts) == 1:
        return parts[0].lower()
    return f"{parts[0].lower()}-{parts[1].upper()}"


def resolve_quality_route(
    *,
    policy: dict[str, Any],
    language: str,
    requested_quality: str,
    workflow: str | None,
    admitted_provider_ids: set[str],
    provider_language_support: dict[str, set[str]],
    hrb_accelerator_lease: bool,
    accelerator_provider_ids: set[str],
    decision_fabric: Any = None,
    decision_provider_id: str = "FA3-PROVIDER-DECISION-RULES-001",
    decision_rollout: str = "SHADOW",
    decision_state: Any = None,
) -> dict[str, Any]:
    locale = normalize_locale(language)
    classes = policy.get("quality_classes", {})
    if requested_quality not in classes:
        raise VoiceQualityRoutingDenied(f"unknown quality class: {requested_quality}")

    workflow_rule = policy.get("workflow_overrides", {}).get(workflow or "", {})
    effective_quality = workflow_rule.get("required_quality_class", requested_quality)
    if effective_quality not in classes:
        raise VoiceQualityRoutingDenied(f"invalid workflow quality class: {effective_quality}")

    forbidden = set(workflow_rule.get("forbidden_provider_ids", []))
    eligibility = policy.get("provider_quality_eligibility", {})
    candidates: list[str] = []
    for provider_id, quality_levels in eligibility.items():
        if provider_id not in admitted_provider_ids or provider_id in forbidden:
            continue
        supported = provider_language_support.get(provider_id, set())
        if locale not in supported and locale.split("-")[0] not in supported:
            continue
        if effective_quality not in quality_levels:
            continue
        if provider_id in accelerator_provider_ids and not hrb_accelerator_lease:
            continue
        candidates.append(provider_id)

    if not candidates:
        raise VoiceQualityRoutingDenied(
            f"no admitted provider satisfies locale={locale}, quality={effective_quality}, workflow={workflow or 'default'}"
        )

    selected_provider_id = candidates[0]
    decision_trace = None
    if decision_fabric is not None:
        try:
            decision_trace = decision_fabric.decide(
            {
                "contract": "SELECT_ONE",
                "purpose": "Choose one already-admitted voice provider satisfying deterministic locale/quality/HRB eligibility",
                "candidates": [
                    {
                        "id": provider_id,
                        "description": f"voice provider for {locale} at {effective_quality}",
                        "metadata": {"priority": -index},
                    }
                    for index, provider_id in enumerate(candidates)
                ],
                "constraints": {},
                "policy_context": {
                    "voice_quality_authority": "FA3-VOICE-QUALITY-ROUTING-001",
                    "deterministic_eligibility_already_applied": True,
                    "hrb_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
                },
                "evidence_refs": [],
                "state": decision_state,
                "failure_policy": "EXISTING_BEHAVIOR",
                "rollout": decision_rollout,
                "final_policy_owner": "FA3-VOICE-QUALITY-ROUTING-001",
            },
                decision_provider_id,
            )
        except DecisionError as exc:
            raise VoiceQualityRoutingDenied("Decision Fabric violated bounded voice candidate set") from exc
        if decision_rollout == "ACTIVE" and decision_trace.get("status") == "DECIDED":
            proposed = (decision_trace.get("result") or {}).get("selected")
            if proposed not in candidates:
                raise VoiceQualityRoutingDenied("Decision Fabric attempted to escape admitted voice candidate set")
            selected_provider_id = proposed

    return {
        "schema": "fa3.voice-quality-routing-receipt.v1",
        "selected_provider_id": selected_provider_id,
        "locale": locale,
        "requested_quality_class": requested_quality,
        "effective_quality_class": effective_quality,
        "workflow": workflow,
        "silent_quality_downgrade": False,
        "hrb_accelerator_lease": hrb_accelerator_lease,
        "decision_trace": decision_trace,
        "decision_fabric_applied": decision_rollout == "ACTIVE" and decision_trace is not None,
    }
