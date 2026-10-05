#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Any

SCHEMA = "fa3.creative-project-state.v1"
PLAN_SCHEMA = "fa3.creative-project-revision-plan.v1"

NODE_TYPES = {
    "PROJECT_SPEC", "STORY_DOCUMENT", "SCREENPLAY", "SHOT", "STORYBOARD_CARD",
    "CHARACTER", "ENVIRONMENT", "ASSET", "AUDIO", "CAPTION", "TIMELINE_SEGMENT",
    "REVIEW_NOTE", "APPROVAL", "DELIVERY",
}
EDGE_TYPES = {
    "DEPENDS_ON", "DERIVED_FROM", "BINDS_MEDIA", "CONTINUES_FROM",
    "PROVIDES_CONTEXT", "EDIT_SOURCE", "REVISION_IMPACTS",
}

class CreativeProjectError(ValueError):
    pass

def _node_map(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = project.get("nodes", [])
    if not isinstance(nodes, list):
        raise CreativeProjectError("nodes must be a list")
    out: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"]:
            raise CreativeProjectError("each node requires a non-empty id")
        if node["id"] in out:
            raise CreativeProjectError(f"duplicate node id: {node['id']}")
        if node.get("type") not in NODE_TYPES:
            raise CreativeProjectError(f"unsupported node type: {node.get('type')}")
        out[node["id"]] = node
    return out

def validate_project_state(project: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(project, dict):
        raise CreativeProjectError("project must be an object")
    if project.get("schema") != SCHEMA:
        raise CreativeProjectError("creative project schema mismatch")
    if not isinstance(project.get("project_id"), str) or not project["project_id"]:
        raise CreativeProjectError("project_id required")
    nodes = _node_map(project)
    edges = project.get("edges", [])
    if not isinstance(edges, list):
        raise CreativeProjectError("edges must be a list")
    for edge in edges:
        if not isinstance(edge, dict):
            raise CreativeProjectError("edge must be an object")
        if edge.get("type") not in EDGE_TYPES:
            raise CreativeProjectError(f"unsupported edge type: {edge.get('type')}")
        if edge.get("from") not in nodes or edge.get("to") not in nodes:
            raise CreativeProjectError("edge references unknown node")
        if not isinstance(edge.get("invalidate_on_revision"), bool):
            raise CreativeProjectError("edge invalidate_on_revision must be explicit boolean")
    docs = project.get("documents", [])
    if not isinstance(docs, list):
        raise CreativeProjectError("documents must be a list")
    for doc in docs:
        if not isinstance(doc, dict) or not doc.get("id"):
            raise CreativeProjectError("document id required")
        origin = doc.get("origin")
        if origin not in {"USER", "AI", "IMPORTED_REFERENCE"}:
            raise CreativeProjectError("document origin must be USER, AI or IMPORTED_REFERENCE")
        if origin == "AI" and not doc.get("provenance_ref"):
            raise CreativeProjectError("AI document provenance_ref required")
        if origin == "IMPORTED_REFERENCE" and doc.get("editable") is not False:
            raise CreativeProjectError("imported references are read-only by default")
        scope = doc.get("scope", [])
        if not isinstance(scope, list):
            raise CreativeProjectError("document scope must be a list")
        unknown = [x for x in scope if x != "*" and x not in nodes]
        if unknown:
            raise CreativeProjectError(f"document scope references unknown nodes: {unknown}")
    return {"result": "PASS", "project_id": project["project_id"], "nodes": len(nodes), "edges": len(edges)}

def plan_scoped_revision(project: dict[str, Any], changed_node_ids: list[str]) -> dict[str, Any]:
    validate_project_state(project)
    nodes = _node_map(project)
    if not changed_node_ids or not all(isinstance(x, str) and x in nodes for x in changed_node_ids):
        raise CreativeProjectError("changed_node_ids must contain known nodes")
    graph: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in project.get("edges", []):
        if edge["invalidate_on_revision"]:
            graph[edge["from"]].append(edge["to"])
    changed = set(changed_node_ids)
    affected = set(changed)
    queue = deque(sorted(changed))
    while queue:
        current = queue.popleft()
        for child in sorted(graph[current]):
            if child not in affected:
                affected.add(child)
                queue.append(child)
    preserved = sorted(set(nodes) - affected)
    approval_nodes = sorted(
        node_id for node_id in affected
        if nodes[node_id].get("locked") is True or nodes[node_id].get("human_approved") is True
    )
    regenerate_candidates = sorted(
        node_id for node_id in affected
        if nodes[node_id].get("type") in {"ASSET", "AUDIO", "CAPTION"}
    )
    return {
        "schema": PLAN_SCHEMA,
        "project_id": project["project_id"],
        "changed_node_ids": sorted(changed),
        "affected_node_ids": sorted(affected),
        "preserved_node_ids": preserved,
        "regenerate_candidate_ids": regenerate_candidates,
        "approval_required": bool(approval_nodes),
        "approval_boundary_node_ids": approval_nodes,
        "execution_authorized": False,
        "authority_expansion": False,
        "model_provider_selection": "FA3-AUTH-MODEL-ROUTER-001",
        "host_resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "action_execution": "FA3-UNIFIED-ACTION-FABRIC-001",
        "editorial_projection": "OpenTimelineIO_OR_FA3_VIDEO_EDITOR_COMMAND_BUS",
        "unaffected_nodes_preserved": True,
        "full_project_regeneration_default": False,
    }

def project_context_slice(project: dict[str, Any], revision_plan: dict[str, Any]) -> dict[str, Any]:
    validate_project_state(project)
    affected = set(revision_plan.get("affected_node_ids", []))
    selected = []
    for doc in project.get("documents", []):
        scope = set(doc.get("scope", []))
        if "*" in scope or scope & affected:
            selected.append(deepcopy(doc))
    return {
        "project_id": project["project_id"],
        "documents": selected,
        "constraints": deepcopy(project.get("constraints", [])),
        "global_corpus_auto_injection": False,
        "task_scoped": True,
    }

def build_timeline_projection_plan(project: dict[str, Any]) -> dict[str, Any]:
    validate_project_state(project)
    nodes = _node_map(project)
    shots = [(node.get("order", 0), node_id) for node_id, node in nodes.items() if node.get("type") == "SHOT"]
    shots.sort(key=lambda x: (x[0], x[1]))
    return {
        "project_id": project["project_id"],
        "ordered_shot_ids": [node_id for _, node_id in shots],
        "canonical_interchange": "OpenTimelineIO",
        "direct_native_project_mutation": False,
        "fa3_video_editor_command_bus_required_for_native_commit": True,
        "human_or_policy_review_before_destructive_commit": True,
    }
