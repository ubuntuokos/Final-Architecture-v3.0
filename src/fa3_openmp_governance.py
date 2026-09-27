#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import re


class OpenMPAdmissionDenied(ValueError):
    """Fail-closed OpenMP runtime governance error."""


_MANAGED_ENV = {
    "OMP_NUM_THREADS",
    "OMP_THREAD_LIMIT",
    "OMP_PLACES",
    "OMP_PROC_BIND",
    "OMP_DYNAMIC",
    "OMP_MAX_ACTIVE_LEVELS",
    "OMP_WAIT_POLICY",
    "OMP_STACKSIZE",
    "OMP_SCHEDULE",
    "OMP_TARGET_OFFLOAD",
    "OMP_DEFAULT_DEVICE",
    "OMP_NUM_TEAMS",
    "OMP_TEAMS_THREAD_LIMIT",
    "GOMP_CPU_AFFINITY",
    "GOMP_STACKSIZE",
    "KMP_AFFINITY",
    "KMP_BLOCKTIME",
    "KMP_STACKSIZE",
    "KMP_LIBRARY",
    "KMP_DETERMINISTIC_REDUCTION",
}
_PREFIXES = ("OMP_", "GOMP_", "KMP_")
_RUNTIME_PATTERNS = (
    ("GNU_LIBGOMP", re.compile(r"(?:^|/)libgomp(?:\.so|$)", re.I)),
    ("LLVM_LIBOMP", re.compile(r"(?:^|/)libomp(?:\.so|$)", re.I)),
    ("INTEL_LIBIOMP", re.compile(r"(?:^|/)libiomp5?(?:\.so|$)", re.I)),
)


def classify_runtime_libraries(libraries: list[str]) -> dict[str, Any]:
    families: set[str] = set()
    matched: list[dict[str, str]] = []
    for raw in libraries:
        value = str(raw)
        for family, pattern in _RUNTIME_PATTERNS:
            if pattern.search(value):
                families.add(family)
                matched.append({"family": family, "library": value})
                break
    status = "NONE_DETECTED"
    if len(families) == 1:
        status = "SINGLE_RUNTIME"
    elif len(families) > 1:
        status = "MULTIPLE_RUNTIME_CONFLICT"
    return {
        "status": status,
        "families": sorted(families),
        "libraries": matched,
    }


def sanitize_openmp_environment(
    inherited: Mapping[str, str],
    projected: Mapping[str, str],
) -> dict[str, Any]:
    removed: dict[str, str] = {}
    conflicts: list[str] = []
    clean = {str(k): str(v) for k, v in inherited.items()}
    for key in list(clean):
        if key.startswith(_PREFIXES):
            old = clean.pop(key)
            removed[key] = old
            if key in projected and str(projected[key]) != old:
                conflicts.append(key)
    clean.update({str(k): str(v) for k, v in projected.items()})
    return {
        "environment": clean,
        "removed_openmp_environment": removed,
        "conflicts": sorted(conflicts),
        "sanitized": True,
    }


def _stack_bytes(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, int):
        if value < 0:
            raise OpenMPAdmissionDenied("OpenMP stack bytes must not be negative")
        return value
    text = str(value).strip().upper()
    match = re.fullmatch(r"(\d+)([KMG]?)", text)
    if not match:
        raise OpenMPAdmissionDenied("OpenMP stack size must be an integer byte count or K/M/G suffix")
    amount = int(match.group(1))
    factor = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[match.group(2)]
    return amount * factor


def build_openmp_plan(
    thread_plan: dict[str, Any],
    request: dict[str, Any],
    *,
    inherited_env: Mapping[str, str] | None = None,
    runtime_libraries: list[str] | None = None,
) -> dict[str, Any]:
    if thread_plan.get("authority_receipt") != "HRB_PLACEMENT_RECEIPT":
        raise OpenMPAdmissionDenied("OpenMP plan requires an HRB-derived thread plan")

    thread_budget = int(thread_plan.get("thread_budget") or 0)
    if thread_budget < 1:
        raise OpenMPAdmissionDenied("OpenMP plan requires a positive admitted thread budget")

    runtime = classify_runtime_libraries(runtime_libraries or [])
    if runtime["status"] == "MULTIPLE_RUNTIME_CONFLICT" and request.get("runtime_compatibility_evidence") is not True:
        raise OpenMPAdmissionDenied("multiple OpenMP runtime families require explicit compatibility evidence")

    active_levels = int(request.get("max_active_levels", 1))
    if active_levels < 1:
        raise OpenMPAdmissionDenied("max_active_levels must be positive")
    nested = active_levels > 1
    if nested:
        if not (
            request.get("nested_parallelism_admitted") is True
            and request.get("benchmark_evidence") is True
        ):
            raise OpenMPAdmissionDenied("nested OpenMP parallelism requires explicit admission and benchmark evidence")
        outer = int(request.get("outer_team_threads") or thread_budget)
        inner = int(request.get("inner_team_threads") or 1)
        if outer < 1 or inner < 1 or outer * inner > thread_budget:
            raise OpenMPAdmissionDenied("nested OpenMP hierarchical team budget exceeds HRB thread budget")

    schedule = str(request.get("schedule", "static")).lower()
    if schedule not in {"static", "dynamic", "guided", "auto"}:
        raise OpenMPAdmissionDenied("unsupported OpenMP schedule")
    if schedule != "static" and request.get("benchmark_evidence") is not True:
        raise OpenMPAdmissionDenied("non-static OpenMP schedule requires benchmark evidence")

    wait_policy = str(request.get("wait_policy", "PASSIVE")).upper()
    if wait_policy not in {"PASSIVE", "ACTIVE"}:
        raise OpenMPAdmissionDenied("unsupported OpenMP wait policy")
    if wait_policy == "ACTIVE" and request.get("latency_sensitive_admission") is not True:
        raise OpenMPAdmissionDenied("ACTIVE OpenMP wait policy requires explicit latency-sensitive admission")

    stack_bytes = _stack_bytes(request.get("stack_size"))
    stack_reservation = stack_bytes * thread_budget
    memory_budget = request.get("hrb_memory_budget_bytes")
    if stack_bytes and memory_budget is None:
        raise OpenMPAdmissionDenied("OpenMP stack sizing requires HRB memory budget")
    if memory_budget is not None and stack_reservation > int(memory_budget):
        raise OpenMPAdmissionDenied("OpenMP worker stack reservation exceeds HRB memory budget")

    target = request.get("target_offload") or {}
    target_enabled = bool(target.get("requested"))
    target_env: dict[str, str] = {}
    if target_enabled:
        if target.get("hrb_accelerator_lease") is not True:
            raise OpenMPAdmissionDenied("OpenMP target offload requires HRB accelerator lease")
        if not target.get("stable_device_identity"):
            raise OpenMPAdmissionDenied("OpenMP target offload requires HRB-bound stable device identity")
        ordinal = target.get("device_ordinal")
        if not isinstance(ordinal, int) or ordinal < 0:
            raise OpenMPAdmissionDenied("OpenMP target offload requires non-negative projected device ordinal")
        target_env["OMP_TARGET_OFFLOAD"] = "MANDATORY"
        target_env["OMP_DEFAULT_DEVICE"] = str(ordinal)
        if target.get("num_teams") is not None:
            teams = int(target["num_teams"])
            if teams < 1:
                raise OpenMPAdmissionDenied("OMP_NUM_TEAMS must be positive")
            target_env["OMP_NUM_TEAMS"] = str(teams)
        if target.get("teams_thread_limit") is not None:
            limit = int(target["teams_thread_limit"])
            if limit < 1:
                raise OpenMPAdmissionDenied("OMP_TEAMS_THREAD_LIMIT must be positive")
            target_env["OMP_TEAMS_THREAD_LIMIT"] = str(limit)

    projected = dict(thread_plan.get("environment", {}))
    projected.update({
        "OMP_WAIT_POLICY": wait_policy,
        "OMP_SCHEDULE": schedule,
        "OMP_MAX_ACTIVE_LEVELS": str(active_levels),
    })
    if stack_bytes:
        projected["OMP_STACKSIZE"] = str(stack_bytes)
    projected.update(target_env)

    provider_settings = dict(thread_plan.get("provider_settings", {}))
    reproducibility = str(request.get("determinism_requirement", "NONE")).upper()
    if reproducibility not in {"NONE", "BEST_EFFORT", "REPRODUCIBLE"}:
        raise OpenMPAdmissionDenied("unsupported determinism requirement")
    if reproducibility == "REPRODUCIBLE":
        families = set(runtime["families"])
        if "INTEL_LIBIOMP" in families:
            provider_settings["KMP_DETERMINISTIC_REDUCTION"] = "TRUE"
        elif request.get("deterministic_reduction_supported") is not True:
            raise OpenMPAdmissionDenied("reproducible reduction requires runtime evidence for deterministic reduction support")

    projected.update(provider_settings)
    sanitized = sanitize_openmp_environment(inherited_env or {}, projected)

    return {
        "schema": "fa3.openmp-runtime-plan.v1",
        "status": "ADMITTED",
        "authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "thread_budget": thread_budget,
        "runtime": runtime,
        "environment": projected,
        "environment_sanitization": {
            "removed": sanitized["removed_openmp_environment"],
            "conflicts": sanitized["conflicts"],
        },
        "effective_child_environment": sanitized["environment"],
        "nested_parallelism": nested,
        "schedule": schedule,
        "wait_policy": wait_policy,
        "stack_bytes_per_worker": stack_bytes,
        "stack_reservation_bytes": stack_reservation,
        "target_offload": {
            "enabled": target_enabled,
            "silent_host_fallback_allowed": False,
            "stable_device_identity": target.get("stable_device_identity") if target_enabled else None,
            "device_ordinal": target.get("device_ordinal") if target_enabled else None,
        },
        "determinism_requirement": reproducibility,
        "current_host_runtime_promotion_claim": False,
    }


def validate_observed_runtime(plan: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    budget = int(plan.get("thread_budget") or 0)
    observed_threads = int(observation.get("max_threads") or 0)
    if observed_threads < 1 or observed_threads > budget:
        findings.append("observed OpenMP thread count exceeds or invalidates HRB budget")

    admitted_cpus = {int(v) for v in observation.get("admitted_cpus", [])}
    observed_cpus = {int(v) for v in observation.get("observed_cpus", [])}
    if not admitted_cpus:
        findings.append("admitted CPU set missing from observation")
    elif not observed_cpus:
        findings.append("observed OpenMP CPU placement missing")
    elif not observed_cpus.issubset(admitted_cpus):
        findings.append("OPENMP_CPUSET_ESCAPE")

    if observation.get("effective_dynamic") is True:
        findings.append("OpenMP dynamic team resizing observed despite bounded plan")

    target = plan.get("target_offload", {})
    if target.get("enabled"):
        if observation.get("target_executed_on_host") is True:
            findings.append("OPENMP_TARGET_SILENT_HOST_FALLBACK")
        if observation.get("target_device_ordinal") != target.get("device_ordinal"):
            findings.append("OpenMP target device differs from HRB projection")

    return {
        "schema": "fa3.openmp-runtime-observation.v1",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
    }
