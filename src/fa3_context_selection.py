#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from fa3_decision_fabric import DecisionFabric

PROTECTED_KINDS = {
    "canonical_decision",
    "user_constraint",
    "user_correction",
    "security_evidence",
    "error",
    "command",
    "source_provenance",
    "current_host_evidence",
    "unresolved_blocker",
    "approval_record",
}
STATES = {"PROTECTED", "ACTIVE", "HIDDEN", "ARCHIVED"}


@dataclass
class ContextItem:
    id: str
    kind: str
    text: str
    state: str = "ACTIVE"
    metadata: dict[str, Any] | None = None

    @staticmethod
    def from_dict(value: dict[str, Any]) -> "ContextItem":
        if not isinstance(value, dict):
            raise ValueError("context item must be object")
        item_id = value.get("id")
        kind = value.get("kind", "note")
        text = value.get("text", "")
        state = value.get("state", "ACTIVE")
        metadata = value.get("metadata", {})
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("context item id required")
        if not isinstance(kind, str) or not isinstance(text, str):
            raise ValueError("kind/text must be strings")
        if state not in STATES:
            raise ValueError("invalid context state")
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be object")
        if kind in PROTECTED_KINDS:
            state = "PROTECTED"
        return ContextItem(item_id, kind, text, state, metadata)


class ContextSelector:
    def __init__(self, fabric: DecisionFabric | None = None) -> None:
        self.fabric = fabric or DecisionFabric()

    @staticmethod
    def source_digest(item: ContextItem) -> str:
        return hashlib.sha256(item.text.encode("utf-8")).hexdigest()

    def project(
        self,
        values: list[dict[str, Any]],
        *,
        target_active: int | None = None,
        provider_id: str = "FA3-PROVIDER-DECISION-RULES-001",
        rollout: str = "SHADOW",
    ) -> dict[str, Any]:
        items = [ContextItem.from_dict(v) for v in values]
        if len({x.id for x in items}) != len(items):
            raise ValueError("duplicate context item id")

        protected = [x for x in items if x.state == "PROTECTED"]
        selectable = [x for x in items if x.state != "PROTECTED"]

        if target_active is None or target_active >= len(selectable):
            selected = {x.id for x in selectable if x.state in {"ACTIVE", "HIDDEN"}}
            trace = None
        else:
            candidates = [
                {
                    "id": x.id,
                    "description": x.text[:512],
                    "metadata": {
                        "priority": int((x.metadata or {}).get("priority", 0)),
                        "relevance": float((x.metadata or {}).get("relevance", 0.0)),
                    },
                }
                for x in selectable
                if x.state in {"ACTIVE", "HIDDEN"}
            ]
            trace = self.fabric.decide(
                {
                    "contract": "RANK",
                    "purpose": "context-selection",
                    "candidates": candidates,
                    "constraints": {},
                    "policy_context": {"target_active": target_active},
                    "evidence_refs": [],
                    "failure_policy": "EXISTING_BEHAVIOR",
                    "rollout": rollout,
                    "final_policy_owner": "FA3-CONTEXT-SELECTION-001",
                },
                provider_id=provider_id,
            )
            ranked = (trace.get("result") or {}).get("ranked", [])
            selected = set(ranked[: max(0, target_active)]) if trace.get("status") == "DECIDED" else {
                x.id for x in selectable if x.state == "ACTIVE"
            }

        projection: list[dict[str, Any]] = []
        for item in items:
            if item.state == "PROTECTED":
                projected_state = "PROTECTED"
            elif item.state == "ARCHIVED":
                projected_state = "ARCHIVED"
            elif item.id in selected:
                projected_state = "ACTIVE"
            else:
                projected_state = "HIDDEN"
            projection.append({
                "id": item.id,
                "kind": item.kind,
                "state": projected_state,
                "text": item.text,
                "source_sha256": self.source_digest(item),
                "source_preserved": True,
                "metadata": item.metadata or {},
            })

        return {
            "schema": "fa3.context-selection-projection.v1",
            "profile": "FA3-CONTEXT-SELECTION-001",
            "items": projection,
            "decision_trace": trace,
            "hidden_is_deleted": False,
            "archived_is_deleted": False,
            "source_authority_changed": False,
        }

    @staticmethod
    def restore(projection: dict[str, Any], item_id: str) -> dict[str, Any]:
        changed = False
        for row in projection.get("items", []):
            if row.get("id") == item_id and row.get("state") == "HIDDEN":
                row["state"] = "ACTIVE"
                changed = True
        if not changed:
            raise KeyError(f"hidden item not found: {item_id}")
        projection["restore_applied"] = item_id
        return projection


def verify_projection(projection: dict[str, Any]) -> None:
    for row in projection.get("items", []):
        if row.get("state") not in STATES:
            raise ValueError("invalid projected state")
        if row.get("source_preserved") is not True:
            raise ValueError("source preservation invariant failed")
        text = row.get("text")
        digest = row.get("source_sha256")
        if not isinstance(text, str) or hashlib.sha256(text.encode()).hexdigest() != digest:
            raise ValueError("context source digest mismatch")
