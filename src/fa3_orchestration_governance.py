#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timezone
import re
from typing import Any

class OrchestrationGovernanceError(ValueError):
    pass

DEPENDENCY_TYPES = {
    "STRUCTURAL_PARENT", "BLOCKED_BY", "DATA_REQUIRES", "APPROVAL_REQUIRES",
    "RESOURCE_REQUIRES", "VERIFY_REQUIRES", "HANDOFF_TO", "SUPERSEDES",
}
HARD_DEPENDENCY_TYPES = {
    "BLOCKED_BY", "DATA_REQUIRES", "APPROVAL_REQUIRES",
    "RESOURCE_REQUIRES", "VERIFY_REQUIRES",
}
QUALIFYING_SPLIT_REASONS = {
    "SPECIALIST_OR_OWNER_BOUNDARY", "PERMISSION_BOUNDARY",
    "INDEPENDENT_PARALLEL_DELIVERABLE", "HARD_DEPENDENCY_OR_HANDOFF",
    "INDEPENDENT_REVIEW_OR_APPROVAL", "INDEPENDENT_RETRY_OR_RECOVERY",
}
HANDOFF_STATES = {"CREATED", "DELIVERED", "ACKNOWLEDGED", "ACCEPTED", "REJECTED", "SUPERSEDED", "EXPIRED"}
RECOVERY_CLASSES = {"RETRYABLE", "RECOVERABLE", "REPLAN_REQUIRED", "HUMAN_REQUIRED", "UNKNOWN_EFFECT"}

LIVENESS_STATES = {
    "READY", "CLAIMED", "RUNNING", "WAITING_INPUT", "WAITING_APPROVAL",
    "WAITING_RESOURCE", "BLOCKED", "RECOVERING", "STALLED", "CANCELLING",
    "FINISHED", "FAILED", "UNKNOWN",
}
TERMINAL_CLAIM_STATES = {"RELEASED", "FINISHED", "FAILED", "CANCELLED", "TIMED_OUT"}
BUDGET_KEYS = {
    "time_seconds", "cpu_seconds", "gpu_seconds", "npu_seconds",
    "memory_byte_seconds", "storage_bytes", "network_bytes",
    "provider_cost", "token_count", "retry_count", "parallelism",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

def _strings(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        raise OrchestrationGovernanceError(f"{name} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise OrchestrationGovernanceError(f"{name} must be unique")
    return list(value)

def validate_responsibility_chain(chain: Any) -> list[dict[str, Any]]:
    if not isinstance(chain, list) or not chain:
        raise OrchestrationGovernanceError("responsibility_chain must be non-empty")
    out = []
    parent_scope = None
    for row in chain:
        if not isinstance(row, dict) or not isinstance(row.get("principal_id"), str) or not row["principal_id"]:
            raise OrchestrationGovernanceError("responsibility principal_id required")
        if not isinstance(row.get("role"), str) or not row["role"]:
            raise OrchestrationGovernanceError("responsibility role required")
        scope = set(_strings(row.get("authority_scope", []), "authority_scope"))
        if parent_scope is not None and not scope.issubset(parent_scope):
            raise OrchestrationGovernanceError("delegated authority scope expansion forbidden")
        parent_scope = scope
        out.append({**row, "authority_scope": sorted(scope)})
    return out

def validate_task_split(task: dict[str, Any]) -> None:
    if task.get("parent_task_id"):
        reasons = set(_strings(task.get("split_reasons", []), "split_reasons"))
        if not reasons or not reasons.issubset(QUALIFYING_SPLIT_REASONS):
            raise OrchestrationGovernanceError("subtask requires a qualifying execution boundary")

def validate_budget_envelope(value: Any) -> dict[str, float | int]:
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise OrchestrationGovernanceError("budget_envelope must be an object")
    if set(value) - BUDGET_KEYS:
        raise OrchestrationGovernanceError("unknown budget key")
    out = {}
    for key, amount in value.items():
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
            raise OrchestrationGovernanceError("budget values must be non-negative numbers")
        out[key] = amount
    return out

def validate_dependency_graph(task_ids: list[str], edges: Any) -> list[dict[str, str]]:
    ids = set(task_ids)
    if not isinstance(edges, list):
        raise OrchestrationGovernanceError("dependency_edges must be a list")
    normalized = []
    seen = set()
    graph = {task_id: [] for task_id in ids}
    for edge in edges:
        if not isinstance(edge, dict):
            raise OrchestrationGovernanceError("dependency edge must be an object")
        source, target, kind = edge.get("from_task_id"), edge.get("to_task_id"), edge.get("type")
        if source not in ids or target not in ids or source == target:
            raise OrchestrationGovernanceError("dependency edge references invalid task")
        if kind not in DEPENDENCY_TYPES:
            raise OrchestrationGovernanceError("unknown dependency type")
        key = (source, target, kind)
        if key in seen:
            raise OrchestrationGovernanceError("duplicate dependency edge")
        seen.add(key)
        normalized.append({"from_task_id": source, "to_task_id": target, "type": kind})
        if kind in HARD_DEPENDENCY_TYPES:
            graph[source].append(target)
    visiting, done = set(), set()
    def visit(node: str) -> None:
        if node in visiting:
            raise OrchestrationGovernanceError("hard dependency cycle")
        if node in done:
            return
        visiting.add(node)
        for nxt in graph[node]:
            visit(nxt)
        visiting.remove(node)
        done.add(node)
    for task_id in ids:
        visit(task_id)
    return normalized

def build_task_governance(task: dict[str, Any], goal: str = "") -> dict[str, Any]:
    validate_task_split(task)
    ancestry = _strings(task.get("objective_ancestry", []), "objective_ancestry")
    if not ancestry:
        ancestry = [x for x in (goal, task.get("task_id")) if isinstance(x, str) and x]
    chain = task.get("responsibility_chain")
    if chain is None:
        chain = [
            {"principal_id": "AUTH-HUMAN", "role": "GOAL_OWNER", "authority_scope": []},
            {"principal_id": "FA3-ORCHESTRATION-DIRECTOR-001", "role": "COORDINATOR", "authority_scope": []},
        ]
    liveness = task.get("liveness_state", "READY")
    if liveness not in LIVENESS_STATES:
        raise OrchestrationGovernanceError("invalid liveness state")
    return {
        "schema": "fa3.orchestration-task-governance.v1",
        "objective_ancestry": ancestry,
        "responsibility_chain": validate_responsibility_chain(chain),
        "budget_envelope": validate_budget_envelope(task.get("budget_envelope", {})),
        "liveness_state": liveness,
        "execution_claim_required": bool(task.get("runtime_execution", False)),
        "approval_binding_required": bool(task.get("approval_required", False)),
        "monitoring_authority": False,
        "durable_lifecycle_authority": "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY",
    }

def issue_execution_claim(task_id: str, claimant_id: str, generation: int, idempotency_key: str,
                          authority_scope: list[str], expires_at: str) -> dict[str, Any]:
    if not all(isinstance(x, str) and x for x in (task_id, claimant_id, idempotency_key, expires_at)):
        raise OrchestrationGovernanceError("claim strings required")
    if not isinstance(generation, int) or generation < 1:
        raise OrchestrationGovernanceError("claim generation must be positive")
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OrchestrationGovernanceError("claim expiry must be ISO-8601") from exc
    if expiry.tzinfo is None:
        raise OrchestrationGovernanceError("claim expiry must be timezone-aware")
    return {
        "schema": "fa3.execution-claim.v1", "task_id": task_id, "claimant_id": claimant_id,
        "generation": generation, "idempotency_key": idempotency_key,
        "authority_scope": sorted(set(_strings(authority_scope, "authority_scope"))),
        "expires_at": expires_at, "state": "CLAIMED",
    }

def validate_claim_takeover(current: dict[str, Any], successor: dict[str, Any], now: str) -> bool:
    if current.get("task_id") != successor.get("task_id"):
        raise OrchestrationGovernanceError("claim task mismatch")
    if not isinstance(successor.get("generation"), int) or successor["generation"] <= current.get("generation", 0):
        raise OrchestrationGovernanceError("claim generation must increase")
    current_scope = set(_strings(current.get("authority_scope", []), "current authority_scope"))
    successor_scope = set(_strings(successor.get("authority_scope", []), "successor authority_scope"))
    if not successor_scope.issubset(current_scope):
        raise OrchestrationGovernanceError("claim takeover cannot expand authority")
    now_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    exp_dt = datetime.fromisoformat(str(current.get("expires_at", "")).replace("Z", "+00:00"))
    expired = exp_dt <= now_dt
    if current.get("state") not in TERMINAL_CLAIM_STATES and not expired:
        raise OrchestrationGovernanceError("live claim takeover forbidden")
    return True

def bind_approval(object_id: str, revision: int, digest: str, scope: str,
                  allowed_operations: list[str], approver: str) -> dict[str, Any]:
    if not isinstance(revision, int) or revision < 1 or not SHA256_RE.fullmatch(digest):
        raise OrchestrationGovernanceError("approval revision/digest invalid")
    operations = _strings(allowed_operations, "allowed_operations")
    if not operations:
        raise OrchestrationGovernanceError("approval requires operations")
    if not all(isinstance(x, str) and x for x in (object_id, scope, approver)):
        raise OrchestrationGovernanceError("approval identity fields required")
    return {
        "schema": "fa3.version-bound-approval.v1", "object_id": object_id, "revision": revision,
        "digest": digest, "scope": scope, "allowed_operations": operations,
        "approver": approver, "revoked": False,
    }

def approval_allows(approval: dict[str, Any], object_id: str, revision: int, digest: str,
                    operation: str) -> bool:
    return bool(
        approval.get("revoked") is False and approval.get("object_id") == object_id
        and approval.get("revision") == revision and approval.get("digest") == digest
        and operation in approval.get("allowed_operations", [])
    )

def build_monitor_projection(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    states = {}
    routed = 0
    attention = 0
    for decision in decisions:
        gov = decision.get("governance_projection", {})
        state = gov.get("liveness_state", "UNKNOWN")
        states[state] = states.get(state, 0) + 1
        if decision.get("status") == "ROUTED":
            routed += 1
        else:
            attention += 1
    return {
        "schema": "fa3.orchestration-monitor-projection.v1",
        "authority": False,
        "durable_source": "Temporal",
        "task_count": len(decisions),
        "routed": routed,
        "attention_required": attention,
        "liveness_counts": states,
    }


def build_handoff_envelope(
    handoff_id: str,
    from_task_id: str,
    to_task_id: str,
    relation_type: str,
    *,
    source_revision: int,
    source_digest: str,
    artifact_refs: list[str] | None = None,
    artifact_digests: list[str] | None = None,
    required_output_contract: str,
    ack_required: bool = True,
    expires_at: str,
    state: str = "CREATED",
) -> dict[str, Any]:
    if not all(isinstance(x, str) and x for x in (handoff_id, from_task_id, to_task_id, required_output_contract, expires_at)):
        raise OrchestrationGovernanceError("handoff identity fields required")
    if relation_type not in DEPENDENCY_TYPES:
        raise OrchestrationGovernanceError("unsupported handoff relation")
    if not isinstance(source_revision, int) or isinstance(source_revision, bool) or source_revision < 1:
        raise OrchestrationGovernanceError("handoff source revision invalid")
    if not SHA256_RE.fullmatch(source_digest):
        raise OrchestrationGovernanceError("handoff source digest invalid")
    if state not in HANDOFF_STATES:
        raise OrchestrationGovernanceError("handoff state invalid")
    refs = _strings(artifact_refs or [], "artifact_refs")
    digests = _strings(artifact_digests or [], "artifact_digests")
    if len(refs) != len(digests):
        raise OrchestrationGovernanceError("artifact refs/digests cardinality mismatch")
    if any(not SHA256_RE.fullmatch(d) for d in digests):
        raise OrchestrationGovernanceError("artifact digest invalid")
    return {
        "schema": "fa3.orchestration-handoff.v1",
        "handoff_id": handoff_id,
        "from_task_id": from_task_id,
        "to_task_id": to_task_id,
        "relation_type": relation_type,
        "source_revision": source_revision,
        "source_digest": source_digest,
        "artifact_refs": refs,
        "artifact_digests": digests,
        "required_output_contract": required_output_contract,
        "ack_required": bool(ack_required),
        "expires_at": expires_at,
        "state": state,
        "ack_is_completion": False,
        "ack_is_verified_evidence": False,
    }


def classify_recovery(classification: str, *, scope_expands: bool = False, participant_set_expands: bool = False,
                      budget_expands_without_approval: bool = False, blind_retry: bool = False) -> dict[str, Any]:
    if classification not in RECOVERY_CLASSES:
        raise OrchestrationGovernanceError("unsupported recovery classification")
    if scope_expands or participant_set_expands or budget_expands_without_approval:
        raise OrchestrationGovernanceError("recovery may not expand scope, participants or unapproved budget")
    if classification == "UNKNOWN_EFFECT" and blind_retry:
        raise OrchestrationGovernanceError("unknown effect outcome forbids blind retry")
    return {
        "schema": "fa3.orchestration-recovery-classification.v1",
        "classification": classification,
        "scope_expands": False,
        "participant_set_expands": False,
        "budget_expands_without_approval": False,
        "blind_retry": False,
        "requires_effect_reconciliation": classification == "UNKNOWN_EFFECT",
        "requires_fresh_revision_binding": classification == "REPLAN_REQUIRED",
        "human_required": classification == "HUMAN_REQUIRED",
    }
