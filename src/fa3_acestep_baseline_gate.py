#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-GATE-ACE-STEP-001"
GATESET_ID = "FA3-ACE-STEP-GATESET-001"
PROVIDER_ID = "FA3-PROVIDER-ACE-STEP-001"
CONTRACT_ID = "FA3-MUSIC-GENERATION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-ACE-STEP-BASELINE-2026-09-12"
CAPABILITY_COUNT = 143
REQUIRED_POLICY = ("rest_automation_must_set_inference_steps_explicitly", "sft_and_xl_sft_must_not_inherit_turbo_step_defaults", "generation_step_policy_is_provenance_bearing", "lm_dit_vram_reserve_must_be_model_duration_and_batch_aware", "kv_cache_floor_must_not_be_silently_violated", "provider_vram_preflight_does_not_replace_hrb_admission", "canonical_lossless_export_must_not_require_unguarded_torchcodec", "torch_pytorch_torchaudio_torchcodec_compatibility_smoke_required_when_torchcodec_is_enabled", "linux_ffmpeg_shared_library_and_audio_export_smoke_required")
REQUIRED_RULES = ("rest_automation_inference_steps_must_be_explicit", "sft_and_xl_sft_turbo_step_default_inheritance_forbidden", "lm_dit_vram_reservation_must_be_model_duration_batch_aware", "kv_cache_floor_violation_must_fail_closed", "canonical_lossless_export_cannot_depend_on_unguarded_torchcodec", "torchcodec_enablement_requires_abi_compatibility_smoke", "linux_audio_export_dependency_smoke_required")

def loadj(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def explicit_steps_valid(model_family: str, steps: int | None) -> bool:
    if steps is None or steps <= 0: return False
    if model_family in {"sft_2b", "xl_sft"}: return steps > 8
    return True
def vram_reserve_valid(*, model_aware: bool, duration_aware: bool, batch_aware: bool, kv_floor_preserved: bool, hrb_lease: bool) -> bool:
    return all((model_aware, duration_aware, batch_aware, kv_floor_preserved, hrb_lease))
def export_path_valid(*, fmt: str, torchcodec_required: bool, fallback_verified: bool, linux_dependency_smoke: bool) -> bool:
    if fmt.lower() not in {"wav", "flac"}: return False
    if torchcodec_required and not fallback_verified: return False
    return linux_dependency_smoke
def torchcodec_enablement_valid(*, enabled: bool, torch_abi_match: bool, torchaudio_abi_match: bool, codec_import_smoke: bool) -> bool:
    if not enabled: return True
    return torch_abi_match and torchaudio_abi_match and codec_import_smoke

def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    provider_path = root / "canonical/providers/FA3-PROVIDER-ACE-STEP-001.json"
    contract_path = root / "canonical/contracts/FA3-MUSIC-GENERATION-CONTRACTS-001.json"
    enforcement_path = root / "canonical/ace-step-enforcement.json"
    decision_path = root / "canonical/decisions/FA3-DEC-ACE-STEP-BASELINE-2026-09-12.json"
    reference_path = root / "evidence/reference/ace-step-upstream-2026-09-12.json"
    descriptor_path = root / "canonical/FA3-GATE-ACE-STEP-001.json"
    for path in (provider_path, contract_path, enforcement_path, decision_path, reference_path, descriptor_path):
        if not path.exists(): findings.append({"code": "ACE15-BL-001", "message": f"missing {path.relative_to(root)}"})
    if findings:
        result = {"schema": "fa3.ace-step-baseline-gate-report.v1", "result": "FAIL", "findings": findings}; writej(root / "reports/ace-step-baseline-2026-09-12.json", result); return result
    provider, contract, enforcement, decision, reference, descriptor = map(loadj, (provider_path, contract_path, enforcement_path, decision_path, reference_path, descriptor_path))
    if provider.get("id") != PROVIDER_ID or provider.get("capability_count") != CAPABILITY_COUNT: findings.append({"code":"ACE15-BL-002","message":"provider identity/capability drift"})
    if provider.get("implementation_status") != "CANONICAL_REQUIRED_PROVIDER_NOT_CURRENT_HOST_PROMOTED": findings.append({"code":"ACE15-BL-003","message":"runtime was promoted without current-host evidence"})
    for key in REQUIRED_POLICY:
        if provider.get("production_policy", {}).get(key) is not True: findings.append({"code":"ACE15-BL-004","message":f"provider policy disabled: {key}"})
    if contract.get("id") != CONTRACT_ID or contract.get("provider_neutral") is not True: findings.append({"code":"ACE15-BL-005","message":"music contract identity/provider-neutral drift"})
    for key in REQUIRED_RULES:
        if contract.get("rules", {}).get(key) is not True: findings.append({"code":"ACE15-BL-006","message":f"music contract rule disabled: {key}"})
    if "inference_steps" not in contract.get("runtime_identity_contract", {}).get("required_fields", []): findings.append({"code":"ACE15-BL-007","message":"inference_steps missing from runtime provenance"})
    tracked = enforcement.get("tracked_upstream_fixes", {})
    for pr in ("PR-1223", "PR-1242", "PR-1301", "PR-1311", "PR-1312", "PR-1319", "PR-1321"):
        if pr not in tracked: findings.append({"code":"ACE15-BL-008","message":f"upstream risk not tracked: {pr}"})
    if enforcement.get("supplemental_executable_gate") != "./bin/fa3-enforce ace-step-baseline": findings.append({"code":"ACE15-BL-009","message":"supplemental gate wiring drift"})
    if decision.get("id") != DECISION_ID or decision.get("status") != "CANONICAL_CLOSED": findings.append({"code":"ACE15-BL-010","message":"baseline decision not canonically closed"})
    if decision.get("new_capabilities") != 0 or decision.get("new_architectural_authorities") != 0: findings.append({"code":"ACE15-BL-011","message":"baseline illegally changed capability/authority count"})
    if reference.get("latest_formal_release", {}).get("tag") != "v0.1.8": findings.append({"code":"ACE15-BL-012","message":"formal release observation drift"})
    if reference.get("observed_main_commit", {}).get("sha") != "ca1e85fe9430179831e6bc6be790c332190a3866": findings.append({"code":"ACE15-BL-013","message":"observed upstream main drift"})
    if reference.get("open_pr_as_promotion_evidence_allowed") is not False: findings.append({"code":"ACE15-BL-014","message":"open PR promotion evidence unexpectedly allowed"})
    if descriptor.get("id") != GATE_ID or descriptor.get("gateset_id") != GATESET_ID: findings.append({"code":"ACE15-BL-015","message":"gate descriptor identity drift"})
    cases = [("explicit_sft_steps", explicit_steps_valid("xl_sft",50), not explicit_steps_valid("xl_sft",8)), ("explicit_steps_required", explicit_steps_valid("xl_turbo",8), not explicit_steps_valid("xl_turbo",None)), ("vram_admission", vram_reserve_valid(model_aware=True,duration_aware=True,batch_aware=True,kv_floor_preserved=True,hrb_lease=True), not vram_reserve_valid(model_aware=True,duration_aware=True,batch_aware=True,kv_floor_preserved=False,hrb_lease=True)), ("hrb_independent", vram_reserve_valid(model_aware=True,duration_aware=True,batch_aware=True,kv_floor_preserved=True,hrb_lease=True), not vram_reserve_valid(model_aware=True,duration_aware=True,batch_aware=True,kv_floor_preserved=True,hrb_lease=False)), ("lossless_export", export_path_valid(fmt="flac",torchcodec_required=False,fallback_verified=True,linux_dependency_smoke=True), not export_path_valid(fmt="mp3",torchcodec_required=False,fallback_verified=True,linux_dependency_smoke=True)), ("torchcodec_guard", torchcodec_enablement_valid(enabled=True,torch_abi_match=True,torchaudio_abi_match=True,codec_import_smoke=True), not torchcodec_enablement_valid(enabled=True,torch_abi_match=False,torchaudio_abi_match=True,codec_import_smoke=False))]
    regressions = [{"name":n,"status":"PASS" if p and neg else "FAIL","positive":p,"negative":neg} for n,p,neg in cases]
    if any(x["status"] != "PASS" for x in regressions): findings.append({"code":"ACE15-BL-016","message":"one or more executable regression cases failed"})
    report = {"schema":"fa3.ace-step-baseline-gate-report.v1","gate_id":GATE_ID,"gateset_id":GATESET_ID,"provider_id":PROVIDER_ID,"capability_count":CAPABILITY_COUNT,"result":"PASS" if not findings else "FAIL","findings":findings,"regressions":regressions,"upstream_release":"v0.1.8","upstream_main":"ca1e85fe9430179831e6bc6be790c332190a3866","current_host_runtime_status":"PENDING_CURRENT_HOST","production_promotion_claimed":False}
    writej(root / "reports/ace-step-baseline-2026-09-12.json", report); return report

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 ACE-Step 1.5 2026-09-12 baseline regression gate"); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=ap.parse_args(); result=gate(Path(args.root).resolve()); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 2
if __name__ == "__main__": raise SystemExit(main())
