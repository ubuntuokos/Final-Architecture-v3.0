from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_acestep_baseline_gate import (  # noqa: E402
    explicit_steps_valid,
    export_path_valid,
    gate,
    torchcodec_enablement_valid,
    vram_reserve_valid,
)


def test_ace_step_20260912_canonical_gate_passes():
    result = gate(ROOT)
    assert result["result"] == "PASS", result
    assert result["capability_count"] == 143
    assert result["current_host_runtime_status"] == "PENDING_CURRENT_HOST"
    assert result["production_promotion_claimed"] is False


def test_sft_api_steps_are_explicit_and_not_turbo_default():
    assert explicit_steps_valid("xl_sft", 50)
    assert not explicit_steps_valid("xl_sft", 8)
    assert not explicit_steps_valid("sft_2b", None)


def test_vram_policy_preserves_kv_floor_and_hrb_authority():
    assert vram_reserve_valid(
        model_aware=True,
        duration_aware=True,
        batch_aware=True,
        kv_floor_preserved=True,
        hrb_lease=True,
    )
    assert not vram_reserve_valid(
        model_aware=True,
        duration_aware=True,
        batch_aware=True,
        kv_floor_preserved=False,
        hrb_lease=True,
    )
    assert not vram_reserve_valid(
        model_aware=True,
        duration_aware=True,
        batch_aware=True,
        kv_floor_preserved=True,
        hrb_lease=False,
    )


def test_lossless_master_and_torchcodec_fail_closed():
    assert export_path_valid(
        fmt="flac",
        torchcodec_required=False,
        fallback_verified=True,
        linux_dependency_smoke=True,
    )
    assert not export_path_valid(
        fmt="mp3",
        torchcodec_required=False,
        fallback_verified=True,
        linux_dependency_smoke=True,
    )
    assert torchcodec_enablement_valid(
        enabled=True,
        torch_abi_match=True,
        torchaudio_abi_match=True,
        codec_import_smoke=True,
    )
    assert not torchcodec_enablement_valid(
        enabled=True,
        torch_abi_match=False,
        torchaudio_abi_match=True,
        codec_import_smoke=False,
    )
