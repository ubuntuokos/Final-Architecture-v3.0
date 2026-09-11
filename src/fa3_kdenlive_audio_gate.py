#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "canonical/contracts/FA3-KDENLIVE-AUDIO-CONDITIONING-CONTRACTS-001.json",
    "canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json",
    "canonical/decisions/FA3-DEC-KDENLIVE-AUDIO-CONDITIONING-2026-09-11.json",
    "canonical/kdenlive-audio-conditioning-enforcement.json",
    "src/fa3_silero_vad_provider.py",
    "src/fa3_kdenlive_audio_pipeline.py",
]


def load_json(rel: str):
    with (ROOT / rel).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")

    if not errors:
        contract = load_json(REQUIRED_FILES[0])
        silero = load_json(REQUIRED_FILES[1])
        decision = load_json(REQUIRED_FILES[2])
        enforcement = load_json(REQUIRED_FILES[3])

        checks = {
            "capability_count": silero.get("capability_count") == 143 and enforcement.get("capability_count") == 143,
            "authority_delta": contract.get("architectural_authority_delta") == 0 and enforcement.get("architectural_authority_delta") == 0,
            "vad_metadata_only": contract["speech_activity_map"].get("metadata_only") is True and silero["output_contract"].get("metadata_only") is True,
            "vad_no_master_mutation": contract["speech_activity_map"].get("master_audio_mutation_forbidden") is True,
            "demucs_conditional": "demucs_if_required" in contract["default_paths"]["mixed_dialogue_restore"],
            "double_denoise_guard": "NO_IMPLICIT_DOUBLE_DENOISE" in contract["processing_invariants"],
            "xml_mutation_forbidden": "DIRECT_KDENLIVE_PROJECT_XML_MUTATION_FORBIDDEN" in contract["processing_invariants"],
            "source_mutation_forbidden": contract["request_contract"].get("source_in_place_mutation_forbidden") is True,
            "production_pending": decision["production_promotion"].get("state") == "PENDING_CURRENT_HOST",
            "fail_closed": enforcement.get("fail_closed") is True,
            "rule_count": len(enforcement.get("rules", [])) >= 30,
        }
        errors.extend(name for name, ok in checks.items() if not ok)

    report = {
        "gate": "FA3-GATE-KDENLIVE-AUDIO-CONDITIONING-001",
        "status": "PASS" if not errors else "FAIL",
        "production_promotion": "PENDING_CURRENT_HOST",
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
