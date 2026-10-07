#!/usr/bin/env python3
"""FA3 goal-driven planning and evidence prechecks; intentionally no execution authority.

Only existing FA3 Workforce, Agent Workload, UAF, Temporal, HRB, Model Router,
Security and canonical Evidence/Gate may authorize real effects or completion.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from fa3_agent_workload import validate_task as validate_workload_task
from fa3_orchestration_workforce import route_task
from fa3_task_scope_closure import TaskScopeClosureError, goal_scope_binding, scope_digest

GOAL_SCHEMA = "fa3.goal-contract.v1"
PLAN_SCHEMA = "fa3.goal-plan.v1"
ASSESS_SCHEMA = "fa3.goal-evidence-assessment.v1"
CONTRACT_ID = "FA3-GOAL-EXECUTION-CONTRACTS-001"
MODE = frozenset({"AUTO", "APPROVAL", "HYBRID"})
EFFECT = frozenset({"READ", "WRITE", "DESTRUCTIVE"})
CHECK = frozenset({"DETERMINISTIC", "HUMAN", "SEMANTIC_ADVISORY_WITH_INDEPENDENT_CHECK"})
SCOPE_ORIGIN = frozenset({"EXPLICIT_USER_SCOPE", "REQUIRED_FOR_APPROVED_GOAL", "EXPLICIT_USER_SCOPE_EXTENSION"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_FIELDS = frozenset({
    "api_key", "password", "secret", "secret_value", "token", "bearer_token",
    "physical_model_id", "model_id", "direct_provider_endpoint", "provider_endpoint",
    "cuda_visible_devices", "rocr_visible_devices", "gpu_index", "gpu_ordinal",
})
_LIMITS = (
    "max_children", "max_depth", "max_concurrent_children", "max_runtime_seconds",
    "max_retries", "max_tool_calls", "max_model_requests",
)
_REUSE_AUTH = "FA3-REUSE-DISCOVERY-001"
_HRB_AUTH = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
_ROUTER_AUTH = "FA3-AUTH-MODEL-ROUTER-001"
_EVIDENCE_AUTH = "FA3-AUTH-OBS-EVIDENCE-001"


class GoalContractError(ValueError):
    """Fail closed on invalid or unauthorized planning input."""


def _required(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GoalContractError(f"{label} is required")
    return value.strip()


def _unique_strings(value: Any, label: str, *, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not empty and not value):
        raise GoalContractError(f"{label} must be a list")
    if not all(isinstance(v, str) and v.strip() == v and v for v in value):
        raise GoalContractError(f"{label} must contain non-empty trimmed strings")
    if len(value) != len(set(value)):
        raise GoalContractError(f"{label} contains duplicates")
    return list(value)


def _reject_forbidden(value: Any) -> None:
    """No secrets or physical backend/device pins in a user-owned goal."""
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_FIELDS:
                raise GoalContractError(f"forbidden goal field: {key}")
            _reject_forbidden(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden(child)



def validate_task_scope_provenance(goal: dict[str, Any], step: dict[str, Any]) -> tuple[str, list[str]]:
    """Require deterministic provenance from every executable task candidate to user-owned scope."""
    origin = _required(step.get("scope_origin"), "scope_origin")
    if origin not in SCOPE_ORIGIN:
        raise GoalContractError("task scope origin is not executable")
    refs = _unique_strings(step.get("scope_refs"), "scope_refs")
    in_scope = set(goal["scope"]["in_scope"])
    if not set(refs).issubset(in_scope):
        raise GoalContractError("task scope reference outside approved goal scope")
    if origin == "EXPLICIT_USER_SCOPE_EXTENSION" and goal["revision"] < 2:
        raise GoalContractError("explicit scope extension requires a revised goal")
    return origin, refs

def digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def validate_goal(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != GOAL_SCHEMA:
        raise GoalContractError("goal schema mismatch")
    _reject_forbidden(value)
    goal = copy.deepcopy(value)
    for key in ("goal_id", "owner_ref", "objective", "workspace_ref"):
        _required(goal.get(key), key)
    if type(goal.get("revision")) is not int or goal["revision"] < 1:
        raise GoalContractError("revision must be a positive integer")
    scope = goal.get("scope")
    if not isinstance(scope, dict):
        raise GoalContractError("explicit scope required")
    _unique_strings(scope.get("in_scope"), "scope.in_scope")
    _unique_strings(scope.get("out_of_scope", []), "scope.out_of_scope", empty=True)
    try:
        scope_digest(scope)
    except TaskScopeClosureError as exc:
        raise GoalContractError(str(exc)) from exc
    criteria = goal.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        raise GoalContractError("at least one independently verifiable criterion required")
    seen = set()
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise GoalContractError("criterion must be an object")
        ident = _required(criterion.get("criterion_id"), "criterion_id")
        _required(criterion.get("expected_observation"), "expected_observation")
        if ident in seen:
            raise GoalContractError("duplicate criterion_id")
        seen.add(ident)
        check = criterion.get("verification")
        if not isinstance(check, dict) or check.get("kind") not in CHECK:
            raise GoalContractError("criterion verifier is missing or unsupported")
        _required(check.get("verifier_ref"), "verifier_ref")
        _unique_strings(check.get("evidence_kinds"), "evidence_kinds")
        if check["kind"] == "SEMANTIC_ADVISORY_WITH_INDEPENDENT_CHECK":
            _required(check.get("independent_verifier_ref"), "independent_verifier_ref")
            if check["independent_verifier_ref"] == check["verifier_ref"]:
                raise GoalContractError("semantic advisory cannot independently verify itself")
    policy = goal.get("execution_policy")
    if not isinstance(policy, dict) or policy.get("mode") not in MODE:
        raise GoalContractError("execution mode is required")
    actions = _unique_strings(policy.get("allowed_action_ids"), "allowed_action_ids")
    effects = _unique_strings(policy.get("allowed_effects"), "allowed_effects")
    if not set(effects).issubset(EFFECT):
        raise GoalContractError("unknown effect class")
    _unique_strings(policy.get("authorized_ai_participants", []), "authorized_ai_participants", empty=True)
    _required(policy.get("policy_ref"), "policy_ref")
    _required(policy.get("approval_policy_ref"), "approval_policy_ref")
    if len(actions) > 1000:
        raise GoalContractError("excessive action allowlist")
    limits = policy.get("limits")
    if not isinstance(limits, dict) or set(limits) != set(_LIMITS):
        raise GoalContractError("complete existing Agent Workload budget required")
    for name in _LIMITS:
        x = limits[name]
        if type(x) is not int or x < 0:
            raise GoalContractError(f"invalid budget: {name}")
    if limits["max_concurrent_children"] > limits["max_children"]:
        raise GoalContractError("concurrency exceeds child budget")
    if limits["max_runtime_seconds"] < 1:
        raise GoalContractError("runtime bound is required")
    if policy["mode"] == "AUTO" and "DESTRUCTIVE" in effects:
        raise GoalContractError("AUTO cannot pre-authorize destructive effects")
    return goal


def prepare_goal(value: dict[str, Any]) -> dict[str, Any]:
    """Return validated, immutable-revision-bound metadata; never start work."""
    goal = validate_goal(value)
    return {
        "schema": "fa3.goal-intake.v1",
        "contract_id": CONTRACT_ID,
        "goal": goal,
        "goal_digest": digest(goal),
        "status": "VALIDATED_PLAN_ONLY",
        "authority": False,
        "execution_performed": False,
        "canonical_goal_owner": "USER",
        "goal_scope_binding": goal_scope_binding(goal),
    }


def compile_plan(root: Path | str, goal_value: dict[str, Any], steps: list[dict[str, Any]],
                 preflight: dict[str, Any]) -> dict[str, Any]:
    """Compile authorized-intent candidate plans through real Workforce/Workload validators.

    Advisory routing is DESIGN ONLY. Receipts here are merely review references:
    existing admission authorities must independently authenticate and recheck each
    receipt immediately before an effect or a resumed execution.
    """
    goal = validate_goal(goal_value)
    immutable_scope_binding = goal_scope_binding(goal)
    if not isinstance(preflight, dict):
        raise GoalContractError("preflight receipt references required")
    if preflight.get("reuse_profile") != _REUSE_AUTH:
        raise GoalContractError("Reuse Discovery required")
    if preflight.get("hardware_resource_authority") != _HRB_AUTH:
        raise GoalContractError("Hardware Audit/HRB boundary required")
    if preflight.get("model_route_authority") != _ROUTER_AUTH:
        raise GoalContractError("central Model Router required")
    for name in ("reuse_assessment_ref", "hardware_audit_ref", "security_policy_ref"):
        _required(preflight.get(name), name)
    if not isinstance(steps, list) or not steps:
        raise GoalContractError("non-empty steps required")
    limit = goal["execution_policy"]["limits"]
    if len(steps) > limit["max_children"]:
        raise GoalContractError("plan exceeds child budget")
    criteria = {c["criterion_id"] for c in goal["acceptance_criteria"]}
    policy = goal["execution_policy"]
    allowed_actions = set(policy["allowed_action_ids"])
    allowed_participants = set(policy.get("authorized_ai_participants", []))
    allowed_effects = set(policy["allowed_effects"])
    planned = []
    seen = set()
    for step in steps:
        if not isinstance(step, dict):
            raise GoalContractError("step must be object")
        _reject_forbidden(step)
        tid = _required(step.get("task_id"), "task_id")
        scope_origin, scope_refs = validate_task_scope_provenance(goal, step)
        if tid in seen:
            raise GoalContractError("duplicate task id")
        seen.add(tid)
        action = _required(step.get("action_id"), "action_id")
        if action not in allowed_actions:
            raise GoalContractError("action outside goal allowlist")
        effect = step.get("effect")
        if effect not in allowed_effects:
            raise GoalContractError("effect outside goal allowlist")
        if effect == "DESTRUCTIVE" and policy["mode"] == "AUTO":
            raise GoalContractError("AUTO destructive effect forbidden")
        cids = _unique_strings(step.get("criterion_ids"), "step.criterion_ids")
        if not set(cids).issubset(criteria):
            raise GoalContractError("step refers to unknown criterion")
        agent = _required(step.get("agent_definition_ref"), "agent_definition_ref")
        if agent not in allowed_participants:
            raise GoalContractError("agent outside authorized participant set")
        model_intent = step.get("model_intent")
        if not isinstance(model_intent, dict) or not model_intent.get("logical_route"):
            raise GoalContractError("logical Model Router route required")
        if set(model_intent) != {"logical_route"}:
            raise GoalContractError("model intent must contain only logical_route")
        requirements = {
            "task_id": tid,
            "domain": _required(step.get("domain"), "domain"),
            "required_capabilities": _unique_strings(step.get("required_capabilities"), "required_capabilities"),
            "authorized_ai_participants": list(policy["authorized_ai_participants"]),
            "resource_requirements": copy.deepcopy(step.get("resource_requirements", {})),
            "required_authorities": copy.deepcopy(step.get("required_authorities", [])),
        }
        routing = route_task(Path(root), requirements, runtime_execution=False)
        if routing["status"] != "ROUTED":
            raise GoalContractError(f"no eligible specialist for task {tid}: {routing['status']}")
        workload = {
            "schema": "fa3.agent-workload-task.v1",
            "task_id": tid,
            "root_task_id": goal["goal_id"],
            "scope_origin": scope_origin,
            "scope_refs": list(scope_refs),
            "goal_scope_binding": copy.deepcopy(immutable_scope_binding),
            "action_ref": action,
            "agent_definition_ref": agent,
            "resource_requirements": copy.deepcopy(step.get("resource_requirements", {})),
            "network_envelope_ref": _required(step.get("network_envelope_ref"), "network_envelope_ref"),
            "model_intent": copy.deepcopy(model_intent),
            "authorized_ai_participants": list(policy["authorized_ai_participants"]),
            "fanout_limits": copy.deepcopy(limit),
        }
        checked = validate_workload_task(workload)
        planned.append({
            "task_id": tid, "criterion_ids": cids, "effect": effect,
            "scope_origin": scope_origin,
            "scope_refs": scope_refs, "goal_scope_binding": copy.deepcopy(immutable_scope_binding),
            "uaf_action_ref": action, "workload_candidate": checked,
            "design_route": routing,
            "requires_effect_authorization": effect != "READ" or policy["mode"] != "AUTO",
            "runtime_admission": "PENDING_EXISTING_AUTHORITIES",
            "execution_performed": False,
        })
    return {
        "schema": PLAN_SCHEMA, "contract_id": CONTRACT_ID,
        "goal_id": goal["goal_id"], "goal_revision": goal["revision"],
        "goal_digest": digest(goal), "steps": planned,
        "preflight_references": copy.deepcopy(preflight),
        "status": "PLAN_ONLY_REQUIRES_EXISTING_AUTHORITY_ADMISSION",
        "temporal_lifecycle_authority": "EXISTING_TEMPORAL_ONLY",
        "resource_authority": _HRB_AUTH,
        "model_route_authority": _ROUTER_AUTH,
        "uaf_required": True, "execution_performed": False,
        "authority": False,
    }


def assess_evidence(goal_value: dict[str, Any], observations: list[dict[str, Any]],
                    *, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Review provenance completeness. NEVER declare VERIFIED from untrusted JSON."""
    goal = validate_goal(goal_value)
    if plan is not None and (plan.get("schema") != PLAN_SCHEMA or
                             plan.get("goal_digest") != digest(goal)):
        raise GoalContractError("stale or foreign plan")
    if not isinstance(observations, list):
        raise GoalContractError("observations must be list")
    obs_by_id = {}
    for row in observations:
        if not isinstance(row, dict):
            raise GoalContractError("observation must be object")
        cid = _required(row.get("criterion_id"), "criterion_id")
        if cid in obs_by_id:
            raise GoalContractError("duplicate criterion observation")
        obs_by_id[cid] = row
    expected = {c["criterion_id"]: c for c in goal["acceptance_criteria"]}
    if not set(obs_by_id).issubset(expected):
        raise GoalContractError("unknown criterion observation")
    results = []
    for cid, criterion in expected.items():
        row = obs_by_id.get(cid)
        status = "MISSING"
        reason = "NO_OBSERVATION"
        if row is not None:
            checker = criterion["verification"]
            if row.get("verifier_ref") != checker["verifier_ref"]:
                status, reason = "BLOCKED", "UNRECOGNIZED_VERIFIER"
            elif row.get("status") != "PASS":
                status, reason = "UNPROVEN", "VERIFIER_DID_NOT_PASS"
            elif not isinstance(row.get("artifact_digest"), str) or not HEX64.fullmatch(row["artifact_digest"]):
                status, reason = "BLOCKED", "ARTIFACT_DIGEST_MISSING_OR_INVALID"
            elif not isinstance(row.get("evidence_ref"), str) or not row["evidence_ref"].strip():
                status, reason = "BLOCKED", "CANONICAL_EVIDENCE_REFERENCE_REQUIRED"
            elif row.get("evidence_authority") != _EVIDENCE_AUTH:
                status, reason = "BLOCKED", "WRONG_EVIDENCE_AUTHORITY"
            elif checker["kind"] == "SEMANTIC_ADVISORY_WITH_INDEPENDENT_CHECK" and (
                row.get("independent_verifier_ref") != checker["independent_verifier_ref"] or
                row.get("independent_check_status") != "PASS"
            ):
                status, reason = "BLOCKED", "SEMANTIC_ADVISORY_NOT_INDEPENDENT_PROOF"
            elif checker["kind"] == "HUMAN" and not row.get("human_approval_ref"):
                status, reason = "BLOCKED", "HUMAN_SIGNOFF_REQUIRED"
            else:
                # The real Evidence/Gate authority must independently fetch and validate
                # digests, scope, runtime receipts, checker identity and approvals.
                status, reason = "READY_FOR_CANONICAL_VERIFICATION", "REFERENCES_PRESENT_NOT_VERIFIED"
        results.append({"criterion_id": cid, "status": status, "reason": reason})
    all_candidate = all(r["status"] == "READY_FOR_CANONICAL_VERIFICATION" for r in results)
    return {
        "schema": ASSESS_SCHEMA, "goal_id": goal["goal_id"],
        "goal_revision": goal["revision"], "goal_digest": digest(goal),
        "criteria": results,
        "status": "CANONICAL_GATE_REQUIRED" if all_candidate else "INCOMPLETE_OR_BLOCKED",
        "verification_claim": False, "authority": False,
        "execution_performed": False,
        "canonical_gate_required": True,
    }


def propose_repair(goal_value: dict[str, Any], assessment: dict[str, Any],
                   attempted_retries: int) -> dict[str, Any]:
    """Return a finite, nonexecuting repair proposal, not a right to retry."""
    goal = validate_goal(goal_value)
    if (assessment.get("schema") != ASSESS_SCHEMA or
            assessment.get("goal_id") != goal["goal_id"] or
            assessment.get("goal_revision") != goal["revision"] or
            assessment.get("goal_digest") != digest(goal)):
        raise GoalContractError("assessment does not match immutable goal revision")
    rows = assessment.get("criteria")
    if not isinstance(rows, list):
        raise GoalContractError("assessment criteria must be list")
    expected_ids = [c["criterion_id"] for c in goal["acceptance_criteria"]]
    seen: set[str] = set()
    allowed_statuses = {"MISSING", "BLOCKED", "UNPROVEN", "READY_FOR_CANONICAL_VERIFICATION"}
    for row in rows:
        if not isinstance(row, dict):
            raise GoalContractError("assessment criterion must be object")
        cid = _required(row.get("criterion_id"), "assessment.criterion_id")
        if cid in seen:
            raise GoalContractError("duplicate assessment criterion")
        if cid not in expected_ids:
            raise GoalContractError("assessment refers to unknown criterion")
        if row.get("status") not in allowed_statuses:
            raise GoalContractError("assessment criterion status invalid")
        seen.add(cid)
    if seen != set(expected_ids):
        raise GoalContractError("assessment criterion set incomplete")
    if type(attempted_retries) is not int or attempted_retries < 0:
        raise GoalContractError("invalid retry count")
    remaining = goal["execution_policy"]["limits"]["max_retries"] - attempted_retries
    failed = [r["criterion_id"] for r in rows
              if r["status"] != "READY_FOR_CANONICAL_VERIFICATION"]
    return {
        "schema": "fa3.goal-repair-proposal.v1", "goal_digest": digest(goal),
        "criterion_ids": failed, "remaining_retry_budget": max(0, remaining),
        "status": ("NO_REPAIR_NEEDED" if not failed else
                   "ESCALATE_BUDGET_EXHAUSTED" if remaining <= 0 else
                   "PROPOSE_AUTHORIZED_REPAIR"),
        "effect_authorization": False, "execution_performed": False,
        "scope_refs": list(goal["scope"]["in_scope"]),
        "scope_expansion_allowed": False, "new_criteria_allowed": False,
        "successor_task_allowed": False if not failed else None,
        "require_fresh_policy_and_admission": True,
    }
