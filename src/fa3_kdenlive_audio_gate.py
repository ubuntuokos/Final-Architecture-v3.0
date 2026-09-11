#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
REPORT_REL = Path("reports/kdenlive-audio-conditioning-gate-report.json")

REQUIRED_FILES = [
    "canonical/contracts/FA3-KDENLIVE-AUDIO-CONDITIONING-CONTRACTS-001.json",
    "canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json",
    "canonical/decisions/FA3-DEC-KDENLIVE-AUDIO-CONDITIONING-2026-09-11.json",
    "canonical/kdenlive-audio-conditioning-enforcement.json",
    "canonical/FA3-GATE-KDENLIVE-AUDIO-CONDITIONING-001.json",
    "src/fa3_silero_vad_provider.py",
    "src/fa3_kdenlive_audio_pipeline.py",
]


def _load_json(root: Path, rel: str) -> dict[str, Any]:
    with (root / rel).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    checks: dict[str, bool] = {}
    if not errors:
        contract = _load_json(root, REQUIRED_FILES[0])
        silero = _load_json(root, REQUIRED_FILES[1])
        decision = _load_json(root, REQUIRED_FILES[2])
        enforcement = _load_json(root, REQUIRED_FILES[3])
        gate_record = _load_json(root, REQUIRED_FILES[4])

        checks = {
            "capability_count_143": silero.get("capability_count") == 143
            and enforcement.get("capability_count") == 143
            and gate_record.get("capability_count") == 143,
            "authority_delta_zero": contract.get("architectural_authority_delta") == 0
            and enforcement.get("architectural_authority_delta") == 0
            and gate_record.get("architectural_authority_delta") == 0,
            "vad_metadata_only": contract["speech_activity_map"].get("metadata_only") is True
            and silero["output_contract"].get("metadata_only") is True,
            "vad_no_master_mutation": contract["speech_activity_map"].get("master_audio_mutation_forbidden") is True,
            "vad_16k_mono_default": contract["speech_activity_map"].get("preferred_analysis_projection")
            == {"sample_rate_hz": 16000, "channels": 1},
            "demucs_conditional": "demucs_if_required" in contract["default_paths"]["mixed_dialogue_restore"],
            "double_denoise_guard": "NO_IMPLICIT_DOUBLE_DENOISE" in contract["processing_invariants"]
            and "LAVASR_AFTER_GTCRN_REQUIRES_DENOISE_DISABLED" in contract["processing_invariants"],
            "stt_optional_conditioning": "STT_MUST_WORK_WITHOUT_OPTIONAL_AUDIO_CONDITIONING"
            in contract["processing_invariants"],
            "xml_mutation_forbidden": "DIRECT_KDENLIVE_PROJECT_XML_MUTATION_FORBIDDEN"
            in contract["processing_invariants"],
            "source_mutation_forbidden": contract["request_contract"].get("source_in_place_mutation_forbidden") is True,
            "provider_neutral_editorial_intent": contract["request_contract"].get("provider_names_forbidden_in_editorial_intent") is True,
            "silero_runtime_no_auto_download": silero["runtime_policy"].get("runtime_auto_download") is False,
            "silero_model_hash_required": silero["runtime_policy"].get("model_sha256_required") is True,
            "silero_no_silent_ep_fallback": silero["runtime_policy"].get("silent_execution_provider_fallback") is False,
            "silero_state_reset": silero["audio_contract"].get("state_reset_required_between_independent_streams") is True,
            "production_pending": decision["production_promotion"].get("state") == "PENDING_CURRENT_HOST",
            "fail_closed": enforcement.get("fail_closed") is True and gate_record.get("fail_closed") is True,
            "rule_count_at_least_30": len(enforcement.get("rules", [])) >= 30,
        }
        errors.extend(name for name, ok in checks.items() if not ok)

    report = {
        "schema": "fa3.kdenlive-audio-conditioning-gate-report.v1",
        "gate": "FA3-GATE-KDENLIVE-AUDIO-CONDITIONING-001",
        "gateset": "FA3-KDENLIVE-AUDIO-CONDITIONING-GATESET-001",
        "result": "PASS" if not errors else "FAIL",
        "blocking_findings": len(errors),
        "checks": checks,
        "findings": errors,
        "capability_count": 143,
        "architectural_authority_delta": 0,
        "production_promotion": "PENDING_CURRENT_HOST",
        "production_note": "Reference/static PASS never substitutes for real current-host audio E2E evidence.",
    }
    report_path = root / REPORT_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    report = gate(DEFAULT_ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
