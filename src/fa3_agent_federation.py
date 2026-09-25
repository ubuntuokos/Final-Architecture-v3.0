#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

ENVELOPE_SCHEMA = "fa3.federation-envelope.v1"
SIGNATURE_ALGORITHM = "ED25519"
BUDGET_FIELDS = (
    "max_hops",
    "max_tokens",
    "max_wall_time_seconds",
    "max_children",
    "max_remote_delegations",
    "max_model_cost_microunits",
    "max_cpu_seconds",
    "max_gpu_seconds",
)


class FederationContractError(ValueError):
    pass


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_digest(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload)).hexdigest()


def signing_bytes(envelope: dict[str, Any]) -> bytes:
    body = dict(envelope)
    body.pop("signature", None)
    return _canonical_json(body)


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise FederationContractError(f"{label} required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FederationContractError(f"{label} invalid") from exc
    if parsed.tzinfo is None:
        raise FederationContractError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def validate_budget(budget: Any) -> dict[str, int]:
    if not isinstance(budget, dict):
        raise FederationContractError("budget object required")
    out: dict[str, int] = {}
    for field in BUDGET_FIELDS:
        value = budget.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise FederationContractError(f"invalid budget field: {field}")
        out[field] = value
    return out


def derive_child_budget(parent_remaining: dict[str, int], requested: dict[str, int]) -> dict[str, int]:
    parent = validate_budget(parent_remaining)
    child = validate_budget(requested)
    for field in BUDGET_FIELDS:
        if child[field] > parent[field]:
            raise FederationContractError(f"child budget exceeds parent remaining: {field}")
    return child


class ReplayGuard:
    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def accept(self, sender_peer_id: str, nonce: str) -> None:
        key = (sender_peer_id, nonce)
        if key in self._seen:
            raise FederationContractError("replayed federation envelope")
        self._seen.add(key)


def _validate_ai_comms_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise FederationContractError("payload object required")
    if payload.get("human_readable_authoritative") is not True:
        raise FederationContractError("FA3 AI-Comms authoritative human text required")
    if payload.get("communication_mode") not in {"HUMAN_LANGUAGE", "CANONICAL_STRUCTURED"}:
        raise FederationContractError("unsupported communication mode")
    if not isinstance(payload.get("language_tag"), str) or not payload.get("language_tag"):
        raise FederationContractError("language_tag required")
    if not isinstance(payload.get("human_readable_text"), str) or not payload.get("human_readable_text").strip():
        raise FederationContractError("human_readable_text required")


def validate_envelope(
    envelope: Any,
    verify_signature: Callable[[str, bytes, str], bool],
    *,
    replay_guard: ReplayGuard | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise FederationContractError("envelope object required")
    required = (
        "schema", "message_id", "task_id", "sender_peer_id", "sender_agent_id",
        "recipient_peer_id", "recipient_agent_id", "issued_at", "expires_at", "nonce",
        "hop", "max_hops", "budget", "payload_digest", "payload",
        "signature_algorithm", "signing_key_id", "signature",
    )
    missing = [field for field in required if field not in envelope]
    if missing:
        raise FederationContractError("missing envelope fields: " + ",".join(missing))
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise FederationContractError("unsupported federation envelope schema")
    for field in ("message_id", "task_id", "sender_peer_id", "sender_agent_id", "recipient_peer_id", "recipient_agent_id", "nonce", "signing_key_id", "signature"):
        if not isinstance(envelope.get(field), str) or not envelope.get(field):
            raise FederationContractError(f"{field} required")
    if envelope.get("signature_algorithm") != SIGNATURE_ALGORITHM:
        raise FederationContractError("only ED25519 federation signatures are canonical")
    issued = _parse_utc(envelope.get("issued_at"), "issued_at")
    expires = _parse_utc(envelope.get("expires_at"), "expires_at")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if expires <= issued or current >= expires:
        raise FederationContractError("expired federation envelope")
    if issued > current:
        raise FederationContractError("future-issued federation envelope")
    hop = envelope.get("hop")
    max_hops = envelope.get("max_hops")
    if not isinstance(hop, int) or not isinstance(max_hops, int) or hop < 0 or max_hops < 0 or hop > max_hops:
        raise FederationContractError("invalid or exceeded hop budget")
    budget = validate_budget(envelope.get("budget"))
    if budget["max_hops"] != max_hops:
        raise FederationContractError("envelope hop limit and budget max_hops differ")
    _validate_ai_comms_payload(envelope.get("payload"))
    if envelope.get("payload_digest") != payload_digest(envelope.get("payload")):
        raise FederationContractError("payload digest mismatch")
    if not verify_signature(envelope["signing_key_id"], signing_bytes(envelope), envelope["signature"]):
        raise FederationContractError("peer signature verification failed")
    if replay_guard is not None:
        replay_guard.accept(envelope["sender_peer_id"], envelope["nonce"])
    return envelope


@dataclass(frozen=True)
class Claim:
    claim_id: str
    resource_id: str
    task_id: str
    owner_peer_id: str
    owner_agent_id: str
    issued_at: int
    expires_at: int
    generation: int
    status: str = "ACTIVE"


class ClaimLedger:
    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}
        self.events: list[dict[str, Any]] = []

    def _active(self, resource_id: str, now: int) -> Claim | None:
        claim = self._claims.get(resource_id)
        if claim is None or claim.status != "ACTIVE":
            return None
        if claim.expires_at <= now:
            expired = Claim(**{**claim.__dict__, "status": "EXPIRED"})
            self._claims[resource_id] = expired
            self.events.append({"event": "EXPIRE", "claim_id": claim.claim_id, "resource_id": resource_id, "generation": claim.generation})
            return None
        return claim

    def acquire(self, *, claim_id: str, resource_id: str, task_id: str, owner_peer_id: str, owner_agent_id: str, now: int, ttl_seconds: int) -> Claim:
        if ttl_seconds <= 0:
            raise FederationContractError("claim ttl must be positive")
        if self._active(resource_id, now) is not None:
            raise FederationContractError("resource already has an active coordination claim")
        previous = self._claims.get(resource_id)
        generation = 1 if previous is None else previous.generation + 1
        claim = Claim(claim_id, resource_id, task_id, owner_peer_id, owner_agent_id, now, now + ttl_seconds, generation)
        self._claims[resource_id] = claim
        self.events.append({"event": "ACQUIRE", "claim_id": claim_id, "resource_id": resource_id, "generation": generation})
        return claim

    def current(self, resource_id: str, *, now: int) -> Claim | None:
        return self._active(resource_id, now)

    def renew(self, resource_id: str, *, owner_peer_id: str, owner_agent_id: str, now: int, ttl_seconds: int) -> Claim:
        claim = self._active(resource_id, now)
        if claim is None:
            raise FederationContractError("no active claim to renew")
        if (claim.owner_peer_id, claim.owner_agent_id) != (owner_peer_id, owner_agent_id):
            raise FederationContractError("only current claim owner may renew")
        if ttl_seconds <= 0:
            raise FederationContractError("claim ttl must be positive")
        renewed = Claim(**{**claim.__dict__, "expires_at": now + ttl_seconds, "generation": claim.generation + 1})
        self._claims[resource_id] = renewed
        self.events.append({"event": "RENEW", "claim_id": claim.claim_id, "resource_id": resource_id, "generation": renewed.generation})
        return renewed

    def handoff(self, resource_id: str, *, from_peer_id: str, from_agent_id: str, to_peer_id: str, to_agent_id: str, now: int, ttl_seconds: int) -> Claim:
        claim = self._active(resource_id, now)
        if claim is None:
            raise FederationContractError("no active claim to handoff")
        if (claim.owner_peer_id, claim.owner_agent_id) != (from_peer_id, from_agent_id):
            raise FederationContractError("only current claim owner may handoff")
        if ttl_seconds <= 0:
            raise FederationContractError("claim ttl must be positive")
        handed = Claim(claim.claim_id, claim.resource_id, claim.task_id, to_peer_id, to_agent_id, now, now + ttl_seconds, claim.generation + 1, "ACTIVE")
        self._claims[resource_id] = handed
        self.events.append({"event": "HANDOFF", "claim_id": claim.claim_id, "resource_id": resource_id, "generation": handed.generation, "to_peer_id": to_peer_id, "to_agent_id": to_agent_id})
        return handed

    def release(self, resource_id: str, *, owner_peer_id: str, owner_agent_id: str, now: int) -> Claim:
        claim = self._active(resource_id, now)
        if claim is None:
            raise FederationContractError("no active claim to release")
        if (claim.owner_peer_id, claim.owner_agent_id) != (owner_peer_id, owner_agent_id):
            raise FederationContractError("only current claim owner may release")
        released = Claim(**{**claim.__dict__, "status": "RELEASED", "generation": claim.generation + 1})
        self._claims[resource_id] = released
        self.events.append({"event": "RELEASE", "claim_id": claim.claim_id, "resource_id": resource_id, "generation": released.generation})
        return released


_ALLOWED_CIRCUIT_TRANSITIONS = {
    "ACTIVE": {"SUSPENDED", "QUARANTINED", "REVOKED"},
    "SUSPENDED": {"ACTIVE", "QUARANTINED", "REVOKED"},
    "QUARANTINED": {"ACTIVE", "REVOKED"},
    "REVOKED": set(),
}


def circuit_transition_allowed(source: str, target: str, *, security_authorized: bool = False) -> bool:
    if target not in _ALLOWED_CIRCUIT_TRANSITIONS.get(source, set()):
        return False
    if source in {"SUSPENDED", "QUARANTINED"} and target == "ACTIVE":
        return security_authorized
    return True


def admit_remote_execution(assertions: dict[str, bool]) -> dict[str, Any]:
    required = ("peer_identity_verified","security_authorized","agent_runtime_admitted","uaf_route_present","remote_hrb_admission_present","provider_runtime_admission_present")
    missing = [key for key in required if assertions.get(key) is not True]
    if missing:
        raise FederationContractError("remote execution admission denied: " + ",".join(missing))
    return {"status":"ADMITTED","authority":False,"resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","execution_boundary":"FA3-UNIFIED-ACTION-FABRIC-001"}


def trust_signal(*, interaction_score: float, interaction_count: int) -> dict[str, Any]:
    return {"score":float(interaction_score),"count":int(interaction_count),"authorization":False,"capability_grant":False,"remote_spawn_grant":False,"semantics":"ADVISORY_ONLY"}


LIFECYCLE_EVENT_TYPES = {
    "TASK_PREPARED", "TASK_STARTED", "DELEGATION_CREATED", "CLAIM_ACQUIRED",
    "ACTION_STARTED", "ACTION_COMPLETED", "DELEGATION_COMPLETED", "CLAIM_RELEASED",
    "TASK_COMPLETED", "TASK_FAILED", "TASK_CANCELLED",
}


def project_lifecycle_event(
    *,
    event_id: str,
    event_type: str,
    task_id: str,
    run_id: str,
    timestamp: str,
    human_readable_text: str,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    if event_type not in LIFECYCLE_EVENT_TYPES:
        raise FederationContractError("unsupported federation lifecycle event")
    if not all(isinstance(v, str) and v for v in (event_id, task_id, run_id, timestamp, human_readable_text)):
        raise FederationContractError("lifecycle event identity/text fields required")
    _parse_utc(timestamp, "timestamp")
    evidence = list(evidence_ids or [])
    if any(not isinstance(x, str) or not x for x in evidence):
        raise FederationContractError("invalid lifecycle evidence id")
    return {
        "schema": "fa3.federation-lifecycle-event-projection.v1",
        "event_id": event_id,
        "event_type": event_type,
        "task_id": task_id,
        "run_id": run_id,
        "timestamp": timestamp,
        "human_readable_text": human_readable_text,
        "evidence_ids": evidence,
        "journal_authority": "FA3-JOURNAL-001",
        "loop_ledger_profile": "FA3-CLOSED-LOOP-AGENT-OPERATIONS-001",
        "authorization": False,
        "durable_orchestration_authority": False,
    }


def build_execution_trajectory(
    *,
    trajectory_id: str,
    events: list[dict[str, Any]],
    outcome: str,
    evidence_ids: list[str],
) -> dict[str, Any]:
    allowed = {"SUCCESS", "PARTIAL", "FAILURE", "CANCELLED", "INCONCLUSIVE"}
    if not isinstance(trajectory_id, str) or not trajectory_id:
        raise FederationContractError("trajectory_id required")
    if outcome not in allowed:
        raise FederationContractError("unsupported trajectory outcome")
    if not events:
        raise FederationContractError("trajectory requires source events")
    task_ids = {x.get("task_id") for x in events}
    run_ids = {x.get("run_id") for x in events}
    event_ids = [x.get("event_id") for x in events]
    if len(task_ids) != 1 or None in task_ids or len(run_ids) != 1 or None in run_ids:
        raise FederationContractError("trajectory source events must share task/run identity")
    if len(event_ids) != len(set(event_ids)) or any(not isinstance(x, str) or not x for x in event_ids):
        raise FederationContractError("trajectory event identity invalid")
    if not evidence_ids or any(not isinstance(x, str) or not x for x in evidence_ids):
        raise FederationContractError("trajectory outcome evidence required")
    return {
        "schema": "fa3.execution-trajectory.v1",
        "trajectory_id": trajectory_id,
        "task_id": next(iter(task_ids)),
        "run_id": next(iter(run_ids)),
        "event_ids": event_ids,
        "started_at": events[0].get("timestamp"),
        "ended_at": events[-1].get("timestamp"),
        "outcome": outcome,
        "evidence_ids": list(evidence_ids),
        "source_event_provenance_preserved": True,
        "evidence_authority": False,
        "memory_authority": False,
    }


def create_pattern_candidate(
    *,
    candidate_id: str,
    trajectory: dict[str, Any],
    proposal: dict[str, Any],
    authority_grants: list[str] | None = None,
    capability_grants: list[str] | None = None,
) -> dict[str, Any]:
    if not candidate_id or trajectory.get("schema") != "fa3.execution-trajectory.v1":
        raise FederationContractError("valid trajectory-bound pattern candidate required")
    if not trajectory.get("evidence_ids"):
        raise FederationContractError("pattern candidate requires outcome evidence lineage")
    if authority_grants or capability_grants:
        raise FederationContractError("learned pattern cannot grant authority or capability")
    return {
        "schema": "fa3.pattern-candidate.v1",
        "candidate_id": candidate_id,
        "trajectory_id": trajectory["trajectory_id"],
        "task_id": trajectory["task_id"],
        "proposal": dict(proposal),
        "source_evidence_ids": list(trajectory["evidence_ids"]),
        "state": "REVIEW_REQUIRED",
        "authority_grants": [],
        "capability_grants": [],
        "automatic_promotion": False,
    }


def review_pattern_candidate(
    candidate: dict[str, Any],
    *,
    review_state: str,
    review_evidence_ids: list[str],
    risk_class: str,
    human_approved: bool,
) -> dict[str, Any]:
    if candidate.get("schema") != "fa3.pattern-candidate.v1":
        raise FederationContractError("pattern candidate required")
    if review_state not in {"APPROVED", "REJECTED"}:
        raise FederationContractError("explicit pattern review state required")
    if not review_evidence_ids:
        raise FederationContractError("pattern review evidence required")
    high_risk = risk_class.upper() in {"HIGH", "CRITICAL"}
    if review_state == "APPROVED" and high_risk and human_approved is not True:
        raise FederationContractError("high-risk pattern promotion requires human approval")
    return {
        "schema": "fa3.pattern-promotion-receipt.v1",
        "candidate_id": candidate["candidate_id"],
        "state": "PROMOTED" if review_state == "APPROVED" else "REJECTED",
        "review_evidence_ids": list(review_evidence_ids),
        "risk_class": risk_class.upper(),
        "human_approved": bool(human_approved),
        "memory_mutation_authority": False,
        "authorization_expansion": False,
        "capability_expansion": False,
    }


def admit_adaptive_worker(
    *,
    trigger_mode: str,
    early_exit: bool,
    budget_gate: bool,
    noop_path: bool,
    temporal_bound: bool,
    uaf_bound: bool,
    hrb_bound: bool,
    hidden_resident_worker: bool,
) -> dict[str, Any]:
    if hidden_resident_worker:
        raise FederationContractError("hidden resident adaptive worker authority forbidden")
    if not all((temporal_bound, uaf_bound, hrb_bound)):
        raise FederationContractError("adaptive worker must reuse Temporal/UAF/HRB boundaries")
    if trigger_mode not in {"EVENT_DRIVEN", "CHANGE_WATCH", "ADAPTIVE_POLLING", "FIXED_POLLING"}:
        raise FederationContractError("unsupported adaptive worker trigger")
    if trigger_mode in {"ADAPTIVE_POLLING", "FIXED_POLLING"} and not all((early_exit, budget_gate, noop_path)):
        raise FederationContractError("polling adaptive worker requires early-exit budget and no-op path")
    return {
        "status": "ADMITTED",
        "trigger_mode": trigger_mode,
        "durable_lifecycle": "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY",
        "execution_boundary": "FA3-UNIFIED-ACTION-FABRIC-001",
        "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "provider_authority": False,
    }
