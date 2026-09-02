#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from fa3_cpu_thread_budget import AdmissionDenied, build_thread_plan, make_reference_t7910_topology


PROFILE = "canonical/profiles/FA3-CPU-NUMA-THREADING-001.json"
CONTRACT = "canonical/contracts/FA3-CPU-NUMA-THREADING-CONTRACTS-001.json"
ENFORCEMENT = "canonical/cpu-numa-threading-enforcement.json"
DECISION = "canonical/decisions/FA3-DEC-CPU-NUMA-THREADING-2026-09-02.json"
REFERENCE = "canonical/references/FA3-T7910-CPU-NUMA-REFERENCE-2026-09-02.json"
HRB_PROFILE = "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
SYSTEMD_PROVIDER = "canonical/providers/FA3-PROVIDER-SYSTEMD-CGROUPV2-001.json"
GATE_ID = "FA3-GATE-CPU-NUMA-THREADING-001"
CAPABILITY_COUNT = 143


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def denied(call: Callable[[], object]) -> bool:
    try:
        call()
    except AdmissionDenied:
        return True
    return False


def _request(**overrides: Any) -> dict[str, Any]:
    request: dict[str, Any] = {
        "authority_receipt": "HRB_PLACEMENT_RECEIPT",
        "workload_class": "CPU_HOST_WIDE",
    }
    request.update(overrides)
    return request


def evaluate(root: Path) -> dict[str, Any]:
    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    enforcement = loadj(root, ENFORCEMENT)
    decision = loadj(root, DECISION)
    reference = loadj(root, REFERENCE)
    hrb = loadj(root, HRB_PROFILE)
    systemd = loadj(root, SYSTEMD_PROVIDER)
    invariants = set(contract.get("invariants", []))
    enforced = set(enforcement.get("p0_invariants", []))
    topology = make_reference_t7910_topology()

    host_plan = build_thread_plan(topology, _request())
    node0_cpus = [entry["cpu_id"] for entry in topology["logical_cpus"] if entry["numa_node"] == 0]
    node_plan = build_thread_plan(topology, _request(workload_class="CPU_NUMA_LOCAL", allowed_cpus=node0_cpus, numa_node=0))
    smt_plan = build_thread_plan(
        topology,
        _request(requested_threads=88, allow_smt=True, benchmark_evidence=True, explicit_smt_admission=True),
    )
    intel_plan = build_thread_plan(topology, _request(requested_threads=8, openmp_provider="INTEL_LIBIOMP"))
    generic_plan = build_thread_plan(topology, _request(requested_threads=8))

    ref_cpu = reference.get("declared_cpu_configuration", {})
    forbidden = " ".join(profile.get("explicitly_forbidden_as_global_baseline", [])).lower()
    runtime_env = host_plan["environment"]
    checks = [
        check("capability-count-stable", profile.get("capability_count") == CAPABILITY_COUNT == contract.get("capability_count") == decision.get("capability_count_after"), "capability count remains 143"),
        check("no-new-authority", profile.get("new_architectural_authority") is False and contract.get("new_architectural_authority") is False and decision.get("new_architectural_authority") is False, "no parallel resource authority introduced"),
        check("mandatory-subprofile", profile.get("requirement") == "MUST" and profile.get("parent_profile_id") == "FA3-HOST-RESOURCE-BROKER-001" and profile.get("profile_alias") == "PROFILE-CPU-NUMA", "PROFILE-CPU-NUMA is an HRB subprofile"),
        check("contract-and-provider-linked", contract.get("id") in hrb.get("contracts", []) and systemd.get("delegates_authority_to") == "FA3-AUTH-HOST-RESOURCE-BROKER-001", "HRB contracts and systemd projection are linked"),
        check("reference-host-corrected", ref_cpu.get("model") == "Intel Xeon E5-2696 v4" and ref_cpu.get("physical_cores_total") == 44 and ref_cpu.get("logical_cpus_total") == 88, "T7910 reference is 2x E5-2696 v4 / 44C / 88T"),
        check("obsolete-host-reference-superseded", "E5-2697 v4" in reference.get("correction", {}).get("supersedes_reference_claim", "") and reference.get("status") == "REFERENCE_DEPLOYMENT", "obsolete 36C/72T reference is explicitly superseded without becoming hardware identity"),
        check("reference-topology-fixture", host_plan["visible_physical_cores"] == 44 and host_plan["visible_logical_cpus"] == 88, "reference topology exposes 44 physical and 88 logical CPUs"),
        check("hrb-authority-required", denied(lambda: build_thread_plan(topology, {"requested_threads": 8})), "missing HRB placement receipt is denied"),
        check("live-discovery-contract", "TOPOLOGY_MUST_BE_LIVE_DISCOVERED_AND_VALIDATED_AT_BOOT_OR_ADMISSION" in invariants and reference.get("admission_requirement"), "boot/admission topology validation is mandatory"),
        check("global-nproc-fanout-forbidden", all(token in forbidden for token in ["nproc", "omp_num_threads=88", "numexpr_num_threads=44", "environment variables"]), "global nproc and fixed thread fan-out are forbidden"),
        check("physical-core-first-hostwide", host_plan["thread_budget"] == 44 and not host_plan["uses_smt_above_physical_budget"], "host-wide default stops at physical cores"),
        check("cpuset-numa-aware", node_plan["visible_physical_cores"] == 22 and node_plan["thread_budget"] == 22 and node_plan["numa_node"] == 0, "NUMA-local admitted cpuset yields 22 physical-core threads"),
        check("dual-instance-reference", any(item.get("physical_core_threads") == "22+22" for item in reference.get("reference_thread_profiles_not_canonical_constants", [])), "2x22 is a reference multi-instance pattern, not a portable constant"),
        check("smt-denied-without-evidence", denied(lambda: build_thread_plan(topology, _request(requested_threads=88))), "88-thread SMT request fails closed without evidence"),
        check("smt-admitted-with-evidence", smt_plan["thread_budget"] == 88 and smt_plan["uses_smt_above_physical_budget"], "SMT can be admitted only with benchmark and explicit admission"),
        check("interleave-all-benchmark-gated", denied(lambda: build_thread_plan(topology, _request(numa_policy="interleave_all"))), "interleave-all is not the default and is benchmark gated"),
        check("openmp-spread-benchmark-gated", denied(lambda: build_thread_plan(topology, _request(omp_proc_bind="spread"))), "OpenMP spread is benchmark gated"),
        check("math-pools-bounded", all(int(runtime_env[key]) <= host_plan["thread_budget"] for key in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_MAX_THREADS", "NUMEXPR_NUM_THREADS"]), "OpenMP MKL OpenBLAS and NumExpr remain inside budget"),
        check("portable-openmp-baseline", runtime_env.get("OMP_PLACES") == "cores" and runtime_env.get("OMP_PROC_BIND") == "close" and runtime_env.get("OMP_DYNAMIC") == "FALSE" and runtime_env.get("OMP_MAX_ACTIVE_LEVELS") == "1", "portable OpenMP core placement and non-nested defaults are applied"),
        check("numexpr-conservative-default", runtime_env.get("NUMEXPR_NUM_THREADS") == "8" and denied(lambda: build_thread_plan(topology, _request(requested_threads=8, numexpr_threads=9))), "NumExpr defaults to min(8,budget) and cannot exceed budget"),
        check("pytorch-intra-inter-separated", host_plan["pytorch"]["intra_op_threads"] == 44 and host_plan["pytorch"]["inter_op_threads"] == 2 and host_plan["pytorch"]["apply_before_parallel_execution"], "PyTorch intra-op and inter-op budgets are separate"),
        check("intel-kmp-provider-scoped", "KMP_AFFINITY" in intel_plan["provider_settings"] and "KMP_AFFINITY" not in generic_plan["provider_settings"] and "DNNL_VERBOSE" in generic_plan["logging_settings"], "KMP is Intel-provider scoped and oneDNN verbosity is logging only"),
        check("enforcement-complete", enforcement.get("fail_closed") is True and enforcement.get("mandatory_rule_count") == 24 and len(enforcement.get("rules", [])) == 24 and invariants == enforced, "all 24 contract invariants are enforced fail-closed"),
        check("current-host-claim-honest", enforcement.get("current_host_runtime_promotion_claim") is False and "CURRENT_T7910_HOST" in decision.get("current_host_claim", ""), "reference PASS does not claim current-host runtime promotion"),
    ]
    passed = all(item["status"] == "PASS" for item in checks)
    return {
        "schema": "fa3.cpu-numa-threading-evidence.v1",
        "gate_id": GATE_ID,
        "status": "PASS" if passed else "FAIL",
        "scope": "CANONICAL_REFERENCE_RUNTIME_CONFORMANCE",
        "current_host_runtime_promotion_claim": False,
        "runtime_scenarios": 11,
        "checks": checks,
        "summary": {"passed": sum(item["status"] == "PASS" for item in checks), "total": len(checks)},
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    report = root / "reports/cpu-numa-threading-gate-report.json"
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
