#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PROVED = "PROVED"
DENIED = "DENIED"
UNPROVEN = "UNPROVEN"
ASSURANCE_ORDER = {
    "EXEC-SEC-L0": 0,
    "EXEC-SEC-L1": 1,
    "EXEC-SEC-L2": 2,
    "EXEC-SEC-L3": 3,
    "EXEC-SEC-L4": 4,
}

def _subset(values: Iterable[str], boundary: Iterable[str]) -> bool:
    return set(values).issubset(set(boundary))

def prove_policy(requested: dict[str, list[str]], boundary: dict[str, list[str]], *, supported: bool = True) -> str:
    if not supported:
        return UNPROVEN
    for plane in ("filesystem", "network", "process", "mcp", "credentials"):
        if not _subset(requested.get(plane, []), boundary.get(plane, [])):
            return DENIED
    return PROVED

def assurance_satisfies(actual: str, minimum: str) -> bool:
    return actual in ASSURANCE_ORDER and minimum in ASSURANCE_ORDER and ASSURANCE_ORDER[actual] >= ASSURANCE_ORDER[minimum]

def execution_admitted(
    *,
    proof_state: str,
    proof_required: bool,
    executable_digest_matches: bool,
    policy_revision_matches: bool,
    approval_valid: bool,
    resource_leases_valid: bool,
    secret_leases_valid: bool,
    actual_assurance: str,
    minimum_assurance: str,
    enforcer_alive: bool,
) -> bool:
    if proof_state == DENIED:
        return False
    if proof_required and proof_state != PROVED:
        return False
    return all((
        executable_digest_matches,
        policy_revision_matches,
        approval_valid,
        resource_leases_valid,
        secret_leases_valid,
        assurance_satisfies(actual_assurance, minimum_assurance),
        enforcer_alive,
    ))

def credential_projection_valid(*, raw_secret_exposed: bool, endpoint_bound: bool, operation_bound: bool, lease_valid: bool) -> bool:
    return (not raw_secret_exposed) and endpoint_bound and operation_bound and lease_valid

@dataclass(frozen=True)
class ExecutionSecurityReceipt:
    task_id: str
    policy_revision: str
    proof_state: str
    assurance_level: str
    executable_digest: str
    authority: bool = False
    current_host_pass: bool = False
