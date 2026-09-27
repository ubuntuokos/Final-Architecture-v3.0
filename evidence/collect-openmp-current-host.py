#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cpu_thread_budget import build_thread_plan, discover_live_topology
from fa3_openmp_governance import build_openmp_plan, classify_runtime_libraries, validate_observed_runtime
from fa3_release_baseline import active_capability_count


PROBE_SOURCE = r"""
#define _GNU_SOURCE
#include <omp.h>
#include <sched.h>
#include <stdio.h>

int main(void) {
    printf("max_threads=%d\n", omp_get_max_threads());
    printf("num_procs=%d\n", omp_get_num_procs());
    printf("num_places=%d\n", omp_get_num_places());
    printf("proc_bind=%d\n", (int)omp_get_proc_bind());
    printf("dynamic=%d\n", omp_get_dynamic());
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        int cpu = sched_getcpu();
        #pragma omp critical
        {
            printf("worker=%d,%d\n", tid, cpu);
        }
    }
    return 0;
}
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _loaded_runtime_libraries(executable: Path) -> list[str]:
    cp = subprocess.run(
        ["ldd", str(executable)],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if cp.returncode != 0:
        return []
    libraries: list[str] = []
    for line in cp.stdout.splitlines():
        if "=>" in line:
            path = line.split("=>", 1)[1].strip().split(" ", 1)[0]
            if path.startswith("/"):
                libraries.append(path)
        else:
            token = line.strip().split(" ", 1)[0]
            if token.startswith("/"):
                libraries.append(token)
    return libraries


def _parse_probe(stdout: str) -> dict[str, Any]:
    scalar: dict[str, int] = {}
    workers: list[dict[str, int]] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("worker="):
            tid, cpu = line.split("=", 1)[1].split(",", 1)
            workers.append({"thread": int(tid), "cpu": int(cpu)})
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            scalar[key] = int(value)
    return {
        **scalar,
        "workers": sorted(workers, key=lambda item: item["thread"]),
        "observed_cpus": sorted({item["cpu"] for item in workers}),
    }


def collect(compiler: str = "cc") -> dict[str, Any]:
    compiler_path = shutil.which(compiler)
    if not compiler_path:
        return {
            "schema": "fa3.openmp-current-host-evidence.v1",
            "status": "FAIL",
            "evidence_level": "CURRENT_HOST_OPENMP_RUNTIME_INCOMPLETE",
            "blocking_reasons": ["OPENMP_COMPILER_UNAVAILABLE"],
            "current_host_runtime_promotion_claim": False,
            "global_promotion_claim": False,
        }

    topology = discover_live_topology()
    thread_plan = build_thread_plan(
        topology,
        {
            "authority_receipt": "HRB_PLACEMENT_RECEIPT",
            "workload_class": "OPENMP_CURRENT_HOST_VALIDATION",
        },
    )

    with tempfile.TemporaryDirectory(prefix="fa3-openmp-probe-") as temp:
        tempdir = Path(temp)
        source = tempdir / "probe.c"
        executable = tempdir / "probe"
        source.write_text(PROBE_SOURCE, encoding="utf-8")
        compile_cp = subprocess.run(
            [compiler_path, "-O2", "-fopenmp", str(source), "-o", str(executable)],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        if compile_cp.returncode != 0:
            return {
                "schema": "fa3.openmp-current-host-evidence.v1",
                "status": "FAIL",
                "evidence_level": "CURRENT_HOST_OPENMP_RUNTIME_INCOMPLETE",
                "compiler": compiler_path,
                "blocking_reasons": ["OPENMP_PROBE_COMPILE_FAILED"],
                "compiler_stderr_sha256": hashlib.sha256(compile_cp.stderr.encode()).hexdigest(),
                "current_host_runtime_promotion_claim": False,
                "global_promotion_claim": False,
            }

        libraries = _loaded_runtime_libraries(executable)
        runtime = classify_runtime_libraries(libraries)
        plan = build_openmp_plan(
            thread_plan,
            {},
            inherited_env=os.environ,
            runtime_libraries=libraries,
        )
        run_cp = subprocess.run(
            [str(executable)],
            env=plan["effective_child_environment"],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        if run_cp.returncode != 0:
            return {
                "schema": "fa3.openmp-current-host-evidence.v1",
                "status": "FAIL",
                "evidence_level": "CURRENT_HOST_OPENMP_RUNTIME_INCOMPLETE",
                "runtime": runtime,
                "blocking_reasons": ["OPENMP_PROBE_EXECUTION_FAILED"],
                "probe_stderr_sha256": hashlib.sha256(run_cp.stderr.encode()).hexdigest(),
                "current_host_runtime_promotion_claim": False,
                "global_promotion_claim": False,
            }

        probe = _parse_probe(run_cp.stdout)
        observation_input = {
            "max_threads": probe.get("max_threads"),
            "admitted_cpus": topology["allowed_cpus"],
            "observed_cpus": probe.get("observed_cpus", []),
            "effective_dynamic": bool(probe.get("dynamic")),
        }
        validation = validate_observed_runtime(plan, observation_input)
        pass_state = (
            runtime.get("status") == "SINGLE_RUNTIME"
            and bool(probe.get("workers"))
            and len(probe["workers"]) <= int(thread_plan["thread_budget"])
            and validation["status"] == "PASS"
        )
        return {
            "schema": "fa3.openmp-current-host-evidence.v1",
            "status": "PASS" if pass_state else "FAIL",
            "evidence_level": (
                "CURRENT_HOST_OPENMP_RUNTIME_PASS"
                if pass_state
                else "CURRENT_HOST_OPENMP_RUNTIME_INCOMPLETE"
            ),
            "collected_at": _now(),
            "compiler": {
                "path": compiler_path,
                "sha256": _sha256(Path(compiler_path)),
            },
            "probe_binary_sha256": _sha256(executable),
            "runtime": runtime,
            "thread_plan": {
                "authority_receipt": thread_plan["authority_receipt"],
                "thread_budget": thread_plan["thread_budget"],
                "allowed_cpus": topology["allowed_cpus"],
                "environment": plan["environment"],
            },
            "observation": {
                "max_threads": probe.get("max_threads"),
                "num_procs": probe.get("num_procs"),
                "num_places": probe.get("num_places"),
                "proc_bind": probe.get("proc_bind"),
                "dynamic": bool(probe.get("dynamic")),
                "worker_count": len(probe.get("workers", [])),
                "observed_cpus": probe.get("observed_cpus", []),
            },
            "validation": validation,
            "target_offload": {
                "tested": False,
                "reason": "CPU_ONLY_OPENMP_CURRENT_HOST_BASELINE; accelerator offload requires separate conditional HRB-bound evidence",
            },
            "capability_count_after": active_capability_count(ROOT),
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "current_host_runtime_promotion_claim": False,
            "global_promotion_claim": False,
            "blocking_reasons": [] if pass_state else [
                "OPENMP_RUNTIME_OR_AFFINITY_OBSERVATION_FAILED"
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect physical OpenMP runtime/affinity evidence")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--compiler", default="cc")
    parser.add_argument("--output", default="evidence/receipts/openmp-current-host.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = collect(args.compiler)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
