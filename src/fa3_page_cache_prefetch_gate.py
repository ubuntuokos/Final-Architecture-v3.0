#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE = "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
CONTRACT = "canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json"
ENFORCEMENT = "canonical/page-cache-prefetch-enforcement.json"
DECISION = "canonical/decisions/FA3-DEC-PAGE-CACHE-PREFETCH-2026-09-11.json"
PROVIDER = "canonical/providers/FA3-PROVIDER-PRELOAD-001.json"
GATE_RECORD = "canonical/FA3-GATE-PAGE-CACHE-PREFETCH-001.json"
GATE_ID = "FA3-GATE-PAGE-CACHE-PREFETCH-001"
GATESET_ID = "FA3-PAGE-CACHE-PREFETCH-GATESET-001"
PARENT_GATE_ID = "FA3-HRB-DETERMINISTIC-LOCALITY-GATESET-001"
CAPABILITY_COUNT = 143

REQUIRED_CONTRACTS = {
    "PageCachePrefetchPolicy",
    "PrefetchProviderDescriptor",
    "PrefetchBenchmarkReceipt",
    "PrefetchRollbackReceipt",
}

REQUIRED_INVARIANTS = {
    "FILESYSTEM_PAGE_CACHE_REMAINS_PRIMARY",
    "PREFETCH_PROVIDER_IS_NON_AUTHORITY",
    "NO_GLOBAL_PREFETCH_MAGIC_CONSTANTS",
    "VIRTUAL_DEVICE_FILESYSTEMS_MUST_NOT_BE_PREFETCHED",
    "BROAD_HOME_TREE_PREFETCH_NOT_DEFAULT",
    "LARGE_MODEL_BLIND_PREFETCH_FORBIDDEN",
    "NO_PERIODIC_DROP_CACHES_OPTIMIZATION",
    "PREFETCH_REQUIRES_COLD_WARM_BENCHMARK_SEPARATION",
    "PREFETCH_REQUIRES_IO_AND_MEMORY_PRESSURE_EVIDENCE",
    "PREFETCH_CONFIGURATION_MUST_BE_ROLLBACKABLE",
    "PREFETCH_MUST_NOT_OVERRIDE_HRB_PLACEMENT",
    "DISABLED_PREFETCH_PROVIDER_MUST_HAVE_NEAR_ZERO_RUNTIME_COST",
}


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def evaluate(root: Path) -> dict[str, Any]:
    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    enforcement = loadj(root, ENFORCEMENT)
    decision = loadj(root, DECISION)
    provider = loadj(root, PROVIDER)
    gate_record = loadj(root, GATE_RECORD)

    contracts = set(contract.get("contracts", []))
    invariants = set(contract.get("invariants", []))
    page_cache_invariants = set(contract.get("page_cache_prefetch_invariants", []))
    enforced = set(enforcement.get("p0_invariants", []))
    provider_projection = profile.get("provider_projection_policy", {})
    page_policy = profile.get("page_cache_prefetch_governance", {})
    provider_config = provider.get("configuration_policy", {})
    rejected = " ".join(decision.get("rejected", [])).lower()
    not_constants = " ".join(profile.get("deployment_policy_not_canonical_constants", [])).lower()

    checks = [
        check(
            "capability-count-stable",
            profile.get("capability_count") == contract.get("capability_count") == enforcement.get("capability_count") == gate_record.get("capability_count") == CAPABILITY_COUNT,
            "page-cache hardening preserves the exact 143-capability catalog",
        ),
        check(
            "no-new-authority",
            profile.get("new_architectural_authority") is False
            and contract.get("new_architectural_authority") is False
            and provider.get("new_architectural_authority") is False
            and gate_record.get("new_architectural_authority") is False,
            "no cache/prefetch authority is introduced",
        ),
        check(
            "hrb-parent-authority",
            profile.get("existing_authority_id") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
            and provider.get("parent_profile_id") == "FA3-HOST-RESOURCE-BROKER-001",
            "prefetch remains subordinate to the existing Host Resource Broker",
        ),
        check(
            "typed-prefetch-contracts",
            REQUIRED_CONTRACTS.issubset(contracts),
            "policy, provider descriptor, benchmark receipt and rollback receipt are typed",
        ),
        check(
            "filesystem-page-cache-taxonomy",
            "FILESYSTEM_PAGE_CACHE" in contract.get("cache_layer_taxonomy", []),
            "filesystem page cache remains an explicit canonical cache layer",
        ),
        check(
            "mandatory-invariants-present",
            REQUIRED_INVARIANTS.issubset(invariants) and page_cache_invariants == REQUIRED_INVARIANTS,
            "all page-cache/prefetch P0 invariants are present in the HRB contract",
        ),
        check(
            "subgate-enforcement-exact",
            enforcement.get("gate_id") == GATESET_ID
            and enforcement.get("parent_gate_id") == PARENT_GATE_ID
            and enforcement.get("fail_closed") is True
            and enforcement.get("mandatory_rule_count") == 12
            and len(enforcement.get("rules", [])) == 12
            and enforced == REQUIRED_INVARIANTS,
            "dedicated subgate enforces the exact twelve P0 invariants fail-closed",
        ),
        check(
            "kernel-page-cache-primary",
            page_policy.get("kernel_page_cache") == "PRIMARY"
            and provider_config.get("kernel_page_cache") == "PRIMARY_CACHE_MECHANISM",
            "userspace prediction never replaces the kernel page cache",
        ),
        check(
            "provider-optional-non-authority",
            provider.get("status") == "OPTIONAL_REFERENCE_PROVIDER"
            and provider.get("requirement") == "MAY"
            and provider.get("default_activation") == "DISABLED_OR_EXPLICIT_HOST_POLICY_CONTROLLED"
            and provider.get("authority_boundary", "").startswith("MUST_NOT_OWN_HRB"),
            "preload is optional, replaceable and non-authoritative",
        ),
        check(
            "provider-projection-linked",
            provider_projection.get("linux_speculative_prefetch_optional_reference") == "FA3-PROVIDER-PRELOAD-001"
            and provider_projection.get("provider_hard_dependency") is False,
            "HRB exposes preload only as an optional provider projection",
        ),
        check(
            "no-global-magic-constants",
            provider_config.get("numeric_tuning") == "HOST_AND_WORKLOAD_BENCHMARK_DERIVED_NOT_CANONICAL_CONSTANTS"
            and all(token in not_constants for token in ["prefetch cycle", "prefetch memory", "prefetch process", "prefetch sort"]),
            "cycle, memory, concurrency and ordering values are not portable constants",
        ),
        check(
            "virtual-filesystems-denied",
            "virtual filesystems" in rejected or "/dev /proc /sys /run" in rejected,
            "kernel virtual/device filesystems are excluded from speculative prefetch",
        ),
        check(
            "home-tree-not-default",
            provider_config.get("home_directory") == "NO_BROAD_HOME_TREE_DEFAULT_ALLOWLIST"
            and "broad /home" in rejected,
            "broad home-tree prefetch is not a portable default",
        ),
        check(
            "large-model-blind-prefetch-forbidden",
            provider_config.get("large_model_files") == "NO_BLIND_WHOLE_MODEL_PREFETCH"
            and "large model" in rejected,
            "large model residency is not forced by blind whole-file reads",
        ),
        check(
            "drop-caches-optimization-forbidden",
            provider_config.get("drop_caches") == "PERIODIC_DROP_CACHES_FOR_PERFORMANCE_FORBIDDEN"
            and "drop_caches" in rejected,
            "periodic drop_caches is rejected as a performance optimization",
        ),
        check(
            "cold-warm-benchmark-separation",
            page_policy.get("benchmark_semantics") == "COLD_START_AND_WARM_STEADY_STATE_SEPARATE",
            "cold startup and warm/steady-state behavior are measured separately",
        ),
        check(
            "io-memory-pressure-evidence",
            set(page_policy.get("required_evidence", [])) >= {
                "startup_latency",
                "major_faults",
                "io_pressure",
                "memory_pressure",
                "host_survival",
            },
            "promotion requires observable I/O, fault, memory-pressure and survival evidence",
        ),
        check(
            "adaptive-readahead-benchmarked",
            page_policy.get("readahead_strategy") == "TOPOLOGY_AND_WORKLOAD_BENCHMARK_DERIVED",
            "adaptive readahead/storage ordering is benchmark-derived rather than hard-coded",
        ),
        check(
            "rollback-required",
            "PrefetchRollbackReceipt" in contracts
            and page_policy.get("rollback") == "REQUIRED",
            "prefetch activation and tuning are rollbackable",
        ),
        check(
            "cannot-override-placement",
            page_policy.get("placement_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001_ONLY"
            and "provider-selected numa cpu gpu or storage placement" in rejected,
            "prefetch providers cannot create parallel NUMA/CPU/GPU/storage placement policy",
        ),
        check(
            "disabled-provider-near-zero-cost",
            provider_config.get("disabled_cost") == "NEAR_ZERO"
            and page_policy.get("disabled_provider_runtime_cost") == "NEAR_ZERO",
            "disabled speculative-prefetch providers must not consume meaningful runtime resources",
        ),
        check(
            "gate-record-bound",
            gate_record.get("id") == GATE_ID
            and gate_record.get("gateset_id") == GATESET_ID
            and gate_record.get("parent_gate_id") == PARENT_GATE_ID
            and gate_record.get("global_binding") == "TRANSITIVELY_MANDATORY_THROUGH_FA3_HRB_DETERMINISTIC_LOCALITY_GATESET_001",
            "page-cache subgate is transitively bound to the already-mandatory HRB gateset",
        ),
        check(
            "current-host-claim-honest",
            enforcement.get("current_host_runtime_promotion_claim") is False
            and gate_record.get("current_host_runtime_promotion_claim") is False
            and decision.get("current_host_runtime_promotion", "").startswith("PENDING_REAL_CURRENT_HOST"),
            "canonical PASS does not fabricate a current-host performance promotion",
        ),
    ]

    passed = all(item["status"] == "PASS" for item in checks)
    return {
        "schema": "fa3.page-cache-prefetch-evidence.v1",
        "gate_id": GATE_ID,
        "gateset_id": GATESET_ID,
        "parent_gate_id": PARENT_GATE_ID,
        "status": "PASS" if passed else "FAIL",
        "scope": "CANONICAL_REFERENCE_CONFORMANCE",
        "current_host_runtime_promotion_claim": False,
        "checks": checks,
        "summary": {
            "passed": sum(item["status"] == "PASS" for item in checks),
            "total": len(checks),
        },
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    report = root / "reports/page-cache-prefetch-gate-report.json"
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
        output = Path(args.evidence)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
