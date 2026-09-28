"""Non-authoritative, bounded action selection for existing FA3 Goal Execution.

Registry/policy/gateway sets must be supplied by their existing trusted owners.
Neither a candidate set nor a Decision Fabric trace grants execution authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from fa3_decision_fabric import DecisionFabric
from fa3_goal_execution import GoalContractError, digest, validate_goal

class ActionBindingDenied(GoalContractError):
    pass

def _ids(values: Iterable[str], label: str) -> set[str]:
    if isinstance(values, (str, bytes)):
        raise ActionBindingDenied(label + " must be a set of IDs")
    try:
        out = set(values)
    except (TypeError, ValueError) as exc:
        raise ActionBindingDenied(label + " invalid") from exc
    if not out or not all(isinstance(x, str) and x.strip() == x and x for x in out):
        raise ActionBindingDenied(label + " contains invalid or no IDs")
    return out

def prepare_action_request(goal_value: dict[str, Any], plan: dict[str, Any], *,
                           registered_action_ids: Iterable[str],
                           gateway_action_ids: Iterable[str],
                           security_action_ids: Iterable[str],
                           eligible_agent_refs: Iterable[str]) -> dict[str, Any]:
    """Intersect pre-authorized sources BEFORE exposing a finite candidate set.

    This is a design-time projection. External owners must authenticate the
    supplied registry, Security and Gateway sets; they are not receipts here.
    """
    goal = validate_goal(goal_value)
    if (not isinstance(plan, dict) or plan.get("schema") != "fa3.goal-plan.v1"
            or plan.get("goal_digest") != digest(goal)
            or plan.get("goal_id") != goal["goal_id"]
            or plan.get("goal_revision") != goal["revision"]):
        raise ActionBindingDenied("stale or foreign goal plan")
    registered = _ids(registered_action_ids, "registered actions")
    gateway = _ids(gateway_action_ids, "gateway actions")
    security = _ids(security_action_ids, "security actions")
    agents = _ids(eligible_agent_refs, "eligible agents")
    policy = goal["execution_policy"]
    permitted = set(policy["allowed_action_ids"]) & registered & gateway & security
    participants = set(policy["authorized_ai_participants"]) & agents
    candidates = []
    seen = set()
    for step in plan.get("steps", []):
        if not isinstance(step, dict):
            raise ActionBindingDenied("invalid plan step")
        task_id = step.get("task_id")
        action = step.get("uaf_action_ref")
        effect = step.get("effect")
        worker = step.get("workload_candidate", {}).get("agent_definition_ref")
        if (not isinstance(task_id, str) or not task_id or task_id in seen):
            raise ActionBindingDenied("invalid or duplicate task id")
        seen.add(task_id)
        if (action not in permitted or effect not in policy["allowed_effects"]
                or worker not in participants):
            continue
        if effect == "DESTRUCTIVE" and policy["mode"] == "AUTO":
            continue
        candidates.append({"id": task_id, "description": action,
                           "metadata": {"effect": effect, "action_ref": action,
                                        "agent_definition_ref": worker}})
    if not candidates:
        raise ActionBindingDenied("no action survived registry, gateway and policy intersection")
    request = {
        "contract": "SELECT_ONE", "purpose": "goal-authorized-action",
        "candidates": candidates, "constraints": {},
        "policy_context": {"goal_id": goal["goal_id"], "goal_digest": digest(goal)},
        "evidence_refs": [], "failure_policy": "FAIL_CLOSED",
        "rollout": "ADVISORY", "final_policy_owner": "FA3-AUTH-SECURITY-GOV-001",
    }
    return {
        "request": request,
        "schema": "fa3.goal-bounded-action-request.v1",
        "goal_digest": digest(goal),
        "candidate_count": len(candidates),
        "status": "DESIGN_CANDIDATES_NOT_ADMITTED",
        "authority": False, "execution_performed": False,
    }

def bind_advisory_selection(prepared: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    """Check the complete Decision Fabric trace; never authorize tool execution."""
    request = prepared.get("request", {})
    candidates = request.get("candidates", [])
    if prepared.get("status") != "DESIGN_CANDIDATES_NOT_ADMITTED":
        raise ActionBindingDenied("invalid prepared action request")
    if (trace.get("schema") != "fa3.decision-trace.v1"
            or trace.get("contract") != "SELECT_ONE"
            or trace.get("purpose") != request.get("purpose")
            or trace.get("status") != "DECIDED"
            or trace.get("authority") is not False
            or trace.get("candidate_set_expanded") is not False):
        raise ActionBindingDenied("invalid advisory decision status or authority")
    digest_payload = json.dumps(candidates, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":")).encode("utf-8")
    if trace.get("candidate_digest_sha256") != hashlib.sha256(digest_payload).hexdigest():
        raise ActionBindingDenied("candidate set was changed after Decision Fabric input")
    selection = trace.get("result", {}).get("selected")
    match = [c for c in candidates if c["id"] == selection] if isinstance(selection, str) else []
    if len(match) != 1:
        raise ActionBindingDenied("selection outside pre-authorized candidates")
    return {
        "schema": "fa3.goal-action-binding.v1",
        "goal_digest": prepared["goal_digest"],
        "selected_task_id": selection,
        "action_ref": match[0]["metadata"]["action_ref"],
        "effect": match[0]["metadata"]["effect"],
        "decision_id": trace.get("decision_id"),
        "status": "SELECTED_REQUIRES_FRESH_UAF_SECURITY_GATEWAY_ADMISSION",
        "authority": False, "execution_performed": False,
        "effect_authorization": False,
    }

def choose_advisory_action(goal_value: dict[str, Any], plan: dict[str, Any], *,
                           registered_action_ids: Iterable[str],
                           gateway_action_ids: Iterable[str],
                           security_action_ids: Iterable[str],
                           eligible_agent_refs: Iterable[str],
                           fabric: DecisionFabric | None = None) -> dict[str, Any]:
    prepared = prepare_action_request(
        goal_value, plan, registered_action_ids=registered_action_ids,
        gateway_action_ids=gateway_action_ids, security_action_ids=security_action_ids,
        eligible_agent_refs=eligible_agent_refs,
    )
    trace = (fabric or DecisionFabric()).decide(prepared["request"])
    return bind_advisory_selection(prepared, trace)
