#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from typing import Iterable

ELIGIBLE_STATES = {"HEALTHY", "DEGRADED", "QUOTA_LOW"}
STATE_ORDER = {"HEALTHY": 0, "DEGRADED": 1, "QUOTA_LOW": 2}

class ExecutionDenied(RuntimeError):
    pass

@dataclass(frozen=True)
class CredentialCandidate:
    provider_id: str
    credential_ref: str
    state: str
    admitted_provider: bool
    active_sessions: int = 0
    quota_pressure: float = 0.0

    def validate(self) -> None:
        if not self.admitted_provider:
            raise ExecutionDenied("provider is not admitted")
        if not self.credential_ref.startswith("secretref:"):
            raise ExecutionDenied("credential must be an opaque SecretReference")
        if self.state not in ELIGIBLE_STATES:
            raise ExecutionDenied(f"credential state is not eligible: {self.state}")
        if self.active_sessions < 0:
            raise ExecutionDenied("active_sessions must be non-negative")
        if not 0.0 <= self.quota_pressure <= 1.0:
            raise ExecutionDenied("quota_pressure must be in [0,1]")

def credential_ref_digest(ref: str) -> str:
    if not ref.startswith("secretref:"):
        raise ExecutionDenied("invalid SecretReference")
    return hashlib.sha256(ref.encode("utf-8")).hexdigest()

def choose_credential(candidates: Iterable[CredentialCandidate], *, provider_id: str, session_credential_ref: str | None = None) -> CredentialCandidate:
    eligible: list[CredentialCandidate] = []
    for row in candidates:
        if row.provider_id != provider_id:
            continue
        try:
            row.validate()
        except ExecutionDenied:
            continue
        eligible.append(row)
    if session_credential_ref:
        for row in eligible:
            if row.credential_ref == session_credential_ref:
                return row
    if not eligible:
        raise ExecutionDenied("no eligible credential in admitted provider pool")
    eligible.sort(key=lambda r: (STATE_ORDER[r.state], r.quota_pressure, r.active_sessions, credential_ref_digest(r.credential_ref)))
    return eligible[0]

def rebind_action(error_class: str, same_provider_eligible: bool) -> str:
    if error_class in {"POLICY_DENIED", "SECURITY_DENIED", "PROTOCOL_INVALID"}:
        return "FAIL_CLOSED"
    if same_provider_eligible and error_class in {"AUTH", "RATE_LIMIT", "QUOTA", "TRANSIENT_NETWORK", "PROVIDER_5XX", "MODEL_UNAVAILABLE"}:
        return "INTRA_PROVIDER_REBIND"
    if error_class in {"AUTH", "RATE_LIMIT", "QUOTA", "TRANSIENT_NETWORK", "PROVIDER_5XX", "MODEL_UNAVAILABLE"}:
        return "MODEL_ROUTER_REEVALUATION_REQUIRED"
    return "FAIL_CLOSED"

def protocol_projection_status(*, unsupported_fields: set[str], security_relevant_fields: set[str]) -> str:
    if unsupported_fields & security_relevant_fields:
        return "UNSUPPORTED_FAIL_CLOSED"
    if unsupported_fields:
        return "TRANSLATABLE_WITH_DECLARED_DEGRADATION"
    return "LOSSLESS"

def execution_receipt(candidate: CredentialCandidate, *, logical_route: str, physical_model: str, selection_reason: str) -> dict:
    candidate.validate()
    return {
        "schema": "fa3.route-execution-receipt.v1",
        "provider_id": candidate.provider_id,
        "credential_ref_sha256": credential_ref_digest(candidate.credential_ref),
        "logical_route": logical_route,
        "physical_model": physical_model,
        "selection_reason": selection_reason,
        "raw_credential_present": False,
    }
