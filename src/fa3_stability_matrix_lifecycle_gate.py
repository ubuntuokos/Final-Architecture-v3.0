#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-STABILITY-MATRIX-001"
MODEL_STORE_PROVIDER_ID = "FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001"
CONTRACT_ID = "FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001"
DECISION_ID = "FA3-DEC-STABILITY-MATRIX-LIFECYCLE-2026-09-06"
GATE_ID = "FA3-STABILITY-MATRIX-LIFECYCLE-GATESET-001"
EVIDENCE_ID = "FA3-EVIDENCE-STABILITY-MATRIX-LIFECYCLE-CI-2026-09-06"
CAPABILITIES = ["CAP-005", "CAP-016", "CAP-120", "CAP-135"]
CAPABILITY_COUNT = 143
P0 = [
    "STABILITY_MATRIX_INTERACTIVE_ADAPTER_NOT_CONTROL_PLANE",
    "STABILITY_MATRIX_UI_SYSTEMD_USER_SERVICE_ONLY",
    "MAINTENANCE_TRIAL_SEPARATE_FROM_PRODUCTION",
    "PRODUCTION_NATIVE_WORKERS_SEPARATE_FROM_GUI",
    "PROMOTED_WORKERS_SURVIVE_PROVIDER_OUTAGE",
    "PACKAGE_REVISION_LOCK_HASH_REQUIRED",
    "AUTOMATIC_PACKAGE_EXTENSION_UPDATE_FORBIDDEN",
    "MAINTENANCE_LOCK_DRAIN_CHECKPOINT_REQUIRED",
    "SMOKE_MEMORY_OUTPUT_VALIDATION_REQUIRED",
    "FAILED_VALIDATION_ROLLBACK_REQUIRED",
    "PACKAGE_OWNED_VENV_HOST_SITE_PACKAGES_FORBIDDEN",
    "GPU_ROUTING_DISCOVERED_UUID_PCI_FAIL_CLOSED",
    "DISPLAY_ACCELERATOR_FALLBACK_FORBIDDEN",
    "PER_UNIT_DROPIN_GLOBAL_GPU_OVERRIDE_FORBIDDEN",
    "LOOPBACK_ONLY_DIRECT_BINDING",
    "CACHE_PLANES_EXPLICIT_AND_SEPARATE",
    "PACKAGE_MODEL_CACHE_RENDER_PLANES_SEPARATE",
    "PROVIDER_LOCAL_STATE_NOT_CANONICAL_SOT",
    "SIGNED_PROMOTION_BEFORE_NATIVE_WORKER_PROJECTION",
    "CLEAN_UNINSTALL_AND_ORPHAN_SCAN_REQUIRED",
    "FAILED_ENVIRONMENT_ISOLATED_FROM_PLATFORM",
    "WRAPPER_OWNS_HOST_POLICY_PACKAGE_OWNS_RUNTIME_ARGS",
    "EXISTING_WORKFLOW_RESOURCE_SECURITY_EVIDENCE_AUTHORITIES_RETAINED",
]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def provider_boundary_valid(provider: dict[str, Any]) -> bool:
    bounds = provider.get("authority_boundaries", {})
    return bool(
        provider.get("id") == PROVIDER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("capability_bindings") == CAPABILITIES
        and provider.get("related_model_store_provider_id") == MODEL_STORE_PROVIDER_ID
        and bounds.get("workflow_orchestration") == "TEMPORAL_AND_EXISTING_FA3_ORCHESTRATION_AUTHORITY_ONLY"
        and bounds.get("host_resource_admission") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        and bounds.get("security_policy") == "FA3-AUTH-SECURITY-GOV-001"
        and bounds.get("evidence_promotion") == "FA3-AUTH-OBS-EVIDENCE-001"
    )


def ui_mode_valid(*, systemd_scope: str, production_worker: bool) -> bool:
    return systemd_scope == "user" and production_worker is False


def maintenance_separation_valid(*, maintenance: bool, production_endpoint: bool, admitted: bool) -> bool:
    return (not maintenance) or (admitted and not production_endpoint)


def native_worker_valid(*, gui_process: bool, native_unit: bool, ai_media_target: bool) -> bool:
    return not gui_process and native_unit and ai_media_target


def outage_survival_valid(*, provider_available: bool, promoted_worker_continues: bool) -> bool:
    return provider_available or promoted_worker_continues


def immutable_package_valid(*, version: str, revision: str, sha256: str, lock_manifest: bool) -> bool:
    return bool(version and revision and len(sha256) == 64 and lock_manifest)


def update_policy_valid(*, automatic_update: bool, explicit_change_set: bool) -> bool:
    return not automatic_update and explicit_change_set


def maintenance_gate_valid(*, lock: bool, drained: bool, checkpoint: bool) -> bool:
    return lock and drained and checkpoint


def validation_valid(*, smoke: bool, memory_envelope: bool, output: bool) -> bool:
    return smoke and memory_envelope and output


def rollback_valid(*, validation_pass: bool, rollback_available: bool, rolled_back: bool) -> bool:
    return validation_pass or (rollback_available and rolled_back)


def environment_valid(*, package_owned_venv: bool, host_site_packages: bool, global_pip_upgrade: bool) -> bool:
    return package_owned_venv and not host_site_packages and not global_pip_upgrade


def device_routing_valid(*, discovered: bool, pci_slot: str, gpu_uuid: str, hrb_lease: bool, hardcoded_model: bool) -> bool:
    return discovered and bool(pci_slot and gpu_uuid and hrb_lease) and not hardcoded_model


def display_fallback_valid(*, selected_role: str, fallback_used: bool) -> bool:
    return selected_role == "compute" and not fallback_used


def dropin_valid(*, per_unit: bool, validated: bool, global_gpu_override: bool) -> bool:
    return per_unit and validated and not global_gpu_override


def network_valid(*, bind_host: str, proxy_approved: bool) -> bool:
    return bind_host in {"127.0.0.1", "::1"} or proxy_approved


def caches_valid(cache_map: dict[str, str]) -> bool:
    required = {"hf", "torch", "triton", "inductor", "pip", "uv", "cuda"}
    return required <= set(cache_map) and all(bool(cache_map[k]) for k in required)


def storage_planes_valid(planes: dict[str, str]) -> bool:
    required = {"package", "model", "cache", "render"}
    return required <= set(planes) and len({planes[k] for k in required}) == len(required)


def state_authority_valid(*, provider_state_canonical: bool, postgres_manifest: bool) -> bool:
    return not provider_state_canonical and postgres_manifest


def promotion_valid(*, interactive_pass: bool, signed_receipt: bool, native_projection: bool) -> bool:
    return interactive_pass and signed_receipt and native_projection


def uninstall_valid(*, clean_uninstall: bool, orphan_scan: bool) -> bool:
    return clean_uninstall and orphan_scan


def failure_isolation_valid(*, environment_isolated: bool, platform_available: bool) -> bool:
    return environment_isolated and platform_available


def wrapper_boundary_valid(*, wrapper_host_policy: bool, package_runtime_args: bool, wrapper_runtime_args: bool) -> bool:
    return wrapper_host_policy and package_runtime_args and not wrapper_runtime_args


def authority_retention_valid(authorities: dict[str, str]) -> bool:
    expected = {
        "workflow": "Temporal",
        "events": "NATS",
        "resources": "HostResourceBroker",
        "security": "SecurityGovernance",
        "evidence": "ObservabilityEvidence",
    }
    return authorities == expected


def _case(index: int, name: str, positive: bool, negative: bool) -> dict[str, Any]:
    return {
        "rule_id": f"FA3-STABILITY-MATRIX-P0-{index:03d}",
        "invariant": P0[index - 1],
        "name": name,
        "status": "PASS" if positive and negative else "FAIL",
        "positive_case": bool(positive),
        "negative_case": bool(negative),
    }


def run_regressions() -> dict[str, Any]:
    sha = "a" * 64
    caches = {k: f"/cache/{k}" for k in ("hf", "torch", "triton", "inductor", "pip", "uv", "cuda")}
    planes = {"package": "/packages", "model": "/models", "cache": "/cache", "render": "/render"}
    authorities = {"workflow": "Temporal", "events": "NATS", "resources": "HostResourceBroker", "security": "SecurityGovernance", "evidence": "ObservabilityEvidence"}
    minimal_provider = {
        "id": PROVIDER_ID, "canonical_root": False, "architectural_authority": False,
        "new_capability": False, "new_architectural_authority": False,
        "capability_count": 143, "capability_bindings": CAPABILITIES,
        "related_model_store_provider_id": MODEL_STORE_PROVIDER_ID,
        "authority_boundaries": {"workflow_orchestration": "TEMPORAL_AND_EXISTING_FA3_ORCHESTRATION_AUTHORITY_ONLY", "host_resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001", "security_policy": "FA3-AUTH-SECURITY-GOV-001", "evidence_promotion": "FA3-AUTH-OBS-EVIDENCE-001"},
    }
    cases = [
        _case(1, "interactive adapter non-authority", provider_boundary_valid(minimal_provider), not provider_boundary_valid({**minimal_provider, "architectural_authority": True})),
        _case(2, "UI user service only", ui_mode_valid(systemd_scope="user", production_worker=False), not ui_mode_valid(systemd_scope="system", production_worker=True)),
        _case(3, "maintenance separated", maintenance_separation_valid(maintenance=True, production_endpoint=False, admitted=True), not maintenance_separation_valid(maintenance=True, production_endpoint=True, admitted=True)),
        _case(4, "native production worker", native_worker_valid(gui_process=False, native_unit=True, ai_media_target=True), not native_worker_valid(gui_process=True, native_unit=False, ai_media_target=False)),
        _case(5, "provider outage survival", outage_survival_valid(provider_available=False, promoted_worker_continues=True), not outage_survival_valid(provider_available=False, promoted_worker_continues=False)),
        _case(6, "immutable package tuple", immutable_package_valid(version="1", revision="r", sha256=sha, lock_manifest=True), not immutable_package_valid(version="1", revision="", sha256=sha, lock_manifest=True)),
        _case(7, "explicit updates", update_policy_valid(automatic_update=False, explicit_change_set=True), not update_policy_valid(automatic_update=True, explicit_change_set=False)),
        _case(8, "maintenance lock drain checkpoint", maintenance_gate_valid(lock=True, drained=True, checkpoint=True), not maintenance_gate_valid(lock=True, drained=False, checkpoint=True)),
        _case(9, "smoke memory output validation", validation_valid(smoke=True, memory_envelope=True, output=True), not validation_valid(smoke=True, memory_envelope=False, output=True)),
        _case(10, "rollback on validation failure", rollback_valid(validation_pass=False, rollback_available=True, rolled_back=True), not rollback_valid(validation_pass=False, rollback_available=True, rolled_back=False)),
        _case(11, "isolated package environment", environment_valid(package_owned_venv=True, host_site_packages=False, global_pip_upgrade=False), not environment_valid(package_owned_venv=True, host_site_packages=True, global_pip_upgrade=False)),
        _case(12, "discovered UUID PCI routing", device_routing_valid(discovered=True, pci_slot="0000:01:00.0", gpu_uuid="GPU-X", hrb_lease=True, hardcoded_model=False), not device_routing_valid(discovered=False, pci_slot="", gpu_uuid="", hrb_lease=False, hardcoded_model=True)),
        _case(13, "display fallback denied", display_fallback_valid(selected_role="compute", fallback_used=False), not display_fallback_valid(selected_role="display", fallback_used=True)),
        _case(14, "per-unit validated drop-in", dropin_valid(per_unit=True, validated=True, global_gpu_override=False), not dropin_valid(per_unit=False, validated=True, global_gpu_override=True)),
        _case(15, "loopback-only binding", network_valid(bind_host="127.0.0.1", proxy_approved=False), not network_valid(bind_host="0.0.0.0", proxy_approved=False)),
        _case(16, "explicit cache planes", caches_valid(caches), not caches_valid({"hf": "/cache"})),
        _case(17, "separate storage planes", storage_planes_valid(planes), not storage_planes_valid({**planes, "render": "/cache"})),
        _case(18, "provider state noncanonical", state_authority_valid(provider_state_canonical=False, postgres_manifest=True), not state_authority_valid(provider_state_canonical=True, postgres_manifest=False)),
        _case(19, "signed promotion", promotion_valid(interactive_pass=True, signed_receipt=True, native_projection=True), not promotion_valid(interactive_pass=True, signed_receipt=False, native_projection=True)),
        _case(20, "clean uninstall and orphan scan", uninstall_valid(clean_uninstall=True, orphan_scan=True), not uninstall_valid(clean_uninstall=True, orphan_scan=False)),
        _case(21, "environment failure isolation", failure_isolation_valid(environment_isolated=True, platform_available=True), not failure_isolation_valid(environment_isolated=False, platform_available=False)),
        _case(22, "wrapper/package argument boundary", wrapper_boundary_valid(wrapper_host_policy=True, package_runtime_args=True, wrapper_runtime_args=False), not wrapper_boundary_valid(wrapper_host_policy=True, package_runtime_args=False, wrapper_runtime_args=True)),
        _case(23, "existing authorities retained", authority_retention_valid(authorities), not authority_retention_valid({**authorities, "workflow": "StabilityMatrix"})),
    ]
    passed = sum(x["status"] == "PASS" for x in cases)
    return {"schema": "fa3.stability-matrix-lifecycle-regression-report.v1", "result": "PASS" if passed == len(cases) else "FAIL", "passed": passed, "total": len(cases), "cases": cases}


def reference_check(root: Path) -> dict[str, Any]:
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-STABILITY-MATRIX-001.json",
        "contract": root / "canonical/contracts/FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-STABILITY-MATRIX-LIFECYCLE-2026-09-06.json",
        "enforcement": root / "canonical/stability-matrix-lifecycle-enforcement.json",
        "gate": root / "canonical/FA3-GATE-STABILITY-MATRIX-LIFECYCLE-001.json",
        "evidence": root / "evidence/reference/stability-matrix-lifecycle-ci-2026-09-06.json",
        "policy": root / "canonical/enforcement-policy.json",
        "registry": root / "evidence/evidence-registry.json",
        "projection": root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    }
    findings = []
    for label, path in paths.items():
        if not path.exists():
            findings.append(_finding("SM-LIFECYCLE-REF-001", f"Missing {label}", file=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings}
    provider, contract, decision, enforcement, gate_record, evidence, policy, registry, release = (_load(paths[k]) for k in paths)
    if not provider_boundary_valid(provider):
        findings.append(_finding("SM-LIFECYCLE-REF-002", "Provider authority or hardware-portability boundary drift"))
    if not (contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("invariants") == P0 and contract.get("capability_count") == CAPABILITY_COUNT):
        findings.append(_finding("SM-LIFECYCLE-REF-003", "Lifecycle contract drift"))
    if not (decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED" and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0 and decision.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("SM-LIFECYCLE-REF-004", "Decision or promotion semantics drift"))
    if not (enforcement.get("gate_id") == GATE_ID and enforcement.get("p0_invariants") == P0 and enforcement.get("mandatory_rule_count") == len(P0) and enforcement.get("fail_closed") is True):
        findings.append(_finding("SM-LIFECYCLE-REF-005", "Enforcement drift"))
    if not (gate_record.get("gateset_id") == GATE_ID and gate_record.get("rule_count") == len(P0) and gate_record.get("executable") == "./bin/fa3-enforce stability-matrix-lifecycle"):
        findings.append(_finding("SM-LIFECYCLE-REF-006", "Gate record drift"))
    if not (evidence.get("id") == EVIDENCE_ID and evidence.get("status") == "PASS" and evidence.get("regression_cases") == {"passed": 23, "total": 23} and evidence.get("current_host_production_claim") is False):
        findings.append(_finding("SM-LIFECYCLE-REF-007", "Reference PASS evidence drift"))
    if GATE_ID not in policy.get("mandatory_reference_gates", []) or policy.get("stability_matrix_lifecycle_provider_id") != PROVIDER_ID or policy.get("stability_matrix_lifecycle_mandatory_p0_rules") != P0:
        findings.append(_finding("SM-LIFECYCLE-REF-008", "Global policy binding drift"))
    records = {x.get("subject_id"): x for x in registry.get("records", [])}
    for capability in CAPABILITIES:
        record = records.get(capability, {})
        projection = record.get("stability_matrix_lifecycle_projection_status", {})
        if not (DECISION_ID in record.get("source_decision_ids", []) and "evidence/reference/stability-matrix-lifecycle-ci-2026-09-06.json" in record.get("evidence_artifacts", []) and projection.get("provider_id") == PROVIDER_ID and projection.get("runtime_status") == "PENDING_REAL_CURRENT_HOST_PRODUCTION_WORKER_E2E" and projection.get("reference_gate_status") == "PASS" and projection.get("current_host_production_claim") is False):
            findings.append(_finding("SM-LIFECYCLE-REF-009", "Evidence Registry projection drift", capability=capability))
    reconciliation = release.get("stability_matrix_lifecycle_reconciliation", {})
    inventory = release.get("overlay_inventory", {})
    manifest_paths = {x.get("path") for x in release.get("manifest", [])}
    required_paths = {
        "canonical/providers/FA3-PROVIDER-STABILITY-MATRIX-001.json",
        "canonical/contracts/FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001.json",
        "canonical/decisions/FA3-DEC-STABILITY-MATRIX-LIFECYCLE-2026-09-06.json",
        "canonical/stability-matrix-lifecycle-enforcement.json",
        "canonical/FA3-GATE-STABILITY-MATRIX-LIFECYCLE-001.json",
        "src/fa3_stability_matrix_lifecycle_gate.py",
        "tests/test_stability_matrix_lifecycle_gate.py",
        "evidence/reference/stability-matrix-lifecycle-ci-2026-09-06.json",
    }
    inventory_ok = (
        "canonical/providers/FA3-PROVIDER-STABILITY-MATRIX-001.json" in inventory.get("provider_records", [])
        and "canonical/contracts/FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001.json" in inventory.get("contract_records", [])
        and "canonical/decisions/FA3-DEC-STABILITY-MATRIX-LIFECYCLE-2026-09-06.json" in inventory.get("decision_records", [])
        and "evidence/reference/stability-matrix-lifecycle-ci-2026-09-06.json" in inventory.get("reference_evidence_records", [])
    )
    if not (
        reconciliation.get("provider_id") == PROVIDER_ID
        and reconciliation.get("contract_id") == CONTRACT_ID
        and reconciliation.get("gate_id") == GATE_ID
        and reconciliation.get("capability_bindings") == CAPABILITIES
        and reconciliation.get("reference_gate_status") == "PASS"
        and reconciliation.get("current_host_runtime_promotion_claim") is False
        and reconciliation.get("new_capabilities") == 0
        and reconciliation.get("new_architectural_authorities") == 0
        and reconciliation.get("capability_count_after") == CAPABILITY_COUNT
        and inventory_ok
        and required_paths <= manifest_paths
    ):
        findings.append(_finding("SM-LIFECYCLE-REF-010", "Unified release/inventory/evidence reconciliation drift"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    passed = reference["result"] == regressions["result"] == "PASS"
    report = {
        "schema": "fa3.stability-matrix-lifecycle-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "contract_id": CONTRACT_ID,
        "capability_bindings": CAPABILITIES,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if passed else "FAIL",
        "mode": "INTERACTIVE_LIFECYCLE_NATIVE_WORKER_PROMOTION_AND_AUTHORITY_BOUNDARY_REGRESSION",
        "reference": reference,
        "regressions": regressions,
        "current_host_runtime_evidence": "PENDING_REAL_CURRENT_HOST_PRODUCTION_WORKER_E2E",
        "current_host_production_claim": False,
        "promotion_effect": "REFERENCE_AND_DESIGN_CONFORMANCE_ONLY_NO_RUNTIME_PROMOTION",
    }
    _write(root / "reports/stability-matrix-lifecycle-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
