#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fa3_closed_loop_agent_ops_reference as refimpl

GATE_ID = "FA3-LOOP-ENGINEERING-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-LOOP-ENGINEERING-001"
PROFILE_ID = "FA3-CLOSED-LOOP-AGENT-OPERATIONS-001"
CONTRACT_ID = "FA3-CLOSED-LOOP-AGENT-OPERATIONS-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-LOOP-ENGINEERING-001"
DECISION_ID = "FA3-DEC-LOOP-ENGINEERING-2026-09-03"
REFERENCE_ID = "FA3-LOOP-ENGINEERING-UPSTREAM-REFERENCE-2026-09-03"
EVIDENCE_ID = "FA3-EVIDENCE-LOOP-ENGINEERING-CI-2026-09-03"
PINNED_COMMIT = "714f1fdf6ea111f27207de6908547c2a155b270c"
RUNTIME_STATUS = "REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY"
CAPABILITY_COUNT = 143
CAPABILITY_ID = "CAP-028"

P0_RULES = [
    "LOOP_ENGINEERING_PROVIDER_NOT_AUTHORITY",
    "LOOP_ENGINEERING_CAPABILITY_AUTHORITY_COUNT_INVARIANT",
    "LOOP_ENGINEERING_IMMUTABLE_UPSTREAM_PIN_REQUIRED",
    "CLOSED_LOOP_PROFILE_NON_ROOT_AGENT_EXEC_PROJECTION",
    "TEMPORAL_REMAINS_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY",
    "CANONICAL_LOOP_LIFECYCLE_TYPED_AND_BOUNDED",
    "DURABLE_EXTERNAL_STATE_NOT_CHAT_CONTEXT",
    "STATE_BACKEND_PROVIDER_NEUTRAL_VERSIONED_PARTITIONED",
    "MULTI_LOOP_STATE_RETENTION_AND_PARTITION_REQUIRED",
    "L2_L3_MAKER_CHECKER_SESSION_SEPARATION",
    "VERIFIER_RESTRICTED_AND_NO_SELF_REPAIR",
    "PROGRESSIVE_AUTONOMY_L0_L3_REQUIRED",
    "L3_REQUIRES_HISTORICAL_READINESS_AND_GATES",
    "RISK_INCIDENT_DRIFT_COST_CAUSE_AUTONOMY_DEMOTION",
    "CIRCUIT_BREAKER_ITERATION_FAILURE_STAGNATION_TIMEOUT_REQUIRED",
    "BUDGET_TOKEN_COST_TIME_TOOL_SUBAGENT_RESOURCE_BOUNDED",
    "AGENT_SELF_BUDGET_RAISE_FORBIDDEN_HUMAN_EXTENSION_REQUIRED",
    "EARLY_EXIT_NOOP_CHEAP_TRIAGE_REQUIRED_WHEN_APPLICABLE",
    "L2_PLUS_MUTATION_REQUIRES_ISOLATED_WORKSPACE",
    "CONCURRENT_MUTATION_REQUIRES_LEASE_LOCK_AND_SINGLE_WRITER_SCOPE",
    "MECHANICAL_POLICY_GATE_DENY_ALLOW_RISK_REQUIRED",
    "AUTO_MERGE_DISABLED_BY_DEFAULT",
    "HIGH_RISK_MUTATION_REQUIRES_HUMAN_GATE",
    "MCP_CONNECTOR_LEAST_PRIVILEGE_AND_L1_READ_ONLY",
    "CONTRACT_STATE_POLICY_DRIFT_BLOCKS_L2_L3",
    "CONTEXT_COMPACTION_PRESERVES_PROVENANCE",
    "STRUCTURED_APPEND_ONLY_RUN_LEDGER_AND_OBSERVABILITY",
    "PAUSE_KILL_RETIRE_AND_INCIDENT_REPORT_ONLY_FALLBACK",
    "EVENT_DRIVEN_PREFERRED_POLLING_REQUIRES_EARLY_EXIT_BUDGET",
    "LOOP_PATTERN_REGISTRY_TYPED_VERSIONED",
    "LOOP_ENGINEERING_CLI_AND_MARKDOWN_FORMATS_NOT_HARD_DEPENDENCIES",
    "HRB_LIVE_CPU_NUMA_GPU_ADMISSION_NO_STATIC_REFERENCE_PLACEMENT",
    "ACCELERATOR_EXECUTION_REQUIRES_HRB_LEASE_UUID_BDF",
    "CORRECTED_T7910_REFERENCE_E52696V4_44C88T_SM86_A1000_AUX_CONDITIONAL",
    "REFERENCE_CI_NOT_CURRENT_HOST_PROMOTION_EVIDENCE",
    "DISABLED_REFERENCE_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
]

PATHS = {
    "profile": "canonical/profiles/FA3-CLOSED-LOOP-AGENT-OPERATIONS-001.json",
    "contract": "canonical/contracts/FA3-CLOSED-LOOP-AGENT-OPERATIONS-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-LOOP-ENGINEERING-001.json",
    "decision": "canonical/decisions/FA3-DEC-LOOP-ENGINEERING-2026-09-03.json",
    "reference": "canonical/references/FA3-LOOP-ENGINEERING-UPSTREAM-REFERENCE-2026-09-03.json",
    "gate_record": "canonical/FA3-GATE-LOOP-ENGINEERING-001.json",
    "enforcement": "canonical/loop-engineering-enforcement.json",
    "admission": "canonical/loop-engineering-runtime-admission.json",
    "evidence": "evidence/reference/loop-engineering-ci-2026-09-03.json",
    "policy": "canonical/enforcement-policy.json",
}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}

def provider_not_authority(*, canonical_root: bool=False,
                           architectural_authority: bool=False) -> bool:
    return not canonical_root and not architectural_authority

def count_invariant(*, capability_count: int=143, new_capabilities: int=0,
                    new_authorities: int=0) -> bool:
    return capability_count == 143 and new_capabilities == 0 and new_authorities == 0

def immutable_pin_valid(commit: str) -> bool:
    return commit == PINNED_COMMIT and commit not in {"", "main", "master", "latest"}

def profile_projection_valid(*, canonical_root: bool, parent_profile: str,
                             relation: str, capability_id: str) -> bool:
    return (not canonical_root and parent_profile == "FA3-AGENT-EXEC-001"
            and relation == "SUBPROFILE-OF" and capability_id == CAPABILITY_ID)

def temporal_authority_valid(*, durable_authority: str,
                             provider_is_orchestrator: bool) -> bool:
    return durable_authority == "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY" and not provider_is_orchestrator

def reference_ci_valid(*, reference_pass: bool, current_host_claim: bool,
                       production_admission: bool) -> bool:
    return reference_pass and not current_host_claim and not production_admission

def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(rule: str, name: str, positive: bool, negative_rejected: bool) -> None:
        cases.append({
            "rule_id": rule,
            "name": name,
            "status": "PASS" if positive and negative_rejected else "FAIL",
            "positive_case": bool(positive),
            "negative_case_rejected": bool(negative_rejected),
        })

    add(P0_RULES[0], "provider never becomes authority",
        provider_not_authority(), not provider_not_authority(architectural_authority=True))
    add(P0_RULES[1], "143 capability and zero authority delta",
        count_invariant(), not count_invariant(capability_count=144, new_capabilities=1))
    add(P0_RULES[2], "immutable upstream pin",
        immutable_pin_valid(PINNED_COMMIT), not immutable_pin_valid("main"))
    add(P0_RULES[3], "closed-loop non-root Agent Exec projection",
        profile_projection_valid(canonical_root=False, parent_profile="FA3-AGENT-EXEC-001", relation="SUBPROFILE-OF", capability_id=CAPABILITY_ID),
        not profile_projection_valid(canonical_root=True, parent_profile="FA3-AGENT-EXEC-001", relation="ROOT", capability_id=CAPABILITY_ID))
    add(P0_RULES[4], "Temporal durable authority is preserved",
        temporal_authority_valid(durable_authority="TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY", provider_is_orchestrator=False),
        not temporal_authority_valid(durable_authority=PROVIDER_ID, provider_is_orchestrator=True))
    add(P0_RULES[5], "canonical lifecycle is complete and ordered",
        refimpl.lifecycle_valid(refimpl.CANONICAL_LIFECYCLE),
        not refimpl.lifecycle_valid(refimpl.CANONICAL_LIFECYCLE[:-1]))
    add(P0_RULES[6], "state is external durable and not chat authority",
        refimpl.durable_state_valid(external=True, durable=True, versioned=True, chat_is_authority=False, provider_neutral=True, partitioned=True, retention_policy=True),
        not refimpl.durable_state_valid(external=False, durable=False, versioned=False, chat_is_authority=True, provider_neutral=True, partitioned=True, retention_policy=True))
    add(P0_RULES[7], "state backend is provider-neutral versioned partitioned",
        refimpl.durable_state_valid(external=True, durable=True, versioned=True, chat_is_authority=False, provider_neutral=True, partitioned=True, retention_policy=True),
        not refimpl.durable_state_valid(external=True, durable=True, versioned=False, chat_is_authority=False, provider_neutral=False, partitioned=False, retention_policy=True))
    add(P0_RULES[8], "multi-loop state partition and retention",
        refimpl.durable_state_valid(external=True, durable=True, versioned=True, chat_is_authority=False, provider_neutral=True, partitioned=True, retention_policy=True),
        not refimpl.durable_state_valid(external=True, durable=True, versioned=True, chat_is_authority=False, provider_neutral=True, partitioned=False, retention_policy=False))
    add(P0_RULES[9], "L2/L3 maker checker session separation",
        refimpl.maker_checker_valid(level="L3_UNATTENDED", maker_session="maker", verifier_session="checker", verifier_restricted=True, verifier_self_repairs=False),
        not refimpl.maker_checker_valid(level="L3_UNATTENDED", maker_session="same", verifier_session="same", verifier_restricted=True, verifier_self_repairs=False))
    add(P0_RULES[10], "verifier restricted and does not self-repair",
        refimpl.maker_checker_valid(level="L2_ASSISTED", maker_session="m", verifier_session="v", verifier_restricted=True, verifier_self_repairs=False),
        not refimpl.maker_checker_valid(level="L2_ASSISTED", maker_session="m", verifier_session="v", verifier_restricted=False, verifier_self_repairs=True))
    add(P0_RULES[11], "progressive autonomy L0-L3",
        refimpl.autonomy_levels_valid(refimpl.AUTONOMY_LEVELS),
        not refimpl.autonomy_levels_valid(("L0_DRAFT", "L3_UNATTENDED")))
    add(P0_RULES[12], "L3 requires readiness evidence and gates",
        refimpl.l3_readiness_valid(level="L3_UNATTENDED", successful_history=True, verifier_reliable=True, budgeted=True, policy_gated=True, observable=True, kill_switch=True, deny_allow=True, human_gate=True),
        not refimpl.l3_readiness_valid(level="L3_UNATTENDED", successful_history=False, verifier_reliable=False, budgeted=True, policy_gated=True, observable=True, kill_switch=True, deny_allow=True, human_gate=True))
    add(P0_RULES[13], "risk incident drift cost cause demotion",
        refimpl.autonomy_demotion_required(incident=True),
        not refimpl.autonomy_demotion_required())
    limits = {"max_iterations":5,"max_attempts":3,"max_consecutive_failures":3,"same_error_repeat_limit":3,"no_progress_limit":3,"timeout_s":60,"token_limit":1000,"cost_limit":10,"tool_call_limit":20,"subagent_limit":4}
    add(P0_RULES[14], "circuit breaker bounds retries stagnation timeout",
        refimpl.circuit_breaker_stop({"attempts":3}, limits),
        not refimpl.circuit_breaker_stop({"attempts":1,"iterations":1,"elapsed_s":1}, limits))
    add(P0_RULES[15], "multi-dimensional budget bounded",
        refimpl.budget_valid(usage={"tokens":100,"cost":1,"wall":10,"tools":2,"subagents":1,"cpu":2,"ram":4,"vram":2,"api":1}, limits={"tokens":1000,"cost":10,"wall":100,"tools":20,"subagents":4,"cpu":8,"ram":64,"vram":12,"api":10}, self_raise=False, extension_human_approved=False),
        not refimpl.budget_valid(usage={"tokens":1001}, limits={"tokens":1000}, self_raise=False, extension_human_approved=False))
    add(P0_RULES[16], "agent cannot self-raise budget",
        refimpl.budget_valid(usage={"tokens":100}, limits={"tokens":1000}, self_raise=False, extension_human_approved=False),
        not refimpl.budget_valid(usage={"tokens":100}, limits={"tokens":1000}, self_raise=True, extension_human_approved=False))
    add(P0_RULES[17], "early exit no-op cheap triage",
        refimpl.early_exit_valid(high_frequency_or_costly=True, early_exit=True, no_op_path=True, cheap_triage=True),
        not refimpl.early_exit_valid(high_frequency_or_costly=True, early_exit=False, no_op_path=False, cheap_triage=False))
    add(P0_RULES[18], "L2+ mutation isolated workspace",
        refimpl.workspace_valid(level="L2_ASSISTED", mutating=True, isolated=True, lease=True, single_writer=True),
        not refimpl.workspace_valid(level="L2_ASSISTED", mutating=True, isolated=False, lease=True, single_writer=True))
    add(P0_RULES[19], "concurrent mutation lease lock single writer",
        refimpl.workspace_valid(level="L3_UNATTENDED", mutating=True, isolated=True, lease=True, single_writer=True),
        not refimpl.workspace_valid(level="L3_UNATTENDED", mutating=True, isolated=True, lease=False, single_writer=False))
    add(P0_RULES[20], "mechanical policy gate",
        refimpl.mechanical_policy_valid(mechanical_gate=True, denylist=True, allowlist=True, risk_classified=True),
        not refimpl.mechanical_policy_valid(mechanical_gate=False, denylist=True, allowlist=True, risk_classified=True))
    add(P0_RULES[21], "auto merge disabled by default",
        refimpl.auto_merge_valid(enabled=False, explicit_allowlist=False, low_risk=False, verifier_pass=False),
        not refimpl.auto_merge_valid(enabled=True, explicit_allowlist=False, low_risk=True, verifier_pass=True))
    add(P0_RULES[22], "high risk requires human gate",
        refimpl.high_risk_gate_valid(high_risk=True, human_approved=True),
        not refimpl.high_risk_gate_valid(high_risk=True, human_approved=False))
    add(P0_RULES[23], "MCP connector least privilege and L1 read-only",
        refimpl.connector_valid(level="L1_REPORT_ONLY", least_privilege=True, read_only=True),
        not refimpl.connector_valid(level="L1_REPORT_ONLY", least_privilege=True, read_only=False))
    add(P0_RULES[24], "state contract policy drift blocks L2/L3",
        refimpl.drift_preflight_valid(level="L3_UNATTENDED", hashes_match=True),
        not refimpl.drift_preflight_valid(level="L3_UNATTENDED", hashes_match=False))
    add(P0_RULES[25], "context compaction preserves provenance",
        refimpl.compaction_valid(required_provenance_ids={"a","b"}, retained_provenance_ids={"a","b","c"}),
        not refimpl.compaction_valid(required_provenance_ids={"a","b"}, retained_provenance_ids={"a"}))
    add(P0_RULES[26], "structured append-only observable run ledger",
        refimpl.observability_valid(append_only=True, otel_compatible=True, fields=refimpl.REQUIRED_OBSERVABILITY_FIELDS),
        not refimpl.observability_valid(append_only=False, otel_compatible=True, fields={"RUN_ID"}))
    add(P0_RULES[27], "pause kill retire and incident fallback",
        refimpl.lifecycle_control_valid(states=refimpl.REQUIRED_CONTROL_STATES, kill_switch=True, incident_fallback="REPORT_ONLY"),
        not refimpl.lifecycle_control_valid(states={"ACTIVE"}, kill_switch=False, incident_fallback="ACTIVE"))
    add(P0_RULES[28], "event-first; polling requires early exit and budget",
        refimpl.trigger_valid(mode="EVENT_DRIVEN", early_exit=False, budget_gate=False, no_op_path=False),
        not refimpl.trigger_valid(mode="FIXED_POLLING", early_exit=False, budget_gate=False, no_op_path=False))
    add(P0_RULES[29], "pattern registry typed versioned risk-cost gated",
        refimpl.pattern_registry_valid(typed=True, versioned=True, risk_cost_metadata=True, human_gate_metadata=True),
        not refimpl.pattern_registry_valid(typed=False, versioned=True, risk_cost_metadata=False, human_gate_metadata=True))
    add(P0_RULES[30], "CLI and Markdown formats are not hard dependencies",
        refimpl.cli_dependency_valid(node_required=False, markdown_required=False, specific_vendor_required=False, specific_scheduler_required=False),
        not refimpl.cli_dependency_valid(node_required=True, markdown_required=True, specific_vendor_required=False, specific_scheduler_required=False))
    add(P0_RULES[31], "HRB live CPU NUMA GPU admission",
        refimpl.hardware_admission_valid(live_discovery=True, hrb_lease=False, static_cpu_ids=False, reference_as_portable_default=False, accelerator_required=False, gpu_uuid=None, pci_bdf=None, ordinal_only=False),
        not refimpl.hardware_admission_valid(live_discovery=False, hrb_lease=False, static_cpu_ids=True, reference_as_portable_default=True, accelerator_required=False, gpu_uuid=None, pci_bdf=None, ordinal_only=False))
    add(P0_RULES[32], "accelerator execution requires HRB lease UUID+BDF",
        refimpl.hardware_admission_valid(live_discovery=True, hrb_lease=True, static_cpu_ids=False, reference_as_portable_default=False, accelerator_required=True, gpu_uuid="GPU-u", pci_bdf="0000:05:00.0", ordinal_only=False),
        not refimpl.hardware_admission_valid(live_discovery=True, hrb_lease=False, static_cpu_ids=False, reference_as_portable_default=False, accelerator_required=True, gpu_uuid=None, pci_bdf=None, ordinal_only=True))
    add(P0_RULES[33], "corrected T7910 reference hardware",
        refimpl.reference_hardware_valid(cpu="2x Intel Xeon E5-2696 v4 @ 2.20 GHz", physical_cores=44, logical_cpus=88, expected_numa_domains=2, compute_gpu="NVIDIA GeForce RTX 3080 12GB", compute_sm="SM86", aux_gpu_conditional=True),
        not refimpl.reference_hardware_valid(cpu="2x Intel Xeon E5-2697 v4 @ 2.30 GHz", physical_cores=36, logical_cpus=72, expected_numa_domains=2, compute_gpu="NVIDIA GeForce RTX 3080 12GB", compute_sm="SM86", aux_gpu_conditional=True))
    add(P0_RULES[34], "reference CI cannot claim current-host promotion",
        reference_ci_valid(reference_pass=True, current_host_claim=False, production_admission=False),
        not reference_ci_valid(reference_pass=True, current_host_claim=True, production_admission=True))
    add(P0_RULES[35], "disabled reference provider has zero near-zero runtime cost",
        refimpl.disabled_provider_valid(enabled=False, resident_processes=0, background_jobs=0, leases=0),
        not refimpl.disabled_provider_valid(enabled=False, resident_processes=1, background_jobs=1, leases=1))

    passed = sum(case["status"] == "PASS" for case in cases)
    return {
        "schema": "fa3.loop-engineering-regression-report.v1",
        "result": "PASS" if passed == len(cases) == len(P0_RULES) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
    }

def scan_authority(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    for path in sorted((root / "canonical").rglob("*.json")):
        scanned += 1
        try:
            obj = _load(path)
        except Exception as exc:
            findings.append(_finding("LOOP-AUTH-000", "JSON parse failure",
                                     file=str(path.relative_to(root)), error=str(exc)))
            continue
        def walk(value: Any, json_path: str="$") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    kp = f"{json_path}.{key}"
                    normalized = key.lower().replace("-", "_")
                    if "authority" in normalized and child == PROVIDER_ID:
                        findings.append(_finding(
                            "LOOP-AUTH-001",
                            "Loop Engineering provider assigned to an authority field",
                            file=str(path.relative_to(root)), path=kp,
                        ))
                    walk(child, kp)
            elif isinstance(value, list):
                for i, child in enumerate(value):
                    walk(child, f"{json_path}[{i}]")
        walk(obj)
    return {
        "result": "PASS" if not findings else "FAIL",
        "scanned_json_files": scanned,
        "findings": findings,
    }

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    docs: dict[str, dict[str, Any]] = {}
    for name, rel in PATHS.items():
        path = root / rel
        if not path.is_file():
            findings.append(_finding("LOOP-REF-001", "required file missing", path=rel))
            continue
        try:
            docs[name] = _load(path)
        except Exception as exc:
            findings.append(_finding("LOOP-REF-002", "invalid JSON", path=rel, error=str(exc)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile = docs["profile"]
    contract = docs["contract"]
    provider = docs["provider"]
    decision = docs["decision"]
    reference = docs["reference"]
    gate_record = docs["gate_record"]
    enforcement = docs["enforcement"]
    admission = docs["admission"]
    evidence = docs["evidence"]
    policy = docs["policy"]

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P0"
        and profile.get("requirement") == "MUST"
        and profile.get("canonical_root") is False
        and profile.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and profile.get("relationship") == "SUBPROFILE-OF"
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("capability_projection") == [CAPABILITY_ID]
        and contract.get("id") in profile.get("contracts", [])
        and profile.get("authority_boundaries", {}).get("durable_orchestration")
            == "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY"
    ):
        findings.append(_finding("LOOP-REF-003", "closed-loop profile drift"))

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("status") == "CANONICAL"
        and contract.get("provider_neutral") is True
        and contract.get("parent_profile") == PROFILE_ID
        and contract.get("source_pattern_provider") == PROVIDER_ID
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == CAPABILITY_COUNT
        and contract.get("canonical_lifecycle") == list(refimpl.CANONICAL_LIFECYCLE)
    ):
        findings.append(_finding("LOOP-REF-004", "closed-loop contract drift"))

    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("capability_projection") == [CAPABILITY_ID]
        and provider.get("runtime_activation_status") == RUNTIME_STATUS
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("immutable_upstream_tuple", {}).get("commit") == PINNED_COMMIT
        and provider.get("authority_boundaries", {}).get("durable_orchestration")
            == "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY"
    ):
        findings.append(_finding("LOOP-REF-005", "Loop Engineering provider drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("profile_id") == PROFILE_ID
        and decision.get("contract_id") == CONTRACT_ID
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("mandatory_p0_rules") == P0_RULES
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("LOOP-REF-006", "canonical decision drift"))

    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("repository") == "cobusgreyling/loop-engineering"
        and reference.get("immutable_observed_commit") == PINNED_COMMIT
        and reference.get("license", {}).get("spdx") == "MIT"
        and reference.get("promotion_evidence") is False
        and reference.get("current_host_runtime_evidence") is False
    ):
        findings.append(_finding("LOOP-REF-007", "upstream reference drift"))

    if not (
        gate_record.get("id") == EXECUTABLE_GATE_ID
        and gate_record.get("gateset_id") == GATE_ID
        and gate_record.get("fail_closed") is True
        and gate_record.get("regression_case_count") == len(P0_RULES)
    ):
        findings.append(_finding("LOOP-REF-008", "executable gate record drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("executable_gate_id") == EXECUTABLE_GATE_ID
        and enforcement.get("p0_invariants") == P0_RULES
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_activation_status") == RUNTIME_STATUS
    ):
        findings.append(_finding("LOOP-REF-009", "enforcement drift"))

    if not (
        admission.get("provider_id") == PROVIDER_ID
        and admission.get("status") == RUNTIME_STATUS
        and admission.get("production_provider_admission") is False
        and admission.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and admission.get("node_npm_required") is False
        and admission.get("markdown_state_backend_required") is False
    ):
        findings.append(_finding("LOOP-REF-010", "reference-only runtime admission drift"))

    if not (
        evidence.get("id") == EVIDENCE_ID
        and evidence.get("status") == "PASS"
        and evidence.get("regression_cases_total") == len(P0_RULES)
        and evidence.get("regression_cases_passed") == len(P0_RULES)
        and evidence.get("current_host_provider_runtime_evidence") is False
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("production_provider_admission_claim") is False
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(_finding("LOOP-REF-011", "reference evidence drift"))

    if not (
        GATE_ID in policy.get("mandatory_reference_gates", [])
        and policy.get("closed_loop_agent_operations_profile_id") == PROFILE_ID
        and policy.get("closed_loop_agent_operations_contract_id") == CONTRACT_ID
        and policy.get("loop_engineering_provider_id") == PROVIDER_ID
        and policy.get("loop_engineering_gate_id") == GATE_ID
        and policy.get("loop_engineering_capability_bindings") == [CAPABILITY_ID]
        and policy.get("loop_engineering_runtime_status") == RUNTIME_STATUS
        and policy.get("loop_engineering_upstream_pin") == PINNED_COMMIT
        and policy.get("loop_engineering_mandatory_p0_rules") == P0_RULES
    ):
        findings.append(_finding("LOOP-REF-012", "global policy binding drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority = scan_authority(root)
    regressions = run_regressions()
    ok = reference["result"] == authority["result"] == regressions["result"] == "PASS"
    report = {
        "schema": "fa3.loop-engineering-gate-report.v1",
        "gate_id": GATE_ID,
        "executable_gate_id": EXECUTABLE_GATE_ID,
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "provider_id": PROVIDER_ID,
        "capability_id": CAPABILITY_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "authority_scan": authority,
        "regressions": regressions,
        "runtime_provider_required": False,
        "current_host_provider_runtime_evidence": False,
        "runtime_activation_status": RUNTIME_STATUS,
    }
    _write(root / "reports/loop-engineering-gate-report.json", report)
    return report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
