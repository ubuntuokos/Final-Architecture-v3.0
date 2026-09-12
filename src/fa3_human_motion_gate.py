#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SOMA_REV = "d29dbe5a3f5a0b2632ecac91e8d5125f243a7e36"
GEM_REV = "32992550dba114c62243fb55e361311972dce8f9"
PROFILE_ID = "FA3-HUMAN-MOTION-001"
CONTRACT_ID = "FA3-HUMAN-MOTION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-SOMA-GEM-X-2026-09-12"
CAPABILITY_ID = "CAP-032"

PATHS = {
    "root_profile": "canonical/profiles/FA3-3D-GEOM-001.json",
    "profile": "canonical/profiles/FA3-HUMAN-MOTION-001.json",
    "contract": "canonical/contracts/FA3-HUMAN-MOTION-CONTRACTS-001.json",
    "soma_provider": "canonical/providers/FA3-PROVIDER-SOMA-X-001.json",
    "gem_provider": "canonical/providers/FA3-PROVIDER-GEM-X-001.json",
    "decision": "canonical/decisions/FA3-DEC-SOMA-GEM-X-2026-09-12.json",
    "soma_reference": "canonical/references/FA3-SOMA-X-UPSTREAM-REFERENCE-2026-09-12.json",
    "gem_reference": "canonical/references/FA3-GEM-X-UPSTREAM-REFERENCE-2026-09-12.json",
    "soma_runtime": "canonical/FA3-SOMA-X-RUNTIME-CONFORMANCE-001.json",
    "gem_runtime": "canonical/FA3-GEM-X-RUNTIME-CONFORMANCE-001.json",
    "soma_gate": "canonical/FA3-GATE-SOMA-X-001.json",
    "gem_gate": "canonical/FA3-GATE-GEM-X-001.json",
    "soma_enforcement": "canonical/soma-x-enforcement.json",
    "gem_enforcement": "canonical/gem-x-enforcement.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-HUMAN-MOTION-2026-09-12.json",
    "soma_evidence": "evidence/reference/soma-x-reference-pass.json",
    "gem_evidence": "evidence/reference/gem-x-reference-pass.json",
}


def load(root: Path, key: str) -> dict[str, Any]:
    return json.loads((root / PATHS[key]).read_text(encoding="utf-8"))


def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def _missing_report(root: Path, keys: list[str], gateset: str, prefix: str) -> dict[str, Any] | None:
    missing = [PATHS[k] for k in keys if not (root / PATHS[k]).is_file()]
    if not missing:
        return None
    return {
        "schema": "fa3.human-motion-gate-report.v1",
        "gate_set_id": gateset,
        "result": "FAIL",
        "blocking_findings": len(missing),
        "findings": [finding(f"{prefix}-000", f"missing {path}") for path in missing],
    }


def soma_x_gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    keys = ["root_profile", "profile", "contract", "soma_provider", "decision", "soma_reference", "soma_runtime", "soma_gate", "soma_enforcement", "release", "soma_evidence"]
    missing = _missing_report(root, keys, "FA3-SOMA-X-GATESET-001", "SOMAX")
    if missing:
        return missing
    root_profile = load(root, "root_profile")
    profile = load(root, "profile")
    contract = load(root, "contract")
    provider = load(root, "soma_provider")
    decision = load(root, "decision")
    reference = load(root, "soma_reference")
    runtime = load(root, "soma_runtime")
    gate_record = load(root, "soma_gate")
    enforcement = load(root, "soma_enforcement")
    release = load(root, "release")
    evidence = load(root, "soma_evidence")
    authorities = provider.get("authority_boundaries", {})
    checks = [
        ("SOMAX-001", profile.get("id") == PROFILE_ID and profile.get("relationship") == {"type":"SUBPROFILE-OF","parent":"FA3-3D-GEOM-001"} and PROFILE_ID in root_profile.get("children", []) and profile.get("capability_bindings") == [CAPABILITY_ID] and profile.get("capability_count") == 143 and profile.get("new_capability") is False, "non-root CAP-032 projection invariant failed"),
        ("SOMAX-002", contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("canonical_representation") == "FA3_HUMAN_MOTION_IR" and contract.get("provider_native_representation_is_canonical") is False, "provider-neutral Human Motion IR invariant failed"),
        ("SOMAX-003", provider.get("id") == "FA3-PROVIDER-SOMA-X-001" and "REQUIRED_SUPPORTED_REFERENCE" in provider.get("classification", []) and "CONDITIONAL_EXECUTION_PROVIDER" in provider.get("classification", []), "SOMA-X provider classification drift"),
        ("SOMAX-004", provider.get("upstream", {}).get("revision") == SOMA_REV and reference.get("immutable_revision") == SOMA_REV, "SOMA-X immutable upstream pin drift"),
        ("SOMAX-005", provider.get("upstream", {}).get("source_code_license") == "Apache-2.0" and reference.get("license", {}).get("source_code") == "Apache-2.0", "SOMA-X source license drift"),
        ("SOMAX-006", provider.get("licensing", {}).get("separate_license_receipt_required") is True and provider.get("licensing", {}).get("user_supplied_restricted_files_must_not_be_redistributed") is True and contract.get("license_policy", {}).get("third_party_identity_backend_license_receipt_required") is True, "third-party identity backend license gate weakened"),
        ("SOMAX-007", provider.get("runtime_policy", {}).get("production_auto_download") is False and contract.get("job_manifest", {}).get("runtime_network_fetch") is False, "production auto-download/network-fetch policy weakened"),
        ("SOMAX-008", provider.get("runtime_policy", {}).get("all_assets_pre_admitted_and_content_addressed") is True and contract.get("human_motion_ir", {}).get("content_addressed") is True, "content-addressed asset invariant failed"),
        ("SOMAX-009", provider.get("interchange", {}).get("native_output_is_canonical_fa3_ir") is False and provider.get("runtime_policy", {}).get("provider_native_output_requires_fa3_ir_projection") is True, "SOMA native representation was promoted to canonical IR"),
        ("SOMAX-010", len(authorities) >= 10 and all(v is False for v in authorities.values()), "SOMA-X claimed architectural authority"),
        ("SOMAX-011", contract.get("interchange", {}).get("provider_native_format_requires_projection_receipt") is True and "USD" in provider.get("interchange", {}).get("supported_projection_formats", []) and "SMPL-X" in provider.get("interchange", {}).get("supported_projection_formats", []), "interchange projection receipt policy drift"),
        ("SOMAX-012", contract.get("quality_and_safety", {}).get("bforartists_or_blender_import_smoke_required_for_dcc_promotion") is True and provider.get("interchange", {}).get("dcc_import_requires_receipt") is True, "DCC import smoke requirement weakened"),
        ("SOMAX-013", runtime.get("status") == "PENDING_CURRENT_HOST" and runtime.get("production_admitted") is False and runtime.get("current_host_receipt_present") is False and provider.get("promotion", {}).get("runtime_promotion_claimed") is False, "runtime promoted without real current-host evidence"),
        ("SOMAX-014", gate_record.get("id") == "FA3-GATE-SOMA-X-001" and gate_record.get("gateset_id") == "FA3-SOMA-X-GATESET-001" and gate_record.get("rule_count") == 18 and gate_record.get("fail_closed") is True, "SOMA-X executable gate descriptor drift"),
        ("SOMAX-015", enforcement.get("mandatory_rule_count") == 18 and len(enforcement.get("p0_invariants", [])) == 18 and len(enforcement.get("rules", [])) == 18 and enforcement.get("fail_closed") is True, "SOMA-X enforcement inventory mismatch"),
        ("SOMAX-016", evidence.get("status") == "PASS" and evidence.get("rules_checked") == 18 and evidence.get("current_host_runtime_evidence") is False and evidence.get("production_promotion") is False, "SOMA-X reference evidence scope drift"),
        ("SOMAX-017", decision.get("status") == "CANONICAL_CLOSED" and "FA3-PROVIDER-SOMA-X-001" in decision.get("provider_ids", []) and decision.get("baseline_effect", {}).get("capability_count_after") == 143 and decision.get("baseline_effect", {}).get("new_architectural_authorities") == 0, "SOMA-X decision/baseline closure failed"),
        ("SOMAX-018", "FA3-PROVIDER-SOMA-X-001" in release.get("provider_ids", []) and release.get("capability_count_after") == 143 and release.get("production_promotion_claimed") is False and release.get("current_host_runtime_status") == "PENDING_CURRENT_HOST", "SOMA-X release projection promoted runtime or changed baseline"),
    ]
    findings = [finding(code, message) for code, ok, message in checks if not ok]
    report = {"schema":"fa3.soma-x-gate-report.v1","gate_set_id":"FA3-SOMA-X-GATESET-001","result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"rules_checked":18,"current_host_runtime_promoted":False}
    out = root / "reports/soma-x-gate-report.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report


def gem_x_gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    keys = ["profile", "contract", "gem_provider", "decision", "gem_reference", "gem_runtime", "gem_gate", "gem_enforcement", "release", "gem_evidence"]
    missing = _missing_report(root, keys, "FA3-GEM-X-GATESET-001", "GEMX")
    if missing:
        return missing
    profile = load(root, "profile"); contract = load(root, "contract"); provider = load(root, "gem_provider"); decision = load(root, "decision"); reference = load(root, "gem_reference"); runtime = load(root, "gem_runtime"); gate_record = load(root, "gem_gate"); enforcement = load(root, "gem_enforcement"); release = load(root, "release"); evidence = load(root, "gem_evidence")
    execution = provider.get("execution", {}); model = provider.get("model_policy", {}); claims = provider.get("output_claims", {}); quality = provider.get("quality_gate", {}); authorities = provider.get("authority_boundaries", {})
    checks = [
        ("GEMX-001", profile.get("id") == PROFILE_ID and profile.get("relationship", {}).get("parent") == "FA3-3D-GEOM-001" and profile.get("capability_bindings") == [CAPABILITY_ID] and profile.get("capability_count") == 143 and profile.get("new_architectural_authority") is False, "GEM-X non-root CAP-032 projection invariant failed"),
        ("GEMX-002", contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("provider_native_representation_is_canonical") is False, "provider-neutral Human Motion IR invariant failed"),
        ("GEMX-003", provider.get("id") == "FA3-PROVIDER-GEM-X-001" and "PREFERRED_REFERENCE" in provider.get("classification", []) and "OPTIONAL_EXECUTION_PROVIDER" in provider.get("classification", []), "GEM-X provider classification drift"),
        ("GEMX-004", provider.get("upstream", {}).get("revision") == GEM_REV and reference.get("immutable_revision") == GEM_REV, "GEM-X immutable upstream pin drift"),
        ("GEMX-005", provider.get("upstream", {}).get("source_code_license") == "Apache-2.0" and reference.get("license", {}).get("source_code") == "Apache-2.0", "GEM-X source license drift"),
        ("GEMX-006", provider.get("upstream", {}).get("model_license") == "NVIDIA Open Model License Agreement" and reference.get("license", {}).get("separate_model_license") is True and model.get("source_code_license_does_not_substitute_for_model_license") is True, "GEM-X source/model license separation weakened"),
        ("GEMX-007", model.get("checkpoint_identity_must_be_content_addressed") is True and model.get("checkpoint_sha256_required") is True and model.get("model_license_receipt_required") is True, "checkpoint provenance/model-license admission weakened"),
        ("GEMX-008", model.get("automatic_huggingface_download_in_production") is False and execution.get("runtime_network_fetch") is False and model.get("weights_must_be_pre_admitted") is True, "production model auto-download/network-fetch was enabled"),
        ("GEMX-009", execution.get("hrb_lease_required") is True and execution.get("stable_accelerator_identity_required") == ["DEVICE_UUID", "PCI_BDF"] and execution.get("display_accelerator_implicit_selection") is False, "HRB/stable-device-identity invariant failed"),
        ("GEMX-010", execution.get("silent_gpu_fallback") is False and execution.get("silent_cpu_fallback") is False and execution.get("provider_fallback") is False, "silent execution fallback was enabled"),
        ("GEMX-011", claims.get("upstream_reported_joint_count") == 77 and claims.get("hands_face_articulation_requires_current_host_validation") is True, "77-joint hands/face claim is not validation-gated"),
        ("GEMX-012", claims.get("world_space_trajectory_requires_current_host_validation") is True and "world_space_trajectory" in runtime.get("required_evidence", []), "world-space trajectory evidence requirement missing"),
        ("GEMX-013", quality.get("finite_output_required") is True and quality.get("nan_inf_forbidden") is True and contract.get("quality_and_safety", {}).get("nan_inf_forbidden") is True, "finite/NaN-Inf quality gate weakened"),
        ("GEMX-014", quality.get("frame_timestamp_consistency_required") is True and contract.get("human_motion_ir", {}).get("timestamps_must_be_monotonic") is True, "frame/timestamp consistency gate weakened"),
        ("GEMX-015", quality.get("motion_continuity_required") is True and "motion_continuity" in runtime.get("required_evidence", []), "motion continuity evidence missing"),
        ("GEMX-016", quality.get("foot_sliding_metric_required") is True and quality.get("hand_jitter_metric_required") is True and "foot_sliding_metric" in runtime.get("required_evidence", []) and "hand_jitter_metric" in runtime.get("required_evidence", []), "foot sliding/hand jitter metrics missing"),
        ("GEMX-017", quality.get("dynamic_camera_trajectory_required") is True and claims.get("dynamic_camera_support_requires_current_host_validation") is True and "dynamic_camera_trajectory" in runtime.get("required_evidence", []), "dynamic-camera trajectory evidence gate weakened"),
        ("GEMX-018", quality.get("soma_to_smplx_roundtrip_required") is True and quality.get("usd_export_required") is True and quality.get("bforartists_or_blender_import_smoke_required") is True, "SOMA/SMPL-X/USD/DCC interchange evidence gate weakened"),
        ("GEMX-019", len(authorities) >= 10 and all(v is False for v in authorities.values()), "GEM-X claimed architectural authority"),
        ("GEMX-020", runtime.get("status") == "PENDING_CURRENT_HOST" and runtime.get("production_admitted") is False and runtime.get("current_host_receipt_present") is False and provider.get("promotion", {}).get("runtime_promotion_claimed") is False, "GEM-X runtime promoted without real evidence"),
        ("GEMX-021", gate_record.get("id") == "FA3-GATE-GEM-X-001" and gate_record.get("rule_count") == 22 and gate_record.get("fail_closed") is True and enforcement.get("mandatory_rule_count") == 22 and len(enforcement.get("p0_invariants", [])) == 22 and len(enforcement.get("rules", [])) == 22, "GEM-X gate/enforcement inventory mismatch"),
        ("GEMX-022", evidence.get("status") == "PASS" and evidence.get("rules_checked") == 22 and evidence.get("current_host_runtime_evidence") is False and evidence.get("production_promotion") is False and "FA3-PROVIDER-GEM-X-001" in decision.get("provider_ids", []) and decision.get("baseline_effect", {}).get("capability_count_after") == 143 and "FA3-PROVIDER-GEM-X-001" in release.get("provider_ids", []) and release.get("production_promotion_claimed") is False, "GEM-X reference/decision/release scope drift"),
    ]
    findings = [finding(code, message) for code, ok, message in checks if not ok]
    report = {"schema":"fa3.gem-x-gate-report.v1","gate_set_id":"FA3-GEM-X-GATESET-001","result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"rules_checked":22,"current_host_runtime_promoted":False}
    out = root / "reports/gem-x-gate-report.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report


def combined_gate(root: Path) -> dict[str, Any]:
    soma = soma_x_gate(root); gem = gem_x_gate(root)
    result = "PASS" if soma.get("result") == gem.get("result") == "PASS" else "FAIL"
    return {"schema":"fa3.human-motion-gate-report.v1","profile_id":PROFILE_ID,"result":result,"soma_x":soma,"gem_x":gem,"current_host_runtime_promoted":False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("soma-x", "gem-x", "human-motion"))
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args(); root = Path(a.root).resolve()
    report = soma_x_gate(root) if a.command == "soma-x" else gem_x_gate(root) if a.command == "gem-x" else combined_gate(root)
    print(json.dumps(report, indent=2))
    return 0 if report.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
