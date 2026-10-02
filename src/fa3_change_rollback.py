#!/usr/bin/env python3
"""Non-executing rollback impact analysis for CHIF."""
from __future__ import annotations

from typing import Any

from fa3_change_graph import reachable
from fa3_change_history import validate_edge


def rollback_impact(target_changeset_id: str, reverted_record_ids: list[str],
                    edges: list[dict[str, Any]]) -> dict[str, Any]:
    for edge in edges:
        validate_edge(edge)
    affected = reachable(
        edges,
        reverted_record_ids,
        {"AFFECTS", "DEPENDS_ON", "INVALIDATES", "REQUALIFIES", "ROLLED_BACK_BY"},
    )
    return {
        "schema": "fa3.rollback-impact.v1",
        "target_changeset_id": target_changeset_id,
        "reverted_record_ids": sorted(set(reverted_record_ids)),
        "affected_ids": affected,
        "derived_index_action": "DELETE_AND_REBUILD",
        "source_mutation": False,
        "rollback_executed": False,
        "requires_explicit_external_rollback_authority": True,
    }
