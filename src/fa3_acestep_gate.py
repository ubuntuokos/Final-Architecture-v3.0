#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-ACE-STEP-001"
PROFILE_ID = "FA3-MUSIC-001"
CONTRACT_ID = "FA3-MUSIC-GENERATION-CONTRACTS-001"
GATE_ID = "FA3-ACE-STEP-GATESET-001"
CAPABILITY_COUNT = 143
LATEST_FORMAL_RELEASE = "v0.1.8"
OBSERVED_MAIN = "ca1e85fe9430179831e6bc6be790c332190a3866"

P0_INVARIANTS = [
    "ACE_STEP_IS_NOT_ARCHITECTURAL_AUTHORITY",
    "PROVIDER_NEUTRAL_MUSIC_CONTRACT",
    "IMMUTABLE_RUNTIME_AND_MODEL_IDENTITY",
    "HRB_ADMISSION_REQUIRED_FOR_ACCELERATOR",
    "REQUESTED_MODEL_MUST_EQUAL_EXECUTED_MODEL_OR_FAIL_CLOSED",
    "TYPED_AUTHENTICATED_LOOPBACK_REST_ADAPTER_REQUIRED",
    "GRADIO_IS_NOT_AUTOMATION_OR_ORCHESTRATION_AUTHORITY",
    "TEXT2MUSIC_STATE_HYGIENE_REQUIRED",
    "NON_TURBO_DCW_MUST_BE_EXPLICIT_AND_QUALITY_GATED",
    "SFT_AND_XL_SFT_REQUIRE_EXPLICIT_CURRENT_HOST_QUALITY_PROMOTION",
    "REINIT_KV_CACHE_MUST_BE_INVARIANT",
    "LM_REINIT_REQUIRES_CLEAN_TEARDOWN_OR_PROCESS_RECYCLE",
    "PROVIDER_VRAM_PREFLIGHT_CANNOT_REPLACE_HRB_ADMISSION",
    "LOSSLESS_MASTER_REQUIRED",
    "PRODUCTION_AUTO_UPDATE_AND_MODEL_AUTO_DOWNLOAD_FORBIDDEN",
    "UPSTREAM_MERGE_IS_NOT_CURRENT_HOST_PROMOTION_EVIDENCE",
    "CUDA_CAPABILITY_PROBE_FAILURE_MUST_NOT_CORRUPT_FALLBACK_CONTROL_FLOW",
    "EXPLICIT_CUDA_DTYPE_OVERRIDE_VALIDATED_AND_PROVENANCE_BEARING",
    "NAN_INF_LATENTS_OR_AUDIO_FAIL_CLOSED",
    "CPU_OFFLOAD_DEVICE_DTYPE_COHERENCE_REQUIRED",
    "OFFLOAD_PLUS_LORA_VALIDATION_MUST_NOT_BE_SILENTLY_SKIPPED",
    "OPEN_UPSTREAM_FIX_OR_RISK_PR_NOT_PROMOTION_EVIDENCE",
]

MERGED_FIXES = {
    "PR-1282": "2c513f9e3ba8354eebe6d5698d41025acb43cd7b",
    "PR-1305": "c86889f488b657c176d1ca857df3450ad1c495d2",
    "PR-1310": "0b5ff8acc553fc037dc3f6db31631c1c30df3e99",
}
OPEN_UPSTREAM = {
    "PR-1309": ("OPEN_FIX_CANDIDATE_NOT_PROMOTION_EVIDENCE", "86cf3a2be6dafd2b5bd2ece6471a9a227dc6d1d9"),
    "PR-1311": ("OPEN_FIX_CANDIDATE_NOT_PROMOTION_EVIDENCE", "49354c10929b94f75e22268357ee96ada20932e2"),
    "PR-1312": ("OPEN_FIX_CANDIDATE_NOT_PROMOTION_EVIDENCE", "f25fa4015b08840f01a8e9696828120f425b63ab"),
    "PR-1319": ("OPEN_UNRESOLVED_RISK_NOT_PROMOTION_EVIDENCE", "ed6e6fdc02655ef62effc8ef154d2f1f7876217a"),
    "PR-1321": ("OPEN_FIX_CANDIDATE_NOT_PROMOTION_EVIDENCE", "33e2d60145ad7ac6d1645a51fa833aeb8d037973"),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def immutable_runtime_pin_valid(ref: str, *, floating: bool, auto_update: bool, auto_download: bool) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")) and not floating and not auto_update and not auto_download


def hrb_admission_valid(*, accelerator: bool, hrb_lease: str | None, provider_self_placed: bool) -> bool:
    if provider_self_placed:
        return False
    return (not accelerator) or bool(hrb_lease)


def requested_model_identity_valid(requested: str, executed: str, *, silent_fallback: bool) -> bool:
    return bool(requested and executed and requested == executed and not silent_fallback)


def api_boundary_valid(*, bind_address: str, authenticated: bool, central_gateway: bool) -> bool:
    return bind_address in {"127.0.0.1", "::1", "localhost"} and authenticated and central_gateway


def text2music_state_hygiene_valid(task_type: str, audio_cover_strength: float, cover_noise_strength: float) -> bool:
    if task_type != "text2music":
        return True
    return abs(audio_cover_strength - 1.0) < 1e-9 and abs(cover_noise_strength) < 1e-9


def non_turbo_dcw_valid(model_family: str, dcw_enabled: bool | None) -> bool:
    if model_family in {"sft_2b", "xl_sft", "base_2b", "xl_base"}:
        return dcw_enabled is False
    return dcw_enabled in {True, False, None}


def sft_promotion_valid(*, dcw_off_pass: bool, quality_pass: bool, negative_regression_pass: bool) -> bool:
    return bool(dcw_off_pass and quality_pass and negative_regression_pass)


def kv_cache_invariance_valid(first_gb: float, second_gb: float, *, tolerance_ratio: float = 0.05) -> bool:
    if first_gb <= 0 or second_gb <= 0:
        return False
    return abs(second_gb - first_gb) <= max(0.05, first_gb * tolerance_ratio)


def lm_reinit_policy_valid(*, in_process_reinit: bool, clean_teardown_pass: bool, process_recycle: bool) -> bool:
    if not in_process_reinit:
        return True
    return bool(clean_teardown_pass or process_recycle)


def cuda_probe_fallback_valid(*, probe_failed: bool, handler_completed: bool, observable: bool, deterministic_fallback: bool) -> bool:
    if not probe_failed:
        return True
    return bool(handler_completed and observable and deterministic_fallback)


def precision_override_valid(*, requested: str | None, hardware_supported: bool, provenance_recorded: bool) -> bool:
    if requested is None:
        return provenance_recorded
    allowed = {"float32", "float16", "bfloat16"}
    return requested.strip().lower() in allowed and hardware_supported and provenance_recorded


def numeric_integrity_valid(*, latent_nan: int, latent_inf: int, audio_nan: int, audio_inf: int) -> bool:
    return all(x == 0 for x in (latent_nan, latent_inf, audio_nan, audio_inf))


def offload_device_dtype_coherence_valid(*, cpu_offload: bool, device_match: bool, dtype_match: bool) -> bool:
    if not cpu_offload:
        return True
    return bool(device_match and dtype_match)


def lora_offload_validation_valid(*, cpu_offload: bool, lora_enabled: bool, consistency_checked: bool, equivalent_guard: bool, mismatch_fail_closed: bool) -> bool:
    if not (cpu_offload and lora_enabled):
        return True
    return bool((consistency_checked or equivalent_guard) and mismatch_fail_closed)


def open_pr_promotion_valid(*, pr_open: bool, used_as_promotion_evidence: bool) -> bool:
    return not (pr_open and used_as_promotion_evidence)


def lossless_master_valid(fmt: str) -> bool:
    return fmt.lower() in {"wav", "flac"}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-MUSIC-001.json",
        "contracts": root / "canonical/contracts/FA3-MUSIC-GENERATION-CONTRACTS-001.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-ACE-STEP-001.json",
        "base_decision": root / "canonical/decisions/FA3-DEC-ACE-STEP-2026-08-30.json",
        "hardening_decision": root / "canonical/decisions/FA3-DEC-ACE-STEP-HARDENING-2026-09-10.json",
        "enforcement": root / "canonical/ace-step-enforcement.json",
        "base_reference": root / "evidence/reference/ace-step-2026-08-30.json",
        "current_reference": root / "evidence/reference/ace-step-upstream-2026-09-10.json",
    }
    for idx, path in enumerate(paths.values(), 1):
        if not path.exists():
            findings.append(_finding(f"ACESTEP-REF-{idx:03d}", f"Missing ACE-Step canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile = _load(paths["profile"])
    contracts = _load(paths["contracts"])
    provider = _load(paths["provider"])
    base_decision = _load(paths["base_decision"])
    hardening = _load(paths["hardening_decision"])
    enforcement = _load(paths["enforcement"])
    base_reference = _load(paths["base_reference"])
    current_reference = _load(paths["current_reference"])

    if profile.get("id") != PROFILE_ID or profile.get("status") != "CANONICAL":
        findings.append(_finding("ACESTEP-REF-010", "FA3-MUSIC-001 identity/status drift"))
    if profile.get("capabilities") != ["CAP-017", "CAP-066", "CAP-131"]:
        findings.append(_finding("ACESTEP-REF-011", "ACE-Step music capability projection drift"))
    if any(profile.get(k) is not False for k in ("canonical_root", "new_capability", "new_architectural_authority")):
        findings.append(_finding("ACESTEP-REF-012", "Music profile changed root/capability/authority invariant"))
    if profile.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("ACESTEP-REF-013", "Music profile capability count drift"))

    if contracts.get("id") != CONTRACT_ID or contracts.get("provider_neutral") is not True:
        findings.append(_finding("ACESTEP-REF-014", "Music contract set identity/provider-neutral invariant failed"))
    required_rules = (
        "requested_model_must_equal_executed_model_or_fail_closed",
        "accelerator_execution_requires_host_resource_broker_lease",
        "automation_must_use_typed_authenticated_adapter",
        "generation_mode_state_must_be_scoped_and_reset",
        "cuda_capability_probe_failure_path_must_be_deterministic_and_observable",
        "invalid_or_unsupported_precision_override_must_fail_closed",
        "non_finite_latent_or_audio_must_fail_closed",
        "cpu_offload_device_dtype_coherence_required",
        "lora_cpu_offload_consistency_validation_cannot_be_silently_skipped",
        "production_auto_update_forbidden",
        "production_model_auto_download_forbidden",
        "lossless_master_required",
        "sft_family_requires_explicit_quality_promotion",
    )
    for key in required_rules:
        if contracts.get("rules", {}).get(key) is not True:
            findings.append(_finding("ACESTEP-REF-015", f"Required ACE-Step contract rule disabled: {key}"))

    if provider.get("id") != PROVIDER_ID or provider.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("ACESTEP-REF-016", "ACE-Step provider identity/capability count mismatch"))
    if any(provider.get(k) is not False for k in ("canonical_root", "architectural_authority", "new_capability", "device_selection_authority", "model_routing_authority", "orchestration_authority")):
        findings.append(_finding("ACESTEP-REF-017", "ACE-Step was promoted to forbidden authority/root/capability"))
    if provider.get("global_runtime_promotion_required") is not True:
        findings.append(_finding("ACESTEP-REF-018", "Required ACE-Step runtime was detached from global promotion"))
    if provider.get("implementation_status") != "CANONICAL_REQUIRED_PROVIDER_NOT_CURRENT_HOST_PROMOTED":
        findings.append(_finding("ACESTEP-REF-019", "ACE-Step current-host promotion state drift"))
    policy = provider.get("production_policy", {})
    for key in (
        "cuda_capability_probe_failure_must_be_observable_and_control_flow_safe",
        "unsupported_precision_override_fail_closed",
        "precision_is_provenance_bearing",
        "non_finite_latent_or_audio_fail_closed",
        "cpu_offload_device_dtype_coherence_required",
        "lora_cpu_offload_validation_skip_forbidden_without_equivalent_guard",
        "open_upstream_pr_not_promotion_evidence",
    ):
        if policy.get(key) is not True:
            findings.append(_finding("ACESTEP-REF-020", f"ACE-Step production hardening policy disabled: {key}"))

    if base_decision.get("status") != "CANONICAL_CLOSED":
        findings.append(_finding("ACESTEP-REF-021", "ACE-Step base decision is not canonically closed"))
    if hardening.get("status") != "CANONICAL_CLOSED" or hardening.get("decision") != "NO_BASELINE_SEMANTIC_CHANGE_IMPLEMENTATION_PROJECTION_HARDENING":
        findings.append(_finding("ACESTEP-REF-022", "ACE-Step September hardening decision is not canonically closed"))
    if hardening.get("new_capabilities") != 0 or hardening.get("new_architectural_authorities") != 0 or hardening.get("capability_count_after") != CAPABILITY_COUNT:
        findings.append(_finding("ACESTEP-REF-023", "ACE-Step hardening decision changed capability/authority invariant"))

    if enforcement.get("gate_id") != GATE_ID or enforcement.get("provider_id") != PROVIDER_ID or enforcement.get("profile_id") != PROFILE_ID:
        findings.append(_finding("ACESTEP-REF-024", "ACE-Step gate/provider/profile identity mismatch"))
    if enforcement.get("p0_invariants") != P0_INVARIANTS:
        findings.append(_finding("ACESTEP-REF-025", "ACE-Step P0 invariant set drift"))
    if enforcement.get("fail_closed") is not True or enforcement.get("floating_main_allowed_as_promotion_evidence") is not False:
        findings.append(_finding("ACESTEP-REF-026", "ACE-Step fail-closed/immutable-reference policy drift"))
    if enforcement.get("runtime_provider_required_for_global_promotion") is not True:
        findings.append(_finding("ACESTEP-REF-027", "ACE-Step runtime no longer required for global promotion"))

    tracked = enforcement.get("tracked_upstream_fixes", {})
    for pr, sha in MERGED_FIXES.items():
        item = tracked.get(pr, {})
        if item.get("state") != "MERGED_FIX_CANDIDATE" or item.get("merge_commit") != sha:
            findings.append(_finding("ACESTEP-REF-028", f"Tracked merged upstream fix drift: {pr}"))
    for pr, (state, head) in OPEN_UPSTREAM.items():
        item = tracked.get(pr, {})
        if item.get("state") != state or item.get("head_commit") != head:
            findings.append(_finding("ACESTEP-REF-029", f"Tracked open upstream disposition drift: {pr}"))

    if base_reference.get("latest_formal_release", {}).get("tag") != LATEST_FORMAL_RELEASE:
        findings.append(_finding("ACESTEP-REF-030", "Historical ACE-Step release reference drift"))
    if current_reference.get("latest_formal_release", {}).get("tag") != LATEST_FORMAL_RELEASE:
        findings.append(_finding("ACESTEP-REF-031", "Current ACE-Step release reference drift"))
    if current_reference.get("observed_main_commit", {}).get("sha") != OBSERVED_MAIN:
        findings.append(_finding("ACESTEP-REF-032", "Current ACE-Step main observation drift"))
    if current_reference.get("floating_main_allowed") is not False or current_reference.get("open_pr_as_promotion_evidence_allowed") is not False or current_reference.get("current_host_evidence_claimed") is not False:
        findings.append(_finding("ACESTEP-REF-033", "Current upstream reference incorrectly authorizes promotion"))
    observed_open = {f"PR-{x.get('pr')}": (x.get("disposition"), x.get("head_commit")) for x in current_reference.get("open_upstream", [])}
    if observed_open != OPEN_UPSTREAM:
        findings.append(_finding("ACESTEP-REF-034", "Open upstream reference set drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add(rule_id: str, name: str, positive: bool, negative: bool) -> None:
        cases.append({
            "rule_id": rule_id,
            "name": name,
            "status": "PASS" if positive and negative else "FAIL",
            "positive_case": positive,
            "negative_case": negative,
        })

    add("FA3-ACE-P0-003", "immutable runtime/model pin",
        immutable_runtime_pin_valid(MERGED_FIXES["PR-1310"], floating=False, auto_update=False, auto_download=False),
        not immutable_runtime_pin_valid("main", floating=True, auto_update=True, auto_download=True))
    add("FA3-ACE-P0-004", "HRB accelerator admission",
        hrb_admission_valid(accelerator=True, hrb_lease="HRB-LEASE-ACE-001", provider_self_placed=False),
        not hrb_admission_valid(accelerator=True, hrb_lease=None, provider_self_placed=False))
    add("FA3-ACE-P0-005", "requested model identity",
        requested_model_identity_valid("xl-turbo@shaA", "xl-turbo@shaA", silent_fallback=False),
        not requested_model_identity_valid("xl-sft@shaB", "xl-turbo@shaA", silent_fallback=True))
    add("FA3-ACE-P0-006", "authenticated loopback API",
        api_boundary_valid(bind_address="127.0.0.1", authenticated=True, central_gateway=True),
        not api_boundary_valid(bind_address="0.0.0.0", authenticated=False, central_gateway=False))
    add("FA3-ACE-P0-008", "text2music state hygiene",
        text2music_state_hygiene_valid("text2music", 1.0, 0.0),
        not text2music_state_hygiene_valid("text2music", 1.0, 0.2))
    add("FA3-ACE-P0-009", "non-turbo DCW explicit off",
        non_turbo_dcw_valid("xl_sft", False),
        not non_turbo_dcw_valid("xl_sft", True))
    add("FA3-ACE-P0-010", "SFT promotion quality gate",
        sft_promotion_valid(dcw_off_pass=True, quality_pass=True, negative_regression_pass=True),
        not sft_promotion_valid(dcw_off_pass=True, quality_pass=False, negative_regression_pass=True))
    add("FA3-ACE-P0-011", "KV-cache reinit invariance",
        kv_cache_invariance_valid(2.95, 2.96),
        not kv_cache_invariance_valid(2.95, 3.77))
    add("FA3-ACE-P0-012", "LM reinit lifecycle",
        lm_reinit_policy_valid(in_process_reinit=True, clean_teardown_pass=False, process_recycle=True),
        not lm_reinit_policy_valid(in_process_reinit=True, clean_teardown_pass=False, process_recycle=False))
    add("FA3-ACE-P0-014", "lossless canonical master",
        lossless_master_valid("flac"),
        not lossless_master_valid("mp3"))
    add("FA3-ACE-P0-015", "production auto-update/download disabled",
        immutable_runtime_pin_valid(MERGED_FIXES["PR-1282"], floating=False, auto_update=False, auto_download=False),
        not immutable_runtime_pin_valid(MERGED_FIXES["PR-1282"], floating=False, auto_update=True, auto_download=False))
    add("FA3-ACE-P0-017", "CUDA capability-probe fallback control flow",
        cuda_probe_fallback_valid(probe_failed=True, handler_completed=True, observable=True, deterministic_fallback=True),
        not cuda_probe_fallback_valid(probe_failed=True, handler_completed=False, observable=False, deterministic_fallback=False))
    add("FA3-ACE-P0-018", "explicit CUDA dtype validation and provenance",
        precision_override_valid(requested="float32", hardware_supported=True, provenance_recorded=True),
        not precision_override_valid(requested="bfloat16", hardware_supported=False, provenance_recorded=True))
    add("FA3-ACE-P0-019", "finite latent/audio numeric integrity",
        numeric_integrity_valid(latent_nan=0, latent_inf=0, audio_nan=0, audio_inf=0),
        not numeric_integrity_valid(latent_nan=1, latent_inf=0, audio_nan=0, audio_inf=0))
    add("FA3-ACE-P0-020", "CPU-offload device/dtype coherence",
        offload_device_dtype_coherence_valid(cpu_offload=True, device_match=True, dtype_match=True),
        not offload_device_dtype_coherence_valid(cpu_offload=True, device_match=False, dtype_match=True))
    add("FA3-ACE-P0-021", "LoRA plus CPU-offload validation",
        lora_offload_validation_valid(cpu_offload=True, lora_enabled=True, consistency_checked=True, equivalent_guard=False, mismatch_fail_closed=True),
        not lora_offload_validation_valid(cpu_offload=True, lora_enabled=True, consistency_checked=False, equivalent_guard=False, mismatch_fail_closed=False))
    add("FA3-ACE-P0-022", "open upstream PR cannot promote runtime",
        open_pr_promotion_valid(pr_open=True, used_as_promotion_evidence=False),
        not open_pr_promotion_valid(pr_open=True, used_as_promotion_evidence=True))

    passed = sum(case["status"] == "PASS" for case in cases)
    return {
        "schema": "fa3.ace-step-regression-report.v1",
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
    }


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    ok = reference["result"] == "PASS" and regressions["result"] == "PASS"
    report = {
        "schema": "fa3.ace-step-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "mode": "CANONICAL_REFERENCE_AND_EXECUTABLE_INVARIANTS",
        "reference": reference,
        "regressions": regressions,
        "runtime_provider_required": True,
        "current_host_receipt": "evidence/receipts/ace-step-current-host.json",
        "promotion_effect": "MANDATORY_PROVIDER_REQUIRES_SEPARATE_CURRENT_HOST_PASS",
    }
    _write(root / "reports/ace-step-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 ACE-Step mandatory generative-music provider invariant gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
