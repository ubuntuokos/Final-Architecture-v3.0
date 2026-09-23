from src.fa3_decision_fabric import DecisionFabric, ProviderResult
from src.fa3_voice_quality_router import VoiceQualityRoutingDenied, resolve_quality_route


class PreferPiperProvider:
    provider_id = "TEST-PREFER-PIPER"
    semantic = True

    def decide(self, request):
        return ProviderResult("DECIDED", {"selected": "FA3-PROVIDER-PIPER-001"}, 1.0)


POLICY = {
    "quality_classes": {
        "BASIC": {},
        "STANDARD": {},
        "PRODUCTION": {},
        "PREMIUM_CLONING": {},
    },
    "provider_quality_eligibility": {
        "FA3-PROVIDER-XTTS-001": ["STANDARD", "PRODUCTION", "PREMIUM_CLONING"],
        "FA3-PROVIDER-PIPER-001": ["BASIC", "STANDARD"],
    },
    "workflow_overrides": {
        "MARKETING_PRODUCTION": {
            "required_quality_class": "PRODUCTION",
            "forbidden_provider_ids": ["FA3-PROVIDER-PIPER-001"],
            "fallback": "FAIL_CLOSED",
        }
    },
}


def test_marketing_production_never_routes_to_piper():
    receipt = resolve_quality_route(
        policy=POLICY,
        language="hu-HU",
        requested_quality="STANDARD",
        workflow="MARKETING_PRODUCTION",
        admitted_provider_ids={"FA3-PROVIDER-XTTS-001", "FA3-PROVIDER-PIPER-001"},
        provider_language_support={
            "FA3-PROVIDER-XTTS-001": {"hu", "hu-HU"},
            "FA3-PROVIDER-PIPER-001": {"hu", "hu-HU"},
        },
        hrb_accelerator_lease=True,
        accelerator_provider_ids={"FA3-PROVIDER-XTTS-001"},
    )
    assert receipt["selected_provider_id"] == "FA3-PROVIDER-XTTS-001"
    assert receipt["effective_quality_class"] == "PRODUCTION"
    assert receipt["silent_quality_downgrade"] is False


def test_piper_remains_valid_for_basic_cpu_tts():
    receipt = resolve_quality_route(
        policy=POLICY,
        language="hu",
        requested_quality="BASIC",
        workflow=None,
        admitted_provider_ids={"FA3-PROVIDER-PIPER-001"},
        provider_language_support={"FA3-PROVIDER-PIPER-001": {"hu"}},
        hrb_accelerator_lease=False,
        accelerator_provider_ids=set(),
    )
    assert receipt["selected_provider_id"] == "FA3-PROVIDER-PIPER-001"


def test_production_fails_closed_without_eligible_provider():
    try:
        resolve_quality_route(
            policy=POLICY,
            language="hu-HU",
            requested_quality="PRODUCTION",
            workflow="MARKETING_PRODUCTION",
            admitted_provider_ids={"FA3-PROVIDER-PIPER-001"},
            provider_language_support={"FA3-PROVIDER-PIPER-001": {"hu-HU"}},
            hrb_accelerator_lease=False,
            accelerator_provider_ids=set(),
        )
    except VoiceQualityRoutingDenied:
        return
    raise AssertionError("production route must fail closed")


def test_accelerator_provider_requires_hrb_lease():
    try:
        resolve_quality_route(
            policy=POLICY,
            language="hu-HU",
            requested_quality="PRODUCTION",
            workflow=None,
            admitted_provider_ids={"FA3-PROVIDER-XTTS-001"},
            provider_language_support={"FA3-PROVIDER-XTTS-001": {"hu-HU"}},
            hrb_accelerator_lease=False,
            accelerator_provider_ids={"FA3-PROVIDER-XTTS-001"},
        )
    except VoiceQualityRoutingDenied:
        return
    raise AssertionError("accelerator provider must require HRB lease")


def test_active_decision_hook_can_choose_only_preeligible_voice_provider():
    receipt = resolve_quality_route(
        policy=POLICY,
        language="hu-HU",
        requested_quality="STANDARD",
        workflow=None,
        admitted_provider_ids={"FA3-PROVIDER-XTTS-001", "FA3-PROVIDER-PIPER-001"},
        provider_language_support={
            "FA3-PROVIDER-XTTS-001": {"hu", "hu-HU"},
            "FA3-PROVIDER-PIPER-001": {"hu", "hu-HU"},
        },
        hrb_accelerator_lease=True,
        accelerator_provider_ids={"FA3-PROVIDER-XTTS-001"},
        decision_fabric=DecisionFabric([PreferPiperProvider()]),
        decision_provider_id="TEST-PREFER-PIPER",
        decision_rollout="ACTIVE",
    )
    assert receipt["selected_provider_id"] == "FA3-PROVIDER-PIPER-001"
    assert receipt["decision_fabric_applied"] is True


def test_decision_hook_never_resurrects_ineligible_voice_provider():
    class InvalidVoiceProvider:
        provider_id = "TEST-INVALID"
        semantic = True
        def decide(self, request):
            return ProviderResult("DECIDED", {"selected": "FA3-PROVIDER-PIPER-001"}, 1.0)

    try:
        resolve_quality_route(
            policy=POLICY,
            language="hu-HU",
            requested_quality="PRODUCTION",
            workflow="MARKETING_PRODUCTION",
            admitted_provider_ids={"FA3-PROVIDER-XTTS-001", "FA3-PROVIDER-PIPER-001"},
            provider_language_support={
                "FA3-PROVIDER-XTTS-001": {"hu-HU"},
                "FA3-PROVIDER-PIPER-001": {"hu-HU"},
            },
            hrb_accelerator_lease=True,
            accelerator_provider_ids={"FA3-PROVIDER-XTTS-001"},
            decision_fabric=DecisionFabric([InvalidVoiceProvider()]),
            decision_provider_id="TEST-INVALID",
            decision_rollout="ACTIVE",
        )
    except VoiceQualityRoutingDenied:
        return
    raise AssertionError("Decision Fabric must not resurrect deterministically ineligible voice provider")
