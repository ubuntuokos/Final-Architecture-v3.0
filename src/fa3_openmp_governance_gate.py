#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from fa3_cpu_thread_budget import build_thread_plan, make_synthetic_dual_numa_topology
from fa3_openmp_governance import (
    OpenMPAdmissionDenied,
    build_openmp_plan,
    classify_runtime_libraries,
    validate_observed_runtime,
)
from fa3_release_baseline import module_active_capability_count


PROFILE = "canonical/profiles/FA3-OPENMP-RUNTIME-GOVERNANCE-001.json"
CONTRACT = "canonical/contracts/FA3-OPENMP-RUNTIME-GOVERNANCE-CONTRACTS-001.json"
ENFORCEMENT = "canonical/openmp-runtime-governance-enforcement.json"
GATE_ID = "FA3-GATE-OPENMP-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def denied(call: Callable[[], object]) -> bool:
    try:
        call()
    except OpenMPAdmissionDenied:
        return True
    return False


def _thread_plan() -> dict[str, Any]:
    topology = make_synthetic_dual_numa_topology()
    return build_thread_plan(
        topology,
        {
            "authority_receipt": "HRB_PLACEMENT_RECEIPT",
            "requested_threads": 8,
        },
    )


def evaluate(root: Path) -> dict[str, Any]:
    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    enforcement = loadj(root, ENFORCEMENT)
    invariants = set(contract.get("invariants", []))
    enforced = set(enforcement.get("rules", []))
    base = _thread_plan()

    generic = build_openmp_plan(
        base,
        {},
        inherited_env={
            "OMP_NUM_THREADS": "999",
            "GOMP_CPU_AFFINITY": "0-63",
            "PATH": "/usr/bin",
        },
        runtime_libraries=["/usr/lib/libgomp.so.1"],
    )
    target = build_openmp_plan(
        base,
        {
            "target_offload": {
                "requested": True,
                "hrb_accelerator_lease": True,
                "stable_device_identity": "ACCELERATOR-UUID-EXAMPLE",
                "device_ordinal": 0,
            }
        },
        runtime_libraries=["/usr/lib/libomp.so"],
    )
    observed_pass = validate_observed_runtime(
        generic,
        {
            "max_threads": 8,
            "admitted_cpus": list(range(8)),
            "observed_cpus": [0, 1, 2, 3],
            "effective_dynamic": False,
        },
    )
    observed_escape = validate_observed_runtime(
        generic,
        {
            "max_threads": 8,
            "admitted_cpus": list(range(8)),
            "observed_cpus": [0, 1, 9],
            "effective_dynamic": False,
        },
    )

    runtime_collision = classify_runtime_libraries(
        ["/usr/lib/libgomp.so.1", "/opt/intel/lib/libiomp5.so"]
    )

    checks = [
        check(
            "baseline-stable",
            profile.get("capability_count") == CAPABILITY_COUNT == contract.get("capability_count") == enforcement.get("capability_count"),
            "OpenMP governance follows the active capability baseline without adding a capability",
        ),
        check(
            "no-new-authority",
            profile.get("new_architectural_authority") is False
            and contract.get("new_architectural_authority") is False
            and profile.get("authority", {}).get("resource_admission") == "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "OpenMP remains a consumer of HRB admission",
        ),
        check(
            "contract-enforcement-complete",
            enforcement.get("fail_closed") is True
            and enforcement.get("mandatory_rule_count") == 24
            and len(invariants) == 24
            and invariants == enforced,
            "all OpenMP P0 invariants are represented by fail-closed enforcement",
        ),
        check(
            "runtime-discovery",
            generic["runtime"]["status"] == "SINGLE_RUNTIME"
            and generic["runtime"]["families"] == ["GNU_LIBGOMP"],
            "loaded OpenMP runtime family is classified explicitly",
        ),
        check(
            "multiple-runtime-conflict",
            runtime_collision["status"] == "MULTIPLE_RUNTIME_CONFLICT"
            and denied(lambda: build_openmp_plan(
                base,
                {},
                runtime_libraries=["/usr/lib/libgomp.so.1", "/opt/intel/lib/libiomp5.so"],
            )),
            "multiple OpenMP runtime families fail closed without compatibility evidence",
        ),
        check(
            "environment-sanitized",
            generic["environment_sanitization"]["removed"].get("OMP_NUM_THREADS") == "999"
            and generic["environment_sanitization"]["removed"].get("GOMP_CPU_AFFINITY") == "0-63"
            and generic["effective_child_environment"]["OMP_NUM_THREADS"] == "8"
            and generic["effective_child_environment"]["PATH"] == "/usr/bin",
            "inherited OMP/GOMP/KMP values are removed only from the child environment and HRB projection wins",
        ),
        check(
            "nested-default-deny",
            denied(lambda: build_openmp_plan(base, {"max_active_levels": 2})),
            "nested parallelism requires explicit hierarchical admission and evidence",
        ),
        check(
            "nested-budget-bounded",
            denied(lambda: build_openmp_plan(
                base,
                {
                    "max_active_levels": 2,
                    "nested_parallelism_admitted": True,
                    "benchmark_evidence": True,
                    "outer_team_threads": 4,
                    "inner_team_threads": 4,
                },
            )),
            "nested team product cannot exceed the admitted HRB thread budget",
        ),
        check(
            "active-wait-gated",
            denied(lambda: build_openmp_plan(base, {"wait_policy": "ACTIVE"})),
            "spin-heavy ACTIVE wait requires latency-sensitive admission",
        ),
        check(
            "schedule-gated",
            denied(lambda: build_openmp_plan(base, {"schedule": "dynamic"})),
            "non-static scheduling requires benchmark evidence",
        ),
        check(
            "stack-accounting",
            denied(lambda: build_openmp_plan(base, {"stack_size": "16M"}))
            and denied(lambda: build_openmp_plan(
                base,
                {"stack_size": "16M", "hrb_memory_budget_bytes": 64 * 1024 * 1024},
            )),
            "worker stack memory is part of HRB memory admission",
        ),
        check(
            "cpu-only-preserved",
            generic["target_offload"]["enabled"] is False,
            "OpenMP remains valid on CPU-only systems",
        ),
        check(
            "target-lease-required",
            denied(lambda: build_openmp_plan(
                base,
                {"target_offload": {"requested": True, "stable_device_identity": "X", "device_ordinal": 0}},
            )),
            "target offload cannot select an accelerator without an HRB lease",
        ),
        check(
            "target-stable-id-required",
            denied(lambda: build_openmp_plan(
                base,
                {"target_offload": {"requested": True, "hrb_accelerator_lease": True, "device_ordinal": 0}},
            )),
            "target offload requires an HRB-bound stable device identity",
        ),
        check(
            "target-fallback-forbidden",
            target["environment"]["OMP_TARGET_OFFLOAD"] == "MANDATORY"
            and target["target_offload"]["silent_host_fallback_allowed"] is False,
            "accelerator request forbids silent host fallback",
        ),
        check(
            "target-ordinal-is-projection",
            target["environment"]["OMP_DEFAULT_DEVICE"] == "0"
            and target["target_offload"]["stable_device_identity"] == "ACCELERATOR-UUID-EXAMPLE",
            "device ordinal is projected only after stable HRB identity binding",
        ),
        check(
            "observed-placement-pass",
            observed_pass["status"] == "PASS",
            "observed worker placement inside admitted cpuset passes",
        ),
        check(
            "observed-placement-escape-fails",
            observed_escape["status"] == "FAIL"
            and "OPENMP_CPUSET_ESCAPE" in observed_escape["findings"],
            "observed worker escape from HRB cpuset fails closed",
        ),
        check(
            "dynamic-runtime-observation-fails",
            validate_observed_runtime(
                generic,
                {
                    "max_threads": 8,
                    "admitted_cpus": list(range(8)),
                    "observed_cpus": [0, 1],
                    "effective_dynamic": True,
                },
            )["status"] == "FAIL",
            "runtime dynamic resizing is rejected by the bounded plan",
        ),
        check(
            "observed-thread-overrun-fails",
            validate_observed_runtime(
                generic,
                {
                    "max_threads": 9,
                    "admitted_cpus": list(range(8)),
                    "observed_cpus": [0, 1],
                    "effective_dynamic": False,
                },
            )["status"] == "FAIL",
            "observed OpenMP max thread count cannot exceed HRB budget",
        ),
        check(
            "target-observation-fails-host-fallback",
            validate_observed_runtime(
                target,
                {
                    "max_threads": 8,
                    "admitted_cpus": list(range(8)),
                    "observed_cpus": [0, 1],
                    "effective_dynamic": False,
                    "target_executed_on_host": True,
                    "target_device_ordinal": 0,
                },
            )["status"] == "FAIL",
            "host execution cannot masquerade as requested accelerator offload",
        ),
        check(
            "target-observation-fails-wrong-device",
            validate_observed_runtime(
                target,
                {
                    "max_threads": 8,
                    "admitted_cpus": list(range(8)),
                    "observed_cpus": [0, 1],
                    "effective_dynamic": False,
                    "target_executed_on_host": False,
                    "target_device_ordinal": 1,
                },
            )["status"] == "FAIL",
            "observed target device must match the HRB projection",
        ),
        check(
            "reproducibility-declared",
            denied(lambda: build_openmp_plan(
                base,
                {"determinism_requirement": "REPRODUCIBLE"},
                runtime_libraries=["/usr/lib/libgomp.so.1"],
            )),
            "reproducible reduction claims require runtime support evidence",
        ),
        check(
            "no-current-host-overclaim",
            profile.get("current_host_runtime_promotion_claim") is False
            and enforcement.get("current_host_runtime_promotion_claim") is False,
            "static OpenMP governance does not create current-host runtime PASS",
        ),
    ]

    passed = all(item["status"] == "PASS" for item in checks)
    return {
        "schema": "fa3.openmp-runtime-governance-evidence.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if passed else "FAIL",
        "scope": "CANONICAL_PORTABLE_RUNTIME_CONFORMANCE",
        "current_host_runtime_promotion_claim": False,
        "checks": checks,
        "summary": {
            "passed": sum(item["status"] == "PASS" for item in checks),
            "total": len(checks),
        },
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    report = root / "reports/openmp-runtime-governance-gate-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = evaluate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
