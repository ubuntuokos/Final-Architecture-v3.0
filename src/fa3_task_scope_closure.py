#!/usr/bin/env python3
"""CFA3 task-scope, bounded-retry and closure primitives.

This module creates and validates policy/state envelopes consumed by existing
Goal Execution and Agent Workload paths. It is not a scheduler or durable
workflow authority. Temporal remains the sole global durable lifecycle owner;
UAF/Security, HRB, Model Router and Evidence retain their existing authorities.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

POLICY_ID = "FA3-TASK-SCOPE-CLOSURE-POLICY-2026-10-03"
GOAL_CONTRACT_ID = "FA3-GOAL-EXECUTION-CONTRACTS-001"
GOAL_SCOPE_BINDING_SCHEMA = "fa3.goal-scope-binding.v1"
TASK_CONTROL_SCHEMA = "fa3.task-scope-control.v1"
FOLLOWUP_SCHEMA = "fa3.task-followup-handoff.v1"
EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"
MAX_SAME_BLOCKER_ATTEMPTS = 3

ACTIVE = "ACTIVE"
HUMAN_INTERVENTION_REQUIRED = "HUMAN_INTERVENTION_REQUIRED"
CLOSED = "CLOSED"
DONE = "DONE"
NEW_TASK_DISCOVERED = "NEW_TASK_DISCOVERED"

_INTERNAL_TERMINAL = frozenset({"VERIFIED", "PARTIAL", "BLOCKED", "FAILED", "CANCELLED"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class TaskScopeClosureError(ValueError):
    """Fail closed on invalid task scope, retry, handoff or closure state."""


def _required(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskScopeClosureError(f"{label} is required")
    return value.strip()


def _string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise TaskScopeClosureError(f"{label} must be a list")
    if not all(isinstance(v, str) and v and v.strip() == v for v in value):
        raise TaskScopeClosureError(f"{label} must contain trimmed non-empty strings")
    if len(value) != len(set(value)):
        raise TaskScopeClosureError(f"{label} contains duplicates")
    return list(value)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def scope_digest(scope: dict[str, Any]) -> str:
    if not isinstance(scope, dict):
        raise TaskScopeClosureError("scope object required")
    in_scope = _string_list(scope.get("in_scope"), "scope.in_scope", allow_empty=False)
    out_of_scope = _string_list(scope.get("out_of_scope", []), "scope.out_of_scope")
    overlap = sorted(set(in_scope) & set(out_of_scope))
    if overlap:
        raise TaskScopeClosureError("scope item cannot be both in_scope and out_of_scope")
    return _digest({"in_scope": in_scope, "out_of_scope": out_of_scope})


def task_control_digest(control: dict[str, Any]) -> str:
    """Hash the validated control bytes used to bind a compiled execution plan."""
    checked = validate_task_control(control)
    return _digest(checked)


def goal_scope_binding(goal: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(goal, dict):
        raise TaskScopeClosureError("goal object required")
    goal_id = _required(goal.get("goal_id"), "goal_id")
    revision = goal.get("revision")
    if type(revision) is not int or revision < 1:
        raise TaskScopeClosureError("goal revision must be a positive integer")
    return {
        "schema": GOAL_SCOPE_BINDING_SCHEMA,
        "policy_id": POLICY_ID,
        "goal_contract_id": GOAL_CONTRACT_ID,
        "goal_id": goal_id,
        "goal_revision": revision,
        "goal_digest": _digest(goal),
        "scope_digest": scope_digest(goal.get("scope")),
        "max_same_blocker_attempts": MAX_SAME_BLOCKER_ATTEMPTS,
        "automatic_scope_expansion": False,
        "out_of_scope_followup": "NEW_TASK_REQUIRED",
        "automatic_followup_execution": False,
        "human_intervention_freezes_execution": True,
        "closed_task_execution": "FORBIDDEN",
        "durable_state_authority": "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY",
        "authority": False,
    }


def validate_goal_scope_binding(
    binding: dict[str, Any],
    *,
    expected_root_task_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(binding, dict) or binding.get("schema") != GOAL_SCOPE_BINDING_SCHEMA:
        raise TaskScopeClosureError("goal scope binding schema mismatch")
    if binding.get("policy_id") != POLICY_ID or binding.get("goal_contract_id") != GOAL_CONTRACT_ID:
        raise TaskScopeClosureError("goal scope policy identity drift")
    goal_id = _required(binding.get("goal_id"), "binding.goal_id")
    if expected_root_task_id is not None and goal_id != expected_root_task_id:
        raise TaskScopeClosureError("goal scope binding root task mismatch")
    if type(binding.get("goal_revision")) is not int or binding["goal_revision"] < 1:
        raise TaskScopeClosureError("goal scope binding revision invalid")
    for key in ("goal_digest", "scope_digest"):
        if not _HEX64.fullmatch(str(binding.get(key, ""))):
            raise TaskScopeClosureError(f"{key} must be sha256")
    if binding.get("max_same_blocker_attempts") != MAX_SAME_BLOCKER_ATTEMPTS:
        raise TaskScopeClosureError("same blocker attempt limit must be exactly three")
    if binding.get("automatic_scope_expansion") is not False:
        raise TaskScopeClosureError("automatic scope expansion forbidden")
    if binding.get("out_of_scope_followup") != "NEW_TASK_REQUIRED":
        raise TaskScopeClosureError("out-of-scope work must require a new task")
    if binding.get("automatic_followup_execution") is not False:
        raise TaskScopeClosureError("automatic follow-up execution forbidden")
    if binding.get("human_intervention_freezes_execution") is not True:
        raise TaskScopeClosureError("human intervention must freeze execution")
    if binding.get("closed_task_execution") != "FORBIDDEN":
        raise TaskScopeClosureError("closed task execution must be forbidden")
    if binding.get("durable_state_authority") != "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY":
        raise TaskScopeClosureError("Temporal durable lifecycle authority drift")
    if binding.get("authority") is not False:
        raise TaskScopeClosureError("task scope binding cannot be an authority")
    return copy.deepcopy(binding)


def start_task_control(
    binding: dict[str, Any],
    *,
    task_id: str,
    root_task_id: str,
) -> dict[str, Any]:
    checked = validate_goal_scope_binding(binding, expected_root_task_id=root_task_id)
    return {
        "schema": TASK_CONTROL_SCHEMA,
        "policy_id": POLICY_ID,
        "task_id": _required(task_id, "task_id"),
        "root_task_id": _required(root_task_id, "root_task_id"),
        "goal_id": checked["goal_id"],
        "goal_revision": checked["goal_revision"],
        "goal_digest": checked["goal_digest"],
        "scope_digest": checked["scope_digest"],
        "control_revision": 1,
        "state": ACTIVE,
        "execution_frozen": False,
        "blocker_attempts": {},
        "attempt_ledger": [],
        "followup_handoffs": [],
        "internal_terminal_state": None,
        "user_closure_state": None,
        "verification_evidence": None,
        "automatic_retry_allowed": True,
        "automatic_replan_allowed": True,
        "alternative_route_allowed": True,
        "durable_state_authority": checked["durable_state_authority"],
        "authority": False,
    }


def _validate_followup_handoff(
    handoff: dict[str, Any],
    *,
    task_id: str,
    root_task_id: str,
    goal_id: str,
    goal_revision: int,
    goal_digest: str,
    scope_digest_value: str,
) -> dict[str, Any]:
    if not isinstance(handoff, dict) or handoff.get("schema") != FOLLOWUP_SCHEMA:
        raise TaskScopeClosureError("follow-up handoff schema mismatch")
    if handoff.get("policy_id") != POLICY_ID or handoff.get("authority") is not False:
        raise TaskScopeClosureError("follow-up handoff policy/authority drift")
    expected = {
        "origin_task_id": task_id,
        "origin_root_task_id": root_task_id,
        "origin_goal_id": goal_id,
        "origin_goal_revision": goal_revision,
        "origin_goal_digest": goal_digest,
        "origin_scope_digest": scope_digest_value,
    }
    for key, value in expected.items():
        if handoff.get(key) != value:
            raise TaskScopeClosureError(f"follow-up handoff origin mismatch: {key}")
    for key in (
        "scope_item", "scope_classification_reason", "discovered_issue",
        "why_out_of_scope", "current_state", "suggested_new_task_objective",
        "suggested_new_conversation_start",
    ):
        _required(handoff.get(key), f"handoff.{key}")
    _string_list(handoff.get("evidence_refs", []), "handoff.evidence_refs")
    if (
        handoff.get("requires_new_task_id") is not True
        or handoff.get("requires_user_start") is not True
        or handoff.get("automatic_start") is not False
        or handoff.get("execution_performed") is not False
    ):
        raise TaskScopeClosureError("follow-up handoff safety flags invalid")
    handoff_id = _required(handoff.get("handoff_id"), "handoff.handoff_id")
    payload = copy.deepcopy(handoff)
    payload.pop("handoff_id", None)
    expected_id = "followup:" + _digest(payload)[:24]
    if handoff_id != expected_id:
        raise TaskScopeClosureError("follow-up handoff id/content mismatch")
    return copy.deepcopy(handoff)


def _validate_verification_evidence(
    evidence: dict[str, Any],
    *,
    task_id: str,
    control_revision_before_close: int,
) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise TaskScopeClosureError("Evidence-authority verification receipt required")
    if evidence.get("authority") != EVIDENCE_AUTHORITY:
        raise TaskScopeClosureError("VERIFIED closure requires canonical Evidence authority")
    if evidence.get("result") != "VERIFIED":
        raise TaskScopeClosureError("Evidence receipt result must be VERIFIED")
    if evidence.get("task_id") != task_id:
        raise TaskScopeClosureError("Evidence receipt task binding mismatch")
    if evidence.get("control_revision") != control_revision_before_close:
        raise TaskScopeClosureError("Evidence receipt task-control revision mismatch")
    _required(evidence.get("receipt_ref"), "verification receipt_ref")
    refs = _string_list(evidence.get("evidence_refs"), "verification evidence_refs", allow_empty=False)
    result = copy.deepcopy(evidence)
    result["evidence_refs"] = refs
    return result


def validate_task_control(
    control: dict[str, Any],
    *,
    expected_task_id: str | None = None,
    expected_root_task_id: str | None = None,
    expected_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(control, dict) or control.get("schema") != TASK_CONTROL_SCHEMA:
        raise TaskScopeClosureError("task control schema mismatch")
    if control.get("policy_id") != POLICY_ID or control.get("authority") is not False:
        raise TaskScopeClosureError("task control policy/authority drift")
    task_id = _required(control.get("task_id"), "control.task_id")
    root_task_id = _required(control.get("root_task_id"), "control.root_task_id")
    if expected_task_id is not None and task_id != expected_task_id:
        raise TaskScopeClosureError("task control task_id mismatch")
    if expected_root_task_id is not None and root_task_id != expected_root_task_id:
        raise TaskScopeClosureError("task control root_task_id mismatch")
    if control.get("goal_id") != root_task_id:
        raise TaskScopeClosureError("task control goal/root identity mismatch")
    if type(control.get("goal_revision")) is not int or control["goal_revision"] < 1:
        raise TaskScopeClosureError("task control goal revision invalid")
    revision = control.get("control_revision")
    if type(revision) is not int or revision < 1:
        raise TaskScopeClosureError("task control revision invalid")
    for key in ("goal_digest", "scope_digest"):
        if not _HEX64.fullmatch(str(control.get(key, ""))):
            raise TaskScopeClosureError(f"task control {key} invalid")
    if expected_binding is not None:
        binding = validate_goal_scope_binding(expected_binding, expected_root_task_id=root_task_id)
        for key in ("goal_id", "goal_revision", "goal_digest", "scope_digest"):
            if control.get(key) != binding.get(key):
                raise TaskScopeClosureError(f"task control binding mismatch: {key}")
    state = control.get("state")
    if state not in {ACTIVE, HUMAN_INTERVENTION_REQUIRED, CLOSED}:
        raise TaskScopeClosureError("task control state invalid")
    attempts = control.get("blocker_attempts")
    if not isinstance(attempts, dict):
        raise TaskScopeClosureError("blocker_attempts must be an object")
    for fingerprint, count in attempts.items():
        if not _HEX64.fullmatch(str(fingerprint)) or type(count) is not int or not (1 <= count <= MAX_SAME_BLOCKER_ATTEMPTS):
            raise TaskScopeClosureError("invalid blocker attempt ledger")
        if count >= MAX_SAME_BLOCKER_ATTEMPTS and state == ACTIVE:
            raise TaskScopeClosureError("three-attempt blocker cannot remain active")
    ledger = control.get("attempt_ledger")
    followups = control.get("followup_handoffs")
    if not isinstance(ledger, list) or not isinstance(followups, list):
        raise TaskScopeClosureError("task control ledgers must be lists")
    derived_attempts: dict[str, int] = {}
    for entry in ledger:
        if not isinstance(entry, dict):
            raise TaskScopeClosureError("attempt ledger entry must be an object")
        fingerprint = str(entry.get("blocker_fingerprint", ""))
        attempt = entry.get("attempt")
        if not _HEX64.fullmatch(fingerprint):
            raise TaskScopeClosureError("attempt ledger blocker fingerprint invalid")
        if type(attempt) is not int or not (1 <= attempt <= MAX_SAME_BLOCKER_ATTEMPTS):
            raise TaskScopeClosureError("attempt ledger sequence invalid")
        if entry.get("result") != "FAIL":
            raise TaskScopeClosureError("attempt ledger result must be FAIL")
        _required(entry.get("summary"), "attempt ledger summary")
        expected_attempt = derived_attempts.get(fingerprint, 0) + 1
        if attempt != expected_attempt:
            raise TaskScopeClosureError("attempt ledger sequence/count mismatch")
        derived_attempts[fingerprint] = attempt
    if attempts != derived_attempts:
        raise TaskScopeClosureError("blocker_attempts must equal append-only attempt ledger")
    handoff_ids: set[str] = set()
    for handoff in followups:
        checked_handoff = _validate_followup_handoff(
            handoff,
            task_id=task_id,
            root_task_id=root_task_id,
            goal_id=control["goal_id"],
            goal_revision=control["goal_revision"],
            goal_digest=control["goal_digest"],
            scope_digest_value=control["scope_digest"],
        )
        hid = checked_handoff["handoff_id"]
        if hid in handoff_ids:
            raise TaskScopeClosureError("duplicate persisted follow-up handoff")
        handoff_ids.add(hid)
    if control.get("durable_state_authority") != "TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY":
        raise TaskScopeClosureError("task control durable authority drift")
    terminal = control.get("internal_terminal_state")
    if terminal is not None and terminal not in _INTERNAL_TERMINAL:
        raise TaskScopeClosureError("internal terminal state invalid")
    verification = control.get("verification_evidence")
    if state == ACTIVE:
        if terminal is not None or verification is not None:
            raise TaskScopeClosureError("active task cannot carry terminal or verification state")
        if control.get("execution_frozen") is not False or control.get("user_closure_state") is not None:
            raise TaskScopeClosureError("active task cannot be frozen or closed")
        if any(control.get(k) is not True for k in (
            "automatic_retry_allowed", "automatic_replan_allowed", "alternative_route_allowed"
        )):
            raise TaskScopeClosureError("active task automatic controls drift")
    elif state == HUMAN_INTERVENTION_REQUIRED:
        if verification is not None:
            raise TaskScopeClosureError("non-verified task cannot carry verification receipt")
        if control.get("execution_frozen") is not True:
            raise TaskScopeClosureError("human-intervention task must freeze execution")
        if control.get("user_closure_state") != HUMAN_INTERVENTION_REQUIRED:
            raise TaskScopeClosureError("human-intervention closure projection mismatch")
        if terminal == "VERIFIED":
            raise TaskScopeClosureError("verified task cannot remain human-intervention state")
        _required(control.get("human_action_required"), "human_action_required")
        if any(control.get(k) is not False for k in (
            "automatic_retry_allowed", "automatic_replan_allowed", "alternative_route_allowed"
        )):
            raise TaskScopeClosureError("human-intervention task cannot auto-continue")
    else:
        if control.get("execution_frozen") is not True:
            raise TaskScopeClosureError("closed task must freeze execution")
        if terminal != "VERIFIED":
            raise TaskScopeClosureError("closed task must carry VERIFIED internal terminal state")
        _validate_verification_evidence(
            verification,
            task_id=task_id,
            control_revision_before_close=revision - 1,
        )
        if control.get("user_closure_state") not in {DONE, NEW_TASK_DISCOVERED}:
            raise TaskScopeClosureError("closed task user closure projection invalid")
        if any(control.get(k) is not False for k in (
            "automatic_retry_allowed", "automatic_replan_allowed", "alternative_route_allowed"
        )):
            raise TaskScopeClosureError("closed task cannot auto-continue")
    return copy.deepcopy(control)


def assert_execution_allowed(control: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    checked = validate_task_control(control, **kwargs)
    if checked["state"] != ACTIVE or checked["execution_frozen"] is not False:
        raise TaskScopeClosureError("task execution is frozen or closed")
    return checked


def classify_scope_item(scope: dict[str, Any], scope_item: str) -> dict[str, Any]:
    item = _required(scope_item, "scope_item")
    if not isinstance(scope, dict):
        raise TaskScopeClosureError("scope object required")
    scope_digest(scope)
    in_scope = _string_list(scope.get("in_scope"), "scope.in_scope", allow_empty=False)
    out_of_scope = _string_list(scope.get("out_of_scope", []), "scope.out_of_scope")
    if item in in_scope:
        return {
            "classification": "IN_SCOPE_REQUIRED_STEP",
            "automatic_execution_allowed_by_scope": True,
            "requires_new_task": False,
            "reason": "EXPLICIT_IN_SCOPE_MATCH",
        }
    return {
        "classification": "OUT_OF_SCOPE_FOLLOWUP",
        "automatic_execution_allowed_by_scope": False,
        "requires_new_task": True,
        "reason": "EXPLICIT_OUT_OF_SCOPE_MATCH" if item in out_of_scope else "UNDECLARED_SCOPE_NOT_AUTO_EXPANDED",
    }


def blocker_fingerprint(blocker_code: str, context_refs: list[str]) -> str:
    return _digest({
        "blocker_code": _required(blocker_code, "blocker_code"),
        "context_refs": _string_list(context_refs, "context_refs"),
    })


def _bump_revision(control: dict[str, Any]) -> None:
    control["control_revision"] = int(control["control_revision"]) + 1


def record_blocker_failure(
    control: dict[str, Any],
    blocker_id: str,
    summary: str,
    *,
    human_action: str | None = None,
) -> dict[str, Any]:
    checked = assert_execution_allowed(control)
    if not _HEX64.fullmatch(str(blocker_id)):
        raise TaskScopeClosureError("blocker fingerprint must be sha256")
    note = _required(summary, "blocker summary")
    result = copy.deepcopy(checked)
    prior = int(result["blocker_attempts"].get(blocker_id, 0))
    if prior >= MAX_SAME_BLOCKER_ATTEMPTS:
        raise TaskScopeClosureError("same blocker attempt limit already exhausted")
    attempt = prior + 1
    result["blocker_attempts"][blocker_id] = attempt
    result["attempt_ledger"].append({
        "blocker_fingerprint": blocker_id,
        "attempt": attempt,
        "result": "FAIL",
        "summary": note,
    })
    result["last_blocker"] = {
        "blocker_fingerprint": blocker_id,
        "attempt": attempt,
        "summary": note,
    }
    if attempt == MAX_SAME_BLOCKER_ATTEMPTS:
        result["state"] = HUMAN_INTERVENTION_REQUIRED
        result["execution_frozen"] = True
        result["user_closure_state"] = HUMAN_INTERVENTION_REQUIRED
        result["automatic_retry_allowed"] = False
        result["automatic_replan_allowed"] = False
        result["alternative_route_allowed"] = False
        result["human_action_required"] = (
            human_action.strip()
            if isinstance(human_action, str) and human_action.strip()
            else "Review the blocker evidence and explicitly decide whether and how to continue."
        )
        result["stop_reason"] = "SAME_BLOCKER_ATTEMPT_LIMIT_REACHED"
    _bump_revision(result)
    return validate_task_control(result)


def register_followup_handoff(
    control: dict[str, Any],
    binding: dict[str, Any],
    scope: dict[str, Any],
    *,
    scope_item: str,
    discovered_issue: str,
    why_out_of_scope: str,
    current_state: str,
    evidence_refs: list[str],
    suggested_new_task_objective: str,
    suggested_new_conversation_start: str,
) -> dict[str, Any]:
    checked = assert_execution_allowed(control)
    bound = validate_goal_scope_binding(binding, expected_root_task_id=checked["root_task_id"])
    if scope_digest(scope) != bound["scope_digest"]:
        raise TaskScopeClosureError("supplied scope does not match immutable bound scope digest")
    classification = classify_scope_item(scope, scope_item)
    if classification["classification"] != "OUT_OF_SCOPE_FOLLOWUP":
        raise TaskScopeClosureError("in-scope work cannot be converted into a follow-up handoff")
    handoff = {
        "schema": FOLLOWUP_SCHEMA,
        "policy_id": POLICY_ID,
        "origin_task_id": checked["task_id"],
        "origin_root_task_id": checked["root_task_id"],
        "origin_goal_id": bound["goal_id"],
        "origin_goal_revision": bound["goal_revision"],
        "origin_goal_digest": bound["goal_digest"],
        "origin_scope_digest": bound["scope_digest"],
        "scope_item": _required(scope_item, "scope_item"),
        "scope_classification_reason": classification["reason"],
        "discovered_issue": _required(discovered_issue, "discovered_issue"),
        "why_out_of_scope": _required(why_out_of_scope, "why_out_of_scope"),
        "current_state": _required(current_state, "current_state"),
        "evidence_refs": _string_list(evidence_refs, "evidence_refs"),
        "suggested_new_task_objective": _required(suggested_new_task_objective, "suggested_new_task_objective"),
        "suggested_new_conversation_start": _required(
            suggested_new_conversation_start, "suggested_new_conversation_start"
        ),
        "requires_new_task_id": True,
        "requires_user_start": True,
        "automatic_start": False,
        "execution_performed": False,
        "authority": False,
    }
    handoff["handoff_id"] = "followup:" + _digest(handoff)[:24]
    result = copy.deepcopy(checked)
    if any(isinstance(x, dict) and x.get("handoff_id") == handoff["handoff_id"] for x in result["followup_handoffs"]):
        raise TaskScopeClosureError("duplicate follow-up handoff")
    result["followup_handoffs"].append(handoff)
    _bump_revision(result)
    return validate_task_control(result, expected_binding=bound)


def close_task_control(
    control: dict[str, Any],
    internal_terminal_state: str,
    *,
    verification_evidence: dict[str, Any] | None = None,
    human_action: str | None = None,
) -> dict[str, Any]:
    checked = assert_execution_allowed(control)
    if internal_terminal_state not in _INTERNAL_TERMINAL:
        raise TaskScopeClosureError("unsupported internal terminal state")
    result = copy.deepcopy(checked)
    before_revision = result["control_revision"]
    result["internal_terminal_state"] = internal_terminal_state
    result["execution_frozen"] = True
    result["automatic_retry_allowed"] = False
    result["automatic_replan_allowed"] = False
    result["alternative_route_allowed"] = False
    if internal_terminal_state == "VERIFIED":
        result["verification_evidence"] = _validate_verification_evidence(
            verification_evidence,
            task_id=result["task_id"],
            control_revision_before_close=before_revision,
        )
        result["state"] = CLOSED
        result["user_closure_state"] = NEW_TASK_DISCOVERED if result["followup_handoffs"] else DONE
    else:
        if verification_evidence is not None:
            raise TaskScopeClosureError("verification evidence cannot close a non-VERIFIED task")
        result["verification_evidence"] = None
        result["state"] = HUMAN_INTERVENTION_REQUIRED
        result["user_closure_state"] = HUMAN_INTERVENTION_REQUIRED
        result["human_action_required"] = (
            human_action.strip()
            if isinstance(human_action, str) and human_action.strip()
            else f"Review terminal state {internal_terminal_state} and explicitly decide whether and how to continue."
        )
        result["stop_reason"] = f"INTERNAL_{internal_terminal_state}"
    _bump_revision(result)
    return validate_task_control(result)
