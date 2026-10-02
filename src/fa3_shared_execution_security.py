from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PROOF_STATES = {"PROVED", "DENIED", "UNPROVEN"}
SECURITY_LEVELS = {"EXEC-SEC-L0", "EXEC-SEC-L1", "EXEC-SEC-L2", "EXEC-SEC-L3", "EXEC-SEC-L4"}

@dataclass(frozen=True)
class PolicyProof:
    state: str
    reason: str = ""

def policy_subset(requested: Iterable[str], authorized: Iterable[str]) -> bool:
    return set(requested).issubset(set(authorized))

def proof_allows_execution(proof_state: str, *, proof_required: bool) -> bool:
    if proof_state not in PROOF_STATES:
        return False
    if proof_state == "DENIED":
        return False
    if proof_required and proof_state != "PROVED":
        return False
    return proof_state in {"PROVED", "UNPROVEN"}

def executable_identity_valid(*, expected_sha256: str | None, observed_sha256: str | None) -> bool:
    if not expected_sha256 or not observed_sha256:
        return False
    return expected_sha256 == observed_sha256

def security_level_satisfies(*, minimum: str, observed: str) -> bool:
    order = ["EXEC-SEC-L0", "EXEC-SEC-L1", "EXEC-SEC-L2", "EXEC-SEC-L3", "EXEC-SEC-L4"]
    if minimum not in order or observed not in order:
        return False
    return order.index(observed) >= order.index(minimum)

def execution_admitted(*, authorized_policy: Iterable[str], requested_policy: Iterable[str],
                       proof_state: str, proof_required: bool,
                       minimum_security_level: str, observed_security_level: str,
                       authorization_valid: bool, lease_valid: bool,
                       executable_digest_valid: bool, enforcer_available: bool) -> bool:
    return all((
        authorization_valid,
        lease_valid,
        enforcer_available,
        executable_digest_valid,
        policy_subset(requested_policy, authorized_policy),
        proof_allows_execution(proof_state, proof_required=proof_required),
        security_level_satisfies(minimum=minimum_security_level, observed=observed_security_level),
    ))
