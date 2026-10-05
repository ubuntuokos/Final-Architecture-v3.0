"""Shared CFA3 development/AI execution-discipline guard.

This module is deliberately authority-neutral: it evaluates the canonical policy
and returns a fail-closed decision. Callers retain their existing architectural
authorities; this module does not route models, schedule work, authorize
security-sensitive effects, or create resource leases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Any


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
    "DEV-06", "DEV-07", "DEV-08", "DEV-09", "DEV-10", "DEV-11",
    "AI-01", "AI-02", "AI-03", "AI-04", "AI-05",
    "AI-06", "AI-07", "AI-08", "AI-09", "AI-10", "AI-11",
}


@dataclass(frozen=True)
class OwnerOverride:
    rule_ids: frozenset[str] = field(default_factory=frozenset)
    conversation_bound: bool = False
    explicit: bool = False
    scope_matches: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "OwnerOverride":
        if not value:
            return cls()
        return cls(
            rule_ids=frozenset(value.get("rule_ids", ())),
            conversation_bound=bool(value.get("conversation_bound", False)),
            explicit=bool(value.get("explicit", False)),
            scope_matches=bool(value.get("scope_matches", False)),
        )

    def permits(self, rule_id: str) -> bool:
        return (
            rule_id in RULE_IDS
            and rule_id in self.rule_ids
            and self.conversation_bound
            and self.explicit
            and self.scope_matches
        )


def _stop(rule_ids: Iterable[str], reason: str, *, blocker: bool = True) -> dict:
    return {
        "decision": "STOP",
        "blocker": blocker,
        "reason": reason,
        "rule_ids": sorted(set(rule_ids)),
        "side_effect_authorized": False,
    }


def _allow(action: str, override: OwnerOverride) -> dict:
    return {
        "decision": "ALLOW",
        "blocker": False,
        "reason": "POLICY_PREFLIGHT_PASS",
        "rule_ids": [],
        "action": action,
        "applied_owner_overrides": sorted(override.rule_ids),
        "side_effect_authorized": action in MUTATING_ACTIONS,
    }


def _self_correction_check(context: Mapping[str, Any]) -> dict | None:
    correction = context.get("self_correction")
    if not correction:
        return None
    if correction.get("requested") is not True:
        return _stop({"DEV-11", "AI-11"}, "SELF_CORRECTION_REQUEST_NOT_EXPLICIT_IN_CONTEXT")

    required_true = (
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
    missing = [name for name in required_true if correction.get(name) is not True]
    if missing:
        return _stop(
            {"DEV-11", "AI-11"},
            "SELF_CORRECTION_MANDATORY_CONDITION_FAILED:" + ",".join(sorted(missing)),
        )

    forbidden_true = (
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
    violated = [name for name in forbidden_true if correction.get(name) is True]
    if violated:
        return _stop(
            {"DEV-11", "AI-11"},
            "SELF_CORRECTION_FORBIDDEN_CONDITION:" + ",".join(sorted(violated)),
        )

    if correction.get("partial_mutation_possible") is True and correction.get("exact_state_verified") is not True:
        return _stop(
            {"DEV-11", "AI-11", "AI-08"},
            "SELF_CORRECTION_EXACT_STATE_REQUIRED_AFTER_POSSIBLE_PARTIAL_MUTATION",
        )

    return {
        "decision": "ALLOW",
        "blocker": False,
        "reason": "SELF_CORRECTION_EXCEPTION_CONDITIONS_PASS",
        "rule_ids": ["AI-11", "DEV-11"],
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


def authorize_action(context: Mapping[str, Any]) -> dict:
    """Evaluate one planned action against the shared CFA3 discipline.

    Required caller-provided facts are explicit by design. Unknown facts fail
    closed rather than being guessed from conversation history or cached state.
    """

    action = str(context.get("action", "")).upper()
    if action not in SIDE_EFFECT_ORDER:
        return _stop({"AI-06", "AI-09"}, "UNKNOWN_OR_MISSING_ACTION")

    override = OwnerOverride.from_mapping(context.get("owner_override"))

    if context.get("current_owner_restriction_allows") is not True:
        if not (override.permits("DEV-10") and override.permits("AI-10")):
            return _stop({"DEV-10", "AI-10"}, "CURRENT_OWNER_RESTRICTION_DENIES_ACTION")

    if context.get("scope_bound") is not True or context.get("scope_allows_action") is not True:
        if not (override.permits("DEV-03") and override.permits("AI-03")):
            return _stop({"DEV-03", "AI-03"}, "TASK_SCOPE_NOT_BOUND_OR_ACTION_OUT_OF_SCOPE")

    if bool(context.get("uncertain_state")):
        if not override.permits("AI-09"):
            return _stop({"AI-09"}, "UNCERTAIN_STATE_FAILS_CLOSED")

    blocker_kind = context.get("blocker_kind")
    if blocker_kind:
        specific_rule = "DEV-05" if blocker_kind == "OVERLAP" else "DEV-01"
        if not (override.permits(specific_rule) and override.permits("AI-01")):
            return _stop({specific_rule, "AI-01"}, f"BLOCKER:{blocker_kind}")

    self_correction = _self_correction_check(context)
    if self_correction is not None and self_correction.get("decision") != "ALLOW":
        return self_correction

    if bool(context.get("autonomous_workaround")):
        if not (override.permits("DEV-02") and override.permits("AI-02")):
            return _stop({"DEV-02", "AI-02"}, "AUTONOMOUS_WORKAROUND_FORBIDDEN")

    if action in MUTATING_ACTIONS:
        if context.get("fresh_state_verified") is not True:
            if not (override.permits("DEV-04") and override.permits("AI-04")):
                return _stop({"DEV-04", "AI-04"}, "FRESH_STATE_REQUIRED_BEFORE_MUTATION")

        if bool(context.get("mutation_report_pending")):
            if not (override.permits("DEV-07") and override.permits("AI-07")):
                return _stop({"DEV-07", "AI-07"}, "PREVIOUS_MUTATION_REPORT_REQUIRED")

        if context.get("side_effect_permission") != action:
            if not override.permits("AI-06"):
                return _stop({"AI-06"}, "EXACT_SIDE_EFFECT_PERMISSION_REQUIRED")

    if action in {"WORKFLOW", "GATE"}:
        if context.get("workflow_or_gate_required_for_closure") is not True:
            if not override.permits("DEV-06"):
                return _stop({"DEV-06"}, "WORKFLOW_OR_GATE_NOT_REQUIRED_FOR_CLOSURE")
        if bool(context.get("equivalent_run_active")):
            if not override.permits("DEV-06"):
                return _stop({"DEV-06"}, "EQUIVALENT_WORKFLOW_OR_GATE_ALREADY_ACTIVE")

    if action == "MERGE":
        if context.get("exact_head_match") is not True or context.get("exact_base_match") is not True:
            if not (override.permits("DEV-08") and override.permits("AI-08")):
                return _stop({"DEV-08", "AI-08"}, "EXACT_HEAD_OR_BASE_MISMATCH")

    if bool(context.get("silent_redesign_or_repair")):
        if not override.permits("DEV-09"):
            return _stop({"DEV-09"}, "SILENT_REDESIGN_OR_REPAIR_FORBIDDEN")

    result = _allow(action, override)
    if self_correction is not None:
        result["self_correction_authorized"] = True
        result["post_correction_report_required"] = True
        result["post_correction_report_fields"] = self_correction["post_correction_report_fields"]
        result["reason"] = "POLICY_PREFLIGHT_PASS_WITH_SELF_CORRECTION_EXCEPTION"
    return result
