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

@dataclass
class CredentialRuntimeState:
    candidate: CredentialCandidate
    state: str
    failure_count: int = 0
    circuit_state: str = "CLOSED"
    cooldown_until: float = 0.0
    circuit_until: float = 0.0
    active_sessions: int = 0

class ProviderExecutionManager:
    """In-memory execution state only; raw credential values never enter this object."""

    def __init__(self, candidates: Iterable[CredentialCandidate], *, lease_ttl_seconds: float = 300.0, circuit_threshold: int = 3, circuit_cooldown_seconds: float = 30.0):
        self.lease_ttl_seconds = float(lease_ttl_seconds)
        self.circuit_threshold = int(circuit_threshold)
        self.circuit_cooldown_seconds = float(circuit_cooldown_seconds)
        if self.lease_ttl_seconds <= 0 or self.circuit_threshold <= 0 or self.circuit_cooldown_seconds <= 0:
            raise ExecutionDenied("invalid execution-manager timing or threshold")
        self._states: dict[str, CredentialRuntimeState] = {}
        self._sessions: dict[str, tuple[str, float]] = {}
        for c in candidates:
            c.validate()
            if c.credential_ref in self._states:
                raise ExecutionDenied("duplicate credential reference")
            self._states[c.credential_ref] = CredentialRuntimeState(c, c.state, active_sessions=c.active_sessions)

    def _refresh(self, st: CredentialRuntimeState, now: float) -> None:
        if st.circuit_state == "OPEN" and now >= st.circuit_until:
            st.circuit_state = "HALF_OPEN"
        if st.state in {"RATE_LIMITED", "COOLDOWN"} and now >= st.cooldown_until:
            st.state = "HEALTHY"

    def _eligible(self, st: CredentialRuntimeState, now: float) -> bool:
        self._refresh(st, now)
        return st.candidate.admitted_provider and st.candidate.credential_ref.startswith("secretref:") and st.state in ELIGIBLE_STATES and st.circuit_state != "OPEN"

    def _release_binding(self, session_id: str) -> None:
        old = self._sessions.pop(session_id, None)
        if old:
            st = self._states.get(old[0])
            if st is not None:
                st.active_sessions = max(0, st.active_sessions - 1)

    def select(self, *, provider_id: str, session_id: str, now: float) -> dict:
        if not session_id:
            raise ExecutionDenied("session_id required")
        bound = self._sessions.get(session_id)
        if bound:
            ref, expires_at = bound
            st = self._states.get(ref)
            if st is not None and expires_at > now and st.candidate.provider_id == provider_id and self._eligible(st, now):
                return self._lease(st, session_id, now, expires_at, reused=True)
            self._release_binding(session_id)
        rows = [st for st in self._states.values() if st.candidate.provider_id == provider_id and self._eligible(st, now)]
        if not rows:
            raise ExecutionDenied("no eligible credential in admitted provider pool")
        rows.sort(key=lambda st: (STATE_ORDER[st.state], st.candidate.quota_pressure, st.active_sessions, credential_ref_digest(st.candidate.credential_ref)))
        st = rows[0]
        expires_at = now + self.lease_ttl_seconds
        self._sessions[session_id] = (st.candidate.credential_ref, expires_at)
        st.active_sessions += 1
        return self._lease(st, session_id, now, expires_at, reused=False)

    def _lease(self, st: CredentialRuntimeState, session_id: str, now: float, expires_at: float, *, reused: bool) -> dict:
        session_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        ref_hash = credential_ref_digest(st.candidate.credential_ref)
        lease_id = hashlib.sha256(f"{session_hash}:{ref_hash}:{int(now*1000)}".encode("utf-8")).hexdigest()
        return {
            "schema": "fa3.credential-execution-lease.v1",
            "lease_id": lease_id,
            "provider_id": st.candidate.provider_id,
            "credential_ref_sha256": ref_hash,
            "session_id_sha256": session_hash,
            "issued_at_monotonic": now,
            "expires_at_monotonic": expires_at,
            "reused_session_binding": reused,
            "circuit_state": st.circuit_state,
            "raw_credential_present": False,
        }

    def record_success(self, *, session_id: str, now: float) -> dict:
        bound = self._sessions.get(session_id)
        if not bound:
            raise ExecutionDenied("session binding missing")
        st = self._states[bound[0]]
        self._refresh(st, now)
        st.failure_count = 0
        st.circuit_state = "CLOSED"
        if st.state == "DEGRADED":
            st.state = "HEALTHY"
        return {"result": "RECORDED", "credential_ref_sha256": credential_ref_digest(st.candidate.credential_ref), "raw_credential_present": False}

    def record_failure(self, *, session_id: str, error_class: str, now: float, retry_after_seconds: float | None = None) -> dict:
        bound = self._sessions.get(session_id)
        if not bound:
            raise ExecutionDenied("session binding missing")
        st = self._states[bound[0]]
        provider_id = st.candidate.provider_id
        old_hash = credential_ref_digest(st.candidate.credential_ref)
        terminal = error_class in {"POLICY_DENIED", "SECURITY_DENIED", "PROTOCOL_INVALID"}
        if terminal:
            return {"schema": "fa3.route-rebind-receipt.v1", "action": "FAIL_CLOSED", "reason": error_class, "old_credential_ref_sha256": old_hash, "raw_credential_present": False}
        force_rebind = False
        if error_class == "AUTH":
            st.state = "AUTH_INVALID"; force_rebind = True
        elif error_class == "QUOTA":
            st.state = "QUOTA_EXHAUSTED"; force_rebind = True
        elif error_class == "RATE_LIMIT":
            st.state = "RATE_LIMITED"
            st.cooldown_until = now + float(retry_after_seconds if retry_after_seconds is not None else 30.0)
            force_rebind = True
        elif error_class in {"TRANSIENT_NETWORK", "PROVIDER_5XX"}:
            st.failure_count += 1
            if st.failure_count >= self.circuit_threshold:
                st.circuit_state = "OPEN"
                st.circuit_until = now + self.circuit_cooldown_seconds
                force_rebind = True
        elif error_class == "MODEL_UNAVAILABLE":
            st.state = "DEGRADED"; force_rebind = True
        else:
            return {"schema": "fa3.route-rebind-receipt.v1", "action": "FAIL_CLOSED", "reason": "UNKNOWN_ERROR_CLASS", "old_credential_ref_sha256": old_hash, "raw_credential_present": False}
        if not force_rebind:
            return {"schema": "fa3.route-rebind-receipt.v1", "action": "RETRY_SAME_CREDENTIAL", "reason": error_class, "old_credential_ref_sha256": old_hash, "raw_credential_present": False}
        self._release_binding(session_id)
        try:
            lease = self.select(provider_id=provider_id, session_id=session_id, now=now)
            return {
                "schema": "fa3.route-rebind-receipt.v1",
                "action": "INTRA_PROVIDER_REBIND",
                "reason": error_class,
                "provider_id": provider_id,
                "old_credential_ref_sha256": old_hash,
                "new_credential_ref_sha256": lease["credential_ref_sha256"],
                "cross_provider_transition": False,
                "raw_credential_present": False,
            }
        except ExecutionDenied:
            return {
                "schema": "fa3.route-rebind-receipt.v1",
                "action": "MODEL_ROUTER_REEVALUATION_REQUIRED",
                "reason": error_class,
                "provider_id": provider_id,
                "old_credential_ref_sha256": old_hash,
                "cross_provider_transition": False,
                "raw_credential_present": False,
            }

    def release_session(self, session_id: str) -> None:
        self._release_binding(session_id)

    def safe_snapshot(self, *, now: float) -> dict:
        rows=[]
        for st in self._states.values():
            self._refresh(st, now)
            rows.append({
                "provider_id": st.candidate.provider_id,
                "credential_ref_sha256": credential_ref_digest(st.candidate.credential_ref),
                "state": st.state,
                "circuit_state": st.circuit_state,
                "failure_count": st.failure_count,
                "active_sessions": st.active_sessions,
            })
        return {"schema":"fa3.provider-execution-state.v1","credentials":sorted(rows,key=lambda r:(r["provider_id"],r["credential_ref_sha256"])),"raw_credential_present":False}
