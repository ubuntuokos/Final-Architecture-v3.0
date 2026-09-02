#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CAPS = 143
PROFILE_ID = "FA3-VOICE-001"
CONTRACT_ID = "FA3-VOICE-CONTRACTS-001"
ADMISSION_ID = "FA3-VOICE-PROVIDER-ADMISSION-001"
DECISION_ID = "FA3-DEC-VOICE-SYNTHESIS-PORTFOLIO-2026-09-01"
GATE_ID = "FA3-VOICE-SYNTHESIS-GATESET-001"
EVIDENCE_PATH = "evidence/reference/voice-synthesis-ci-2026-09-01.json"
PROVIDER_IDS = (
    "FA3-PROVIDER-VOXCPM-001",
    "FA3-PROVIDER-XTTS-001",
    "FA3-PROVIDER-PIPER-001",
    "FA3-PROVIDER-QWEN3-TTS-001",
    "FA3-PROVIDER-MMS-TTS-HUN-001",
)
CAPABILITY_IDS = ("CAP-115", "CAP-116", "CAP-117")
CLONING_MODES = {"zero_shot", "cross_lingual", "voice_clone", "controllable_clone", "ultimate_clone", "instruct2"}


class VoicePolicyDenied(RuntimeError):
    pass


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_locale(value: str) -> str:
    locale = value.strip().replace("_", "-").lower()
    if locale in {"hu", "hu-hu"}:
        return "hu-HU"
    if not locale:
        raise VoicePolicyDenied("language/locale is required")
    return locale


def resolve_route(request: dict[str, Any], admitted: set[str]) -> dict[str, Any]:
    locale = normalize_locale(str(request.get("language", "")))
    mode = str(request.get("mode", "")).strip()
    if not mode:
        raise VoicePolicyDenied("mode is required")
    if locale != "hu-HU":
        raise VoicePolicyDenied("reference router only materializes the canonical hu-HU policy")
    if mode in CLONING_MODES:
        candidates = ["FA3-PROVIDER-XTTS-001"]
    elif mode in {"plain", "preset_voice", "voice_design"}:
        candidates = ["FA3-PROVIDER-XTTS-001", "FA3-PROVIDER-PIPER-001"]
    else:
        raise VoicePolicyDenied(f"unsupported synthesis mode: {mode}")
    selected = next((item for item in candidates if item in admitted), None)
    if not selected:
        raise VoicePolicyDenied("no production-admitted Hungarian provider for requested capability")
    return {
        "schema": "fa3.voice-provider-decision-receipt.v1",
        "selected_provider_id": selected,
        "language_status": "HU_PROVIDER_CAPABILITY_MATCH",
        "fallback_chain": candidates,
        "silent_fallback": False,
    }


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def run_conformance(root: Path) -> dict[str, Any]:
    paths = {
        "profile": root / "canonical/profiles/FA3-VOICE-001.json",
        "contract": root / "canonical/contracts/FA3-VOICE-CONTRACTS-001.json",
        "admission": root / "canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-VOICE-SYNTHESIS-PORTFOLIO-2026-09-01.json",
        "reference": root / "canonical/references/FA3-VOICE-SYNTHESIS-UPSTREAM-REFERENCE-2026-09-01.json",
        "enforcement": root / "canonical/voice-synthesis-enforcement.json",
        "evidence": root / EVIDENCE_PATH,
        "policy": root / "canonical/enforcement-policy.json",
        "registry": root / "evidence/evidence-registry.json",
    }
    for provider_id in PROVIDER_IDS:
        paths[provider_id] = root / f"canonical/providers/{provider_id}.json"
    missing = [str(path.relative_to(root)) for path in paths.values() if not path.is_file()]
    if missing:
        return {"result": "FAIL", "passed": 0, "total": 32, "cases": [], "findings": [_finding("VOICE-ARTIFACTS", "Voice synthesis artifacts missing", missing=missing)]}

    objs = {name: loadj(path) for name, path in paths.items()}
    profile, contract = objs["profile"], objs["contract"]
    admission, decision = objs["admission"], objs["decision"]
    reference, enforcement = objs["reference"], objs["enforcement"]
    evidence, policy, registry = objs["evidence"], objs["policy"], objs["registry"]
    providers = {provider_id: objs[provider_id] for provider_id in PROVIDER_IDS}
    rules = {item.get("name") for item in enforcement.get("rules", [])}
    checks: list[dict[str, Any]] = []

    def check(case_id: str, condition: bool, detail: str) -> None:
        checks.append({"id": case_id, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("VOICE-001", profile.get("id") == PROFILE_ID and contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True, "profile/contract identity and provider-neutral boundary")
    check("VOICE-002", all(p.get("architectural_authority") is False and p.get("canonical_root") is False for p in providers.values()), "providers are not authorities or roots")
    check("VOICE-003", profile.get("capability_count") == CAPS and decision.get("capability_count_after") == CAPS and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0, "143-capability and zero-authority invariant")
    pins = reference.get("immutable_snapshots", {})
    check("VOICE-004", pins.get("voxcpm_runtime", {}).get("commit") == "f5a1c6a6b901bc732e20f0d59a369f6829ad717a" and pins.get("xtts_v2_model", {}).get("revision") == "6c2b0d75eae4b7047358e3b6bd9325f857d43f77" and reference.get("floating_main_allowed_for_promotion_evidence") is False, "immutable upstream/model pins")
    check("VOICE-005", admission.get("policy") == "ALLOWLIST_AND_CAPABILITY_EVIDENCE_ONLY_FAIL_CLOSED" and admission.get("arbitrary_local_checkpoint_paths_allowed") is False, "allowlist-only model admission")
    check("VOICE-006", admission.get("runtime_network_fetch_allowed") is False and admission.get("bootstrap_download_requires_explicit_authorization") is True, "no runtime network fetch")
    check("VOICE-007", admission.get("direct_application_or_comfyui_venv_install_allowed") is False and providers["FA3-PROVIDER-XTTS-001"].get("runtime", {}).get("isolated_environment_required") is True, "isolated provider environments")
    check("VOICE-008", "VOICE_CENTRAL_GATEWAY_MEDIATION" in rules, "central gateway mediation")
    check("VOICE-009", "VOICE_HRB_ACCELERATOR_ADMISSION" in rules, "HRB accelerator admission")
    check("VOICE-010", "VOICE_NO_SILENT_PROVIDER_MODEL_DEVICE_CLOUD_FALLBACK" in rules and admission.get("routing", {}).get("hu-HU", {}).get("forbidden_silent_fallbacks"), "explicit fail-closed fallback")
    check("VOICE-011", profile.get("hungarian_baseline", {}).get("locale") == "hu-HU", "explicit Hungarian baseline")
    check("VOICE-012", profile.get("hungarian_baseline", {}).get("voice_cloning_primary_candidate") == "FA3-PROVIDER-XTTS-001" and "hu" in providers["FA3-PROVIDER-XTTS-001"].get("model", {}).get("official_languages", []), "XTTS Hungarian cloning candidate")
    check("VOICE-013", profile.get("hungarian_baseline", {}).get("lightweight_cpu_fallback_candidate") == "FA3-PROVIDER-PIPER-001" and str(providers["FA3-PROVIDER-PIPER-001"].get("routing_policy", {}).get("hu_voice_cloning", "")).startswith("UNSUPPORTED"), "Piper CPU fallback and no cloning")
    check("VOICE-014", providers["FA3-PROVIDER-VOXCPM-001"].get("language_policy", {}).get("hu") == "UNSUPPORTED_FAIL_CLOSED", "VoxCPM2 Hungarian denial")
    check("VOICE-015", providers["FA3-PROVIDER-QWEN3-TTS-001"].get("language_policy", {}).get("hu") == "UNSUPPORTED_FAIL_CLOSED", "Qwen3-TTS Hungarian denial")
    check("VOICE-016", admission.get("providers", {}).get("FA3-PROVIDER-COSYVOICE-001", {}).get("hu_plain_tts") == "EXPERIMENTAL", "CosyVoice Hungarian remains experimental")
    check("VOICE-017", providers["FA3-PROVIDER-MMS-TTS-HUN-001"].get("routing_policy", {}).get("production") == "DENY" and providers["FA3-PROVIDER-MMS-TTS-HUN-001"].get("model", {}).get("license") == "CC-BY-NC-4.0", "MMS Hungarian production denied")
    license_required = contract.get("contracts", {}).get("license_and_rights", {}).get("required", [])
    check("VOICE-018", set(admission.get("license_dimensions", [])) == set(license_required), "separate license dimensions")
    check("VOICE-019", providers["FA3-PROVIDER-XTTS-001"].get("model", {}).get("license_acceptance_required") is True and "VOICE_LICENSE_ACCEPTANCE_AUDITABLE" in rules, "auditable model-license acceptance")
    consent_rules = contract.get("contracts", {}).get("consent", {}).get("rules", [])
    check("VOICE-020", any("VOICE_CLONING" in item for item in consent_rules), "typed cloning consent scope")
    check("VOICE-021", any("expired or revoked" in item for item in consent_rules), "consent expiry/revocation")
    reference_rules = contract.get("contracts", {}).get("reference", {}).get("rules", [])
    check("VOICE-022", any("transcript digest" in item for item in reference_rules) and any("audio_sha256" in item for item in reference_rules), "reference audio/transcript hashes")
    check("VOICE-023", "retention_policy_ref" in contract.get("contracts", {}).get("reference", {}).get("required", []), "reference retention/deletion policy")
    check("VOICE-024", contract.get("security", {}).get("voice_design_requires_synthetic_disclosure") is True and contract.get("security", {}).get("impersonation_fraud_and_disinformation_use_forbidden") is True, "synthetic disclosure and misuse policy")
    quality = contract.get("contracts", {}).get("quality", {})
    check("VOICE-025", {"numbers", "dates", "abbreviations", "currency", "diacritics", "long-form chunk boundaries"}.issubset(set(quality.get("hungarian_minimum", []))), "Hungarian normalization corpus")
    check("VOICE-026", profile.get("promotion", {}).get("hungarian_golden_corpus_required") is True and "speaker_similarity_if_cloned" in quality.get("required", []), "Hungarian quality gate")
    audio = contract.get("contracts", {}).get("result", {}).get("audio_contract", {})
    check("VOICE-027", any("native-rate master" in item for item in contract.get("contracts", {}).get("result", {}).get("rules", [])), "native master preservation")
    check("VOICE-028", audio.get("media_mezzanine", {}).get("sample_rate_hz") == 48000 and audio.get("resample_requires_derived_artifact_lineage") is True, "48 kHz media mezzanine lineage")
    check("VOICE-029", "VOICE_STREAMING_NOT_SESSION_AUTHORITY" in rules, "streaming is not session authority")
    check("VOICE-030", "VOICE_EVIDENCE_COMPLETE" in rules, "complete voice execution evidence")
    check("VOICE-031", evidence.get("result") == "PASS" and evidence.get("current_host_production_claim") is False and evidence.get("hungarian_quality_claim") is False, "CI PASS does not claim current-host or Hungarian quality")
    bound = []
    for capability_id in CAPABILITY_IDS:
        item = next((entry for entry in registry.get("records", []) if entry.get("subject_id") == capability_id), {})
        bound.append(DECISION_ID in item.get("source_decision_ids", []) and EVIDENCE_PATH in item.get("evidence_artifacts", []) and item.get("status") == "PENDING_CURRENT_HOST")
    check("VOICE-032", GATE_ID in policy.get("mandatory_reference_gates", []) and all(bound) and admission.get("new_capabilities") == 0, "mandatory gate, evidence bindings and disabled-provider nonblocking invariant")

    passed = sum(item["result"] == "PASS" for item in checks)
    return {"schema": "fa3.voice-synthesis-gate-report.v1", "gate_id": GATE_ID, "profile_id": PROFILE_ID, "result": "PASS" if passed == len(checks) == 32 else "FAIL", "passed": passed, "total": len(checks), "cases": checks, "current_host_status": "PENDING_REAL_HOST_EXECUTION", "current_host_production_claim": False, "hungarian_quality_claim": False}


def gate(root: Path) -> dict[str, Any]:
    report = run_conformance(root.resolve())
    writej(root.resolve() / "reports/voice-synthesis-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
