#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

PROFILE_ID = "FA3-MANAGER-001"
PROVIDER_ID = "FA3-PROVIDER-MANAGER-LOCAL-001"
VERSION = "0.1.0"
ALLOWED_MODES = {"PLAN", "PRIORITIZE", "DELEGATE", "STATUS", "BLOCKER_REVIEW", "REPLAN", "VERIFY_CLOSURE"}
ALLOWED_STATES = {"DRAFT", "READY", "DELEGATED", "RUNNING", "BLOCKED", "PAUSED", "EVIDENCE_PENDING", "VERIFIED", "CANCELLED"}


class ManagerInputError(ValueError):
    pass


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManagerInputError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str, limit: int = 32) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ManagerInputError(f"{field} must be a list of strings")
    return [item.strip() for item in value if item.strip()][:limit]


def _normalize_items(raw_items: Any) -> list[dict[str, Any]]:
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise ManagerInputError("work_items must be a list")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ManagerInputError(f"work_items[{index}] must be an object")
        item_id = _required_text(raw.get("id"), f"work_items[{index}].id")
        if item_id in seen:
            raise ManagerInputError(f"duplicate work item id: {item_id}")
        seen.add(item_id)
        state = str(raw.get("state", "DRAFT")).upper()
        if state not in ALLOWED_STATES:
            raise ManagerInputError(f"unsupported state for {item_id}: {state}")
        acceptance = _string_list(raw.get("acceptance_criteria"), f"{item_id}.acceptance_criteria")
        evidence_refs = _string_list(raw.get("evidence_refs"), f"{item_id}.evidence_refs")
        acceptance_met = raw.get("acceptance_met", False) is True
        if state == "VERIFIED" and (not acceptance or not acceptance_met or not evidence_refs):
            raise ManagerInputError(
                f"{item_id}: VERIFIED requires acceptance criteria, acceptance_met=true and evidence_refs"
            )
        blocker = raw.get("blocker")
        if state == "BLOCKED" and (not isinstance(blocker, dict) or not blocker.get("provenance")):
            raise ManagerInputError(f"{item_id}: BLOCKED requires blocker.provenance")
        items.append({
            "id": item_id,
            "title": _required_text(raw.get("title"), f"work_items[{index}].title"),
            "state": state,
            "priority": str(raw.get("priority", "NORMAL")).upper(),
            "depends_on": _string_list(raw.get("depends_on"), f"{item_id}.depends_on"),
            "capability_refs": _string_list(raw.get("capability_refs"), f"{item_id}.capability_refs"),
            "provider_refs": _string_list(raw.get("provider_refs"), f"{item_id}.provider_refs"),
            "acceptance_criteria": acceptance,
            "acceptance_met": acceptance_met,
            "evidence_refs": evidence_refs,
            "approval_required": raw.get("approval_required", False) is True,
            "blocker": blocker if isinstance(blocker, dict) else None,
        })
    ids = {item["id"] for item in items}
    for item in items:
        missing = set(item["depends_on"]) - ids
        if missing:
            raise ManagerInputError(f"{item['id']}: unknown dependencies: {sorted(missing)}")
    return items


def _assert_acyclic(items: list[dict[str, Any]]) -> None:
    graph = {item["id"]: item["depends_on"] for item in items}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ManagerInputError(f"dependency cycle detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dep in graph[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def build_management_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a bounded management projection without executing or persisting actions."""
    if not isinstance(payload, dict):
        raise ManagerInputError("request must be a JSON object")

    mode = str(payload.get("mode", "PLAN")).upper()
    if mode not in ALLOWED_MODES:
        raise ManagerInputError(f"unsupported mode: {mode}")
    objective = _required_text(payload.get("objective"), "objective")
    items = _normalize_items(payload.get("work_items", []))
    _assert_acyclic(items)

    if mode == "VERIFY_CLOSURE" and not items:
        raise ManagerInputError("VERIFY_CLOSURE requires work_items")
    if mode == "VERIFY_CLOSURE":
        unverified = [item["id"] for item in items if item["state"] != "VERIFIED"]
        if unverified:
            raise ManagerInputError(f"VERIFY_CLOSURE requires all work items VERIFIED: {unverified}")

    knowledge_gap = payload.get("knowledge_gap", False) is True
    coaching_needed = payload.get("coaching_needed", False) is True
    actionable_request = payload.get("actionable_request", False) is True

    delegations: list[dict[str, str]] = []
    if knowledge_gap:
        delegations.append({"kind": "MENTOR", "target": "FA3-MENTOR-001", "reason": "knowledge_or_skill_gap"})
    if coaching_needed:
        delegations.append({"kind": "COACH", "target": "FA3-COACH-001", "reason": "goal_or_accountability_coaching"})
    if actionable_request:
        delegations.append({
            "kind": "ACTION",
            "target": "FA3-AUTH-MCP-GATEWAY-001_OR_FA3-AGENT-EXEC-001",
            "reason": "typed_execution_delegation_required",
        })

    ready = []
    blocked = []
    states = {item["id"]: item["state"] for item in items}
    terminal_ok = {"VERIFIED", "CANCELLED"}
    for item in items:
        unresolved = [dep for dep in item["depends_on"] if states.get(dep) not in terminal_ok]
        if item["state"] == "BLOCKED" or unresolved:
            blocked.append({"id": item["id"], "unresolved_dependencies": unresolved, "blocker": item["blocker"]})
        elif item["state"] in {"DRAFT", "READY", "PAUSED"}:
            ready.append(item["id"])

    verified = [item["id"] for item in items if item["state"] == "VERIFIED"]
    evidence_pending = [item["id"] for item in items if item["state"] == "EVIDENCE_PENDING"]

    return {
        "schema": "fa3.manager-projection.v1",
        "profile_id": PROFILE_ID,
        "provider_id": PROVIDER_ID,
        "version": VERSION,
        "mode": mode,
        "status": "MANAGEMENT_PROJECTION_ONLY",
        "objective": {"owner": "USER_OR_EXISTING_CANONICAL_SOURCE", "text": objective},
        "work_items": items,
        "summary": {
            "work_item_count": len(items),
            "ready_or_resumable": ready,
            "blocked": blocked,
            "evidence_pending": evidence_pending,
            "verified": verified,
        },
        "delegations": delegations,
        "authority": {
            "direct_execution_allowed": False,
            "orchestration_authority": False,
            "canonical_registry_mutation_allowed": False,
            "decision_authority": False,
            "security_override_allowed": False,
            "approval_bypass_allowed": False,
            "evidence_authority": False,
            "architectural_authority": False,
        },
        "boundaries": {
            "knowledge_gap_owner": "FA3-MENTOR-001",
            "goal_coaching_owner": "FA3-COACH-001",
            "action_execution": "TYPED_DELEGATION_ONLY",
            "verified_closure": "ACCEPTANCE_PLUS_EVIDENCE_REQUIRED",
            "capability_provider_binding": "PROPOSAL_ONLY",
        },
    }


def self_check() -> None:
    projection = build_management_projection({
        "mode": "PLAN",
        "objective": "Ship a verifiable FA3 change",
        "work_items": [
            {"id": "design", "title": "Define acceptance criteria", "state": "VERIFIED",
             "acceptance_criteria": ["criteria exist"], "acceptance_met": True, "evidence_refs": ["evidence://design"]},
            {"id": "gate", "title": "Run conformance gate", "state": "READY", "depends_on": ["design"]},
        ],
        "knowledge_gap": True,
        "coaching_needed": True,
        "actionable_request": True,
    })
    assert projection["status"] == "MANAGEMENT_PROJECTION_ONLY"
    assert projection["authority"]["direct_execution_allowed"] is False
    assert projection["authority"]["architectural_authority"] is False
    assert set(item["kind"] for item in projection["delegations"]) == {"MENTOR", "COACH", "ACTION"}
    assert projection["summary"]["ready_or_resumable"] == ["gate"]


def _load_input(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Manager local reference management-projection engine")
    parser.add_argument("--input", help="JSON request file; stdin is used when omitted")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_check:
            self_check()
            print("FA3 Manager self-check: PASS")
            return 0
        projection = build_management_projection(_load_input(args.input))
    except (ManagerInputError, json.JSONDecodeError, OSError) as exc:
        print(f"FA3 Manager: FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
