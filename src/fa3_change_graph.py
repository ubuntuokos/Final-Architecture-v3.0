#!/usr/bin/env python3
"""Explicit Change Graph primitives for FA3 CHIF."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Iterable

from fa3_change_history import ChangeHistoryError, RELATIONS, validate_edge


def make_edge(*, edge_id: str, source_id: str, target_id: str, relation: str,
              provenance: dict[str, Any], details: dict[str, Any] | None = None) -> dict[str, Any]:
    if relation not in RELATIONS:
        raise ChangeHistoryError("unsupported change relation")
    if not source_id or not target_id:
        raise ChangeHistoryError("explicit source and target are required")
    row = {
        "id": edge_id,
        "source_id": source_id,
        "target_id": target_id,
        "relation": relation,
        "details": details or {},
        "provenance": provenance,
    }
    validate_edge(row)
    return row


def explicit_pairs(sources: Iterable[str], targets: Iterable[str],
                   declared_pairs: Iterable[tuple[str, str]] | None) -> list[tuple[str, str]]:
    """Never infer a cartesian product. Exact lineage pairs must be supplied."""
    source_set, target_set = set(sources), set(targets)
    if declared_pairs is None:
        if source_set and target_set:
            raise ChangeHistoryError("implicit cartesian lineage is forbidden")
        return []
    result: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source, target in declared_pairs:
        pair = (source, target)
        if source not in source_set or target not in target_set:
            raise ChangeHistoryError("lineage pair references undeclared endpoint")
        if pair not in seen:
            result.append(pair)
            seen.add(pair)
    return result


def reachable(edges: Iterable[dict[str, Any]], seeds: Iterable[str],
              relations: set[str] | None = None) -> list[str]:
    allowed = relations or {"AFFECTS", "DEPENDS_ON", "INVALIDATES", "REQUALIFIES", "ROLLED_BACK_BY"}
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        validate_edge(edge)
        if edge["relation"] in allowed:
            graph[edge["source_id"]].append(edge["target_id"])
    queue = deque(sorted(set(seeds)))
    visited = set(queue)
    while queue:
        current = queue.popleft()
        for target in sorted(graph.get(current, [])):
            if target not in visited:
                visited.add(target)
                queue.append(target)
    return sorted(visited - set(seeds))
