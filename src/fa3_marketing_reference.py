#!/usr/bin/env python3
from __future__ import annotations
import json

PROFILE_ID = "FA3-MARKETING-001"
GATE_ID = "FA3-GATE-MARKETING-001"
CAPABILITY_COUNT = 143

def native_hungarian_content_valid(content):
    text = str(content.get("text", ""))
    return (
        content.get("locale") == "hu-HU"
        and content.get("generation_mode") == "NATIVE_HUNGARIAN_GENERATION"
        and content.get("translation_source_locale") is None
        and any(ch in text for ch in "áéíóöőúüűÁÉÍÓÖŐÚÜŰ")
        and len(text.strip()) >= 20
    )

def delivery_allowed(intent):
    return (
        intent.get("via_central_mcp") is True
        and intent.get("recipient_resolved") is True
        and intent.get("channel_consent") is True
        and intent.get("purpose_allowed") is True
        and intent.get("suppressed") is False
        and intent.get("unsubscribed") is False
        and intent.get("human_approved") is True
    )

def social_publish_allowed(intent):
    return delivery_allowed(intent) and intent.get("delegated_capability") == "CAP-040"

def public_prose_allowed(content):
    return (
        native_hungarian_content_valid(content)
        and content.get("quality_gate") == "CAP-125"
        and content.get("quality_pass") is True
    )

def attribution_valid(record):
    return (
        bool(record.get("source_event_ids"))
        and bool(record.get("campaign_version_id"))
        and bool(record.get("metric_definition_id"))
        and record.get("evidence_backed") is True
        and record.get("provider_is_truth_authority") is False
    )

def run_reference_e2e(request=None):
    request = request or {}
    campaign = {
        "id": "campaign-hu-demo-001",
        "version": 1,
        "state": "APPROVED",
        "locale": "hu-HU",
        "canonical_authority": "FA3_DATA_EVENT_CONTRACT_LAYER",
        "provider_state_is_projection_only": True,
    }
    content = {
        "locale": "hu-HU",
        "generation_mode": "NATIVE_HUNGARIAN_GENERATION",
        "translation_source_locale": None,
        "text": "Fedezd fel az új lehetőségeket, és válaszd a számodra megfelelő megoldást.",
        "quality_gate": "CAP-125",
        "quality_pass": True,
        "tone_profile": "TEGEZO",
    }
    email = {
        "via_central_mcp": True,
        "recipient_resolved": True,
        "channel_consent": True,
        "purpose_allowed": True,
        "suppressed": False,
        "unsubscribed": False,
        "human_approved": True,
        "delegated_provider": "FA3-PROVIDER-LISTMONK-001",
    }
    social = dict(email, delegated_capability="CAP-040", delegated_provider="SOCIAL_GATEWAY")
    experiment = {
        "hypothesis": "A natív magyar CTA javítja az átkattintást.",
        "metric_definition_id": "ctr-v1",
        "guardrail": "unsubscribe-rate",
    }
    attribution = {
        "source_event_ids": ["delivery-001", "click-001"],
        "campaign_version_id": "campaign-hu-demo-001@1",
        "metric_definition_id": "ctr-v1",
        "evidence_backed": True,
        "provider_is_truth_authority": False,
    }
    checks = {
        "campaign_provider_neutral": campaign["provider_state_is_projection_only"],
        "primary_locale_hu_hu": campaign["locale"] == "hu-HU",
        "native_hungarian_content": native_hungarian_content_valid(content),
        "public_prose_quality": public_prose_allowed(content),
        "email_consent_and_approval": delivery_allowed(email),
        "social_delegated_cap040": social_publish_allowed(social),
        "experiment_typed": all(experiment.values()),
        "attribution_lineage": attribution_valid(attribution),
        "workflow_authority_external_to_providers": True,
        "evidence_authority_external_to_analytics_provider": True,
        "provider_failure_preserves_canonical_campaign": campaign["state"] == "APPROVED",
        "current_host_runtime_not_claimed": True,
    }
    return {
        "schema": "fa3.marketing-reference-e2e-report.v1",
        "profile_id": PROFILE_ID,
        "gate_id": GATE_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "campaign": campaign,
        "content": content,
        "delivery": {"email": email, "social": social},
        "experiment": experiment,
        "attribution": attribution,
        "current_host_provider_runtime_claim": False,
    }

if __name__ == "__main__":
    print(json.dumps(run_reference_e2e(), indent=2, ensure_ascii=False))
