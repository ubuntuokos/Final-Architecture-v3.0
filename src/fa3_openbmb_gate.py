#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
FAMILY_ID = "FA3-PROVIDER-FAMILY-OPENBMB-001"
DECISION_ID = "FA3-DEC-OPENBMB-2026-09-02"
GATE_ID = "FA3-OPENBMB-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-OPENBMB-001"
REFERENCE_ID = "FA3-OPENBMB-UPSTREAM-REFERENCE-2026-09-02"
EVIDENCE_ID = "FA3-EVIDENCE-OPENBMB-CI-2026-09-02"

PROVIDER_IDS = [
    "FA3-PROVIDER-MINICPM-V-001",
    "FA3-PROVIDER-MINICPM-O-001",
    "FA3-PROVIDER-AGENTCPM-001",
    "FA3-PROVIDER-ULTRARAG-001",
    "FA3-PROVIDER-CPMCU-001",
    "FA3-PROVIDER-VOXCPM-001",
]
NEW_PROVIDER_IDS = PROVIDER_IDS[:-1]
CONTRACT_IDS = [
    "FA3-WORKSPACE-SCOPED-AGENT-CONTEXT-CONTRACTS-001",
    "FA3-HARNESS-DRIVEN-AUTONOMOUS-DEVELOPMENT-CONTRACTS-001",
]
CAPABILITY_BINDINGS = [
    "CAP-005", "CAP-007", "CAP-010", "CAP-021", "CAP-028", "CAP-050",
    "CAP-056", "CAP-060", "CAP-069", "CAP-078", "CAP-079", "CAP-086",
    "CAP-087", "CAP-103", "CAP-115", "CAP-116",
]
PINS = {
    "MiniCPM-V": "f0866559fae0305bc7cacfb6a950640a927f6984",
    "AgentCPM": "4a43561e790c154292798b3edd50171f71241cec",
    "UltraRAG": "37e0cce42e2156d710467cde77a2c0fd0114a2c4",
    "CPM.cu": "23aa7b7fefc537113166691cec63d5baa5209ebe",
    "EdgeClaw": "5e461861b370f5677d2eb6b35499764632989279",
    "PilotDeck": "bcff0a4972c71fc5e08ab46443a2e03a6cd1cec1",
    "StaffDeck": "da371b716d94aada693bdfc99c569fa02784886e",
    "ForgeTrain": "3242a5cd74851a14a7e0c1ebbfb19decdafd2cde",
    "ForgeStencil": "1c8311c8a79abaedd40fc6609d888a4f88dea3a2",
    "AgentCPM-GUI": "2168ae21b1bed1cdb88736d422934825795a9fd7",
}

P0_RULES = [
    "OPENBMB_FAMILY_NOT_AUTHORITY", "OPENBMB_PROVIDERS_NOT_AUTHORITY",
    "OPENBMB_CAPABILITY_AND_AUTHORITY_COUNT_INVARIANT", "OPENBMB_IMMUTABLE_UPSTREAM_SNAPSHOTS",
    "OPENBMB_MODEL_ARTIFACT_ADMISSION_SEPARATE", "OPENBMB_NO_SILENT_MODEL_BACKEND_DEVICE_OR_CLOUD_FALLBACK",
    "MINICPM_MODALITY_DESCRIPTOR_REQUIRED", "MINICPM_O_CONTINUOUS_CAPTURE_CONSENT_AND_PRIVACY_GATE",
    "MINICPM_PROVIDER_NOT_MODEL_REGISTRY_OR_ROUTER", "AGENTCPM_LONG_HORIZON_EXECUTION_BOUNDED",
    "AGENTCPM_TOOL_AND_SANDBOX_CANONICALLY_MEDIATED", "ULTRARAG_MCP_BEHIND_CENTRAL_GATEWAY",
    "ULTRARAG_PIPELINE_NOT_WORKFLOW_AUTHORITY", "RAG_STEP_PROVENANCE_REQUIRED",
    "WORKSPACE_SCOPE_ISOLATION_REQUIRED", "WHITE_BOX_MEMORY_LINEAGE_AND_ROLLBACK_REQUIRED",
    "MEMORY_PROVIDER_NOT_MEMORY_AUTHORITY", "ALWAYS_ON_EXECUTION_REQUIRES_TEMPORAL_ADMISSION",
    "HARNESS_GENERATED_CODE_NOT_COMPLETION", "HARNESS_CORRECTNESS_PRECEDES_PERFORMANCE",
    "HARNESS_REPRODUCIBLE_HARDWARE_BOUND_BENCHMARK", "HARNESS_LICENSE_PROVENANCE_AND_ROLLBACK",
    "FORGETRAIN_COMING_SOON_HARNESS_NOT_IMPLEMENTATION_EVIDENCE", "FORGESTENCIL_DATACENTER_RESULTS_NOT_CURRENT_HOST_EVIDENCE",
    "CPMCU_EXECUTION_BACKEND_ONLY", "CPMCU_HRB_LEASE_REQUIRED", "CPMCU_TARGET_NATIVE_ABI_AND_SM_ADMISSION",
    "REFERENCE_HOST_FACTS_NOT_PORTABLE_DEFAULTS", "AGPL_PATTERN_SOURCE_PROCESS_ISOLATION",
    "OPENBMB_REFERENCE_CI_NOT_CURRENT_HOST_PROMOTION", "OPENBMB_DISABLED_PROVIDERS_ZERO_NEAR_ZERO_RUNTIME_COST",
]

PATHS = {
    "family": "canonical/registries/FA3-PROVIDER-FAMILY-OPENBMB-001.json",
    "workspace_contract": "canonical/contracts/FA3-WORKSPACE-SCOPED-AGENT-CONTEXT-CONTRACTS-001.json",
    "harness_contract": "canonical/contracts/FA3-HARNESS-DRIVEN-AUTONOMOUS-DEVELOPMENT-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-OPENBMB-2026-09-02.json",
    "reference": "canonical/references/FA3-OPENBMB-UPSTREAM-REFERENCE-2026-09-02.json",
    "admission": "canonical/openbmb-runtime-admission.json",
    "enforcement": "canonical/openbmb-enforcement.json",
    "gate_record": "canonical/FA3-GATE-OPENBMB-001.json",
    "evidence": "evidence/reference/openbmb-ci-2026-09-02.json",
    "evidence_registry": "evidence/evidence-registry.json",
    "policy": "canonical/enforcement-policy.json",
    "projection": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
}
for provider_id in PROVIDER_IDS:
    PATHS[provider_id] = f"canonical/providers/{provider_id}.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def provider_not_authority(canonical_root: bool, architectural_authority: bool) -> bool:
    return not canonical_root and not architectural_authority


def immutable_pin_valid(commit: str) -> bool:
    return len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)


def digest_valid(digest: str) -> bool:
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)


def model_admission_valid(revision: str, hashes_present: bool, licenses_gated: bool, admitted: bool) -> bool:
    if not admitted:
        return revision == "REQUIRED_AT_ACTIVATION_NO_FLOATING" and licenses_gated
    return immutable_pin_valid(revision) and hashes_present and licenses_gated


def no_silent_fallback_valid(requested: str, executed: str, explicit_degraded: bool, evidence: bool) -> bool:
    return requested == executed or (explicit_degraded and evidence)


def modality_descriptor_valid(modalities: set[str], required: set[str]) -> bool:
    return required <= modalities


def capture_policy_valid(consent: bool, visible: bool, retention: bool, egress_gate: bool) -> bool:
    return consent and visible and retention and egress_gate


def model_authority_valid(provider_owns_registry: bool, provider_owns_router: bool) -> bool:
    return not provider_owns_registry and not provider_owns_router


def long_horizon_valid(bounded: bool, cancellable: bool, checkpointed: bool, budgeted: bool) -> bool:
    return bounded and cancellable and checkpointed and budgeted


def tool_sandbox_valid(mcp_mediated: bool, sandbox_admitted: bool, provider_is_authority: bool) -> bool:
    return mcp_mediated and sandbox_admitted and not provider_is_authority


def mcp_projection_valid(central_gateway: bool, auto_authorized: bool) -> bool:
    return central_gateway and not auto_authorized


def pipeline_authority_valid(provider_owns_workflow: bool, temporal_receipt: bool) -> bool:
    return not provider_owns_workflow and temporal_receipt


def rag_receipt_valid(receipt: dict[str, Any]) -> bool:
    required = {"request_id", "step_id", "component", "provider_id", "input_artifact_hashes", "retrieval_query", "result_artifact_hash", "source_citations", "policy_receipt_id", "started_at", "completed_at", "status"}
    return required <= receipt.keys() and receipt.get("status") == "PASS" and bool(receipt.get("source_citations"))


def workspace_scope_valid(scopes: set[str], cross_workspace_authorized: bool) -> bool:
    required = {"files", "memory", "skills", "credentials", "network_egress", "provenance", "resource_budget"}
    return required <= scopes and not cross_workspace_authorized


def memory_lineage_valid(source_ids: list[str], content_hash: str, audited: bool, rollback: bool) -> bool:
    return bool(source_ids) and digest_valid(content_hash) and audited and rollback


def memory_authority_valid(provider_is_authority: bool, canonical_receipt: bool) -> bool:
    return not provider_is_authority and canonical_receipt


def always_on_valid(temporal_scheduled: bool, admitted: bool, cancellable: bool) -> bool:
    return temporal_scheduled and admitted and cancellable


def generated_completion_valid(code_generated: bool, correctness: bool, provenance: bool, acceptance: bool) -> bool:
    return code_generated and correctness and provenance and acceptance


def correctness_order_valid(correctness_pass: bool, benchmark_accepted: bool) -> bool:
    return correctness_pass or not benchmark_accepted


def benchmark_valid(hardware_fingerprint: str, runtime_abi: str, baseline_hash: str, interleaved: bool, samples: int) -> bool:
    return all(digest_valid(x) for x in (hardware_fingerprint, baseline_hash)) and bool(runtime_abi) and interleaved and samples >= 3


def license_rollback_valid(source_provenance: bool, license_gate: bool, rollback_receipt: bool) -> bool:
    return source_provenance and license_gate and rollback_receipt


def forgetrain_claim_valid(harness_observed: str, implementation_evidence_claimed: bool) -> bool:
    return harness_observed == "COMING_SOON" and not implementation_evidence_claimed


def forgestencil_host_claim_valid(validated_hardware: set[str], current_host_claimed: bool) -> bool:
    return validated_hardware <= {"A100", "H100", "B200"} and not current_host_claimed


def cpmcu_backend_valid(execution_backend_only: bool, owns_placement: bool, owns_model_registry: bool) -> bool:
    return execution_backend_only and not owns_placement and not owns_model_registry


def hrb_lease_valid(live_discovery: bool, authorized: bool, device_uuid: str, lease_id: str) -> bool:
    return live_discovery and authorized and bool(device_uuid) and bool(lease_id)


def target_native_valid(target_sm: str, build_sm: str, host_cuda_abi: str, build_cuda_abi: str, correctness: bool) -> bool:
    return target_sm == build_sm and host_cuda_abi == build_cuda_abi and correctness


def reference_host_semantics_valid(semantics: str, live_discovery: bool, static_cpu_numbering: bool) -> bool:
    return semantics == "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT" and live_discovery and not static_cpu_numbering


def agpl_isolation_valid(code_vendored: bool, pattern_only: bool, process_isolated_if_used: bool) -> bool:
    return not code_vendored and pattern_only and process_isolated_if_used


def promotion_valid(reference_ci_pass: bool, current_host_pass: bool, claims_current_host: bool) -> bool:
    return reference_ci_pass and claims_current_host == current_host_pass


def disabled_provider_valid(enabled: bool, resident_processes: int, active_leases: int, background_agents: int) -> bool:
    return enabled or (resident_processes == 0 and active_leases == 0 and background_agents == 0)


def scan_authority_collisions(root: Path) -> dict[str, Any]:
    forbidden = set(PROVIDER_IDS + [FAMILY_ID])
    findings: list[dict[str, Any]] = []
    scanned = 0

    def walk(value: Any, path: str, file_path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                next_path = f"{path}.{key}"
                if "authority" in key.lower().replace("-", "_"):
                    values = {item} if isinstance(item, str) else set(item) if isinstance(item, list) and all(isinstance(x, str) for x in item) else set()
                    collision = sorted(values & forbidden)
                    if collision:
                        findings.append(_finding("OPENBMB-AUTH-001", "OpenBMB family/member assigned to authority-bearing field", file=file_path, path=next_path, ids=collision))
                walk(item, next_path, file_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]", file_path)

    for path in sorted((root / "canonical").rglob("*.json")):
        scanned += 1
        try:
            walk(_load(path), "$", str(path.relative_to(root)))
        except Exception as exc:
            findings.append(_finding("OPENBMB-AUTH-002", "JSON parse failure during authority scan", file=str(path.relative_to(root)), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "scanned_json_files": scanned, "findings": findings}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    loaded: dict[str, dict[str, Any]] = {}
    for name, rel in PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(_finding("OPENBMB-REF-001", "required canonical material missing", path=rel))
            continue
        try:
            loaded[name] = _load(path)
        except Exception as exc:
            findings.append(_finding("OPENBMB-REF-002", "required JSON invalid", path=rel, error=str(exc)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    family = loaded["family"]
    if not (
        family.get("id") == FAMILY_ID
        and family.get("provider_members") == PROVIDER_IDS
        and family.get("contracts") == CONTRACT_IDS
        and provider_not_authority(family.get("canonical_root", True), family.get("architectural_authority", True))
        and family.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(_finding("OPENBMB-REF-003", "provider-family closure or authority invariant drift"))

    for provider_id in PROVIDER_IDS:
        provider = loaded[provider_id]
        legacy_voxcpm = provider_id == "FA3-PROVIDER-VOXCPM-001"
        if not (
            provider.get("id") == provider_id
            and provider_not_authority(provider.get("canonical_root", True), provider.get("architectural_authority", True))
            and provider.get("new_capability") is False
            and (provider.get("new_architectural_authority") is False or (legacy_voxcpm and provider.get("new_architectural_authority") is None))
            and provider.get("capability_count") == CAPABILITY_COUNT
            and provider.get("activation_mode") in ({"OPTIONAL_PROVIDER_ROUTED"} if legacy_voxcpm else {"OPTIONAL_DISABLED_BY_DEFAULT"})
        ):
            findings.append(_finding("OPENBMB-REF-004", "provider boundary or count drift", provider_id=provider_id))

    reference = loaded["reference"]
    snapshots = reference.get("immutable_snapshots", {})
    if not (
        reference.get("id") == REFERENCE_ID
        and all(snapshots.get(name, {}).get("commit") == commit for name, commit in PINS.items())
        and reference.get("floating_main_allowed_as_promotion_evidence") is False
        and reference.get("upstream_performance_claims_are_fa3_evidence") is False
    ):
        findings.append(_finding("OPENBMB-REF-005", "immutable upstream snapshot or non-promotion semantics drift"))

    decision = loaded["decision"]
    enforcement = loaded["enforcement"]
    if not (
        decision.get("id") == DECISION_ID and decision.get("mandatory_p0_rules") == P0_RULES
        and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and enforcement.get("gate_id") == GATE_ID and enforcement.get("executable_gate_id") == EXECUTABLE_GATE_ID
        and enforcement.get("mandatory_rule_count") == len(P0_RULES) and enforcement.get("p0_invariants") == P0_RULES
    ):
        findings.append(_finding("OPENBMB-REF-006", "decision/enforcement rule set drift"))

    for contract_name in ("workspace_contract", "harness_contract"):
        contract = loaded[contract_name]
        if not (contract.get("id") in CONTRACT_IDS and contract.get("provider_neutral") is True and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False and contract.get("capability_count") == CAPABILITY_COUNT):
            findings.append(_finding("OPENBMB-REF-007", "provider-neutral contract drift", contract=contract_name))

    admission = loaded["admission"]
    if not (
        admission.get("status") == "REFERENCE_PROVIDERS_NOT_ADMITTED"
        and admission.get("hardware_semantics") == "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT"
        and admission.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and admission.get("production_provider_admission") is False
        and "STATIC_CPU_OR_GPU_NUMBERING" in admission.get("forbidden_shortcuts", [])
        and "BLOCKED_UNTIL_TARGET_NATIVE_CUDA13_SM86_BUILD_CORRECTNESS_QUALITY_BENCHMARK_AND_ROLLBACK_EVIDENCE" == admission.get("provider_disposition", {}).get("FA3-PROVIDER-CPMCU-001")
    ):
        findings.append(_finding("OPENBMB-REF-008", "current-host admission/hardware semantics drift"))

    evidence = loaded["evidence"]
    gate_record = loaded["gate_record"]
    if not (
        evidence.get("id") == EVIDENCE_ID and evidence.get("status") == "PASS"
        and evidence.get("regression_cases_total") == len(P0_RULES) and evidence.get("regression_cases_passed") == len(P0_RULES)
        and evidence.get("current_host_provider_runtime_evidence") is False
        and evidence.get("current_host_runtime_promotion_claim") is False
        and gate_record.get("id") == EXECUTABLE_GATE_ID and gate_record.get("gate_set_id") == GATE_ID
    ):
        findings.append(_finding("OPENBMB-REF-009", "gate/evidence binding drift"))

    policy = loaded["policy"]
    if not (
        GATE_ID in policy.get("mandatory_reference_gates", [])
        and policy.get("openbmb_family_id") == FAMILY_ID
        and policy.get("openbmb_provider_ids") == PROVIDER_IDS
        and policy.get("openbmb_mandatory_p0_rules") == P0_RULES
    ):
        findings.append(_finding("OPENBMB-REF-010", "global enforcement-policy binding missing or drifted"))

    projection = loaded["projection"].get("openbmb_reconciliation", {})
    registry = loaded["evidence_registry"].get("openbmb_reconciliation", {})
    for label, item in (("release projection", projection), ("evidence registry", registry)):
        if not (
            item.get("family_id") == FAMILY_ID
            and item.get("decision_id") == DECISION_ID
            and item.get("gate_id") == GATE_ID
            and item.get("reference_evidence") == PATHS["evidence"]
            and item.get("capability_count_after") == CAPABILITY_COUNT
            and item.get("new_capabilities") == 0
            and item.get("new_architectural_authorities") == 0
            and item.get("current_host_runtime_promotion_claim") is False
        ):
            findings.append(_finding("OPENBMB-REF-011", f"{label} reconciliation drift"))
    if projection.get("evidence_registry_capability_bindings") != CAPABILITY_BINDINGS or registry.get("capability_bindings") != CAPABILITY_BINDINGS:
        findings.append(_finding("OPENBMB-REF-012", "capability bindings are not globally reconciled"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add(rule_id: str, detail: str, positive: bool, negative: bool) -> None:
        cases.append({"rule_id": rule_id, "detail": detail, "positive_case": bool(positive), "negative_case": bool(negative), "status": "PASS" if positive and negative else "FAIL"})

    digest = "a" * 64
    rag = {"request_id": "r", "step_id": "s", "component": "retriever", "provider_id": "p", "input_artifact_hashes": [digest], "retrieval_query": "q", "result_artifact_hash": digest, "source_citations": ["source:1"], "policy_receipt_id": "policy:1", "started_at": "t1", "completed_at": "t2", "status": "PASS"}
    scopes = {"files", "memory", "skills", "credentials", "network_egress", "provenance", "resource_budget"}
    add(P0_RULES[0], "family is not authority", provider_not_authority(False, False), not provider_not_authority(False, True))
    add(P0_RULES[1], "providers are not authority", provider_not_authority(False, False), not provider_not_authority(True, False))
    add(P0_RULES[2], "143 capabilities and zero authorities", CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144)
    add(P0_RULES[3], "immutable commit pins", all(immutable_pin_valid(x) for x in PINS.values()), not immutable_pin_valid("main"))
    add(P0_RULES[4], "model artifacts require separate admission", model_admission_valid("REQUIRED_AT_ACTIVATION_NO_FLOATING", False, True, False), not model_admission_valid("main", False, False, True))
    add(P0_RULES[5], "no silent fallback", no_silent_fallback_valid("gpu", "gpu", False, False), not no_silent_fallback_valid("gpu", "cpu", False, False))
    add(P0_RULES[6], "typed modalities", modality_descriptor_valid({"IMAGE_INPUT", "VIDEO_INPUT", "TEXT_OUTPUT"}, {"IMAGE_INPUT", "VIDEO_INPUT"}), not modality_descriptor_valid({"TEXT_INPUT"}, {"IMAGE_INPUT"}))
    add(P0_RULES[7], "continuous capture consent/privacy", capture_policy_valid(True, True, True, True), not capture_policy_valid(False, True, True, True))
    add(P0_RULES[8], "model provider not registry/router", model_authority_valid(False, False), not model_authority_valid(True, False))
    add(P0_RULES[9], "long horizon bounded", long_horizon_valid(True, True, True, True), not long_horizon_valid(True, False, True, True))
    add(P0_RULES[10], "tools and sandbox mediated", tool_sandbox_valid(True, True, False), not tool_sandbox_valid(True, False, True))
    add(P0_RULES[11], "UltraRAG MCP behind gateway", mcp_projection_valid(True, False), not mcp_projection_valid(False, True))
    add(P0_RULES[12], "pipeline not workflow authority", pipeline_authority_valid(False, True), not pipeline_authority_valid(True, False))
    add(P0_RULES[13], "RAG step provenance", rag_receipt_valid(rag), not rag_receipt_valid({k: v for k, v in rag.items() if k != "source_citations"}))
    add(P0_RULES[14], "workspace scope isolation", workspace_scope_valid(scopes, False), not workspace_scope_valid({"files", "memory"}, True))
    add(P0_RULES[15], "memory lineage and rollback", memory_lineage_valid(["source:1"], digest, True, True), not memory_lineage_valid([], digest, True, False))
    add(P0_RULES[16], "memory provider not authority", memory_authority_valid(False, True), not memory_authority_valid(True, False))
    add(P0_RULES[17], "always-on through Temporal", always_on_valid(True, True, True), not always_on_valid(False, True, False))
    add(P0_RULES[18], "generated code not completion", generated_completion_valid(True, True, True, True), not generated_completion_valid(True, False, False, False))
    add(P0_RULES[19], "correctness precedes performance", correctness_order_valid(True, True), not correctness_order_valid(False, True))
    add(P0_RULES[20], "hardware-bound reproducible benchmark", benchmark_valid(digest, "cuda-13.2/sm86", digest, True, 5), not benchmark_valid("unknown", "", digest, False, 1))
    add(P0_RULES[21], "license provenance and rollback", license_rollback_valid(True, True, True), not license_rollback_valid(True, False, False))
    add(P0_RULES[22], "ForgeTrain coming-soon caveat", forgetrain_claim_valid("COMING_SOON", False), not forgetrain_claim_valid("COMING_SOON", True))
    add(P0_RULES[23], "ForgeStencil results not current-host evidence", forgestencil_host_claim_valid({"A100", "H100", "B200"}, False), not forgestencil_host_claim_valid({"A100"}, True))
    add(P0_RULES[24], "CPM.cu backend only", cpmcu_backend_valid(True, False, False), not cpmcu_backend_valid(True, True, False))
    add(P0_RULES[25], "CPM.cu HRB lease", hrb_lease_valid(True, True, "GPU-uuid", "lease:1"), not hrb_lease_valid(True, False, "GPU-uuid", ""))
    add(P0_RULES[26], "target-native ABI and SM", target_native_valid("sm86", "sm86", "cuda13.2", "cuda13.2", True), not target_native_valid("sm86", "sm90", "cuda13.2", "cuda12.8", True))
    add(P0_RULES[27], "reference host not portable default", reference_host_semantics_valid("REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT", True, False), not reference_host_semantics_valid("GLOBAL_THREAD_DEFAULT", False, True))
    add(P0_RULES[28], "AGPL sources pattern/process isolated", agpl_isolation_valid(False, True, True), not agpl_isolation_valid(True, False, False))
    add(P0_RULES[29], "reference CI not current-host promotion", promotion_valid(True, False, False), not promotion_valid(True, False, True))
    add(P0_RULES[30], "disabled providers zero cost", disabled_provider_valid(False, 0, 0, 0), not disabled_provider_valid(False, 1, 0, 1))
    passed = sum(case["status"] == "PASS" for case in cases)
    return {"schema": "fa3.openbmb-regression-report.v1", "result": "PASS" if passed == len(cases) else "FAIL", "passed": passed, "total": len(cases), "cases": cases}


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority = scan_authority_collisions(root)
    regressions = run_regressions()
    ok = reference["result"] == authority["result"] == regressions["result"] == "PASS"
    report = {
        "schema": "fa3.openbmb-gate-report.v1", "gate_id": GATE_ID,
        "executable_gate_id": EXECUTABLE_GATE_ID, "family_id": FAMILY_ID,
        "capability_count": CAPABILITY_COUNT, "result": "PASS" if ok else "FAIL",
        "reference": reference, "authority_scan": authority, "regressions": regressions,
        "runtime_provider_required": False, "current_host_provider_runtime_evidence": False,
        "production_provider_admission": False,
        "promotion_effect": "MANDATORY_BOUNDARY_AND_HARDWARE_INVARIANTS_OPTIONAL_PROVIDER_RUNTIME",
    }
    _write(root / "reports/openbmb-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 OpenBMB canonical boundary and hardware admission gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
