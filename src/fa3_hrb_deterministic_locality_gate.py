#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE = "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
CONTRACT = "canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json"
ENFORCEMENT = "canonical/hrb-deterministic-locality-enforcement.json"
DECISION = "canonical/decisions/FA3-DEC-HRB-DETERMINISTIC-LOCALITY-2026-09-02.json"
PROVIDERS = [
    "canonical/providers/FA3-PROVIDER-SYSTEMD-CGROUPV2-001.json",
    "canonical/providers/FA3-PROVIDER-XANMOD-001.json",
    "canonical/providers/FA3-PROVIDER-SCHED-EXT-001.json",
]
GATE_ID = "FA3-GATE-HRB-DETERMINISTIC-LOCALITY-001"
CAPABILITY_COUNT = 143


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def evaluate(root: Path) -> dict[str, Any]:
    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    enforcement = loadj(root, ENFORCEMENT)
    decision = loadj(root, DECISION)
    providers = [loadj(root, path) for path in PROVIDERS]

    invariants = set(contract.get("invariants", []))
    enforced = set(enforcement.get("p0_invariants", []))
    provider_ids = {p.get("id") for p in providers}
    contracts = set(contract.get("contracts", []))
    forbidden_constants = " ".join(profile.get("deployment_policy_not_canonical_constants", [])).lower()
    systemd_provider = providers[0]
    manager_policy = systemd_provider.get("manager_global_defaults_policy", {})
    profile_manager_policy = profile.get("systemd_manager_defaults_policy", {})
    explicitly_not_baseline = " ".join(decision.get("explicitly_not_baseline", [])).lower()

    checks = [
        check("capability-count-stable", profile.get("capability_count") == CAPABILITY_COUNT == contract.get("capability_count") == decision.get("capability_count_after"), "capability count remains 143"),
        check("no-new-authority", profile.get("new_architectural_authority") is False and decision.get("new_architectural_authority") is False, "no parallel authority introduced"),
        check("hrb-authority-preserved", profile.get("existing_authority_id") == "FA3-AUTH-HOST-RESOURCE-BROKER-001", "HRB remains placement authority"),
        check("contract-linked", "FA3-HOST-RESOURCE-BROKER-CONTRACTS-001" in profile.get("contracts", []), "profile links deterministic locality contracts"),
        check("stable-accelerator-identity", {"AcceleratorAssignment", "AcceleratorIdentity", "HostTopologySnapshot"}.issubset(contracts) and "GPU_RUNTIME_INDEX_IS_NOT_CANONICAL_IDENTITY" in invariants, "UUID/BDF identity is canonical; runtime index is not"),
        check("fail-closed-routing", {"PRODUCTION_ACCELERATOR_ROUTING_FAIL_CLOSED", "NO_IMPLICIT_DISPLAY_COMPUTE_OR_COMPUTE_ACCELERATOR_FALLBACK"}.issubset(invariants), "implicit accelerator fallback denied"),
        check("typed-locality-policy", {"ExecutionPolicy", "ComputeCPUSet", "HousekeepingCPUSet", "MemoryPlacementPolicy", "IRQPlacementPolicy"}.issubset(contracts), "CPU memory accelerator IRQ locality are typed"),
        check("numa-policy-coherent", "EXPLICIT_NUMA_PINNING_DISALLOWS_COMPETING_AUTOMATIC_NUMA_MIGRATION" in invariants, "explicit NUMA placement cannot compete with automatic migration"),
        check("bounded-admission", "AdmissionQueueConcurrencyPolicy" in contracts and "ADMISSION_QUEUE_CONCURRENCY_MUST_BE_BOUNDED_AND_BACKPRESSURED" in invariants, "bounded queue/backpressure required"),
        check("model-residency-explicit", "ModelResidencyPolicy" in contracts and "MODEL_RESIDENCY_AND_EVICTION_POLICY_MUST_BE_EXPLICIT" in invariants, "model residency/eviction explicit"),
        check("cache-taxonomy", len(contract.get("cache_layer_taxonomy", [])) >= 7, "cache classes are separated"),
        check("zram-not-memory-tier", "CompressedSwapPolicy" in contracts and "COMPRESSED_SWAP_IS_PRESSURE_SAFETY_NOT_NORMAL_ACCELERATOR_MEMORY_TIER" in invariants, "compressed swap is pressure safety only"),
        check("no-global-magic-constants", all(token in forbidden_constants for token in ["32 gib zram", "18c/36t", "swappiness", "comfyui"]), "host/workload numeric tuning remains deployment policy"),
        check("execution-profiles", set(contract.get("execution_profiles", [])) == {"LATENCY", "BALANCED", "BATCH"}, "three canonical execution profile classes"),
        check("telemetry-evidence", {"PlacementEvidence", "AIExecutionTelemetry"}.issubset(contracts) and "P50_P95_P99_AND_TAIL_LATENCY_TELEMETRY_REQUIRED_FOR_LATENCY_PROFILE" in invariants, "placement and tail latency evidence required"),
        check("rollback", "ExecutionRollbackProfile" in contracts and "KERNEL_SCHEDULER_NUMA_IRQ_HUGEPAGE_ZRAM_SYSCTL_CHANGES_REQUIRE_ROLLBACK_PATH" in invariants, "tuning changes require rollback"),
        check("systemd-reference-only", "FA3-PROVIDER-SYSTEMD-CGROUPV2-001" in provider_ids and providers[0].get("new_architectural_authority") is False, "systemd/cgroup v2 is projection, not authority"),
        check("manager-defaults-neutral", profile_manager_policy.get("status") == "MANDATORY_NEUTRAL_BASELINE" and manager_policy.get("default") == "DO_NOT_USE_SYSTEM_MANAGER_GLOBAL_DEFAULTS_FOR_AI_HPC_WORKLOAD_PLACEMENT_OR_BUDGETING" and "SYSTEMD_MANAGER_GLOBAL_RESOURCE_DEFAULTS_MUST_REMAIN_NEUTRAL_UNLESS_EXPLICIT_HOST_SURVIVAL_POLICY_REQUIRES_CHANGE" in invariants, "AI/HPC tuning cannot become global systemd Manager resource defaults"),
        check("manager-affinity-numa-not-placement", set(manager_policy.get("forbidden_without_explicit_host_survival_policy", [])) == {"CPUAffinity", "NUMAPolicy", "NUMAMask"} and "GLOBAL_SYSTEMD_MANAGER_CPUAFFINITY_AND_NUMA_POLICY_MUST_NOT_REPLACE_HRB_PLACEMENT" in invariants, "global Manager CPU/NUMA affinity cannot replace HRB placement"),
        check("global-unbounded-limits-forbidden", all(token in explicitly_not_baseline for token in ["defaulttasksmax=infinity", "defaultlimitmemlock=infinity", "defaultlimitnproc=infinity"]) and "UNBOUNDED_TASK_NPROC_MEMLOCK_LIMITS_FOR_AI_WORKLOADS_ARE_FORBIDDEN_AS_GLOBAL_MANAGER_DEFAULTS" in invariants, "unbounded task nproc and memlock are per-workload policy, not global defaults"),
        check("memory-pressure-observability", "defaultmemorypressurewatch=no globally" in explicitly_not_baseline and "MEMORY_PRESSURE_OBSERVABILITY_MUST_NOT_BE_DISABLED_TO_HIDE_RESOURCE_EXHAUSTION" in invariants, "memory-pressure observability cannot be disabled to mask exhaustion"),
        check("oom-workload-scoped", "defaultoompolicy=continue globally" in explicitly_not_baseline and "OOM_POLICY_MUST_BE_WORKLOAD_SCOPED_AND_MUST_NOT_USE_GLOBAL_CONTINUE_AS_AI_BASELINE" in invariants, "OOM policy is workload-scoped and global continue is rejected"),
        check("restart-timeout-bounded-per-service", manager_policy.get("lifecycle_tuning_scope") == "PER_SERVICE_UNLESS_EXPLICIT_HOST_SURVIVAL_POLICY" and "RESTART_AND_TIMEOUT_POLICY_MUST_BE_BOUNDED_PER_SERVICE_AND_MUST_NOT_CREATE_RESTART_STORMS" in invariants, "restart and timeout tuning is per-service and bounded"),
        check("global-timer-baseline-forbidden", "defaulttimeraccuracysec=1ms globally" in explicitly_not_baseline and "GLOBAL_LOW_LATENCY_TIMER_ACCURACY_MUST_NOT_BE_USED_AS_AI_PERFORMANCE_BASELINE" in invariants, "global 1ms timer accuracy is not an AI performance baseline"),
        check("per-workload-projection-change-control", manager_policy.get("resource_tuning_scope") == "PER_SERVICE_SLICE_OR_SCOPE_FROM_HRB_RECEIPT" and "ResourcePolicyChangeSet" in contracts and "PER_WORKLOAD_SYSTEMD_CGROUP_PROJECTION_REQUIRES_HRB_RECEIPT_SEMANTIC_DIFF_ROLLBACK_AND_EVIDENCE" in invariants, "per-workload projection requires HRB receipt, semantic diff, rollback and evidence"),
        check("xanmod-optional", "FA3-PROVIDER-XANMOD-001" in provider_ids and providers[1].get("status") == "OPTIONAL_REFERENCE_PROVIDER", "XanMod is optional reference"),
        check("sched-ext-experimental", "FA3-PROVIDER-SCHED-EXT-001" in provider_ids and providers[2].get("status") == "EXPERIMENTAL_REFERENCE_PROVIDER", "sched_ext remains experimental"),
        check("legacy-schedulers-not-baseline", all(x in decision.get("explicitly_not_baseline", []) for x in ["PDS", "BMQ", "MuQSS", "PREEMPT_RT"]), "legacy/RT schedulers are not required baseline"),
        check("enforcement-complete", enforcement.get("fail_closed") is True and enforcement.get("mandatory_rule_count") == 34 and len(enforcement.get("rules", [])) == 34 and invariants == enforced, "all 30 contract invariants enforced fail-closed"),
        check("current-host-claim-honest", enforcement.get("current_host_runtime_promotion_claim") is False and "REFERENCE_CONFORMANCE_ONLY" in decision.get("current_host_claim", ""), "no uncollected current-host locality PASS is claimed"),
    ]
    passed = all(c["status"] == "PASS" for c in checks)
    return {
        "schema": "fa3.hrb-deterministic-locality-evidence.v1",
        "gate_id": GATE_ID,
        "status": "PASS" if passed else "FAIL",
        "scope": "CANONICAL_REFERENCE_CONFORMANCE",
        "current_host_runtime_promotion_claim": False,
        "checks": checks,
        "summary": {"passed": sum(c["status"] == "PASS" for c in checks), "total": len(checks)},
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    report = root / "reports/hrb-deterministic-locality-gate-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"result": result["status"], **result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--evidence")
    args = parser.parse_args()
    result = evaluate(Path(args.root).resolve())
    if args.evidence:
        out = Path(args.evidence)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
