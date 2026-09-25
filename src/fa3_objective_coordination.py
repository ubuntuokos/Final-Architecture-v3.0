#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

SCHEMA = "fa3.objective-coordination.v1"
SNAPSHOT_SCHEMA = "fa3.objective-coordination-snapshot.v1"
RUNTIME_ID = "FA3-OBJECTIVE-COORDINATION-REF-RUNTIME-001"
PROFILE_ID = "FA3-COORDINATION-LAYER-001"

NODE_STATES = {
    "PENDING", "RUNNING", "WAITING", "BLOCKED", "COMPLETED", "FAILED", "CANCELLED"
}
DEPENDENCY_RELATIONS = {
    "REQUIRES", "HANDOFF_AFTER", "APPROVAL_BEFORE", "ARTIFACT_BEFORE"
}
HANDOFF_STATES = {"PLANNED", "OFFERED", "RECEIVED", "REJECTED", "FAILED"}
BLOCKER_STATES = {"OPEN", "RESOLVED"}
BLOCKER_KINDS = {
    "DEPENDENCY", "HUMAN_APPROVAL", "ARTIFACT", "PROVIDER", "RESOURCE",
    "RECONCILIATION", "HANDOFF", "POLICY", "EXTERNAL"
}
FORBIDDEN_AUTHORITY_FLAGS = {
    "execute", "authorize", "allocate_resources", "move_artifacts",
    "select_model_provider", "admit_provider", "grant_secret"
}


class CoordinationContractError(ValueError):
    pass


@dataclass(frozen=True)
class ReplaySummary:
    accepted: tuple[dict[str, Any], ...]
    replayed_event_ids: tuple[str, ...]


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, field: str, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise CoordinationContractError(f"{field} must be a list")
    if not allow_empty and not value:
        raise CoordinationContractError(f"{field} must not be empty")
    if not all(_nonempty(v) for v in value):
        raise CoordinationContractError(f"{field} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise CoordinationContractError(f"{field} must be unique")
    return list(value)


def _nodes_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise CoordinationContractError("nodes must be a non-empty list")
    out: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or not _nonempty(node.get("node_id")):
            raise CoordinationContractError("each node requires node_id")
        node_id = node["node_id"]
        if node_id in out:
            raise CoordinationContractError(f"duplicate node_id: {node_id}")
        if node.get("state") not in NODE_STATES:
            raise CoordinationContractError(f"unsupported node state: {node.get('state')}")
        if not _nonempty(node.get("kind")):
            raise CoordinationContractError(f"node {node_id} requires kind")
        if node.get("authority") not in (None, False):
            raise CoordinationContractError(f"node {node_id} cannot be authority")
        out[node_id] = node
    return out


def _validated_edges(payload: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    edges = payload.get("dependencies", [])
    if not isinstance(edges, list):
        raise CoordinationContractError("dependencies must be a list")
    result = []
    seen: set[tuple[str, str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise CoordinationContractError("dependency must be an object")
        upstream = edge.get("upstream")
        downstream = edge.get("downstream")
        relation = edge.get("relation", "REQUIRES")
        if upstream not in nodes or downstream not in nodes:
            raise CoordinationContractError("dependency endpoint is not a known node")
        if upstream == downstream:
            raise CoordinationContractError("self dependency denied")
        if relation not in DEPENDENCY_RELATIONS:
            raise CoordinationContractError(f"unsupported dependency relation: {relation}")
        key = (upstream, downstream, relation)
        if key in seen:
            raise CoordinationContractError(f"duplicate dependency: {key}")
        seen.add(key)
        result.append({
            "upstream": upstream,
            "downstream": downstream,
            "relation": relation,
            "required": edge.get("required", True) is not False,
        })
    return result


def assert_acyclic(nodes: Iterable[str], edges: list[dict[str, Any]]) -> None:
    node_ids = list(nodes)
    indegree = {node_id: 0 for node_id in node_ids}
    outgoing = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if not edge.get("required", True):
            continue
        upstream, downstream = edge["upstream"], edge["downstream"]
        indegree[downstream] += 1
        outgoing[upstream].append(downstream)
    ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        current = ready.pop(0)
        visited += 1
        for downstream in sorted(outgoing[current]):
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                ready.append(downstream)
                ready.sort()
    if visited != len(node_ids):
        raise CoordinationContractError("required dependency graph contains a cycle")


def dependency_batches(node_ids: Iterable[str], edges: list[dict[str, Any]]) -> list[list[str]]:
    node_ids = list(node_ids)
    indegree = {node_id: 0 for node_id in node_ids}
    outgoing = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if not edge.get("required", True):
            continue
        indegree[edge["downstream"]] += 1
        outgoing[edge["upstream"]].append(edge["downstream"])
    remaining = set(node_ids)
    batches: list[list[str]] = []
    while remaining:
        batch = sorted(node_id for node_id in remaining if indegree[node_id] == 0)
        if not batch:
            raise CoordinationContractError("required dependency graph contains a cycle")
        batches.append(batch)
        for current in batch:
            remaining.remove(current)
            for downstream in outgoing[current]:
                indegree[downstream] -= 1
    return batches


def _validate_handoffs(payload: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    handoffs = payload.get("handoffs", [])
    if not isinstance(handoffs, list):
        raise CoordinationContractError("handoffs must be a list")
    seen: set[str] = set()
    result = []
    for handoff in handoffs:
        if not isinstance(handoff, dict) or not _nonempty(handoff.get("handoff_id")):
            raise CoordinationContractError("handoff requires handoff_id")
        handoff_id = handoff["handoff_id"]
        if handoff_id in seen:
            raise CoordinationContractError(f"duplicate handoff_id: {handoff_id}")
        seen.add(handoff_id)
        if handoff.get("source_node") not in nodes or handoff.get("target_node") not in nodes:
            raise CoordinationContractError(f"handoff {handoff_id} has unknown endpoint")
        if handoff.get("state") not in HANDOFF_STATES:
            raise CoordinationContractError(f"handoff {handoff_id} has invalid state")
        _string_list(handoff.get("artifact_refs"), field=f"{handoff_id}.artifact_refs", allow_empty=False)
        _string_list(handoff.get("provenance_refs"), field=f"{handoff_id}.provenance_refs", allow_empty=False)
        result.append(dict(handoff))
    return result


def _validate_blockers(payload: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = payload.get("blockers", [])
    if not isinstance(blockers, list):
        raise CoordinationContractError("blockers must be a list")
    seen: set[str] = set()
    result = []
    for blocker in blockers:
        if not isinstance(blocker, dict) or not _nonempty(blocker.get("blocker_id")):
            raise CoordinationContractError("blocker requires blocker_id")
        blocker_id = blocker["blocker_id"]
        if blocker_id in seen:
            raise CoordinationContractError(f"duplicate blocker_id: {blocker_id}")
        seen.add(blocker_id)
        if blocker.get("target_node") not in nodes:
            raise CoordinationContractError(f"blocker {blocker_id} targets unknown node")
        if blocker.get("kind") not in BLOCKER_KINDS:
            raise CoordinationContractError(f"blocker {blocker_id} has invalid kind")
        if blocker.get("state") not in BLOCKER_STATES:
            raise CoordinationContractError(f"blocker {blocker_id} has invalid state")
        if not _nonempty(blocker.get("reason")):
            raise CoordinationContractError(f"blocker {blocker_id} requires reason")
        result.append(dict(blocker))
    return result


def validate_objective(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise CoordinationContractError(f"schema must be {SCHEMA}")
    if not _nonempty(payload.get("objective_id")) or not _nonempty(payload.get("title")):
        raise CoordinationContractError("objective_id and title are required")
    if payload.get("authority") is not False:
        raise CoordinationContractError("coordination document must declare authority=false")
    forbidden = sorted(flag for flag in FORBIDDEN_AUTHORITY_FLAGS if payload.get(flag) is True)
    if forbidden:
        raise CoordinationContractError("authority action flags are forbidden: " + ",".join(forbidden))
    nodes = _nodes_by_id(payload)
    edges = _validated_edges(payload, nodes)
    assert_acyclic(nodes, edges)
    handoffs = _validate_handoffs(payload, nodes)
    blockers = _validate_blockers(payload, nodes)
    trace = payload.get("trace_context", {})
    if not isinstance(trace, dict) or not _nonempty(trace.get("correlation_id")):
        raise CoordinationContractError("trace_context.correlation_id is required")
    if trace.get("causation_id") is not None and not _nonempty(trace.get("causation_id")):
        raise CoordinationContractError("trace_context.causation_id must be null or non-empty")
    return {
        "nodes": nodes,
        "edges": edges,
        "handoffs": handoffs,
        "blockers": blockers,
        "trace_context": trace,
    }


def derive_blockers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validated = validate_objective(payload)
    nodes = validated["nodes"]
    blockers = [b for b in validated["blockers"] if b["state"] == "OPEN"]
    existing = {(b["target_node"], b["kind"], b.get("source_ref")) for b in blockers}
    for edge in validated["edges"]:
        if not edge["required"]:
            continue
        if nodes[edge["upstream"]]["state"] != "COMPLETED":
            key = (edge["downstream"], "DEPENDENCY", edge["upstream"])
            if key not in existing:
                blockers.append({
                    "blocker_id": f"derived:dependency:{edge['upstream']}->{edge['downstream']}",
                    "target_node": edge["downstream"],
                    "kind": "DEPENDENCY",
                    "state": "OPEN",
                    "reason": f"waiting for {edge['upstream']} to complete",
                    "source_ref": edge["upstream"],
                    "derived": True,
                })
                existing.add(key)
    for handoff in validated["handoffs"]:
        if handoff["state"] != "RECEIVED" and handoff.get("required", True) is not False:
            key = (handoff["target_node"], "HANDOFF", handoff["handoff_id"])
            if key not in existing:
                blockers.append({
                    "blocker_id": f"derived:handoff:{handoff['handoff_id']}",
                    "target_node": handoff["target_node"],
                    "kind": "HANDOFF",
                    "state": "OPEN",
                    "reason": f"handoff {handoff['handoff_id']} not received",
                    "source_ref": handoff["handoff_id"],
                    "derived": True,
                })
                existing.add(key)
    return sorted(blockers, key=lambda b: (b["target_node"], b["kind"], b["blocker_id"]))


def ready_nodes(payload: dict[str, Any]) -> list[str]:
    validated = validate_objective(payload)
    nodes = validated["nodes"]
    blocked = {b["target_node"] for b in derive_blockers(payload)}
    ready = []
    for node_id, node in nodes.items():
        if node["state"] != "PENDING" or node_id in blocked:
            continue
        incoming = [
            edge for edge in validated["edges"]
            if edge["required"] and edge["downstream"] == node_id
        ]
        if all(nodes[edge["upstream"]]["state"] == "COMPLETED" for edge in incoming):
            ready.append(node_id)
    return sorted(ready)


def deduplicate_events(events: list[dict[str, Any]]) -> ReplaySummary:
    if not isinstance(events, list):
        raise CoordinationContractError("events must be a list")
    digests: dict[str, str] = {}
    accepted: list[dict[str, Any]] = []
    replayed: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            raise CoordinationContractError("event must be an object")
        for field in ("event_id", "event_type", "correlation_id", "source_ref"):
            if not _nonempty(event.get(field)):
                raise CoordinationContractError(f"event requires {field}")
        causation = event.get("causation_id")
        if causation is not None and not _nonempty(causation):
            raise CoordinationContractError("event causation_id must be null or non-empty")
        event_id = event["event_id"]
        digest = hashlib.sha256(
            json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if event_id in digests:
            if digests[event_id] != digest:
                raise CoordinationContractError(f"event replay payload mismatch: {event_id}")
            replayed.append(event_id)
            continue
        digests[event_id] = digest
        accepted.append(dict(event))
    return ReplaySummary(tuple(accepted), tuple(replayed))


def compile_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    validated = validate_objective(payload)
    nodes = validated["nodes"]
    blockers = derive_blockers(payload)
    ready = ready_nodes(payload)
    running = sorted(node_id for node_id, node in nodes.items() if node["state"] == "RUNNING")
    failed = sorted(node_id for node_id, node in nodes.items() if node["state"] == "FAILED")
    cancelled = sorted(node_id for node_id, node in nodes.items() if node["state"] == "CANCELLED")
    if all(node["state"] == "COMPLETED" for node in nodes.values()):
        objective_state = "COMPLETED"
    elif failed:
        objective_state = "FAILED"
    elif cancelled and len(cancelled) == len(nodes):
        objective_state = "CANCELLED"
    elif running or ready:
        objective_state = "ACTIVE"
    elif blockers:
        objective_state = "BLOCKED"
    else:
        objective_state = "WAITING"
    batches = dependency_batches(nodes, validated["edges"])
    return {
        "schema": SNAPSHOT_SCHEMA,
        "runtime_id": RUNTIME_ID,
        "profile_id": PROFILE_ID,
        "objective_id": payload["objective_id"],
        "title": payload["title"],
        "authority": False,
        "objective_state": objective_state,
        "ready_node_ids": ready,
        "running_node_ids": running,
        "blocked_node_ids": sorted({b["target_node"] for b in blockers}),
        "failed_node_ids": failed,
        "blockers": blockers,
        "handoffs": validated["handoffs"],
        "dependency_batches": batches,
        "trace_context": dict(validated["trace_context"]),
        "execution_semantics": "OBSERVE_COORDINATE_RECOMMEND_ONLY",
        "mutation_semantics": "TYPED_UAF_DRAFT_INTENT_ONLY",
        "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "decision_fabric": "FA3-DECISION-FABRIC-001_BOUNDED_ADVISORY_ONLY",
    }
