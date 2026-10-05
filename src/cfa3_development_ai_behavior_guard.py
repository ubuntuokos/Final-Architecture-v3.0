"""Shared CFA3 development/AI execution-discipline guard.

This module is authority-neutral. It evaluates the canonical behavior policy and
returns a fail-closed preflight decision. It does not authorize Security
Governance effects, UAF execution, HRB resources, model/provider routing,
evidence promotion, or durable workflow transitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


MUTATING_ACTIONS = {
    "WRITE", "COMMIT", "PUSH", "PR", "WORKFLOW", "GATE",
    "MERGE", "RELEASE", "EXTERNAL_ACTION",
}

SIDE_EFFECT_ORDER = (
    "READ", "ANALYZE", "PLAN", "WRITE", "COMMIT", "PUSH",
    "PR", "WORKFLOW", "GATE", "MERGE", "RELEASE", "EXTERNAL_ACTION",
)

RULE_IDS = {
    "DEV-01", "DEV-02", "DEV-03", "DEV-04", "DEV-05",
    "DEV-06", "DEV-07", "DEV-08", "DEV-09", "DEV-10", "DEV-11", "DEV-12",
    "AI-01", "AI-02", "AI-03", "AI-04", "AI-05",
    "AI-06", "AI-07", "AI-08", "AI-09", "AI-10", "AI-11",
}

_BASE_BOOL_FACTS = (
    "current_owner_restriction_allows",
    "scope_bound",
    "scope_allows_action",
    "uncertain_state",
    "autonomous_workaround",
    "silent_redesign_or_repair",
)
_MUTATION_BOOL_FACTS = ("fresh_state_verified", "mutation_report_pending")
_WORKFLOW_BOOL_FACTS = ("workflow_or_gate_required_for_closure", "equivalent_run_active")
_MERGE_BOOL_FACTS = ("exact_head_match", "exact_base_match")

_SELF_CORRECTION_REQUIRED_TRUE = (
    "error_caused_by_ai",
    "mechanical_or_technical",
    "correction_deterministic",
    "user_intent_preserved",
    "scope_preserved",
    "architecture_authority_policy_plan_preserved",
    "no_new_component_workaround",
    "notification_sent",
    "existing_authorization_covers_corrected_action",
)
_SELF_CORRECTION_REQUIRED_FALSE = (
    "blocker_gate_or_security_bypass",
    "unnecessary_workflow_gate_or_side_effect",
    "redesign_required",
    "alternative_technical_solution",
    "new_pr_or_branch_required",
    "other_component_modification_required",
    "user_restriction_weakened",
    "review_discovered_real_design_or_implementation_defect",
    "new_permission_or_side_effect_required",
    "correction_uncertain",
)


@dataclass(frozen=True)
class OwnerOverride:
    rule_ids: frozenset[str] = field(default_factory=frozenset)
    conversation_bound: bool = False
    explicit: bool = False
    scope_matches: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "OwnerOverride":
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise ValueError("owner_override must be an object")
        rule_ids = value.get("rule_ids")
        if not isinstance(rule_ids, list) or any(not isinstance(x, str) for x in rule_ids):
            raise ValueError("owner_override.rule_ids must be a string list")
        if len(rule_ids) != len(set(rule_ids)) or any(x not in RULE_IDS for x in rule_ids):
            raise ValueError("owner_override.rule_ids contains duplicate or unknown rule")
        for key in ("conversation_bound", "explicit", "scope_matches"):
            if value.get(key) is not True and value.get(key) is not False:
                raise ValueError(f"owner_override.{key} must be boolean")
        return cls(
            rule_ids=frozenset(rule_ids),
            conversation_bound=value["conversation_bound"],
            explicit=value["explicit"],
            scope_matches=value["scope_matches"],
        )

    def permits(self, rule_id: str) -> bool:
        return (
            rule_id in self.rule_ids
            and self.conversation_bound is True
            and self.explicit is True
            and self.scope_matches is True
        )


def _stop(rule_ids: Iterable[str], reason: str, *, blocker: bool = True) -> dict:
    return {
        "decision": "STOP",
        "blocker": blocker,
        "reason": reason,
        "rule_ids": sorted(set(rule_ids)),
        "policy_preflight_passed": False,
        "side_effect_authorized": False,
    }


def _allow(action: str, applied_overrides: set[str]) -> dict:
    return {
        "decision": "ALLOW",
        "blocker": False,
        "reason": "POLICY_PREFLIGHT_PASS",
        "rule_ids": [],
        "action": action,
        "applied_owner_overrides": sorted(applied_overrides),
        "policy_preflight_passed": True,
        "side_effect_authorized": False,
        "effect_authority_required": action in MUTATING_ACTIONS,
    }


def _validate_bool_facts(context: Mapping[str, Any], names: Iterable[str]) -> str | None:
    for name in names:
        if name not in context:
            return f"MISSING_REQUIRED_FACT:{name}"
        value = context[name]
        if value is not True and value is not False:
            return f"INVALID_REQUIRED_BOOLEAN_FACT:{name}"
    return None


def _validate_context(context: Mapping[str, Any], action: str) -> str | None:
    problem = _validate_bool_facts(context, _BASE_BOOL_FACTS)
    if problem:
        return problem
    if "blocker_kind" not in context:
        return "MISSING_REQUIRED_FACT:blocker_kind"
    blocker_kind = context["blocker_kind"]
    if blocker_kind is not None and (not isinstance(blocker_kind, str) or not blocker_kind.strip()):
        return "INVALID_BLOCKER_KIND"
    if action in MUTATING_ACTIONS:
        problem = _validate_bool_facts(context, _MUTATION_BOOL_FACTS)
        if problem:
            return problem
        if "side_effect_permission" not in context or not isinstance(context["side_effect_permission"], str):
            return "MISSING_OR_INVALID_SIDE_EFFECT_PERMISSION"
    if action in {"WORKFLOW", "GATE"}:
        problem = _validate_bool_facts(context, _WORKFLOW_BOOL_FACTS)
        if problem:
            return problem
    if action == "MERGE":
        problem = _validate_bool_facts(context, _MERGE_BOOL_FACTS)
        if problem:
            return problem
    return None


def _self_correction_check(context: Mapping[str, Any]) -> dict | None:
    correction = context.get("self_correction")
    if correction is None:
        return None
    if not isinstance(correction, Mapping):
        return _stop({"DEV-11", "AI-11"}, "SELF_CORRECTION_CONTEXT_MUST_BE_MAPPING")
    required_bool_fields = (
        ("requested",)
        + _SELF_CORRECTION_REQUIRED_TRUE
        + _SELF_CORRECTION_REQUIRED_FALSE
        + ("partial_mutation_possible", "exact_state_verified")
    )
    problem = _validate_bool_facts(correction, required_bool_fields)
    if problem:
        return _stop({"DEV-11", "AI-11"}, "SELF_CORRECTION_" + problem)
    if correction["requested"] is not True:
        return _stop({"DEV-11", "AI-11"}, "SELF_CORRECTION_REQUEST_NOT_ACTIVE")
    missing_true = [name for name in _SELF_CORRECTION_REQUIRED_TRUE if correction[name] is not True]
    if missing_true:
        return _stop(
            {"DEV-11", "AI-11"},
            "SELF_CORRECTION_MANDATORY_CONDITION_FAILED:" + ",".join(sorted(missing_true)),
        )
    violated = [name for name in _SELF_CORRECTION_REQUIRED_FALSE if correction[name] is not False]
    if violated:
        return _stop(
            {"DEV-11", "AI-11"},
            "SELF_CORRECTION_FORBIDDEN_CONDITION:" + ",".join(sorted(violated)),
        )
    if correction["partial_mutation_possible"] is True and correction["exact_state_verified"] is not True:
        return _stop(
            {"DEV-11", "AI-11", "AI-08"},
            "SELF_CORRECTION_EXACT_STATE_REQUIRED_AFTER_POSSIBLE_PARTIAL_MUTATION",
        )
    return {
        "decision": "ALLOW",
        "blocker": False,
        "reason": "SELF_CORRECTION_EXCEPTION_CONDITIONS_PASS",
        "rule_ids": ["AI-11", "DEV-11"],
        "policy_preflight_passed": True,
        "side_effect_authorized": False,
        "self_correction_authorized": True,
        "post_correction_report_required": True,
        "post_correction_report_fields": [
            "OWN_ERROR",
            "CORRECTION",
            "STATE_CHANGE",
            "CURRENT_HEAD_SHA_OR_RELEVANT_STATE",
            "REMAINING_BLOCKER",
        ],
    }


_DEVELOPMENT_DIVERSION_TRIGGERS = frozenset({
    "NEW_RULE",
    "PARALLEL_TASK",
    "PARALLEL_PR",
    "MONITORING_OBLIGATION",
    "OTHER",
})
_DEVELOPMENT_TASK_BOOL_FACTS = (
    "action_serves_main_task",
    "task_switch_requested",
    "explicit_owner_task_switch",
)


def authorize_development_task_continuity(context: Mapping[str, Any]) -> dict:
    """Enforce DEV-12 for FA3/CFA3 development task continuity.

    New rules and parallel work may constrain or block the active main task,
    but they cannot silently become the main task. This preflight does not
    authorize repository side effects.
    """
    if not isinstance(context, Mapping):
        return _stop({"DEV-12", "AI-09"}, "DEVELOPMENT_TASK_CONTINUITY_CONTEXT_MUST_BE_MAPPING")
    for key in ("main_task_id", "current_task_id"):
        value = context.get(key)
        if not isinstance(value, str) or not value.strip():
            return _stop({"DEV-12", "AI-09"}, f"MISSING_OR_INVALID_DEVELOPMENT_TASK_ID:{key}")
    problem = _validate_bool_facts(context, _DEVELOPMENT_TASK_BOOL_FACTS)
    if problem:
        return _stop({"DEV-12", "AI-09"}, "DEVELOPMENT_TASK_CONTINUITY_" + problem)
    trigger = context.get("diversion_trigger")
    if trigger is not None and trigger not in _DEVELOPMENT_DIVERSION_TRIGGERS:
        return _stop({"DEV-12", "AI-09"}, "INVALID_DEVELOPMENT_DIVERSION_TRIGGER")

    if context["task_switch_requested"] is True:
        if context["explicit_owner_task_switch"] is not True:
            return _stop({"DEV-12"}, "MAIN_TASK_SWITCH_REQUIRES_EXPLICIT_CURRENT_OWNER_DIRECTIVE")
        return {
            "decision": "ALLOW",
            "blocker": False,
            "reason": "EXPLICIT_CURRENT_OWNER_MAIN_TASK_SWITCH_AUTHORIZED",
            "rule_ids": ["DEV-12"],
            "policy_preflight_passed": True,
            "side_effect_authorized": False,
            "main_task_switch_authorized": True,
            "requires_main_task_rebind_before_execution": True,
        }

    if context["current_task_id"] != context["main_task_id"]:
        return _stop({"DEV-12"}, "CURRENT_TASK_DIFFERS_FROM_BOUND_MAIN_TASK")
    if context["action_serves_main_task"] is not True:
        return _stop({"DEV-12"}, "ACTION_WOULD_DIVERT_FROM_BOUND_MAIN_TASK")

    disposition = (
        "ACTIVE_MAIN_TASK_CONSTRAINT"
        if trigger == "NEW_RULE"
        else "ACTIVE_MAIN_TASK_OBSERVATION_OR_DEPENDENCY"
        if trigger in {"PARALLEL_TASK", "PARALLEL_PR", "MONITORING_OBLIGATION"}
        else "ACTIVE_MAIN_TASK_STEP"
    )
    return {
        "decision": "ALLOW",
        "blocker": False,
        "reason": "MAIN_TASK_CONTINUITY_PASS",
        "rule_ids": ["DEV-12"],
        "policy_preflight_passed": True,
        "side_effect_authorized": False,
        "main_task_preserved": True,
        "main_task_id": context["main_task_id"],
        "diversion_trigger": trigger,
        "disposition": disposition,
    }


def _override_allows(override: OwnerOverride, rule_ids: Iterable[str]) -> bool:
    return all(override.permits(rule_id) for rule_id in rule_ids)


def authorize_action(context: Mapping[str, Any]) -> dict:
    """Evaluate one action against the shared CFA3 execution discipline.

    Missing or malformed live facts fail closed. ALLOW means only that this
    policy preflight passed; it never grants effect authority.
    """
    if not isinstance(context, Mapping):
        return _stop({"AI-09"}, "CONTEXT_MUST_BE_MAPPING")
    action = str(context.get("action", "")).upper()
    if action not in SIDE_EFFECT_ORDER:
        return _stop({"AI-06", "AI-09"}, "UNKNOWN_OR_MISSING_ACTION")
    problem = _validate_context(context, action)
    if problem:
        return _stop({"AI-09"}, problem)
    try:
        override = OwnerOverride.from_mapping(context.get("owner_override"))
    except ValueError as exc:
        return _stop({"AI-09"}, f"INVALID_OWNER_OVERRIDE:{exc}")
    applied_overrides: set[str] = set()

    if context["current_owner_restriction_allows"] is not True:
        return _stop({"DEV-10", "AI-10"}, "CURRENT_OWNER_RESTRICTION_DENIES_ACTION")

    if context["scope_bound"] is not True or context["scope_allows_action"] is not True:
        needed = {"DEV-03", "AI-03"}
        if not _override_allows(override, needed):
            return _stop(needed, "TASK_SCOPE_NOT_BOUND_OR_ACTION_OUT_OF_SCOPE")
        applied_overrides.update(needed)

    if context["uncertain_state"] is True:
        needed = {"AI-09"}
        if not _override_allows(override, needed):
            return _stop(needed, "UNCERTAIN_STATE_FAILS_CLOSED")
        applied_overrides.update(needed)

    blocker_kind = context["blocker_kind"]
    if blocker_kind:
        needed = {"DEV-05", "AI-01"} if blocker_kind == "OVERLAP" else {"DEV-01", "AI-01"}
        if not _override_allows(override, needed):
            return _stop(needed, f"BLOCKER:{blocker_kind}")
        applied_overrides.update(needed)

    if context["autonomous_workaround"] is True:
        needed = {"DEV-02", "AI-02"}
        if not _override_allows(override, needed):
            return _stop(needed, "AUTONOMOUS_WORKAROUND_FORBIDDEN")
        applied_overrides.update(needed)

    self_correction = _self_correction_check(context)
    if self_correction is not None and self_correction.get("decision") != "ALLOW":
        return self_correction

    if action in MUTATING_ACTIONS:
        if context["fresh_state_verified"] is not True:
            needed = {"DEV-04", "AI-04"}
            if not _override_allows(override, needed):
                return _stop(needed, "FRESH_STATE_REQUIRED_BEFORE_MUTATION")
            applied_overrides.update(needed)
        if context["mutation_report_pending"] is True:
            needed = {"DEV-07", "AI-07"}
            if not _override_allows(override, needed):
                return _stop(needed, "PREVIOUS_MUTATION_REPORT_REQUIRED")
            applied_overrides.update(needed)
        if context["side_effect_permission"] != action:
            needed = {"AI-06"}
            if not _override_allows(override, needed):
                return _stop(needed, "EXACT_SIDE_EFFECT_PERMISSION_REQUIRED")
            applied_overrides.update(needed)

    if action in {"WORKFLOW", "GATE"}:
        if context["workflow_or_gate_required_for_closure"] is not True:
            needed = {"DEV-06"}
            if not _override_allows(override, needed):
                return _stop(needed, "WORKFLOW_OR_GATE_NOT_REQUIRED_FOR_CLOSURE")
            applied_overrides.update(needed)
        if context["equivalent_run_active"] is True:
            needed = {"DEV-06"}
            if not _override_allows(override, needed):
                return _stop(needed, "EQUIVALENT_WORKFLOW_OR_GATE_ALREADY_ACTIVE")
            applied_overrides.update(needed)

    if action == "MERGE":
        if context["exact_head_match"] is not True or context["exact_base_match"] is not True:
            needed = {"DEV-08", "AI-08"}
            if not _override_allows(override, needed):
                return _stop(needed, "EXACT_HEAD_OR_BASE_MISMATCH")
            applied_overrides.update(needed)

    if context["silent_redesign_or_repair"] is True:
        needed = {"DEV-09"}
        if not _override_allows(override, needed):
            return _stop(needed, "SILENT_REDESIGN_OR_REPAIR_FORBIDDEN")
        applied_overrides.update(needed)

    result = _allow(action, applied_overrides)
    if self_correction is not None:
        result["self_correction_authorized"] = True
        result["post_correction_report_required"] = True
        result["post_correction_report_fields"] = self_correction["post_correction_report_fields"]
        result["reason"] = "POLICY_PREFLIGHT_PASS_WITH_SELF_CORRECTION_EXCEPTION"
    return result
