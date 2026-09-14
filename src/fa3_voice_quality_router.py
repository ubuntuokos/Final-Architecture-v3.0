#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

    return {
        "schema": "fa3.voice-quality-routing-receipt.v1",
        "selected_provider_id": candidates[0],
        "locale": locale,
        "requested_quality_class": requested_quality,
        "effective_quality_class": effective_quality,
        "workflow": workflow,
        "silent_quality_downgrade": False,
        "hrb_accelerator_lease": hrb_accelerator_lease,
    }
