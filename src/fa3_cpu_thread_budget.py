#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable


class AdmissionDenied(ValueError):
    """Fail-closed CPU thread-budget admission error."""


def discover_live_topology() -> dict[str, Any]:
    allowed = sorted(os.sched_getaffinity(0))
    logical_cpus: list[dict[str, int]] = []
    for cpu in allowed:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            socket_id = int((topology / "physical_package_id").read_text().strip())
            core_id = int((topology / "core_id").read_text().strip())
        except (FileNotFoundError, ValueError) as exc:
            raise AdmissionDenied(f"cannot discover topology for allowed CPU {cpu}") from exc
        numa_node = -1
        for candidate in Path(f"/sys/devices/system/cpu/cpu{cpu}").glob("node[0-9]*"):
            try:
                numa_node = int(candidate.name[4:])
                break
            except ValueError:
                continue
        logical_cpus.append(
            {"cpu_id": cpu, "socket_id": socket_id, "core_id": core_id, "numa_node": numa_node}
        )
    return {
        "schema": "fa3.cpu-thread-topology-snapshot.v1",
        "source": "LIVE_OS_AFFINITY_AND_SYSFS",
        "allowed_cpus": allowed,
        "logical_cpus": logical_cpus,
    }


def make_reference_t7910_topology() -> dict[str, Any]:
    logical: list[dict[str, int]] = []
    cpu_id = 0
    for socket_id in range(2):
        for core_id in range(22):
            for _smt_thread in range(2):
                logical.append(
                    {
                        "cpu_id": cpu_id,
                        "socket_id": socket_id,
                        "core_id": core_id,
                        "numa_node": socket_id,
                    }
                )
                cpu_id += 1
    return {
        "schema": "fa3.cpu-thread-topology-snapshot.v1",
        "source": "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST",
        "reference_deployment_id": "FA3-T7910-CPU-NUMA-REFERENCE-2026-09-02",
        "allowed_cpus": list(range(88)),
        "logical_cpus": logical,
    }


def _selected_entries(topology: dict[str, Any], request: dict[str, Any]) -> list[dict[str, int]]:
    entries = topology.get("logical_cpus")
    if not isinstance(entries, list) or not entries:
        raise AdmissionDenied("topology has no logical CPUs")
    topology_allowed = set(topology.get("allowed_cpus", []))
    placement_allowed = set(request.get("allowed_cpus", topology_allowed))
    selected_ids = topology_allowed & placement_allowed
    if not selected_ids:
        raise AdmissionDenied("admitted cpuset and visible affinity do not intersect")
    selected = [entry for entry in entries if entry.get("cpu_id") in selected_ids]
    numa_node = request.get("numa_node")
    if numa_node is not None:
        selected = [entry for entry in selected if entry.get("numa_node") == numa_node]
    if not selected:
        raise AdmissionDenied("placement selects no logical CPUs after NUMA filtering")
    return selected


def _unique_physical_cores(entries: Iterable[dict[str, int]]) -> set[tuple[int, int]]:
    return {(int(entry["socket_id"]), int(entry["core_id"])) for entry in entries}


def build_thread_plan(topology: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    if request.get("authority_receipt") != "HRB_PLACEMENT_RECEIPT":
        raise AdmissionDenied("thread budgets require an HRB placement receipt")
    selected = _selected_entries(topology, request)
    logical_budget = len({int(entry["cpu_id"]) for entry in selected})
    physical_budget = len(_unique_physical_cores(selected))
    if physical_budget < 1:
        raise AdmissionDenied("no physical cores are visible in the admitted cpuset")

    requested = int(request.get("requested_threads") or physical_budget)
    if requested < 1:
        raise AdmissionDenied("requested thread count must be positive")
    smt_requested = requested > physical_budget
    if smt_requested and not (
        request.get("allow_smt") is True
        and request.get("benchmark_evidence") is True
        and request.get("explicit_smt_admission") is True
    ):
        raise AdmissionDenied("SMT above the physical-core budget requires benchmark evidence and explicit admission")
    if requested > logical_budget:
        raise AdmissionDenied("requested threads exceed the admitted logical cpuset")

    numa_policy = request.get("numa_policy", "local")
    if numa_policy == "interleave_all" and request.get("benchmark_evidence") is not True:
        raise AdmissionDenied("NUMA interleave-all requires benchmark evidence")
    omp_binding = request.get("omp_proc_bind", "close")
    if omp_binding == "spread" and request.get("benchmark_evidence") is not True:
        raise AdmissionDenied("OpenMP spread binding requires benchmark evidence")
    if omp_binding not in {"close", "spread"}:
        raise AdmissionDenied("unsupported OpenMP binding policy")

    numexpr_threads = int(request.get("numexpr_threads") or min(8, requested))
    pytorch_interop = int(request.get("pytorch_interop_threads") or min(2, requested))
    if not 1 <= numexpr_threads <= requested:
        raise AdmissionDenied("NumExpr pool exceeds the admitted thread budget")
    if not 1 <= pytorch_interop <= requested:
        raise AdmissionDenied("PyTorch inter-op pool exceeds the admitted thread budget")
    if pytorch_interop > 2 and request.get("benchmark_evidence") is not True:
        raise AdmissionDenied("PyTorch inter-op above two threads requires benchmark evidence")

    environment = {
        "AI_CPU_THREAD_BUDGET": str(requested),
        "OMP_NUM_THREADS": str(requested),
        "OMP_THREAD_LIMIT": str(requested),
        "OMP_PLACES": "cores",
        "OMP_PROC_BIND": omp_binding,
        "OMP_DYNAMIC": "FALSE",
        "OMP_MAX_ACTIVE_LEVELS": "1",
        "MKL_NUM_THREADS": str(requested),
        "MKL_DYNAMIC": "FALSE",
        "OPENBLAS_NUM_THREADS": str(requested),
        "NUMEXPR_MAX_THREADS": str(requested),
        "NUMEXPR_NUM_THREADS": str(numexpr_threads),
    }
    provider_settings: dict[str, str] = {}
    if request.get("openmp_provider") == "INTEL_LIBIOMP":
        provider_settings = {
            "KMP_AFFINITY": "granularity=fine,compact,1,0",
            "KMP_BLOCKTIME": str(int(request.get("kmp_blocktime", 1))),
        }
    logging_settings = {"DNNL_VERBOSE": str(int(request.get("dnnl_verbose", 0)))}

    return {
        "schema": "fa3.thread-pool-budget.v1",
        "status": "ADMITTED",
        "authority_receipt": request["authority_receipt"],
        "topology_source": topology.get("source"),
        "workload_class": request.get("workload_class", "UNSPECIFIED"),
        "visible_logical_cpus": logical_budget,
        "visible_physical_cores": physical_budget,
        "thread_budget": requested,
        "uses_smt_above_physical_budget": smt_requested,
        "numa_node": request.get("numa_node"),
        "numa_policy": numa_policy,
        "environment": environment,
        "provider_settings": provider_settings,
        "logging_settings": logging_settings,
        "pytorch": {
            "intra_op_threads": requested,
            "inter_op_threads": pytorch_interop,
            "apply_before_parallel_execution": True,
        },
        "evidence_required": True,
        "rollback_profile_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or apply an HRB-derived CPU thread plan")
    parser.add_argument("--topology", help="TopologySnapshot JSON; live discovery when omitted")
    parser.add_argument("--request", required=True, help="CPUThreadBudgetRequest JSON")
    parser.add_argument("--exec", dest="execute", action="store_true", help="apply admitted env and execute command")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    topology = json.loads(Path(args.topology).read_text()) if args.topology else discover_live_topology()
    request = json.loads(Path(args.request).read_text())
    try:
        plan = build_thread_plan(topology, request)
    except AdmissionDenied as exc:
        print(json.dumps({"status": "DENIED", "reason": str(exc)}, indent=2))
        return 2
    print(json.dumps(plan, indent=2))
    if args.execute:
        command = args.command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            raise SystemExit("--exec requires a command after --")
        env = os.environ.copy()
        env.update(plan["environment"])
        env.update(plan["provider_settings"])
        env.update(plan["logging_settings"])
        os.execvpe(command[0], command, env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
