#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_task_group import TaskGroupContractError, resolve_task_group, task_group_key_from_task

CONTRACT_REL = Path("canonical/contracts/FA3-ORCHESTRATION-GUARD-CHAIN-CONTRACTS-001.json")
ORDER = [f"G{i}" for i in range(11)]
PHASES = {"PLANNING", "RUNTIME", "POST_EXECUTION"}
VALID_STATES = {"PASS", "BLOCK", "HUMAN_REQUIRED", "WAITING_AUTHORITY", "WAITING_RESOURCE", "WAITING_RUNTIME_ADMISSION", "DEFERRED"}


class GuardChainError(ValueError):
    pass


def load_guard_contract(root: Path | str) -> dict[str, Any]:
    data = json.loads((Path(root) / CONTRACT_REL).read_text(encoding="utf-8"))
    if data.get("id") != "FA3-ORCHESTRATION-GUARD-CHAIN-CONTRACTS-001" or data.get("authority") is not False:
        raise GuardChainError("invalid guard-chain contract")
    chain = data.get("guard_chain")
    if not isinstance(chain, list) or [x.get("guard_id") for x in chain] != ORDER:
        raise GuardChainError("guard-chain order drift")
    return data


def _row(guard_id: str, state: str, reason: str, owner_boundary: str) -> dict[str, Any]:
    if state not in VALID_STATES:
        raise GuardChainError("invalid guard state")
    return {
        "guard_id": guard_id,
        "state": state,
        "reason": reason,
        "owner_boundary": owner_boundary,
        "decision_ref": None,
        "evidence_refs": [],
    }


def _overall(rows: list[dict[str, Any]], phase: str) -> str:
    active = [r for r in rows if r["state"] != "DEFERRED"]
    for state in ("BLOCK", "HUMAN_REQUIRED", "WAITING_RUNTIME_ADMISSION", "WAITING_RESOURCE", "WAITING_AUTHORITY"):
        if any(r["state"] == state for r in active):
            return state
    return "PASS" if active and all(r["state"] == "PASS" for r in active) else "HUMAN_REQUIRED"


def evaluate_guard_chain(
    root: Path | str,
    task: dict[str, Any],
    *,
    phase: str = "PLANNING",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if phase not in PHASES:
        raise GuardChainError("unsupported guard phase")
    contract = load_guard_contract(root)
    ctx = context or {}
    owners = {x["guard_id"]: x["owner_boundary"] for x in contract["guard_chain"]}
    rows: list[dict[str, Any]] = []

    # G0 Goal / Intent
    if phase == "PLANNING":
        ancestry = task.get("objective_ancestry", [])
        goal_valid = ctx.get("goal_valid")
        if goal_valid is False:
            rows.append(_row("G0", "BLOCK", "GOAL_OR_INTENT_INVALID", owners["G0"]))
        elif goal_valid is True or (isinstance(ancestry, list) and bool(ancestry)):
            rows.append(_row("G0", "PASS", "GOAL_OR_INTENT_BOUND", owners["G0"]))
        else:
            rows.append(_row("G0", "HUMAN_REQUIRED", "GOAL_OR_INTENT_CONTEXT_MISSING", owners["G0"]))
    else:
        rows.append(_row("G0", "DEFERRED", "PLANNING_PHASE_ONLY", owners["G0"]))

    # G1 Task Group
    if phase == "PLANNING":
        key = task_group_key_from_task(task)
        if key is None:
            rows.append(_row("G1", "HUMAN_REQUIRED", "TASK_GROUP_NOT_DECLARED", owners["G1"]))
            snapshot = None
        else:
            try:
                snapshot = resolve_task_group(root, key)
                rows.append(_row("G1", "PASS", "TASK_GROUP_RESOLVED", owners["G1"]))
            except TaskGroupContractError:
                snapshot = None
                rows.append(_row("G1", "BLOCK", "TASK_GROUP_UNKNOWN_OR_INVALID", owners["G1"]))
    else:
        snapshot = None
        rows.append(_row("G1", "DEFERRED", "PLANNING_PHASE_ONLY", owners["G1"]))

    # G2 Role / Responsibility Scope
    if phase == "PLANNING":
        monotonic = ctx.get("scope_monotonic")
        bp = task.get("metadata", {}).get("agent_application_blueprint", {}) if isinstance(task.get("metadata", {}), dict) else {}
        if monotonic is False:
            rows.append(_row("G2", "BLOCK", "RESPONSIBILITY_SCOPE_EXPANSION", owners["G2"]))
        elif monotonic is True or (isinstance(bp, dict) and bp.get("role_kind")):
            rows.append(_row("G2", "PASS", "ROLE_SCOPE_NON_EXPANDING", owners["G2"]))
        else:
            rows.append(_row("G2", "HUMAN_REQUIRED", "ROLE_SCOPE_NOT_PROVEN", owners["G2"]))
    else:
        rows.append(_row("G2", "DEFERRED", "PLANNING_PHASE_ONLY", owners["G2"]))

    # G3 Dependency / Handoff
    if phase == "PLANNING":
        dep = ctx.get("dependency_graph_valid")
        if dep is False:
            rows.append(_row("G3", "BLOCK", "DEPENDENCY_OR_HANDOFF_INVALID", owners["G3"]))
        elif dep is True:
            rows.append(_row("G3", "PASS", "DEPENDENCY_OR_HANDOFF_VALIDATED", owners["G3"]))
        else:
            rows.append(_row("G3", "HUMAN_REQUIRED", "DEPENDENCY_VALIDATION_NOT_PROVIDED", owners["G3"]))
    else:
        rows.append(_row("G3", "DEFERRED", "PLANNING_PHASE_ONLY", owners["G3"]))

    # G4 Identity / Security
    if phase == "PLANNING":
        sec = ctx.get("security_decision")
        if sec == "PASS":
            rows.append(_row("G4", "PASS", "SECURITY_DECISION_PRESENT", owners["G4"]))
        elif sec == "BLOCK":
            rows.append(_row("G4", "BLOCK", "SECURITY_DENIED", owners["G4"]))
        else:
            rows.append(_row("G4", "WAITING_AUTHORITY", "SECURITY_DECISION_REQUIRED", owners["G4"]))
    else:
        rows.append(_row("G4", "DEFERRED", "PLANNING_PHASE_ONLY", owners["G4"]))

    # G5 Capability / Specialist Eligibility
    if phase == "PLANNING":
        elig = ctx.get("specialist_eligible")
        if elig is True:
            rows.append(_row("G5", "PASS", "SPECIALIST_ELIGIBILITY_PROVEN", owners["G5"]))
        elif elig is False:
            rows.append(_row("G5", "BLOCK", "NO_ELIGIBLE_SPECIALIST", owners["G5"]))
        else:
            rows.append(_row("G5", "WAITING_AUTHORITY", "SPECIALIST_ELIGIBILITY_REQUIRED", owners["G5"]))
    else:
        rows.append(_row("G5", "DEFERRED", "PLANNING_PHASE_ONLY", owners["G5"]))

    # G6-G9 runtime
    if phase == "RUNTIME":
        runtime = ctx.get("runtime_admitted")
        rows.append(_row("G6", "PASS" if runtime is True else ("BLOCK" if runtime is False else "WAITING_RUNTIME_ADMISSION"), "RUNTIME_ADMISSION_" + ("VALID" if runtime is True else "REQUIRED"), owners["G6"]))

        mode_ok = ctx.get("workload_mode_compatible")
        hrb = ctx.get("hrb_admitted")
        if mode_ok is False:
            rows.append(_row("G7", "BLOCK", "WORKLOAD_MODE_CONFLICT", owners["G7"]))
        elif hrb is False:
            rows.append(_row("G7", "WAITING_RESOURCE", "HRB_ADMISSION_REQUIRED", owners["G7"]))
        elif mode_ok is True and hrb is True:
            rows.append(_row("G7", "PASS", "WORKLOAD_MODE_AND_HRB_VALID", owners["G7"]))
        else:
            rows.append(_row("G7", "WAITING_RESOURCE", "WORKLOAD_MODE_OR_HRB_STATE_REQUIRED", owners["G7"]))

        model = ctx.get("model_route_valid")
        rows.append(_row("G8", "PASS" if model is True else ("BLOCK" if model is False else "WAITING_AUTHORITY"), "MODEL_ROUTE_" + ("VALID" if model is True else "REQUIRED"), owners["G8"]))

        effect = ctx.get("uaf_effect_authorized")
        rows.append(_row("G9", "PASS" if effect is True else ("BLOCK" if effect is False else "WAITING_AUTHORITY"), "UAF_EFFECT_" + ("AUTHORIZED" if effect is True else "AUTHORIZATION_REQUIRED"), owners["G9"]))
    else:
        for gid in ("G6", "G7", "G8", "G9"):
            rows.append(_row(gid, "DEFERRED", "RUNTIME_PHASE_ONLY", owners[gid]))

    # G10 post execution
    if phase == "POST_EXECUTION":
        evidence = ctx.get("evidence_verified")
        rows.append(_row("G10", "PASS" if evidence is True else ("BLOCK" if evidence is False else "WAITING_AUTHORITY"), "EVIDENCE_" + ("VERIFIED" if evidence is True else "VERIFICATION_REQUIRED"), owners["G10"]))
    else:
        rows.append(_row("G10", "DEFERRED", "POST_EXECUTION_ONLY", owners["G10"]))

    result = _overall(rows, phase)
    return {
        "schema": "fa3.orchestration-guard-evaluation.v1",
        "phase": phase,
        "task_id": task.get("task_id"),
        "task_group": None if snapshot is None else {
            "task_group_id": snapshot["task_group_id"],
            "revision": snapshot["revision"],
            "digest": snapshot["digest"],
            "registry_revision": snapshot["registry_revision"],
        },
        "authority": False,
        "guards": rows,
        "overall_result": result,
    }


def require_guard_pass(evaluation: dict[str, Any]) -> None:
    if evaluation.get("overall_result") != "PASS":
        raise GuardChainError(f"guard chain not PASS: {evaluation.get('overall_result')}")
