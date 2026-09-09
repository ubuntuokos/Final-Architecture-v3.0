#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PROFILE = ROOT / "canonical/profiles/FA3-VOICE-ACTIVITY-DETECTION-001.json"
CONTRACTS = ROOT / "canonical/contracts/FA3-VAD-CONTRACTS-001.json"
PROVIDER = ROOT / "canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json"
ALLOWLIST = ROOT / "canonical/FA3-SILERO-VAD-MODEL-ALLOWLIST-001.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-SILERO-VAD-2026-09-09.json"
REFERENCE = ROOT / "canonical/references/FA3-SILERO-VAD-UPSTREAM-REFERENCE-2026-09-09.json"
ENFORCEMENT = ROOT / "canonical/silero-vad-enforcement.json"
GATE_RECORD = ROOT / "canonical/FA3-GATE-SILERO-VAD-001.json"
PROVIDER_ADAPTER = ROOT / "src/fa3_silero_vad_provider.py"
SINGLE_AUDIO_COLLECTOR = ROOT / "evidence/collect-silero-vad-current-host.py"
PROMOTION_COLLECTOR = ROOT / "evidence/collect-silero-vad-promotion-current-host.py"
CURRENT_HOST_WORKFLOW = ROOT / ".github/workflows/fa3-silero-vad-current-host.yml"

REQUIRED_FILES = [
    PROFILE, CONTRACTS, PROVIDER, ALLOWLIST, DECISION, REFERENCE,
    ENFORCEMENT, GATE_RECORD, PROVIDER_ADAPTER, SINGLE_AUDIO_COLLECTOR,
    PROMOTION_COLLECTOR, CURRENT_HOST_WORKFLOW,
]


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_gate() -> tuple[bool, list[str]]:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}", errors)
    if errors:
        return False, errors

    profile = load(PROFILE)
    contracts = load(CONTRACTS)
    provider = load(PROVIDER)
    allowlist = load(ALLOWLIST)
    decision = load(DECISION)
    reference = load(REFERENCE)
    enforcement = load(ENFORCEMENT)
    gate_record = load(GATE_RECORD)
    adapter_text = PROVIDER_ADAPTER.read_text(encoding="utf-8")
    collector_text = SINGLE_AUDIO_COLLECTOR.read_text(encoding="utf-8")
    promotion_text = PROMOTION_COLLECTOR.read_text(encoding="utf-8")
    workflow_text = CURRENT_HOST_WORKFLOW.read_text(encoding="utf-8")

    # Architecture invariants.
    require(profile.get("id") == "FA3-VOICE-ACTIVITY-DETECTION-001", "wrong VAD profile id", errors)
    require(profile.get("relationship", {}).get("parent") == "FA3-AUDIO-001", "VAD must remain under FA3-AUDIO-001", errors)
    require(profile.get("requirement") == "MUST-IF-VAD-USED", "VAD profile requirement drift", errors)
    require(profile.get("capability_count") == 143, "capability count must remain 143", errors)
    require(profile.get("new_capability") is False, "VAD must not add a capability", errors)
    require(profile.get("new_architectural_authority") is False, "VAD must not add authority", errors)
    require(provider.get("capability_count") == 143, "provider capability count must remain 143", errors)
    require(provider.get("new_capability") is False, "provider must not add a capability", errors)
    require(provider.get("new_architectural_authority") is False, "provider must not add authority", errors)
    require(contracts.get("provider_neutral") is True, "VAD contracts must remain provider-neutral", errors)
    require("VadQualityCorpusManifest" in contracts.get("contracts", []), "quality corpus contract missing", errors)

    # Authority boundaries.
    expected_authorities = {
        "provider_routing": "FA3-AUTH-MODEL-ROUTER-001",
        "host_admission_placement_reservation": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "security_governance": "FA3-AUTH-SECURITY-GOV-001",
        "observability_evidence": "FA3-AUTH-OBS-EVIDENCE-001",
        "artifact_model_identity": "FA3-REG-ARTIFACT-MODEL-001",
        "audio_device_routing": "EXISTING_FA3_AUDIO_PIPEWIRE_AUTHORITY_ONLY",
    }
    require(profile.get("authority") == expected_authorities, "VAD authority boundary drift", errors)
    require(all(value is False for value in provider.get("authority_boundaries", {}).values()), "Silero provider acquired authority", errors)

    # Hardware portability and HRB rules.
    runtime = provider.get("runtime", {})
    hardware = provider.get("hardware_policy", {})
    require(runtime.get("portable_cpu_execution_required") is True, "portable CPU execution path is required", errors)
    require(runtime.get("baseline_execution_provider") == "CPUExecutionProvider", "CPU baseline EP drift", errors)
    require(runtime.get("gpu_required") is False, "GPU must not be required for portable baseline", errors)
    require(runtime.get("accelerator_optional_with_hrb_receipt") is True, "accelerator route must require HRB receipt", errors)
    require(runtime.get("accelerator_device_binding_source") == "HRB_ACCELERATOR_EXECUTION_LEASE_ONLY", "accelerator device must be HRB-bound", errors)
    require(runtime.get("silent_execution_provider_fallback") is False, "silent EP fallback must be disabled", errors)
    require(runtime.get("accelerator_cpu_ep_fallback_disabled") is True, "accelerator CPU EP fallback must be disabled", errors)
    require(hardware.get("consume_dynamic_discovery") is True, "provider must consume dynamic hardware discovery", errors)
    require(hardware.get("host_resource_broker_authoritative") is True, "HRB must remain placement authority", errors)
    forbidden = set(hardware.get("forbidden_portable_pins", []))
    required_forbidden = {"CPU_VENDOR", "CPU_MODEL", "CPU_ID", "NUMA_NODE", "GPU_SKU", "VRAM_SIZE", "PCI_BDF", "CUDA_ORDINAL", "FIXED_DEVICE_COUNT"}
    require(required_forbidden.issubset(forbidden), "portable hardware pin forbiddance incomplete", errors)

    # Inference/model policy.
    model_policy = provider.get("model_policy", {})
    require(model_policy.get("preferred_format") == "ONNX", "ONNX must remain preferred interchange", errors)
    require(model_policy.get("runtime_torch_hub_loading") is False, "torch.hub runtime loading must stay forbidden", errors)
    require(model_policy.get("runtime_auto_download") is False, "runtime auto-download must stay forbidden", errors)
    require(model_policy.get("runtime_network_acquisition") is False, "runtime network acquisition must stay forbidden", errors)
    require(model_policy.get("sha256_required_before_current_host_promotion") is True, "SHA-256 required before promotion", errors)
    require(model_policy.get("half_precision_default") is False, "FP16 must not become default without evidence", errors)

    # Audio/runtime semantics.
    require(runtime.get("sample_rates_hz") == [8000, 16000], "Silero sample-rate contract drift", errors)
    require(runtime.get("channels") == [1], "Silero mono contract drift", errors)
    require(runtime.get("streaming_state") == "EXPLICIT_RESETTABLE", "streaming state must remain explicit/resettable", errors)
    require(runtime.get("resampling") == "EXTERNAL_OR_EXPLICIT_WITH_PROVENANCE", "implicit resampling must stay forbidden", errors)

    # Executable adapter/harness invariants.
    lower_adapter = adapter_text.lower()
    for remembered_identity in ("xeon", "rtx 3090", "rtx a1000", "cuda:0", "numa node 0"):
        require(remembered_identity not in lower_adapter, f"remembered host identity leaked into adapter: {remembered_identity}", errors)
    require("AcceleratorExecutionLease@1" in adapter_text, "adapter does not validate HRB lease schema", errors)
    require("session.disable_cpu_ep_fallback" in adapter_text, "adapter does not disable accelerator CPU EP fallback", errors)
    require("device_id" in adapter_text and "device_ordinal" in adapter_text, "CUDA device not bound from HRB lease", errors)
    require("FA3_CURRENT_HOST_RUNNER" in collector_text, "single-audio collector lacks current-host runner guard", errors)
    require("FA3_CURRENT_HOST_RUNNER" in promotion_text, "promotion collector lacks current-host runner guard", errors)
    require("runs-on: [self-hosted, linux, x64, fa3-current-host]" in workflow_text, "current-host workflow runner labels drift", errors)
    require("workflow_dispatch:" in workflow_text, "current-host production workflow must remain explicit/manual", errors)

    # Immutable upstream and allowlist.
    upstream = provider.get("upstream", {})
    require(upstream.get("release") == "v6.2.1", "upstream release drift", errors)
    require(upstream.get("revision") == "7e30209a3e901f9842f81b225f3e93d8199902b1", "upstream revision drift", errors)
    require(reference.get("revision") == upstream.get("revision"), "upstream reference/provider revision mismatch", errors)
    require(allowlist.get("provider_id") == provider.get("id"), "allowlist/provider mismatch", errors)
    require(allowlist.get("runtime_auto_download") is False, "allowlist permits runtime download", errors)
    require(allowlist.get("production_sha256_required") is True, "allowlist must require production SHA-256", errors)
    artifacts = allowlist.get("artifacts", [])
    require(any(a.get("name") == "silero_vad.onnx" and a.get("role") == "PRIMARY_CANDIDATE" for a in artifacts), "primary ONNX artifact missing", errors)
    require(all(a.get("production_admitted") is False for a in artifacts), "artifact promoted without current-host SHA-256 receipt", errors)

    # Promotion/evidence discipline.
    promotion = provider.get("promotion", {})
    require(promotion.get("current_host_real_onnx_e2e") == "REQUIRED", "real ONNX E2E must be required", errors)
    require(promotion.get("sample_rate_8k_e2e") == "REQUIRED", "8 kHz E2E must be required", errors)
    require(promotion.get("sample_rate_16k_e2e") == "REQUIRED", "16 kHz E2E must be required", errors)
    require(promotion.get("quality_regression") == "REQUIRED", "quality regression must be required", errors)
    require(promotion.get("concurrent_stream_test") == "REQUIRED", "concurrency evidence must be required", errors)
    require(promotion.get("long_run_soak") == "REQUIRED", "soak evidence must be required", errors)
    require(promotion.get("runtime_promotion_claimed") is False, "runtime promotion claimed without evidence", errors)
    require(gate_record.get("promotion", {}).get("document_derived_runtime_pass") is False, "document-derived runtime PASS forbidden", errors)
    require(gate_record.get("promotion", {}).get("production_runtime_promoted") is False, "production runtime promoted without current-host receipt", errors)
    require(decision.get("capability_count_before") == 143 and decision.get("capability_count_after") == 143, "decision changes capability count", errors)

    # Enforcement must remain fail-closed and non-trivial.
    require(enforcement.get("fail_closed") is True, "enforcement must fail closed", errors)
    require(len(enforcement.get("rules", [])) >= 26, "enforcement rule set unexpectedly reduced", errors)

    return not errors, errors


def main() -> int:
    ok, errors = run_gate()
    if ok:
        print("FA3-GATE-SILERO-VAD-001: PASS")
        return 0
    print("FA3-GATE-SILERO-VAD-001: FAIL")
    for error in errors:
        print(f" - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
