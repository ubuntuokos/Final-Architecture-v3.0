#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_pytorch3d_provider import ALLOWED_OPERATIONS, SOURCE_REVISION, reference_policy_conformance

PATHS = {
    "root_profile": "canonical/profiles/FA3-3D-GEOM-001.json",
    "profile": "canonical/profiles/FA3-DIFFERENTIABLE-3D-001.json",
    "geometry_contract": "canonical/contracts/FA3-GEOMETRY-CONTRACTS-001.json",
    "contract": "canonical/contracts/FA3-DIFFERENTIABLE-3D-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-PYTORCH3D-001.json",
    "decision": "canonical/decisions/FA3-DEC-PYTORCH3D-2026-09-11.json",
    "reference": "canonical/references/FA3-PYTORCH3D-UPSTREAM-REFERENCE-2026-09-11.json",
    "runtime": "canonical/FA3-PYTORCH3D-RUNTIME-CONFORMANCE-001.json",
    "gate": "canonical/FA3-GATE-PYTORCH3D-001.json",
    "enforcement": "canonical/pytorch3d-enforcement.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-PYTORCH3D-2026-09-11.json",
    "evidence": "evidence/reference/pytorch3d-reference-pass.json",
    "registry": "evidence/evidence-registry.json",
    "global_policy": "canonical/enforcement-policy.json",
    "global_release": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
}

CAPABILITY_ID = "CAP-032"
PROFILE_ID = "FA3-DIFFERENTIABLE-3D-001"
PROVIDER_ID = "FA3-PROVIDER-PYTORCH3D-001"
CONTRACT_ID = "FA3-DIFFERENTIABLE-3D-CONTRACTS-001"
DECISION_ID = "FA3-DEC-PYTORCH3D-2026-09-11"
GATESET_ID = "FA3-PYTORCH3D-GATESET-001"
REFERENCE_EVIDENCE = "evidence/reference/pytorch3d-reference-pass.json"
EXPECTED_RULE_COUNT = 32


def load(root: Path, key: str) -> dict[str, Any]:
    return json.loads((root / PATHS[key]).read_text(encoding="utf-8"))


def finding(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    missing = [path for path in PATHS.values() if not (root / path).is_file()]
    if missing:
        report = {
            "schema": "fa3.pytorch3d-gate-report.v1",
            "gate_set_id": GATESET_ID,
            "result": "FAIL",
            "blocking_findings": len(missing),
            "findings": [finding("P3D-000", f"missing {path}") for path in missing],
        }
        return report

    root_profile = load(root, "root_profile")
    profile = load(root, "profile")
    geometry_contract = load(root, "geometry_contract")
    contract = load(root, "contract")
    provider = load(root, "provider")
    decision = load(root, "decision")
    reference = load(root, "reference")
    runtime = load(root, "runtime")
    gate_record = load(root, "gate")
    enforcement = load(root, "enforcement")
    release = load(root, "release")
    evidence = load(root, "evidence")
    registry = load(root, "registry")
    global_policy = load(root, "global_policy")
    global_release = load(root, "global_release")
    records = registry.get("records", [])
    cap032 = next((item for item in records if item.get("subject_id") == CAPABILITY_ID), {})
    projection = cap032.get("pytorch3d_provider_projection_status", {})
    global_reconciliation = global_release.get("pytorch3d_reconciliation", {})
    manifest_paths = {item.get("path") for item in global_release.get("manifest", [])}
    inventory = global_release.get("overlay_inventory", {})
    authorities = provider.get("authority_boundaries", {})
    policy = reference_policy_conformance()

    checks = [
        ("P3D-001", profile.get("id") == PROFILE_ID and profile.get("canonical_root") is False and profile.get("relationship") == {"type": "SUBPROFILE-OF", "parent": "FA3-3D-GEOM-001"}, "profile must be a non-root child of the sole geometry root"),
        ("P3D-002", PROFILE_ID in root_profile.get("children", []) and root_profile.get("authority_role") == "SOLE_CANONICAL_GEOMETRY_SEMANTIC_AUTHORITY", "geometry root/child closure failed"),
        ("P3D-003", profile.get("capability_bindings") == [CAPABILITY_ID] and profile.get("capability_count") == 143 and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False, "CAP-032/no-new-capability invariant failed"),
        ("P3D-004", contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("parent_contract") == geometry_contract.get("id"), "provider-neutral geometry contract closure failed"),
        ("P3D-005", tuple(contract.get("job_manifest", {}).get("allowed_operations", [])) == ALLOWED_OPERATIONS and contract.get("job_manifest", {}).get("schema") == "fa3.differentiable-3d-job.v1", "typed capability surface drift"),
        ("P3D-006", contract.get("source_build_receipt", {}).get("isolated_pip_venv_required") is True and contract.get("source_build_receipt", {}).get("conda_baseline_allowed") is False and contract.get("source_build_receipt", {}).get("floating_git_install") is False, "source-build receipt policy drift"),
        ("P3D-007", contract.get("accelerator_execution", {}).get("hrb_lease_required") is True and contract.get("accelerator_execution", {}).get("silent_cpu_fallback") is False and contract.get("accelerator_execution", {}).get("silent_accelerator_fallback") is False, "accelerator/fallback contract drift"),
        ("P3D-008", contract.get("quality_and_safety", {}).get("pulsar_invalid_device_must_raise") is True and contract.get("quality_and_safety", {}).get("pulsar_active_device_restoration_required") is True, "Pulsar device safety contract drift"),
        ("P3D-009", provider.get("id") == PROVIDER_ID and "REQUIRED_SUPPORTED_REFERENCE" in provider.get("classification", []) and "CONDITIONAL_EXECUTION_PROVIDER" in provider.get("classification", []), "provider classification drift"),
        ("P3D-010", provider.get("upstream", {}).get("revision") == SOURCE_REVISION and reference.get("immutable_revision") == SOURCE_REVISION, "immutable upstream pin drift"),
        ("P3D-011", provider.get("upstream", {}).get("license") == "BSD-3-Clause" and reference.get("license", {}).get("license_file_sha256") == "6da05663049417a91409fa349bfad5778ed56c9ef68226dde28dffd541481579", "license identity drift"),
        ("P3D-012", provider.get("binary_channel_policy", {}).get("current") == "SOURCE_BUILD_ONLY" and provider.get("binary_channel_policy", {}).get("official_binary_for_accepted_tuple_available") is False, "source-build-only policy weakened"),
        ("P3D-013", all(provider.get("binary_channel_policy", {}).get(key) is False for key in ("conda_channel_admissible", "pytorch3d_nightly_channel_admissible", "community_wheel_admissible", "pytorch3duniverse_admissible")), "forbidden binary channel admitted"),
        ("P3D-014", provider.get("build_policy", {}).get("isolated_pip_venv") is True and provider.get("build_policy", {}).get("shared_comfyui_or_other_torch_environment") is False and provider.get("build_policy", {}).get("conda_or_mamba") is False, "isolated build environment policy drift"),
        ("P3D-015", provider.get("build_policy", {}).get("torch_torchvision_python_cuda_compiler_cxx_abi_tuple_required") is True and provider.get("build_policy", {}).get("target_architectures_derived_from_admitted_hardware") is True and provider.get("build_policy", {}).get("build_parallelism_derived_from_hrb") is True, "ABI/hardware/build-budget policy drift"),
        ("P3D-016", provider.get("activation", {}).get("automatic_gpu_or_cpu_fallback") is False and provider.get("activation", {}).get("requires_hrb_lease") is True and provider.get("activation", {}).get("execution_model") == "TRANSIENT_JOB_WORKER", "activation/lifecycle policy drift"),
        ("P3D-017", len(authorities) == 10 and all(value is False for value in authorities.values()), "provider claimed architectural authority"),
        ("P3D-018", len(provider.get("capability_surface", [])) == 8 and provider.get("capability_bindings") == [CAPABILITY_ID], "provider capability projection drift"),
        ("P3D-019", decision.get("status") == "CANONICAL_CLOSED" and decision.get("profile_id") == PROFILE_ID and decision.get("provider_id") == PROVIDER_ID and decision.get("baseline_effect", {}).get("capability_count_after") == 143 and decision.get("baseline_effect", {}).get("new_architectural_authorities") == 0, "decision closure/baseline invariant failed"),
        ("P3D-020", reference.get("release", {}).get("latest_tag") == "v0.7.9" and reference.get("release", {}).get("commit") == "33824be3cbc87a7dd1db0f6a9a9de9ac81b2d0ba" and reference.get("release", {}).get("main_commits_ahead") == 45, "upstream release/reference facts drift"),
        ("P3D-021", reference.get("upstream_documented_compatibility", {}).get("highest_documented_pytorch") == "2.4.1" and reference.get("upstream_documented_compatibility", {}).get("official_current_binary_absence_confirmed_by_maintainer") is True and reference.get("upstream_documented_compatibility", {}).get("modern_pyproject_toml_present") is False, "upstream compatibility risk evidence drift"),
        ("P3D-022", reference.get("stable_alias", {}).get("exists_as_tag") is True and reference.get("stable_alias", {}).get("admissible_as_production_identity") is False, "stale stable alias incorrectly admitted"),
        ("P3D-023", runtime.get("status") == "PENDING_CURRENT_HOST" and runtime.get("production_admitted") is False and runtime.get("current_host_receipt_present") is False and runtime.get("global_143_capability_promotion_claim") is False, "runtime must remain pending before real-host evidence"),
        ("P3D-024", gate_record.get("id") == "FA3-GATE-PYTORCH3D-001" and gate_record.get("gateset_id") == GATESET_ID and gate_record.get("rule_count") == EXPECTED_RULE_COUNT and gate_record.get("fail_closed") is True, "executable gate descriptor drift"),
        ("P3D-025", enforcement.get("mandatory_rule_count") == EXPECTED_RULE_COUNT and len(enforcement.get("p0_invariants", [])) == EXPECTED_RULE_COUNT and len(enforcement.get("rules", [])) == EXPECTED_RULE_COUNT and enforcement.get("fail_closed") is True, "enforcement inventory mismatch"),
        ("P3D-026", policy.get("result") == "PASS" and policy.get("case_count") == 21 and policy.get("current_host_runtime_promotion") is False, "executable policy regressions failed"),
        ("P3D-027", evidence.get("status") == "PASS" and evidence.get("rules_checked") == EXPECTED_RULE_COUNT and evidence.get("current_host_runtime_evidence") is False and evidence.get("production_promotion") is False, "reference evidence scope drift"),
        ("P3D-028", release.get("provider_id") == PROVIDER_ID and release.get("profile_id") == PROFILE_ID and release.get("capability_bindings") == [CAPABILITY_ID] and release.get("current_host_runtime_status") == "PENDING_CURRENT_HOST" and release.get("production_promotion_claimed") is False, "provider release projection drift"),
        ("P3D-029", registry.get("canonical_capability_count") == registry.get("record_count") == 143 and DECISION_ID in cap032.get("source_decision_ids", []) and REFERENCE_EVIDENCE in cap032.get("evidence_artifacts", []) and projection.get("provider_id") == PROVIDER_ID and cap032.get("runtime_conformance") == "EVIDENCE-PENDING", "CAP-032 Evidence Registry binding missing"),
        ("P3D-030", GATESET_ID in global_policy.get("mandatory_reference_gates", []) and global_policy.get("pytorch3d_provider_id") == PROVIDER_ID and global_policy.get("pytorch3d_mandatory_p0_rules") == enforcement.get("p0_invariants"), "global enforcement policy binding missing"),
        ("P3D-031", global_reconciliation.get("provider_id") == PROVIDER_ID and global_reconciliation.get("reconciliation_status") == "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILED_REFERENCE_PASS_CURRENT_HOST_PENDING" and global_reconciliation.get("runtime_activation_status") == "NOT_PRODUCTION_PROMOTED" and global_reconciliation.get("capability_count_after") == 143 and PATHS["provider"] in inventory.get("provider_records", []) and PATHS["provider"] in manifest_paths and PATHS["evidence"] in manifest_paths, "global release/inventory/evidence reconciliation missing"),
        ("P3D-032", root_profile.get("id") == "FA3-3D-GEOM-001" and root_profile.get("canonical_root") is True and root_profile.get("capability_count") == 143 and geometry_contract.get("status") == "CANONICAL", "sole geometry root invariant changed"),
    ]

    findings = [finding(code, message) for code, ok, message in checks if not ok]
    report = {
        "schema": "fa3.pytorch3d-gate-report.v1",
        "gate_set_id": GATESET_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "rules_checked": EXPECTED_RULE_COUNT,
        "provider_executable_conformance": policy,
        "current_host_runtime_promoted": False,
    }
    out = root / "reports/pytorch3d-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[1]
    result = gate(here)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["result"] == "PASS" else 2)
