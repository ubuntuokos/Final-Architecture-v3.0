#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_openfx_interop import (
    REFERENCE_STANDARD_COMMIT,
    REFERENCE_STANDARD_VERSION,
    run_reference_conformance,
)


PATHS = {
    "parent_profile": "canonical/profiles/FA3-COMPOSITING-001.json",
    "parent_contract": "canonical/contracts/FA3-COMPOSITING-CONTRACTS-001.json",
    "profile": "canonical/profiles/FA3-STANDARD-OPENFX-001.json",
    "contract": "canonical/contracts/FA3-OPENFX-INTEROPERABILITY-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-NATRON-001.json",
    "decision": "canonical/decisions/FA3-DEC-OPENFX-INTEROPERABILITY-2026-09-11.json",
    "reference": "canonical/references/FA3-OPENFX-UPSTREAM-REFERENCE-2026-09-11.json",
    "runtime": "canonical/FA3-OPENFX-RUNTIME-CONFORMANCE-001.json",
    "gate": "canonical/FA3-GATE-OPENFX-INTEROPERABILITY-001.json",
    "enforcement": "canonical/openfx-interoperability-enforcement.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-OPENFX-2026-09-11.json",
    "evidence": "evidence/reference/openfx-interoperability-ci-2026-09-11.json",
    "registry": "evidence/evidence-registry.json",
    "global_policy": "canonical/enforcement-policy.json",
    "global_release": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    "kdenlive_profile": "canonical/profiles/FA3-KDENLIVE-EDITORIAL-001.json",
}

PROFILE_ID = "FA3-STANDARD-OPENFX-001"
CONTRACT_ID = "FA3-OPENFX-INTEROPERABILITY-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-NATRON-001"
DECISION_ID = "FA3-DEC-OPENFX-INTEROPERABILITY-2026-09-11"
GATESET_ID = "FA3-OPENFX-INTEROPERABILITY-GATESET-001"
EVIDENCE_PATH = "evidence/reference/openfx-interoperability-ci-2026-09-11.json"
CAPABILITY_IDS = ("CAP-071", "CAP-126")
EXPECTED_RULE_COUNT = 30
NATRON_COMMIT = "3763d805d7d277d10af10025ae41af677682b3e6"
OPENFX_LICENSE_SHA256 = "63b0f0533a90223e7dbe5dd50b94821b069672f91797ac03dbbad496b4ca7d9b"
NATRON_LICENSE_SHA256 = "2a91027307410797b226e00b3bc4ca6160d8114898fb70ef779629c262591a88"


def load(root: Path, key: str) -> dict[str, Any]:
    return json.loads((root / PATHS[key]).read_text(encoding="utf-8"))


def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root)
    missing = [path for path in PATHS.values() if not (root / path).is_file()]
    if missing:
        return {
            "schema": "fa3.openfx-interoperability-gate-report.v1",
            "gate_set_id": GATESET_ID,
            "result": "FAIL",
            "blocking_findings": len(missing),
            "findings": [finding("OFX-000", f"missing {path}") for path in missing],
            "rules_checked": EXPECTED_RULE_COUNT,
        }

    parent_profile = load(root, "parent_profile")
    parent_contract = load(root, "parent_contract")
    profile = load(root, "profile")
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
    kdenlive = load(root, "kdenlive_profile")
    policy = run_reference_conformance()
    openfx_source = next((item for item in reference.get("sources", []) if item.get("repository") == "AcademySoftwareFoundation/openfx"), {})
    natron_source = next((item for item in reference.get("sources", []) if item.get("repository") == "NatronGitHub/Natron"), {})
    native = contract.get("native_code_admission", {})
    abi = contract.get("abi_and_suite_negotiation", {})
    isolation = contract.get("execution_isolation", {})
    accelerator = contract.get("accelerator_execution", {})
    color = contract.get("color_management", {})
    render = contract.get("render_and_provenance", {})
    natron_cap = provider.get("openfx_host_capability", {})
    bindings = {
        cap_id: next((item for item in registry.get("records", []) if item.get("subject_id") == cap_id), {})
        for cap_id in CAPABILITY_IDS
    }
    binding_ok = all(
        DECISION_ID in record.get("source_decision_ids", [])
        and EVIDENCE_PATH in record.get("evidence_artifacts", [])
        and record.get("openfx_interoperability_projection_status", {}).get("profile_id") == PROFILE_ID
        and record.get("openfx_interoperability_projection_status", {}).get("runtime_status") == "PENDING_CURRENT_HOST"
        and record.get("runtime_conformance") == "EVIDENCE-PENDING"
        and record.get("promotion_state") == "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
        for record in bindings.values()
    )
    reconciliation = global_release.get("openfx_interoperability_reconciliation", {})
    manifest_paths = {item.get("path") for item in global_release.get("manifest", [])}
    inventory = global_release.get("overlay_inventory", {})
    required_manifest = {
        *PATHS.values(),
        "src/fa3_openfx_interop.py",
        "src/fa3_openfx_interop_gate.py",
        "tests/test_openfx_interop_gate.py",
        ".github/workflows/openfx-reference-gate.yml",
        "src/fa3_enforce.py",
        ".github/workflows/fa3-permanent-enforcement.yml",
        "README.md",
    }
    required_manifest.discard(PATHS["global_release"])
    provider_files = list((root / "canonical/providers").glob("FA3-PROVIDER-NATRON-*.json"))
    forbidden_openfx_provider = root / "canonical/providers/FA3-PROVIDER-OPENFX-001.json"

    checks = [
        ("OFX-001", profile.get("id") == PROFILE_ID and profile.get("canonical_root") is False and profile.get("relationship") == {"type": "SUBPROFILE-OF", "parent": "FA3-COMPOSITING-001"} and parent_profile.get("id") == "FA3-COMPOSITING-001", "OpenFX profile is not a non-root compositing subprofile"),
        ("OFX-002", profile.get("capability_bindings") == list(CAPABILITY_IDS) and profile.get("baseline_effect") == {"new_capability": False, "new_architectural_authority": False, "capability_count_after": 143}, "capability or authority baseline changed"),
        ("OFX-003", profile.get("standard_identity", {}).get("current_reference_version") == REFERENCE_STANDARD_VERSION and profile.get("standard_identity", {}).get("release_tag") == "OFX_Release_1.5.1" and profile.get("standard_identity", {}).get("immutable_commit") == REFERENCE_STANDARD_COMMIT and profile.get("standard_identity", {}).get("license") == "BSD-3-Clause" and openfx_source.get("release") == REFERENCE_STANDARD_VERSION and openfx_source.get("tag") == "OFX_Release_1.5.1" and openfx_source.get("immutable_commit") == REFERENCE_STANDARD_COMMIT and openfx_source.get("license", {}).get("spdx") == "BSD-3-Clause" and openfx_source.get("license", {}).get("sha256") == OPENFX_LICENSE_SHA256, "OpenFX standard identity pin drift"),
        ("OFX-004", profile.get("standard_identity", {}).get("standard_is_architectural_authority") is False and profile.get("authority_bindings", {}).get("security_and_plugin_admission") == "FA3-AUTH-SECURITY-GOV-001", "standard or authority ownership drift"),
        ("OFX-005", profile.get("interoperability_policy", {}).get("host_and_plugin_capability_negotiation_required") is True and profile.get("interoperability_policy", {}).get("required_api_and_suites_declared_per_job") is True, "host/plugin negotiation is not mandatory"),
        ("OFX-006", abi.get("missing_required_api_or_suite_action") == "FAIL_CLOSED" and abi.get("silent_downgrade") is False and abi.get("host_version_label_alone_is_sufficient") is False, "API/suite negotiation no longer fails closed"),
        ("OFX-007", profile.get("interoperability_policy", {}).get("host_project_format_is_canonical_ir") is False and profile.get("interoperability_policy", {}).get("plugin_parameter_serialization_is_canonical_ir") is False, "provider formats became canonical IR"),
        ("OFX-008", profile.get("provider_model", {}).get("host_and_plugin_packages_replaceable") is True and profile.get("provider_model", {}).get("reference_host_is_mandatory_runtime") is False, "host/plugin replaceability drift"),
        ("OFX-009", provider.get("id") == PROVIDER_ID and provider.get("canonical_root") is False and provider.get("architectural_authority") is False and provider.get("new_capability") is False and provider.get("new_architectural_authority") is False and len(provider_files) == 1 and not forbidden_openfx_provider.exists(), "Natron provider was duplicated or acquired architectural authority"),
        ("OFX-010", provider.get("upstream", {}).get("immutable_commit") == NATRON_COMMIT and provider.get("upstream", {}).get("branch") == "RB-2.6" and provider.get("upstream", {}).get("declared_version") == "2.6.0" and provider.get("upstream", {}).get("license") == "GPL-2.0-or-later" and provider.get("upstream", {}).get("license_file_sha256") == NATRON_LICENSE_SHA256 and natron_source.get("branch") == "RB-2.6" and natron_source.get("declared_version") == "2.6.0" and natron_source.get("immutable_commit") == NATRON_COMMIT and natron_source.get("license", {}).get("spdx") == "GPL-2.0-or-later" and natron_source.get("license", {}).get("sha256") == NATRON_LICENSE_SHA256, "Natron upstream or license pin drift"),
        ("OFX-011", natron_cap.get("documented_api_version") == "1.4" and natron_cap.get("openfx_1_5_specific_suites_attested") is False and natron_cap.get("suite_discovery_required_per_job") is True, "Natron OFX 1.4 limit was overclaimed"),
        ("OFX-012", contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("parent_contract") == parent_contract.get("id") and native.get("plugin_is_native_code") is True and native.get("untrusted_by_default") is True, "provider-neutral/native-code contract drift"),
        ("OFX-013", all(native.get(key) is True for key in ("immutable_plugin_binary_sha256_required", "allowlist_membership_required", "license_inventory_required", "dependency_inventory_required", "sbom_required")), "plugin digest/inventory/SBOM admission weakened"),
        ("OFX-014", native.get("malware_and_behavioral_scan_required") is True and native.get("signature_or_explicit_exception_receipt_required") is True, "plugin security/signature admission weakened"),
        ("OFX-015", native.get("automatic_plugin_install_or_update") is False and native.get("plugin_search_paths") == "ADMITTED_DIRECTORIES_ONLY", "automatic update or unbounded plugin discovery enabled"),
        ("OFX-016", isolation.get("dedicated_worker_process_required") is True and isolation.get("network_default") == "DENY" and isolation.get("cpu_memory_io_and_walltime_limits_required") is True, "worker isolation/resource/network boundary drift"),
        ("OFX-017", isolation.get("workspace_scope") == "CONTENT_ADDRESSED_INPUT_READONLY_OUTPUT_STAGING_WRITEONLY" and isolation.get("partial_output_promotion") == "FORBIDDEN", "content-addressed staged-output boundary drift"),
        ("OFX-018", isolation.get("host_project_direct_mutation") is False and "OPENFX_HOST_NOT_EDITORIAL_TIMELINE_AUTHORITY" in contract.get("authority_denials", []), "OpenFX acquired direct editorial mutation authority"),
        ("OFX-019", accelerator.get("hrb_lease_required_for_accelerator_execution") is True and accelerator.get("stable_accelerator_identity") == ["device_uuid", "pci_bdf"], "HRB accelerator lease identity drift"),
        ("OFX-020", accelerator.get("runtime_ordinal_is_canonical_identity") is False, "runtime ordinal became canonical identity"),
        ("OFX-021", accelerator.get("concrete_gpu_sku_or_vram_is_canonical_requirement") is False, "concrete GPU SKU/VRAM became canonical"),
        ("OFX-022", accelerator.get("requested_backend_must_equal_observed_backend") is True, "requested/observed backend equality weakened"),
        ("OFX-023", accelerator.get("silent_cpu_accelerator_display_gpu_or_cloud_fallback") is False, "silent backend or display/cloud fallback enabled"),
        ("OFX-024", color.get("input_working_and_output_color_spaces_required") is True and color.get("ocio_config_identity_sha256_required_when_ocio_used") is True and color.get("implicit_color_conversion") is False, "color/OCIO binding weakened"),
        ("OFX-025", render.get("output_sha256_and_frame_checksums_required") is True and render.get("finite_pixel_and_alpha_quality_checks_required") is True, "render checksum or QC requirement weakened"),
        ("OFX-026", render.get("source_to_output_lineage_required") is True and render.get("effect_identifier_version_parameters_and_plugin_digest_required") is True, "render provenance lineage weakened"),
        ("OFX-027", isolation.get("crash_containment_and_worker_termination_required") is True and render.get("rollback_and_unload_receipt_required") is True, "crash containment or rollback requirement weakened"),
        ("OFX-028", policy.get("result") == "PASS" and policy.get("case_count") == 21 and policy.get("cases_passed") == 21 and policy.get("real_openfx_binary_executed") is False, "reference positive/negative execution suite failed"),
        ("OFX-029", runtime.get("status") == "PENDING_CURRENT_HOST" and runtime.get("production_admitted") is False and runtime.get("current_host_receipt_present") is False and evidence.get("status") == "PASS" and evidence.get("current_host_runtime_evidence") is False and evidence.get("production_promotion") is False and decision.get("current_host_runtime_promotion_claim") is False, "reference evidence overclaims current-host runtime"),
        ("OFX-030", gate_record.get("rule_count") == EXPECTED_RULE_COUNT and gate_record.get("fail_closed") is True and enforcement.get("mandatory_rule_count") == EXPECTED_RULE_COUNT and len(enforcement.get("p0_invariants", [])) == EXPECTED_RULE_COUNT and len(enforcement.get("rules", [])) == EXPECTED_RULE_COUNT and binding_ok and GATESET_ID in global_policy.get("mandatory_reference_gates", []) and global_policy.get("openfx_interoperability_mandatory_p0_rules") == enforcement.get("p0_invariants") and reconciliation.get("reconciliation_status") == "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILED_REFERENCE_PASS_CURRENT_HOST_PENDING" and reconciliation.get("capability_bindings") == list(CAPABILITY_IDS) and reconciliation.get("current_host_runtime_evidence") == "PENDING_REAL_OPENFX_HOST_PLUGIN_RENDER_EXECUTION" and reconciliation.get("production_promotion_claimed") is False and PATHS["profile"] in inventory.get("profile_records", []) and PATHS["contract"] in inventory.get("contract_records", []) and PATHS["decision"] in inventory.get("decision_records", []) and PATHS["reference"] in inventory.get("upstream_reference_records", []) and PATHS["evidence"] in inventory.get("reference_evidence_records", []) and required_manifest.issubset(manifest_paths) and release.get("reference_conformance") == "PASS" and kdenlive.get("canonical_timeline_ir") == "OpenTimelineIO", "global release/inventory/evidence or adjacent editorial reconciliation missing"),
    ]

    findings = [finding(code, message) for code, ok, message in checks if not ok]
    report = {
        "schema": "fa3.openfx-interoperability-gate-report.v1",
        "gate_set_id": GATESET_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "rules_checked": EXPECTED_RULE_COUNT,
        "typed_reference_conformance": policy,
        "current_host_runtime_promoted": False,
    }
    out = root / "reports/openfx-interoperability-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[1]
    result = gate(here)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["result"] == "PASS" else 2)
