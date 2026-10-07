#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import re


class SysctlGovernanceDenied(ValueError):
    pass


OBSERVE_ONLY = "OBSERVE_ONLY"
WORKLOAD_SENSITIVE = "WORKLOAD_SENSITIVE"
SAFETY_SECURITY_SENSITIVE = "SAFETY_SECURITY_SENSITIVE"
FORBIDDEN_AUTOMATIC_MUTATION = "FORBIDDEN_AUTOMATIC_MUTATION"

_KEY_CLASSES: dict[str, str] = {
    "vm.swappiness": WORKLOAD_SENSITIVE,
    "vm.overcommit_memory": WORKLOAD_SENSITIVE,
    "vm.overcommit_ratio": WORKLOAD_SENSITIVE,
    "vm.dirty_ratio": WORKLOAD_SENSITIVE,
    "vm.dirty_background_ratio": WORKLOAD_SENSITIVE,
    "vm.dirty_bytes": WORKLOAD_SENSITIVE,
    "vm.dirty_background_bytes": WORKLOAD_SENSITIVE,
    "vm.vfs_cache_pressure": WORKLOAD_SENSITIVE,
    "vm.min_free_kbytes": SAFETY_SECURITY_SENSITIVE,
    "vm.max_map_count": WORKLOAD_SENSITIVE,
    "vm.zone_reclaim_mode": WORKLOAD_SENSITIVE,
    "vm.compaction_proactiveness": WORKLOAD_SENSITIVE,
    "vm.extfrag_threshold": WORKLOAD_SENSITIVE,
    "vm.nr_hugepages": WORKLOAD_SENSITIVE,
    "vm.nr_overcommit_hugepages": WORKLOAD_SENSITIVE,
    "kernel.numa_balancing": WORKLOAD_SENSITIVE,
    "kernel.kptr_restrict": SAFETY_SECURITY_SENSITIVE,
    "kernel.dmesg_restrict": SAFETY_SECURITY_SENSITIVE,
    "kernel.unprivileged_bpf_disabled": SAFETY_SECURITY_SENSITIVE,
    "kernel.yama.ptrace_scope": SAFETY_SECURITY_SENSITIVE,
    "fs.protected_hardlinks": SAFETY_SECURITY_SENSITIVE,
    "fs.protected_symlinks": SAFETY_SECURITY_SENSITIVE,
    "fs.protected_fifos": SAFETY_SECURITY_SENSITIVE,
    "fs.protected_regular": SAFETY_SECURITY_SENSITIVE,
}

_FORBIDDEN_PREFIXES = (
    "kernel.core_pattern",
    "kernel.modprobe",
)

_ALLOWED_PERSISTENCE_PREFIX = "90-fa3-"
_ALLOWED_PERSISTENCE_SUFFIX = ".conf"


def classify_key(key: str) -> str:
    key = str(key).strip()
    if not key or not re.fullmatch(r"[A-Za-z0-9_.]+", key):
        raise SysctlGovernanceDenied("invalid sysctl key")
    if any(key == p or key.startswith(p + ".") for p in _FORBIDDEN_PREFIXES):
        return FORBIDDEN_AUTOMATIC_MUTATION
    return _KEY_CLASSES.get(key, OBSERVE_ONLY)


def snapshot_digest(values: Mapping[str, Any]) -> str:
    payload = json.dumps({str(k): str(v) for k, v in sorted(values.items())}, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_persistence_path(path: str) -> bool:
    p = Path(path)
    return (
        p.parent == Path("/etc/sysctl.d")
        and p.name.startswith(_ALLOWED_PERSISTENCE_PREFIX)
        and p.name.endswith(_ALLOWED_PERSISTENCE_SUFFIX)
        and p.name not in {"90-fa3.conf", "99-sysctl.conf"}
    )


def build_change_plan(
    current: Mapping[str, Any],
    requested: Mapping[str, Any],
    *,
    mode: str = "OBSERVE_ONLY",
    hrb_authorized: bool = False,
    security_authorized: bool = False,
    explicit_user_approval: bool = False,
    benchmark_evidence: bool = False,
    rollback_ready: bool = False,
    persistence_path: str | None = None,
) -> dict[str, Any]:
    mode = str(mode).upper()
    if mode not in {"OBSERVE_ONLY", "EPHEMERAL_MUTATION", "PERSISTENT_MUTATION"}:
        raise SysctlGovernanceDenied("unsupported sysctl governance mode")

    current_norm = {str(k): str(v) for k, v in current.items()}
    requested_norm = {str(k): str(v) for k, v in requested.items()}
    changes: list[dict[str, Any]] = []

    for key, new_value in requested_norm.items():
        cls = classify_key(key)
        old_value = current_norm.get(key)
        if old_value == new_value:
            continue
        if cls == FORBIDDEN_AUTOMATIC_MUTATION:
            raise SysctlGovernanceDenied(f"{key} is forbidden for FA3 automatic mutation")
        if mode == "OBSERVE_ONLY":
            raise SysctlGovernanceDenied("observe-only mode cannot mutate sysctl state")
        if cls == OBSERVE_ONLY:
            raise SysctlGovernanceDenied(f"{key} has no admitted mutation policy")
        if not (hrb_authorized and explicit_user_approval and rollback_ready):
            raise SysctlGovernanceDenied("host-global sysctl mutation requires HRB authorization, explicit approval and rollback")
        if cls == WORKLOAD_SENSITIVE and not benchmark_evidence:
            raise SysctlGovernanceDenied(f"{key} requires workload/host benchmark evidence")
        if cls == SAFETY_SECURITY_SENSITIVE and not security_authorized:
            raise SysctlGovernanceDenied(f"{key} requires security authorization")

        changes.append({
            "key": key,
            "classification": cls,
            "old_value": old_value,
            "new_value": new_value,
            "rollback_value": old_value,
        })

    if mode == "PERSISTENT_MUTATION":
        if not persistence_path or not validate_persistence_path(persistence_path):
            raise SysctlGovernanceDenied("persistent sysctl mutation requires a namespaced /etc/sysctl.d/90-fa3-*.conf path")

    return {
        "schema": "fa3.sysctl-change-plan.v1",
        "status": "ADMITTED" if changes else "NO_CHANGE",
        "mode": mode,
        "authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "security_authority_required": any(x["classification"] == SAFETY_SECURITY_SENSITIVE for x in changes),
        "current_snapshot_sha256": snapshot_digest(current_norm),
        "changes": changes,
        "persistence_path": persistence_path if mode == "PERSISTENT_MUTATION" else None,
        "requires_post_apply_acceptance": bool(changes),
        "requires_rollback_verification": bool(changes),
        "global_promotion_claim": False,
    }


def validate_post_apply(plan: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    observed_norm = {str(k): str(v) for k, v in observed.items()}
    for change in plan.get("changes", []):
        key = change["key"]
        if observed_norm.get(key) != str(change["new_value"]):
            findings.append(f"SYSCTL_APPLY_MISMATCH:{key}")
    return {
        "schema": "fa3.sysctl-post-apply-validation.v1",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "global_promotion_claim": False,
    }


def validate_rollback(plan: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    observed_norm = {str(k): str(v) for k, v in observed.items()}
    for change in plan.get("changes", []):
        key = change["key"]
        rollback_value = change.get("rollback_value")
        if rollback_value is None:
            findings.append(f"SYSCTL_ROLLBACK_VALUE_MISSING:{key}")
        elif observed_norm.get(key) != str(rollback_value):
            findings.append(f"SYSCTL_ROLLBACK_MISMATCH:{key}")
    return {
        "schema": "fa3.sysctl-rollback-validation.v1",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "global_promotion_claim": False,
    }
