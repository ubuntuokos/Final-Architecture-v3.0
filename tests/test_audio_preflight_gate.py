from src.fa3_audio_preflight_gate import validate_request


def valid_request():
    return {
        "artifact_id": "audio-1",
        "sha256": "a" * 64,
        "codec": "wav",
        "sample_rate_hz": 48000,
        "channels": 2,
        "supported_codecs": ["wav", "flac"],
        "supported_sample_rates_hz": [44100, 48000],
        "supported_channel_counts": [1, 2],
        "ram_budget_bytes": 8_000_000_000,
        "vram_budget_bytes": 12_000_000_000,
        "estimated_peak_ram_bytes": 2_000_000_000,
        "estimated_peak_vram_bytes": 4_000_000_000,
        "bounded_execution": True,
        "accelerator": True,
        "hrb_lease_id": "lease-123",
        "provider_self_placed_device": False,
        "source_artifact_id": "source-1",
        "provider_id": "FA3-PROVIDER-DEMUCS-001",
        "model_or_runtime_lock_ref": "FA3-UPSTREAM-LOCK-REGISTRY-001#demucs",
        "output_artifact_type": "audio/stems",
        "output_codec": "wav",
        "output_lineage_required": True,
    }


def test_all_layers_pass_for_valid_request():
    report = validate_request(valid_request())
    assert report["result"] == "PASS"
    assert len(report["layers"]) == 6
    assert all(layer["result"] == "PASS" for layer in report["layers"])


def test_accelerator_without_hrb_lease_fails():
    req = valid_request()
    req["hrb_lease_id"] = ""
    report = validate_request(req)
    assert report["result"] == "FAIL"
    hrb = next(layer for layer in report["layers"] if layer["layer"] == "L4_HRB_ADMISSION")
    assert hrb["result"] == "FAIL"


def test_resource_overcommit_fails():
    req = valid_request()
    req["estimated_peak_vram_bytes"] = req["vram_budget_bytes"] + 1
    report = validate_request(req)
    budget = next(layer for layer in report["layers"] if layer["layer"] == "L3_RESOURCE_BUDGET")
    assert budget["result"] == "FAIL"


def test_missing_lock_provenance_fails():
    req = valid_request()
    req["model_or_runtime_lock_ref"] = ""
    report = validate_request(req)
    provenance = next(layer for layer in report["layers"] if layer["layer"] == "L5_PROVENANCE")
    assert provenance["result"] == "FAIL"
