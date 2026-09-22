"""FA3 accelerator contention policy engine.

Provider-neutral core for FA3-ACCEL-GUARD-001. Hardware telemetry adapters
(NVML/DRM/Linux accel/etc.) feed snapshots into this module. This module does
not terminate processes or manipulate devices; HRB/action executors apply an
explicit user decision or a previously saved explicit policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Optional

from fa3_accelerator_execution_path import execution_path_matches


class Origin(str, Enum):
    FA3_MANAGED = "FA3_MANAGED"
    SYSTEM_TRUSTED = "SYSTEM_TRUSTED"
    EXTERNAL_KNOWN = "EXTERNAL_KNOWN"
    EXTERNAL_ALLOWED = "EXTERNAL_ALLOWED"
    EXTERNAL_UNKNOWN = "EXTERNAL_UNKNOWN"
    ORPHANED_FA3 = "ORPHANED_FA3"


class GuardMode(str, Enum):
    OBSERVE = "OBSERVE"
    RECOMMEND = "RECOMMEND"
    POLICY = "POLICY"
    EXCLUSIVE = "EXCLUSIVE"


class AcceleratorState(str, Enum):
    AVAILABLE = "AVAILABLE"
    SHARED_SAFE = "SHARED_SAFE"
    CONTENTION_WARNING = "CONTENTION_WARNING"
    CONFLICT = "CONFLICT"
    USER_DECISION_REQUIRED = "USER_DECISION_REQUIRED"
    RESERVED = "RESERVED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class WorkloadState(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_ACCELERATOR = "WAITING_ACCELERATOR"
    PENDING_USER_DECISION = "PENDING_USER_DECISION"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    MIGRATING = "MIGRATING"
    TERMINATING = "TERMINATING"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    FAILED = "FAILED"


class DecisionAction(str, Enum):
    KEEP_EXTERNAL = "KEEP_EXTERNAL"
    PREFER_FA3 = "PREFER_FA3"
    MOVE_FA3 = "MOVE_FA3"
    PAUSE_FA3 = "PAUSE_FA3"
    WAIT = "WAIT"
    ALLOW_SHARED = "ALLOW_SHARED"
    CANCEL_FA3 = "CANCEL_FA3"
    ALLOW_ONCE = "ALLOW_ONCE"
    REMEMBER_DECISION = "REMEMBER_DECISION"


@dataclass(frozen=True)
class ClientUsage:
    pid: int
    name: str
    origin: Origin
    memory_bytes: int = 0
    compute_utilization: float = 0.0
    systemd_unit: Optional[str] = None
    cgroup: Optional[str] = None
    workload_id: Optional[str] = None
    lease_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.pid < 0:
            raise ValueError("pid must be non-negative")
        if self.memory_bytes < 0:
            raise ValueError("memory_bytes must be non-negative")
        if not 0.0 <= self.compute_utilization <= 1.0:
            raise ValueError("compute_utilization must be in [0, 1]")


@dataclass(frozen=True)
class AcceleratorSnapshot:
    accelerator_id: str
    kind: str
    total_memory_bytes: int
    clients: tuple[ClientUsage, ...] = ()
    safety_headroom_bytes: int = 0
    role: str = "compute"
    healthy: bool = True
    vendor: Optional[str] = None
    stable_device_id: Optional[str] = None
    pci_bdf: Optional[str] = None
    kernel_driver: Optional[str] = None
    execution_paths: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if self.total_memory_bytes < 0 or self.safety_headroom_bytes < 0:
            raise ValueError("memory values must be non-negative")

    @property
    def allocated_memory_bytes(self) -> int:
        return sum(c.memory_bytes for c in self.clients)

    @property
    def effective_available_memory_bytes(self) -> int:
        return max(0, self.total_memory_bytes - self.allocated_memory_bytes - self.safety_headroom_bytes)

    @property
    def external_clients(self) -> tuple[ClientUsage, ...]:
        return tuple(c for c in self.clients if c.origin in {
            Origin.EXTERNAL_KNOWN, Origin.EXTERNAL_ALLOWED, Origin.EXTERNAL_UNKNOWN
        })


@dataclass(frozen=True)
class WorkloadRequest:
    workload_id: str
    required_memory_bytes: int
    accelerator_kind: Optional[str] = None
    preferred_accelerator_id: Optional[str] = None
    execution_requirement: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.required_memory_bytes < 0:
            raise ValueError("required_memory_bytes must be non-negative")


@dataclass(frozen=True)
class Assessment:
    severity: str
    memory_capacity_risk: str
    compute_contention_risk: str
    reason: str


@dataclass(frozen=True)
class Recommendation:
    action: DecisionAction
    target_accelerator_id: Optional[str]
    reason: str
    action_taken: bool = False


@dataclass
class ConflictRecord:
    id: str
    accelerator_id: str
    state: AcceleratorState
    existing_clients: tuple[ClientUsage, ...]
    requesting_workload: WorkloadRequest
    assessment: Assessment
    recommendation: Recommendation
    workload_state: WorkloadState
    decision: Optional[DecisionAction] = None
    decision_actor: Optional[str] = None
    policy_id: Optional[str] = None


@dataclass(frozen=True)
class SavedPolicy:
    policy_id: str
    external_name: Optional[str]
    fa3_workload_prefix: Optional[str]
    action: DecisionAction
    explicit_user_created: bool = True

    def matches(self, external_names: Iterable[str], workload_id: str) -> bool:
        if not self.explicit_user_created:
            return False
        if self.external_name is not None and self.external_name not in set(external_names):
            return False
        if self.fa3_workload_prefix is not None and not workload_id.startswith(self.fa3_workload_prefix):
            return False
        return True


def _compute_risk(snapshot: AcceleratorSnapshot) -> str:
    external_peak = max((c.compute_utilization for c in snapshot.external_clients), default=0.0)
    if external_peak >= 0.80:
        return "HIGH"
    if external_peak >= 0.40:
        return "MEDIUM"
    return "LOW"


def _supports_execution(snapshot: AcceleratorSnapshot, request: WorkloadRequest) -> bool:
    if request.execution_requirement in (None, {}):
        return True
    return any(
        execution_path_matches(request.execution_requirement, path)
        for path in snapshot.execution_paths
    )


def _find_alternative(request: WorkloadRequest, candidates: Iterable[AcceleratorSnapshot], exclude_id: str) -> Optional[AcceleratorSnapshot]:
    viable = [s for s in candidates if s.accelerator_id != exclude_id and s.healthy
              and (request.accelerator_kind is None or s.kind == request.accelerator_kind)
              and _supports_execution(s, request)
              and s.effective_available_memory_bytes >= request.required_memory_bytes]
    return max(viable, key=lambda s: s.effective_available_memory_bytes, default=None)


def evaluate_request(snapshot: AcceleratorSnapshot, request: WorkloadRequest, *, candidates: Iterable[AcceleratorSnapshot] = (), conflict_id: str = "pending") -> Optional[ConflictRecord]:
    """Return a conflict only when a user/policy decision is materially needed."""
    if not _supports_execution(snapshot, request):
        assessment = Assessment("CRITICAL", "UNKNOWN", "UNKNOWN", "accelerator execution path is incompatible with workload requirement")
        alt = _find_alternative(request, candidates, snapshot.accelerator_id)
        recommendation = (
            Recommendation(DecisionAction.MOVE_FA3, alt.accelerator_id, "Use another execution-compatible accelerator.")
            if alt is not None
            else Recommendation(DecisionAction.WAIT, None, "No execution-compatible alternative accelerator is currently available.")
        )
        return ConflictRecord(conflict_id, snapshot.accelerator_id, AcceleratorState.USER_DECISION_REQUIRED,
                              snapshot.clients, request, assessment, recommendation, WorkloadState.PENDING_USER_DECISION)

    if not snapshot.healthy:
        assessment = Assessment("CRITICAL", "UNKNOWN", "UNKNOWN", "accelerator is unhealthy")
        alt = _find_alternative(request, candidates, snapshot.accelerator_id)
        recommendation = Recommendation(DecisionAction.MOVE_FA3, getattr(alt, "accelerator_id", None), "Use another healthy accelerator when available.")
        return ConflictRecord(conflict_id, snapshot.accelerator_id, AcceleratorState.USER_DECISION_REQUIRED,
                              snapshot.clients, request, assessment, recommendation, WorkloadState.PENDING_USER_DECISION)

    free = snapshot.effective_available_memory_bytes
    compute_risk = _compute_risk(snapshot)
    if free >= request.required_memory_bytes and compute_risk == "LOW":
        return None

    deficit = max(0, request.required_memory_bytes - free)
    if deficit > 0:
        ratio = deficit / max(request.required_memory_bytes, 1)
        severity = "CRITICAL" if ratio >= 0.25 else "HIGH"
        memory_risk = "HIGH"
        reason = f"required={request.required_memory_bytes} available={free}; safe memory capacity is insufficient"
    else:
        severity = "WARNING"
        memory_risk = "LOW"
        reason = "memory fits, but concurrent external compute load may degrade or destabilize the workload"

    alternative = _find_alternative(request, candidates, snapshot.accelerator_id)
    if alternative is not None:
        recommendation = Recommendation(DecisionAction.MOVE_FA3, alternative.accelerator_id,
                                        "Alternative accelerator has sufficient measured effective capacity.")
    else:
        recommendation = Recommendation(DecisionAction.WAIT, None,
                                        "No conflict-free alternative accelerator has sufficient measured capacity.")

    return ConflictRecord(conflict_id, snapshot.accelerator_id, AcceleratorState.USER_DECISION_REQUIRED,
                          snapshot.clients, request, Assessment(severity, memory_risk, compute_risk, reason),
                          recommendation, WorkloadState.PENDING_USER_DECISION)


def resolve_actor(conflict: ConflictRecord, mode: GuardMode, policies: Iterable[SavedPolicy]) -> tuple[str, Optional[SavedPolicy]]:
    """Select USER unless POLICY mode has an explicit matching user-created rule."""
    if mode is GuardMode.POLICY:
        external_names = [c.name for c in conflict.existing_clients]
        for policy in policies:
            if policy.matches(external_names, conflict.requesting_workload.workload_id):
                return "POLICY", policy
    return "USER", None


def submit_decision(conflict: ConflictRecord, action: DecisionAction, *, actor: str = "USER", policy_id: Optional[str] = None) -> ConflictRecord:
    """Record an authorized decision; actual device/process action belongs to HRB/executor."""
    if actor not in {"USER", "POLICY"}:
        raise ValueError("actor must be USER or POLICY")
    if actor == "POLICY" and not policy_id:
        raise ValueError("policy decision requires policy_id")
    conflict.decision = action
    conflict.decision_actor = actor
    conflict.policy_id = policy_id
    return conflict


def action_plan(conflict: ConflictRecord) -> dict[str, object]:
    """Translate a recorded decision into a side-effect-free HRB executor plan."""
    if conflict.decision is None:
        raise ValueError("decision is required before execution planning")
    return {
        "conflict_id": conflict.id,
        "accelerator_id": conflict.accelerator_id,
        "workload_id": conflict.requesting_workload.workload_id,
        "action": conflict.decision.value,
        "actor": conflict.decision_actor,
        "policy_id": conflict.policy_id,
        "force_terminate_external": False,
        "requires_hrb_execution": True,
    }
