from src.fa3_kdenlive_audio_pipeline import AudioConditioningRequest, plan_request
from src.fa3_silero_vad_provider import build_speech_activity_map


def _hash(ch: str) -> str:
    return ch * 64


def test_dialogue_clean_forbids_double_denoise():
    req = AudioConditioningRequest(
        source_artifact="clip.wav",
        source_hash=_hash("a"),
        operation="dialogue_clean",
        timebase="1/48000",
    )
    plan = plan_request(req)
    assert plan.lavasr_denoise is False
    assert plan.source_in_place_mutation is False
    assert plan.direct_kdenlive_xml_mutation is False


def test_mixed_dialogue_keeps_demucs_conditional():
    req = AudioConditioningRequest(
        source_artifact="mix.wav",
        source_hash=_hash("b"),
        operation="mixed_dialogue_restore",
        timebase="1/48000",
    )
    plan = plan_request(req)
    assert "conditional_source_separation" in plan.steps


def test_accelerator_requires_hrb_lease():
    req = AudioConditioningRequest(
        source_artifact="clip.wav",
        source_hash=_hash("c"),
        operation="noise_reduction",
        timebase="1/48000",
        allow_accelerator=True,
    )
    try:
        plan_request(req)
    except PermissionError:
        return
    raise AssertionError("missing HRB lease must fail closed")


def test_silero_speech_activity_map_is_metadata_only():
    sam = build_speech_activity_map(
        source_hash=_hash("d"),
        sample_rate_hz=16000,
        channels=1,
        segments=[{"start_sample": 0, "end_sample": 16000, "confidence": 0.99}],
        provider_revision="867c2aa692646a1f1de3e94a15c9dd9f614c0acb",
        model_hash=_hash("e"),
        source_timebase="1/48000",
    ).to_dict()
    assert sam["artifact_type"] == "SpeechActivityMap"
    assert sam["metadata_only"] is True
    assert sam["analysis_sample_rate_hz"] == 16000
    assert sam["channels"] == 1
