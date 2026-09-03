#!/usr/bin/env python3
from __future__ import annotations

from typing import Iterable, Mapping

AUTONOMY_LEVELS = ("L0_DRAFT", "L1_REPORT_ONLY", "L2_ASSISTED", "L3_UNATTENDED")
CANONICAL_LIFECYCLE = (
    "TRIGGER_OR_EVENT",
    "LOAD_DEFINITION_POLICY_STATE",
    "CAPABILITY_PERMISSION_BUDGET_PREFLIGHT",
    "CONTRACT_STATE_POLICY_DRIFT_CHECK",
    "DISCOVER_TRIAGE",
    "CLAIM_WORK_ITEM_AND_LEASE",
    "ISOLATED_WORKSPACE",
    "MAKER_EXECUTION",
    "INDEPENDENT_VERIFICATION",
    "POLICY_AND_HUMAN_GATE",
    "APPLY_PR_OR_ESCALATE",
    "DURABLE_STATE_AND_APPEND_ONLY_RUN_LOG",
    "CONTINUE_PAUSE_RETIRE",
)
REQUIRED_OBSERVABILITY_FIELDS = {
    "RUN_ID", "LOOP_PATTERN_VERSION", "TRIGGER", "TIMESTAMPS", "STATE_HASH",
    "MODEL_PROVIDER_VERSION", "WORK_ITEM", "ATTEMPTS", "VERIFIER_RESULT",
    "POLICY_DECISIONS", "HUMAN_GATES", "CHANGED_ARTIFACTS",
    "TOKEN_COST_TOOL_USAGE", "ESCALATIONS", "OUTCOME", "FAILURE_MODE",
}
REQUIRED_CONTROL_STATES = {
    "ACTIVE", "PAUSED", "DEGRADED", "REPORT_ONLY", "BLOCKED", "KILLED", "RETIRED",
}

def lifecycle_valid(stages: Iterable[str]) -> bool:
    return tuple(stages) == CANONICAL_LIFECYCLE

def durable_state_valid(*, external: bool, durable: bool, versioned: bool,
                        chat_is_authority: bool, provider_neutral: bool,
                        partitioned: bool, retention_policy: bool) -> bool:
    return all((external, durable, versioned, provider_neutral, partitioned, retention_policy)) and not chat_is_authority

def maker_checker_valid(*, level: str, maker_session: str, verifier_session: str,
                        verifier_restricted: bool, verifier_self_repairs: bool) -> bool:
    if level not in {"L2_ASSISTED", "L3_UNATTENDED"}:
        return True
    return bool(maker_session and verifier_session) and maker_session != verifier_session and verifier_restricted and not verifier_self_repairs

def autonomy_levels_valid(levels: Iterable[str]) -> bool:
    return tuple(levels) == AUTONOMY_LEVELS

def l3_readiness_valid(*, level: str, successful_history: bool, verifier_reliable: bool,
                       budgeted: bool, policy_gated: bool, observable: bool,
                       kill_switch: bool, deny_allow: bool, human_gate: bool) -> bool:
    if level != "L3_UNATTENDED":
        return True
    return all((successful_history, verifier_reliable, budgeted, policy_gated,
                observable, kill_switch, deny_allow, human_gate))

def autonomy_demotion_required(*, incident: bool=False, policy_violation: bool=False,
                               cost_spike: bool=False, failure_rate_bad: bool=False,
                               drift: bool=False) -> bool:
    return any((incident, policy_violation, cost_spike, failure_rate_bad, drift))

def circuit_breaker_stop(metrics: Mapping[str, float], limits: Mapping[str, float]) -> bool:
    pairs = (
        ("iterations", "max_iterations"),
        ("attempts", "max_attempts"),
        ("consecutive_failures", "max_consecutive_failures"),
        ("same_error_repeats", "same_error_repeat_limit"),
        ("no_progress", "no_progress_limit"),
        ("elapsed_s", "timeout_s"),
        ("tokens", "token_limit"),
        ("cost", "cost_limit"),
        ("tool_calls", "tool_call_limit"),
        ("subagents", "subagent_limit"),
    )
    return any(float(metrics.get(m, 0)) >= float(limits[l]) for m, l in pairs if l in limits)

def budget_valid(*, usage: Mapping[str, float], limits: Mapping[str, float],
                 self_raise: bool, extension_human_approved: bool) -> bool:
    if self_raise and not extension_human_approved:
        return False
    return all(float(usage.get(k, 0)) <= float(v) for k, v in limits.items())

def early_exit_valid(*, high_frequency_or_costly: bool, early_exit: bool,
                     no_op_path: bool, cheap_triage: bool) -> bool:
    return (not high_frequency_or_costly) or all((early_exit, no_op_path, cheap_triage))

def workspace_valid(*, level: str, mutating: bool, isolated: bool,
                    lease: bool, single_writer: bool) -> bool:
    if not mutating or level in {"L0_DRAFT", "L1_REPORT_ONLY"}:
        return True
    return isolated and lease and single_writer

def mechanical_policy_valid(*, mechanical_gate: bool, denylist: bool,
                            allowlist: bool, risk_classified: bool) -> bool:
    return all((mechanical_gate, denylist, allowlist, risk_classified))

def auto_merge_valid(*, enabled: bool, explicit_allowlist: bool,
                     low_risk: bool, verifier_pass: bool) -> bool:
    return (not enabled) or all((explicit_allowlist, low_risk, verifier_pass))

def high_risk_gate_valid(*, high_risk: bool, human_approved: bool) -> bool:
    return (not high_risk) or human_approved

def connector_valid(*, level: str, least_privilege: bool, read_only: bool) -> bool:
    return least_privilege and (level != "L1_REPORT_ONLY" or read_only)

def drift_preflight_valid(*, level: str, hashes_match: bool) -> bool:
    return level not in {"L2_ASSISTED", "L3_UNATTENDED"} or hashes_match

def compaction_valid(*, required_provenance_ids: Iterable[str],
                     retained_provenance_ids: Iterable[str]) -> bool:
    return set(required_provenance_ids).issubset(set(retained_provenance_ids))

def observability_valid(*, append_only: bool, otel_compatible: bool,
                        fields: Iterable[str]) -> bool:
    return append_only and otel_compatible and REQUIRED_OBSERVABILITY_FIELDS.issubset(set(fields))

def lifecycle_control_valid(*, states: Iterable[str], kill_switch: bool,
                            incident_fallback: str) -> bool:
    return REQUIRED_CONTROL_STATES.issubset(set(states)) and kill_switch and incident_fallback in {"REPORT_ONLY", "PAUSED"}

def trigger_valid(*, mode: str, early_exit: bool, budget_gate: bool,
                  no_op_path: bool) -> bool:
    if mode in {"EVENT_DRIVEN", "CHANGE_WATCH"}:
        return True
    if mode in {"ADAPTIVE_POLLING", "FIXED_POLLING"}:
        return all((early_exit, budget_gate, no_op_path))
    return False

def pattern_registry_valid(*, typed: bool, versioned: bool,
                           risk_cost_metadata: bool, human_gate_metadata: bool) -> bool:
    return all((typed, versioned, risk_cost_metadata, human_gate_metadata))

def cli_dependency_valid(*, node_required: bool, markdown_required: bool,
                         specific_vendor_required: bool, specific_scheduler_required: bool) -> bool:
    return not any((node_required, markdown_required, specific_vendor_required, specific_scheduler_required))

def hardware_admission_valid(*, live_discovery: bool, hrb_lease: bool,
                             static_cpu_ids: bool, reference_as_portable_default: bool,
                             accelerator_required: bool, gpu_uuid: str | None,
                             pci_bdf: str | None, ordinal_only: bool) -> bool:
    if not live_discovery or static_cpu_ids or reference_as_portable_default or ordinal_only:
        return False
    if accelerator_required:
        return hrb_lease and bool(gpu_uuid) and bool(pci_bdf)
    return True

def portable_hardware_floor_valid(*, cpu_packages: int,
                                  physical_cores_per_package: int,
                                  cpu_vendor_pinned: bool,
                                  cpu_model_pinned: bool,
                                  gpu_count: int,
                                  gpu_rtx_series: int,
                                  gpu_specific_sku_pinned: bool,
                                  gpu_specific_vram_pinned: bool,
                                  gpu_specific_sm_pinned: bool,
                                  newer_rtx_generations_allowed: bool) -> bool:
    return (
        cpu_packages >= 1
        and physical_cores_per_package >= 8
        and not cpu_vendor_pinned
        and not cpu_model_pinned
        and gpu_count >= 1
        and gpu_rtx_series >= 30
        and not gpu_specific_sku_pinned
        and not gpu_specific_vram_pinned
        and not gpu_specific_sm_pinned
        and newer_rtx_generations_allowed
    )

def disabled_provider_valid(*, enabled: bool, resident_processes: int,
                            background_jobs: int, leases: int) -> bool:
    return enabled or (resident_processes == 0 and background_jobs == 0 and leases == 0)
