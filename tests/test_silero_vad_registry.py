from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_gate_module():
    path = ROOT / "src/fa3_silero_vad_gate.py"
    spec = importlib.util.spec_from_file_location("fa3_silero_vad_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_silero_vad_gate_passes():
    gate = load_gate_module()
    ok, errors = gate.run_gate()
    assert ok, errors


def test_vad_is_provider_neutral_subprofile_without_new_authority():
    profile = load("canonical/profiles/FA3-VOICE-ACTIVITY-DETECTION-001.json")
    contracts = load("canonical/contracts/FA3-VAD-CONTRACTS-001.json")
    assert profile["relationship"] == {"type": "SUBPROFILE-OF", "parent": "FA3-AUDIO-001"}
    assert profile["requirement"] == "MUST-IF-VAD-USED"
    assert profile["new_capability"] is False
    assert profile["new_architectural_authority"] is False
    assert profile["capability_count"] == 143
    assert contracts["provider_neutral"] is True


def test_silero_provider_cannot_become_hardware_or_routing_authority():
    provider = load("canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json")
    assert all(value is False for value in provider["authority_boundaries"].values())
    assert provider["hardware_policy"]["host_resource_broker_authoritative"] is True
    assert provider["hardware_policy"]["consume_dynamic_discovery"] is True
    assert provider["runtime"]["gpu_required"] is False
    assert provider["runtime"]["accelerator_optional_with_hrb_receipt"] is True
    assert provider["runtime"]["silent_execution_provider_fallback"] is False


def test_no_remembered_current_host_identity_is_portable_requirement():
    provider = load("canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json")
    forbidden = set(provider["hardware_policy"]["forbidden_portable_pins"])
    assert {
        "CPU_VENDOR", "CPU_MODEL", "CPU_ID", "NUMA_NODE", "GPU_SKU",
        "VRAM_SIZE", "PCI_BDF", "CUDA_ORDINAL", "FIXED_DEVICE_COUNT"
    }.issubset(forbidden)
    serialized = json.dumps(provider).lower()
    for remembered_identity in ["xeon", "rtx 3090", "a1000", "cuda:0", "numa node 0"]:
        assert remembered_identity not in serialized


def test_model_admission_is_onnx_first_and_runtime_download_is_forbidden():
    provider = load("canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json")
    allowlist = load("canonical/FA3-SILERO-VAD-MODEL-ALLOWLIST-001.json")
    assert provider["model_policy"]["preferred_format"] == "ONNX"
    assert provider["model_policy"]["runtime_torch_hub_loading"] is False
    assert provider["model_policy"]["runtime_auto_download"] is False
    assert provider["model_policy"]["runtime_network_acquisition"] is False
    assert allowlist["production_sha256_required"] is True
    assert all(a["production_admitted"] is False for a in allowlist["artifacts"])


def test_runtime_promotion_remains_pending_without_real_audio_receipt():
    provider = load("canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json")
    gate = load("canonical/FA3-GATE-SILERO-VAD-001.json")
    assert provider["promotion"]["runtime_promotion_claimed"] is False
    assert gate["promotion"]["current_host_runtime"] == "PENDING_UNTIL_REAL_AUDIO_E2E_RECEIPT"
    assert gate["promotion"]["document_derived_runtime_pass"] is False
