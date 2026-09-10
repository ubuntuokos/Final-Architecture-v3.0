#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from fa3_kdenlive_audio_conditioning import build_execution_plan, validate_editorial_labels, AudioConditioningPolicyError
from fa3_silero_vad_provider import reference_policy_conformance

PATHS = {
    "kdenlive_profile": "canonical/profiles/FA3-KDENLIVE-EDITORIAL-001.json",
    "speech_contract": "canonical/contracts/FA3-SPEECH-ENHANCEMENT-CONTRACTS-001.json",
    "gtcrn_provider": "canonical/providers/FA3-PROVIDER-GTCRN-001.json",
    "lavasr_provider": "canonical/providers/FA3-PROVIDER-LAVASR-001.json",
    "demucs_provider": "canonical/providers/FA3-PROVIDER-DEMUCS-001.json",
    "contract": "canonical/contracts/FA3-KDENLIVE-AUDIO-CONDITIONING-CONTRACTS-001.json",
    "silero_provider": "canonical/providers/FA3-PROVIDER-SILERO-VAD-001.json",
    "silero_reference": "canonical/references/FA3-SILERO-VAD-UPSTREAM-REFERENCE-2026-09-10.json",
    "silero_allowlist": "canonical/FA3-SILERO-VAD-MODEL-ALLOWLIST-001.json",
    "silero_runtime": "canonical/FA3-SILERO-VAD-RUNTIME-CONFORMANCE-001.json",
    "decision": "canonical/decisions/FA3-DEC-KDENLIVE-AUDIO-CONDITIONING-2026-09-10.json",
    "gate": "canonical/FA3-GATE-KDENLIVE-AUDIO-CONDITIONING-001.json",
    "enforcement": "canonical/kdenlive-audio-conditioning-enforcement.json",
}
EXPECTED_RULE_COUNT = 32


def load(root: Path, key: str) -> dict:
    return json.loads((root / PATHS[key]).read_text(encoding="utf-8"))


def finding(code: str, message: str) -> dict:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict:
    root = Path(root)
    missing = [rel for rel in PATHS.values() if not (root / rel).is_file()]
    if missing:
        return {
            "schema": "fa3.kdenlive-audio-conditioning-gate-report.v1",
            "gate_set_id": "FA3-KDENLIVE-AUDIO-CONDITIONING-GATESET-001",
            "result": "FAIL",
            "blocking_findings": len(missing),
            "findings": [finding("KAC-000", f"missing {rel}") for rel in missing],
        }

    k = load(root, "kdenlive_profile")
    s = load(root, "speech_contract")
    g = load(root, "gtcrn_provider")
    l = load(root, "lavasr_provider")
    d = load(root, "demucs_provider")
    c = load(root, "contract")
    v = load(root, "silero_provider")
    r = load(root, "silero_reference")
    a = load(root, "silero_allowlist")
    rt = load(root, "silero_runtime")
    dec = load(root, "decision")
    gr = load(root, "gate")
    e = load(root, "enforcement")

    checks = [
        ("KAC-001", k.get("id") == "FA3-KDENLIVE-EDITORIAL-001", "Kdenlive canonical profile mismatch"),
        ("KAC-002", k.get("new_capability") is False and k.get("new_architectural_authority") is False, "Kdenlive authority invariant failed"),
        ("KAC-003", k.get("project_mutation_policy") == "NO_EXTERNAL_DIRECT_KDENLIVE_XML_MUTATION", "direct Kdenlive XML mutation protection drift"),
        ("KAC-004", c.get("provider_neutral") is True, "conditioning contract must be provider-neutral"),
        ("KAC-005", c.get("new_capability") is False and c.get("new_architectural_authority") is False and c.get("capability_count") == 143, "conditioning baseline invariant failed"),
        ("KAC-006", c.get("media_preparation", {}).get("native_master_immutable") is True, "native master immutability missing"),
        ("KAC-007", c.get("media_preparation", {}).get("analysis_projection", {}).get("sample_rate_hz") == 16000 and c.get("media_preparation", {}).get("analysis_projection", {}).get("channels") == 1, "16 kHz mono analysis projection required"),
        ("KAC-008", c.get("speech_activity", {}).get("metadata_only") is True and c.get("speech_activity", {}).get("master_audio_mutation") is False, "VAD must remain metadata-only"),
        ("KAC-009", c.get("routing", {}).get("source_separation_conditional_only") is True and c.get("routing", {}).get("pipeline_must_work_without_source_separation") is True, "source separation must remain optional/conditional"),
        ("KAC-010", c.get("denoise_policy", {}).get("implicit_double_denoise") is False, "implicit double denoise must be forbidden"),
        ("KAC-011", c.get("execution", {}).get("accelerator_requires_hrb_receipt") is True, "HRB accelerator admission missing"),
        ("KAC-012", c.get("execution", {}).get("subprocess_policy") == "ARGV_SHELL_FALSE_ONLY", "shell=False argv policy missing"),
        ("KAC-013", c.get("request", {}).get("provider_names_in_editorial_preset_surface") is False, "provider-neutral editorial surface required"),
        ("KAC-014", c.get("media_preparation", {}).get("final_editorial_mezzanine", {}).get("sample_rate_hz") == 48000, "48 kHz editorial mezzanine required"),
        ("KAC-015", c.get("delegates_transcription_to") == "FA3-STT-MEDIA-001", "transcription must delegate to existing media STT profile"),
        ("KAC-016", v.get("id") == "FA3-PROVIDER-SILERO-VAD-001", "Silero provider id mismatch"),
        ("KAC-017", v.get("upstream", {}).get("revision") == "867c2aa692646a1f1de3e94a15c9dd9f614c0acb", "Silero upstream pin drift"),
        ("KAC-018", v.get("upstream", {}).get("license") == "MIT", "Silero license reference drift"),
        ("KAC-019", v.get("runtime", {}).get("kdenlive_default_analysis_sample_rate_hz") == 16000 and v.get("runtime", {}).get("channels") == [1], "Silero Kdenlive analysis format drift"),
        ("KAC-020", v.get("output_policy", {}).get("metadata_only") is True and v.get("output_policy", {}).get("master_audio_mutation") is False, "Silero provider must be metadata-only"),
        ("KAC-021", all(not value for value in v.get("authority_boundaries", {}).values()), "Silero provider claimed architectural authority"),
        ("KAC-022", r.get("revision") == v.get("upstream", {}).get("revision"), "Silero reference/provider pin mismatch"),
        ("KAC-023", a.get("runtime_auto_download") is False and a.get("sha256_required") is True, "Silero model admission policy incomplete"),
        ("KAC-024", rt.get("status") == "PENDING_CURRENT_HOST" and rt.get("production_admitted") is False, "Silero current-host runtime must remain pending"),
        ("KAC-025", g.get("runtime", {}).get("sample_rate_hz") == 16000 and g.get("runtime", {}).get("channels") == [1], "GTCRN 16 kHz mono contract drift"),
        ("KAC-026", l.get("runtime", {}).get("output_sample_rate_hz") == 48000 and l.get("runtime", {}).get("default_denoise") is False, "LavaSR 48 kHz/default-denoise contract drift"),
        ("KAC-027", d.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT", "Demucs must remain optional"),
        ("KAC-028", s.get("adapter_boundaries", {}).get("daw_nle_input_conditioning") == "ALLOWED_PROJECTION", "speech enhancement NLE projection missing"),
        ("KAC-029", s.get("execution_provider", {}).get("accelerator_requires_hrb_admission") is True, "speech enhancement HRB rule drift"),
        ("KAC-030", dec.get("baseline_effect", {}).get("new_profile") == 0 and dec.get("baseline_effect", {}).get("capability_count_after") == 143, "decision created a new profile/capability"),
        ("KAC-031", gr.get("fail_closed") is True and gr.get("rule_count") == EXPECTED_RULE_COUNT, "gate record drift"),
        ("KAC-032", e.get("fail_closed") is True and e.get("rule_count") == EXPECTED_RULE_COUNT and len(e.get("rules", [])) == EXPECTED_RULE_COUNT, "enforcement rule inventory drift"),
    ]

    findings = [finding(code, message) for code, ok, message in checks if not ok]

    try:
        validate_editorial_labels()
        clean = build_execution_plan({
            "request_id": "gate-clean",
            "source_artifact_ref": "sha256:source",
            "output_artifact_ref": "sha256:derived",
            "preset": "clean-dialogue",
            "restoration_denoise": False,
        })
        mixed = build_execution_plan({
            "request_id": "gate-mixed",
            "source_artifact_ref": "sha256:source",
            "output_artifact_ref": "sha256:derived",
            "preset": "mixed-dialogue",
            "restoration_denoise": False,
        })
        try:
            build_execution_plan({
                "request_id": "gate-negative",
                "source_artifact_ref": "sha256:source",
                "output_artifact_ref": "sha256:derived",
                "preset": "clean-dialogue",
                "restoration_denoise": True,
            })
            findings.append(finding("KAC-EXEC-001", "double-denoise negative regression did not fail closed"))
        except AudioConditioningPolicyError:
            pass
        executable = {
            "result": "PASS",
            "clean_plan": clean,
            "mixed_plan": mixed,
            "silero_policy": reference_policy_conformance(),
        }
    except Exception as exc:
        executable = {"result": "FAIL", "error": str(exc)}
        findings.append(finding("KAC-EXEC-000", f"reference executable conformance failed: {exc}"))

    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.kdenlive-audio-conditioning-gate-report.v1",
        "gate_set_id": "FA3-KDENLIVE-AUDIO-CONDITIONING-GATESET-001",
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "rules_checked": EXPECTED_RULE_COUNT,
        "reference_executable_conformance": executable,
        "current_host_runtime_status": "PENDING_CURRENT_HOST",
        "production_promotion_claimed": False,
    }
    out = root / "reports/kdenlive-audio-conditioning-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    report = gate(repo)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["result"] == "PASS" else 2)
