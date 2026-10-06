#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Iterable

ELIGIBLE_STATES = {"HEALTHY", "DEGRADED", "QUOTA_LOW"}
STATE_ORDER = {"HEALTHY": 0, "DEGRADED": 1, "QUOTA_LOW": 2}
HEALTH_STATES = {"HEALTHY", "DEGRADED", "UNAVAILABLE"}
HEALTH_ORDER = {"HEALTHY": 0, "DEGRADED": 1, "UNAVAILABLE": 2}
REBINDS_ALLOWED = {
    "AUTH", "CREDENTIAL_REVOKED", "RATE_LIMIT", "QUOTA", "TRANSIENT_NETWORK",
    "PROVIDER_5XX", "PROVIDER_OVERLOAD", "PROVIDER_UNAVAILABLE",
    "MODEL_UNAVAILABLE", "ENDPOINT_UNAVAILABLE",
}
FAIL_CLOSED_ERRORS = {"POLICY_DENIED", "SECURITY_DENIED", "PROTOCOL_INVALID"}

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
    model_id: str | None = None
    endpoint_id: str | None = None
    provider_health: str = "HEALTHY"
    model_health: str = "HEALTHY"
    endpoint_health: str = "HEALTHY"
    quota_reset_at: float | None = None

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
        for label, value in (
            ("provider_health", self.provider_health),
            ("model_health", self.model_health),
            ("endpoint_health", self.endpoint_health),
        ):
            if value not in HEALTH_STATES:
                raise ExecutionDenied(f"invalid {label}: {value}")
        if self.quota_reset_at is not None and (
            isinstance(self.quota_reset_at, bool) or self.quota_reset_at < 0
        ):
            raise ExecutionDenied("quota_reset_at must be non-negative when present")

def credential_ref_digest(ref: str) -> str:
    if not ref.startswith("secretref:"):
        raise ExecutionDenied("invalid SecretReference")
    return hashlib.sha256(ref.encode("utf-8")).hexdigest()

def _candidate_eligible(row: CredentialCandidate) -> bool:
    try:
        row.validate()
    except ExecutionDenied:
        return False
    return (
        row.state in ELIGIBLE_STATES
        and row.provider_health != "UNAVAILABLE"
        and row.model_health != "UNAVAILABLE"
        and row.endpoint_health != "UNAVAILABLE"
    )

def _candidate_rank(row: CredentialCandidate) -> tuple:
    return (
        HEALTH_ORDER[row.provider_health],
        HEALTH_ORDER[row.model_health],
        HEALTH_ORDER[row.endpoint_health],
        STATE_ORDER[row.state],
        row.quota_pressure,
        row.active_sessions,
        credential_ref_digest(row.credential_ref),
    )

def choose_credential(candidates: Iterable[CredentialCandidate], *, provider_id: str, session_credential_ref: str | None = None) -> CredentialCandidate:
    eligible = [row for row in candidates if row.provider_id == provider_id and _candidate_eligible(row)]
    if session_credential_ref:
        for row in eligible:
            if row.credential_ref == session_credential_ref:
                return row
    if not eligible:
        raise ExecutionDenied("no eligible credential in admitted provider pool")
    eligible.sort(key=_candidate_rank)
    return eligible[0]

def rebind_action(error_class: str, same_provider_eligible: bool) -> str:
    if error_class in FAIL_CLOSED_ERRORS:
        return "FAIL_CLOSED"
    if same_provider_eligible and error_class in REBINDS_ALLOWED:
        return "INTRA_PROVIDER_REBIND"
    if error_class in REBINDS_ALLOWED:
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

@dataclass
class SessionRuntimeState:
    credential_ref: str
    expires_at: float
    rebind_count: int = 0
    attempted_refs: set[str] = field(default_factory=set)

class ProviderExecutionManager:
    """Provider-local execution state. Raw credential values never enter this object."""

    def __init__(
        self,
        candidates: Iterable[CredentialCandidate],
        *,
        lease_ttl_seconds: float = 300.0,
        circuit_threshold: int = 3,
        circuit_cooldown_seconds: float = 30.0,
        max_rebind_attempts: int = 2,
        max_credentials_per_request: int = 3,
        backoff_schedule_seconds: tuple[float, ...] = (5.0, 15.0, 30.0, 60.0),
    ):
        self.lease_ttl_seconds = float(lease_ttl_seconds)
        self.circuit_threshold = int(circuit_threshold)
        self.circuit_cooldown_seconds = float(circuit_cooldown_seconds)
        self.max_rebind_attempts = int(max_rebind_attempts)
        self.max_credentials_per_request = int(max_credentials_per_request)
        self.backoff_schedule_seconds = tuple(float(x) for x in backoff_schedule_seconds)
        if (
            self.lease_ttl_seconds <= 0
            or self.circuit_threshold <= 0
            or self.circuit_cooldown_seconds <= 0
            or self.max_rebind_attempts < 0
            or self.max_credentials_per_request <= 0
            or not self.backoff_schedule_seconds
            or any(x <= 0 for x in self.backoff_schedule_seconds)
        ):
            raise ExecutionDenied("invalid execution-manager timing, threshold or pool bound")
        self._states: dict[str, CredentialRuntimeState] = {}
        self._sessions: dict[str, SessionRuntimeState] = {}
        self._provider_health: dict[str, str] = {}
        self._model_health: dict[tuple[str, str], str] = {}
        self._endpoint_health: dict[tuple[str, str], str] = {}
        for candidate in candidates:
            candidate.validate()
            if candidate.credential_ref in self._states:
                raise ExecutionDenied("duplicate credential reference")
            self._states[candidate.credential_ref] = CredentialRuntimeState(candidate, candidate.state, active_sessions=candidate.active_sessions)
            self._merge_health(self._provider_health, candidate.provider_id, candidate.provider_health)
            if candidate.model_id:
                self._merge_health(self._model_health, (candidate.provider_id, candidate.model_id), candidate.model_health)
            if candidate.endpoint_id:
                self._merge_health(self._endpoint_health, (candidate.provider_id, candidate.endpoint_id), candidate.endpoint_health)

    @staticmethod
    def _merge_health(store: dict, key: object, state: str) -> None:
        if state not in HEALTH_STATES:
            raise ExecutionDenied("invalid health state")
        current = store.get(key)
        if current is None or HEALTH_ORDER[state] > HEALTH_ORDER[current]:
            store[key] = state

    def update_health(self, *, provider_id: str, state: str, model_id: str | None = None, endpoint_id: str | None = None) -> None:
        if state not in HEALTH_STATES:
            raise ExecutionDenied("invalid health state")
        if model_id and endpoint_id:
            raise ExecutionDenied("update one health dimension at a time")
        if model_id:
            self._model_health[(provider_id, model_id)] = state
        elif endpoint_id:
            self._endpoint_health[(provider_id, endpoint_id)] = state
        else:
            self._provider_health[provider_id] = state

    def _effective_health(self, st: CredentialRuntimeState) -> tuple[str, str, str]:
        c = st.candidate
        provider = self._provider_health.get(c.provider_id, c.provider_health)
        model = self._model_health.get((c.provider_id, c.model_id), c.model_health) if c.model_id else c.model_health
        endpoint = self._endpoint_health.get((c.provider_id, c.endpoint_id), c.endpoint_health) if c.endpoint_id else c.endpoint_health
        return provider, model, endpoint

    def _refresh(self, st: CredentialRuntimeState, now: float) -> None:
        if st.circuit_state == "OPEN" and now >= st.circuit_until:
            st.circuit_state = "HALF_OPEN"
        if st.state in {"RATE_LIMITED", "COOLDOWN"} and now >= st.cooldown_until:
            st.state = "HEALTHY"

    def _eligible(self, st: CredentialRuntimeState, now: float) -> bool:
        self._refresh(st, now)
        provider_health, model_health, endpoint_health = self._effective_health(st)
        return (
            st.candidate.admitted_provider
            and st.candidate.credential_ref.startswith("secretref:")
            and st.state in ELIGIBLE_STATES
            and st.circuit_state != "OPEN"
            and provider_health != "UNAVAILABLE"
            and model_health != "UNAVAILABLE"
            and endpoint_health != "UNAVAILABLE"
        )

    def _runtime_rank(self, st: CredentialRuntimeState) -> tuple:
        provider_health, model_health, endpoint_health = self._effective_health(st)
        return (
            HEALTH_ORDER[provider_health],
            HEALTH_ORDER[model_health],
            HEALTH_ORDER[endpoint_health],
            STATE_ORDER[st.state],
            st.candidate.quota_pressure,
            st.active_sessions,
            credential_ref_digest(st.candidate.credential_ref),
        )

    def _release_binding(self, session_id: str) -> None:
        old = self._sessions.pop(session_id, None)
        if old:
            st = self._states.get(old.credential_ref)
            if st is not None:
                st.active_sessions = max(0, st.active_sessions - 1)

    def select(self, *, provider_id: str, session_id: str, now: float, _excluded_refs: set[str] | None = None, _rebind_count: int = 0, _attempted_refs: set[str] | None = None) -> dict:
        if not session_id:
            raise ExecutionDenied("session_id required")
        excluded = set(_excluded_refs or ())
        bound = self._sessions.get(session_id)
        if bound and not excluded:
            st = self._states.get(bound.credential_ref)
            if st is not None and bound.expires_at > now and st.candidate.provider_id == provider_id:
                self._refresh(st, now)
                if self._eligible(st, now):
                    return self._lease(st, session_id, now, bound.expires_at, reused=True)
                if st.state in {"COOLDOWN", "RATE_LIMITED"} and now < st.cooldown_until:
                    raise ExecutionDenied("session credential is in explicit backoff")
            self._release_binding(session_id)
        rows = [
            st for st in self._states.values()
            if st.candidate.provider_id == provider_id
            and st.candidate.credential_ref not in excluded
            and self._eligible(st, now)
        ]
        if not rows:
            raise ExecutionDenied("no eligible credential in admitted provider pool")
        rows.sort(key=self._runtime_rank)
        st = rows[0]
        expires_at = now + self.lease_ttl_seconds
        attempted = set(_attempted_refs or ())
        attempted.add(st.candidate.credential_ref)
        self._sessions[session_id] = SessionRuntimeState(st.candidate.credential_ref, expires_at, _rebind_count, attempted)
        st.active_sessions += 1
        return self._lease(st, session_id, now, expires_at, reused=False)

    def _lease(self, st: CredentialRuntimeState, session_id: str, now: float, expires_at: float, *, reused: bool) -> dict:
        session_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        ref_hash = credential_ref_digest(st.candidate.credential_ref)
        lease_id = hashlib.sha256(f"{session_hash}:{ref_hash}:{int(now*1000)}".encode("utf-8")).hexdigest()
        provider_health, model_health, endpoint_health = self._effective_health(st)
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
            "provider_health": provider_health,
            "model_health": model_health,
            "endpoint_health": endpoint_health,
            "raw_credential_present": False,
        }

    def _backoff_seconds(self, st: CredentialRuntimeState, retry_after_seconds: float | None) -> float:
        if retry_after_seconds is not None:
            value = float(retry_after_seconds)
            if value <= 0 or value > 86400:
                raise ExecutionDenied("retry_after_seconds outside bounded range")
            return value
        idx = min(max(st.failure_count - 1, 0), len(self.backoff_schedule_seconds) - 1)
        return self.backoff_schedule_seconds[idx]

    def record_success(self, *, session_id: str, now: float) -> dict:
        binding = self._sessions.get(session_id)
        if not binding:
            raise ExecutionDenied("session binding missing")
        st = self._states[binding.credential_ref]
        self._refresh(st, now)
        st.failure_count = 0
        st.circuit_state = "CLOSED"
        if st.state == "DEGRADED":
            st.state = "HEALTHY"
        c = st.candidate
        if self._provider_health.get(c.provider_id) == "DEGRADED":
            self._provider_health[c.provider_id] = "HEALTHY"
        if c.model_id and self._model_health.get((c.provider_id, c.model_id)) == "DEGRADED":
            self._model_health[(c.provider_id, c.model_id)] = "HEALTHY"
        if c.endpoint_id and self._endpoint_health.get((c.provider_id, c.endpoint_id)) == "DEGRADED":
            self._endpoint_health[(c.provider_id, c.endpoint_id)] = "HEALTHY"
        binding.rebind_count = 0
        binding.attempted_refs = {binding.credential_ref}
        return {"result":"RECORDED","credential_ref_sha256":credential_ref_digest(c.credential_ref),"transient_failure_state_reset":True,"raw_credential_present":False}

    def _receipt(self, *, action: str, reason: str, provider_id: str, old_hash: str, binding: SessionRuntimeState, new_hash: str | None = None, backoff_seconds: float | None = None) -> dict:
        result = {
            "schema":"fa3.route-rebind-receipt.v1","action":action,"reason":reason,"provider_id":provider_id,
            "old_credential_ref_sha256":old_hash,"cross_provider_transition":False,
            "rebind_attempt":binding.rebind_count,"max_rebind_attempts":self.max_rebind_attempts,
            "pool_traversal_count":len(binding.attempted_refs),"max_credentials_per_request":self.max_credentials_per_request,
            "raw_credential_present":False,
        }
        if new_hash is not None:
            result["new_credential_ref_sha256"] = new_hash
        if backoff_seconds is not None:
            result["backoff_seconds"] = backoff_seconds
        return result

    def record_failure(self, *, session_id: str, error_class: str, now: float, retry_after_seconds: float | None = None) -> dict:
        binding = self._sessions.get(session_id)
        if not binding:
            raise ExecutionDenied("session binding missing")
        st = self._states[binding.credential_ref]
        provider_id = st.candidate.provider_id
        old_hash = credential_ref_digest(st.candidate.credential_ref)
        if error_class in FAIL_CLOSED_ERRORS:
            return self._receipt(action="FAIL_CLOSED",reason=error_class,provider_id=provider_id,old_hash=old_hash,binding=binding)
        if error_class not in REBINDS_ALLOWED:
            return self._receipt(action="FAIL_CLOSED",reason="UNKNOWN_ERROR_CLASS",provider_id=provider_id,old_hash=old_hash,binding=binding)
        st.failure_count += 1
        force_rebind = False
        backoff_seconds = None
        if error_class in {"AUTH","CREDENTIAL_REVOKED"}:
            st.state = "AUTH_INVALID"; force_rebind = True
        elif error_class == "QUOTA":
            st.state = "QUOTA_EXHAUSTED"; force_rebind = True
        elif error_class == "RATE_LIMIT":
            backoff_seconds = self._backoff_seconds(st,retry_after_seconds)
            st.state = "RATE_LIMITED"; st.cooldown_until = now + backoff_seconds; force_rebind = True
        elif error_class in {"TRANSIENT_NETWORK","PROVIDER_5XX"}:
            backoff_seconds = self._backoff_seconds(st,retry_after_seconds)
            st.state = "COOLDOWN"; st.cooldown_until = now + backoff_seconds
            if st.failure_count >= self.circuit_threshold:
                st.circuit_state = "OPEN"; st.circuit_until = now + self.circuit_cooldown_seconds; force_rebind = True
        elif error_class == "PROVIDER_OVERLOAD":
            backoff_seconds = self._backoff_seconds(st,retry_after_seconds)
            st.state = "COOLDOWN"; st.cooldown_until = now + backoff_seconds
            self._provider_health[provider_id] = "DEGRADED"; force_rebind = True
        elif error_class == "PROVIDER_UNAVAILABLE":
            self._provider_health[provider_id] = "UNAVAILABLE"; force_rebind = True
        elif error_class == "MODEL_UNAVAILABLE":
            if st.candidate.model_id:
                self._model_health[(provider_id,st.candidate.model_id)] = "UNAVAILABLE"
            else:
                st.state = "DEGRADED"
            force_rebind = True
        elif error_class == "ENDPOINT_UNAVAILABLE":
            if st.candidate.endpoint_id:
                self._endpoint_health[(provider_id,st.candidate.endpoint_id)] = "UNAVAILABLE"
            else:
                st.state = "DEGRADED"
            force_rebind = True
        if not force_rebind:
            return self._receipt(action="RETRY_SAME_CREDENTIAL",reason=error_class,provider_id=provider_id,old_hash=old_hash,binding=binding,backoff_seconds=backoff_seconds)
        attempted = set(binding.attempted_refs); attempted.add(st.candidate.credential_ref)
        next_rebind = binding.rebind_count + 1
        if next_rebind > self.max_rebind_attempts or len(attempted) >= self.max_credentials_per_request:
            binding.rebind_count = next_rebind; binding.attempted_refs = attempted
            receipt = self._receipt(action="MODEL_ROUTER_REEVALUATION_REQUIRED",reason="POOL_TRAVERSAL_BOUNDED",provider_id=provider_id,old_hash=old_hash,binding=binding,backoff_seconds=backoff_seconds)
            self._release_binding(session_id)
            return receipt
        self._release_binding(session_id)
        try:
            lease = self.select(provider_id=provider_id,session_id=session_id,now=now,_excluded_refs=attempted,_rebind_count=next_rebind,_attempted_refs=attempted)
            new_binding = self._sessions[session_id]
            return self._receipt(action="INTRA_PROVIDER_REBIND",reason=error_class,provider_id=provider_id,old_hash=old_hash,new_hash=lease["credential_ref_sha256"],binding=new_binding,backoff_seconds=backoff_seconds)
        except ExecutionDenied:
            exhausted = SessionRuntimeState(st.candidate.credential_ref,now,next_rebind,attempted)
            return self._receipt(action="MODEL_ROUTER_REEVALUATION_REQUIRED",reason=error_class,provider_id=provider_id,old_hash=old_hash,binding=exhausted,backoff_seconds=backoff_seconds)

    def release_session(self, session_id: str) -> None:
        self._release_binding(session_id)

    def safe_snapshot(self, *, now: float) -> dict:
        rows=[]
        for st in self._states.values():
            self._refresh(st,now)
            provider_health,model_health,endpoint_health=self._effective_health(st)
            rows.append({
                "provider_id":st.candidate.provider_id,"model_id":st.candidate.model_id,"endpoint_id":st.candidate.endpoint_id,
                "credential_ref_sha256":credential_ref_digest(st.candidate.credential_ref),"credential_state":st.state,
                "provider_health":provider_health,"model_health":model_health,"endpoint_health":endpoint_health,
                "quota_pressure":st.candidate.quota_pressure,"quota_reset_at":st.candidate.quota_reset_at,
                "circuit_state":st.circuit_state,"failure_count":st.failure_count,
                "cooldown_until_monotonic":st.cooldown_until,"active_sessions":st.active_sessions,
            })
        return {
            "schema":"fa3.provider-execution-state.v2",
            "credentials":sorted(rows,key=lambda r:(r["provider_id"],r["credential_ref_sha256"])),
            "pool_bounds":{"max_rebind_attempts":self.max_rebind_attempts,"max_credentials_per_request":self.max_credentials_per_request,"backoff_schedule_seconds":list(self.backoff_schedule_seconds)},
            "raw_credential_present":False,
        }
