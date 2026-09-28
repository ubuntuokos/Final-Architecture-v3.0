#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from fa3_decision_fabric import Candidate, DecisionError, DecisionFabric, DecisionRequest, ProviderResult

MAX_OPTIONS = 255
RISKS = {"read", "write", "destructive"}
FINISH = "__finish__"
ESCALATE = "__escalate__"
NEXT_ACTION = "next_action"
GOAL_REACHED = "goal_reached"
DEFAULT_THRESHOLDS = {
    "read": 0.5,
    "write": 0.6,
    "destructive": 0.8,
    "finish": 0.5,
}


class SystemOneSpecError(DecisionError):
    pass


@dataclass(frozen=True)
class CompiledSystemOneStep:
    questions: dict[str, Any]
    feasible: tuple[str, ...]
    omitted: dict[str, str]
    parameter_keys: dict[str, dict[str, str]]
    stated_keys: dict[str, dict[str, str]]
    truncated: dict[str, int]
    thresholds: dict[str, float]
    allow_finish: bool
    allow_escalate: bool

    @property
    def questions_sha256(self) -> str:
        payload = json.dumps(
            self.questions,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()


def _as_choice_map(value: Any, *, label: str) -> dict[str, str]:
    if isinstance(value, list):
        value = {str(item): str(item) for item in value}
    if not isinstance(value, dict) or not value:
        raise SystemOneSpecError(f"{label} requires a non-empty finite choice set")
    out = {str(k): str(v) for k, v in value.items()}
    if len(out) > MAX_OPTIONS:
        raise SystemOneSpecError(f"{label} declares more than {MAX_OPTIONS} values")
    return out


def _thresholds(constraints: dict[str, Any]) -> dict[str, float]:
    out = dict(DEFAULT_THRESHOLDS)
    raw = constraints.get("confidence_thresholds", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise SystemOneSpecError("confidence_thresholds must be an object")
    for key, value in raw.items():
        if key not in out:
            raise SystemOneSpecError(f"unknown confidence threshold class: {key}")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SystemOneSpecError(f"confidence threshold {key} must be numeric")
        value = float(value)
        if not 0.0 <= value <= 1.0:
            raise SystemOneSpecError(f"confidence threshold {key} must be within 0..1")
        out[key] = value
    return out


def _param_question(
    action_id: str,
    param_name: str,
    spec: dict[str, Any],
    parameter_candidates: dict[str, Any],
    truncated: dict[str, int],
) -> tuple[dict[str, Any], str | None]:
    if not isinstance(spec, dict):
        raise SystemOneSpecError(f"parameter {action_id}.{param_name} must be an object")
    kind = spec.get("kind")
    instructions = str(spec.get("instructions") or f"Choose {param_name} for {action_id}.")
    if kind == "choices":
        return {
            "type": "choice",
            "instructions": instructions,
            "criteria": _as_choice_map(spec.get("choices"), label=f"{action_id}.{param_name}"),
        }, None
    if kind == "candidates":
        source = spec.get("source")
        if not isinstance(source, str) or not source:
            raise SystemOneSpecError(f"{action_id}.{param_name} candidates require source")
        raw = parameter_candidates.get(source)
        if not raw:
            return {}, f"no pre-authorized candidates for {param_name!r}"
        choices = raw if isinstance(raw, dict) else {str(v): str(v) for v in raw}
        if not isinstance(choices, dict):
            raise SystemOneSpecError(f"parameter candidate source {source!r} must be list/object")
        normalized = {str(k): str(v) for k, v in choices.items()}
        key = f"{action_id}__{param_name}"
        if len(normalized) > MAX_OPTIONS:
            truncated[key] = len(normalized) - MAX_OPTIONS
            normalized = dict(list(normalized.items())[:MAX_OPTIONS])
        return {"type": "choice", "instructions": instructions, "criteria": normalized}, None
    if kind == "flag":
        return {"type": "noul", "instructions": instructions}, None
    if kind == "levels":
        levels = spec.get("levels")
        if not isinstance(levels, list) or not 2 <= len(levels) <= 10:
            raise SystemOneSpecError(f"{action_id}.{param_name} levels require 2..10 values")
        if any(not isinstance(x, str) or not x for x in levels):
            raise SystemOneSpecError(f"{action_id}.{param_name} levels must be non-empty strings")
        return {"type": "score", "instructions": instructions, "criteria": list(levels)}, None
    raise SystemOneSpecError(
        f"{action_id}.{param_name} would require free text; "
        "only choices, candidates, flag, and levels are allowed"
    )


def compile_system_one_step(request: DecisionRequest) -> CompiledSystemOneStep:
    if request.contract != "BOUNDED_ACTION":
        raise SystemOneSpecError("System One action compiler requires BOUNDED_ACTION")
    constraints = request.constraints
    parameter_candidates = constraints.get("parameter_candidates", {})
    if parameter_candidates is None:
        parameter_candidates = {}
    if not isinstance(parameter_candidates, dict):
        raise SystemOneSpecError("parameter_candidates must be an object")

    allow_finish = bool(constraints.get("allow_finish", True))
    allow_escalate = bool(constraints.get("allow_escalate", True))
    reserved = int(allow_finish) + int(allow_escalate)
    if len(request.candidates) + reserved > MAX_OPTIONS:
        raise SystemOneSpecError("next action choice exceeds System One option ceiling")

    questions: dict[str, Any] = {}
    parameter_keys: dict[str, dict[str, str]] = {}
    stated_keys: dict[str, dict[str, str]] = {}
    omitted: dict[str, str] = {}
    truncated: dict[str, int] = {}
    feasible: list[str] = []

    for candidate in request.candidates:
        metadata = candidate.metadata
        risk = str(metadata.get("risk", "write"))
        if risk not in RISKS:
            raise SystemOneSpecError(f"action {candidate.id!r} has invalid risk {risk!r}")
        raw_params = metadata.get("parameters", {})
        if raw_params is None:
            raw_params = {}
        if not isinstance(raw_params, dict):
            raise SystemOneSpecError(f"action {candidate.id!r} parameters must be an object")

        local_questions: dict[str, Any] = {}
        local_keys: dict[str, str] = {}
        local_stated: dict[str, str] = {}
        omit_reason: str | None = None

        for param_name, param_spec in raw_params.items():
            if not isinstance(param_name, str) or not param_name or "__" in param_name:
                raise SystemOneSpecError(f"invalid parameter name for action {candidate.id!r}")
            key = f"{candidate.id}__{param_name}"
            question, omit_reason = _param_question(
                candidate.id,
                param_name,
                param_spec,
                parameter_candidates,
                truncated,
            )
            if omit_reason:
                break
            local_questions[key] = question
            local_keys[param_name] = key
            if bool(param_spec.get("optional", False)):
                stated_key = f"{key}__stated"
                local_questions[stated_key] = {
                    "type": "noul",
                    "instructions": (
                        f"Does the goal or bounded observation specify {param_name} "
                        f"for action {candidate.id!r}?"
                    ),
                }
                local_stated[param_name] = stated_key

        if omit_reason:
            omitted[candidate.id] = omit_reason
            continue

        feasible.append(candidate.id)
        questions.update(local_questions)
        parameter_keys[candidate.id] = local_keys
        stated_keys[candidate.id] = local_stated

    criteria = {
        candidate.id: candidate.description or candidate.id
        for candidate in request.candidates
        if candidate.id in feasible
    }
    if allow_finish:
        criteria[FINISH] = "The goal is already achieved; propose stopping the reflex loop."
    if allow_escalate:
        criteria[ESCALATE] = "No offered action safely fits; request a System Two or human handoff."
    if not criteria:
        raise SystemOneSpecError("no feasible bounded action or terminal choice")

    questions = {
        NEXT_ACTION: {
            "type": "choice",
            "instructions": (
                "Choose one offered next action. Never invent an action or value. "
                "Choose finish only when the bounded state shows the goal is achieved."
            ),
            "criteria": criteria,
        },
        GOAL_REACHED: {
            "type": "noul",
            "instructions": "Is the stated goal already fully achieved in the bounded state?",
        },
        **questions,
    }
    return CompiledSystemOneStep(
        questions=questions,
        feasible=tuple(feasible),
        omitted=omitted,
        parameter_keys=parameter_keys,
        stated_keys=stated_keys,
        truncated=truncated,
        thresholds=_thresholds(constraints),
        allow_finish=allow_finish,
        allow_escalate=allow_escalate,
    )


def _number(value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 0.0
    return min(max(float(value), 0.0), 1.0)


def _choice(answer: dict[str, Any], question: dict[str, Any]) -> tuple[str, float]:
    value = answer.get("choice")
    criteria = question.get("criteria", {})
    if not isinstance(value, str) or value not in criteria:
        raise SystemOneSpecError("model selected a value outside the compiled finite set")
    probabilities = answer.get("probabilities", {})
    probability = None
    if isinstance(probabilities, dict):
        probability = probabilities.get(value)
    if not isinstance(probability, (int, float)):
        probability = answer.get("confidence")
    return value, _number(probability)


def _param_value(answer: dict[str, Any], question: dict[str, Any]) -> tuple[Any, float]:
    qtype = question.get("type")
    if qtype == "choice":
        return _choice(answer, question)
    if qtype == "noul":
        p = _number(answer.get("noul"))
        return p >= 0.5, max(p, 1.0 - p)
    if qtype == "score":
        probabilities = answer.get("probabilities", {})
        criteria = question.get("criteria", [])
        if not isinstance(probabilities, dict) or not probabilities:
            raise SystemOneSpecError("score answer requires per-level probabilities")
        best_key = max(probabilities, key=lambda key: _number(probabilities[key]))
        try:
            index = int(best_key)
        except (TypeError, ValueError):
            if best_key in criteria:
                return best_key, _number(probabilities[best_key])
            raise SystemOneSpecError("score answer legend/index is invalid")
        if not 0 <= index < len(criteria):
            raise SystemOneSpecError("score answer index is outside compiled levels")
        return criteria[index], _number(probabilities[best_key])
    raise SystemOneSpecError(f"unsupported compiled question type: {qtype!r}")


def _state_digest(state: Any) -> str:
    payload = json.dumps(
        state,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def evaluate_system_one_answers(
    request: DecisionRequest,
    compiled: CompiledSystemOneStep,
    answers: dict[str, Any],
) -> ProviderResult:
    if not isinstance(answers, dict):
        raise SystemOneSpecError("System One response answers must be an object")
    next_answer = answers.get(NEXT_ACTION)
    if not isinstance(next_answer, dict):
        raise SystemOneSpecError("System One response missing next_action")
    action, action_probability = _choice(next_answer, compiled.questions[NEXT_ACTION])
    next_probabilities = next_answer.get("probabilities", {})
    score_map = {
        str(k): _number(v)
        for k, v in next_probabilities.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    } if isinstance(next_probabilities, dict) else {}

    base_meta = {
        "system_one": True,
        "questions_sha256": compiled.questions_sha256,
        "state_sha256": _state_digest(request.state),
        "feasible_actions": list(compiled.feasible),
        "omitted_actions": dict(compiled.omitted),
        "truncated_candidates": dict(compiled.truncated),
        "execution_performed": False,
        "authorization_granted": False,
        "confidence_is_authorization": False,
    }

    if action == ESCALATE:
        if not compiled.allow_escalate:
            raise SystemOneSpecError("escalate was not offered")
        base_meta["handoff"] = {
            "reason": "escalation_requested",
            "proposed_action": None,
            "weakest": action_probability,
            "threshold": None,
            "target_classes": ["SYSTEM_TWO", "HUMAN"],
        }
        return ProviderResult("HUMAN_CONFIRM", {"terminal": "ESCALATE"}, action_probability, score_map, base_meta)

    if action == FINISH:
        if not compiled.allow_finish:
            raise SystemOneSpecError("finish was not offered")
        goal_answer = answers.get(GOAL_REACHED, {})
        goal_probability = _number(goal_answer.get("noul")) if isinstance(goal_answer, dict) else 0.0
        threshold = compiled.thresholds["finish"]
        weakest = min(action_probability, goal_probability)
        if weakest < threshold:
            base_meta["handoff"] = {
                "reason": "finish_not_confident",
                "proposed_action": FINISH,
                "weakest": weakest,
                "threshold": threshold,
                "target_classes": ["SYSTEM_TWO", "HUMAN"],
            }
            return ProviderResult("NO_DECISION", {"terminal": "FINISH_REFUSED"}, weakest, score_map, base_meta)
        return ProviderResult(
            "DECIDED",
            {
                "terminal": "FINISH",
                "gate": {"risk": "finish", "threshold": threshold, "weakest": weakest},
            },
            weakest,
            score_map,
            base_meta,
        )

    candidate_by_id = {candidate.id: candidate for candidate in request.candidates}
    if action not in compiled.feasible or action not in candidate_by_id:
        raise SystemOneSpecError("selected action was not feasible")
    candidate = candidate_by_id[action]
    params_spec = candidate.metadata.get("parameters") or {}
    params: dict[str, Any] = {}
    judgments: dict[str, float] = {NEXT_ACTION: action_probability}

    for param_name, key in compiled.parameter_keys.get(action, {}).items():
        question = compiled.questions[key]
        stated_key = compiled.stated_keys.get(action, {}).get(param_name)
        if stated_key is not None:
            stated_answer = answers.get(stated_key, {})
            stated_probability = _number(stated_answer.get("noul")) if isinstance(stated_answer, dict) else 0.0
            judgments[stated_key] = max(stated_probability, 1.0 - stated_probability)
            if stated_probability < 0.5:
                params[param_name] = params_spec[param_name].get("default")
                continue
        answer = answers.get(key)
        if not isinstance(answer, dict):
            raise SystemOneSpecError(f"System One response missing parameter answer {key}")
        value, probability = _param_value(answer, question)
        params[param_name] = value
        judgments[key] = probability

    weakest = min(judgments.values()) if judgments else 0.0
    risk = str(candidate.metadata.get("risk", "write"))
    threshold = compiled.thresholds[risk]
    if weakest < threshold:
        base_meta["handoff"] = {
            "reason": "no_confident_action",
            "proposed_action": action,
            "proposed_parameters": params,
            "risk": risk,
            "weakest": weakest,
            "threshold": threshold,
            "judgments": judgments,
            "target_classes": ["SYSTEM_TWO", "HUMAN"],
        }
        return ProviderResult(
            "NO_DECISION",
            {
                "proposed_action": action,
                "gate": {"risk": risk, "threshold": threshold, "weakest": weakest},
            },
            weakest,
            score_map,
            base_meta,
        )

    return ProviderResult(
        "DECIDED",
        {
            "selected": action,
            "parameters": params,
            "gate": {
                "risk": risk,
                "threshold": threshold,
                "weakest": weakest,
                "judgments": judgments,
            },
        },
        weakest,
        score_map,
        base_meta,
    )


@dataclass
class SystemOneReflexRuntime:
    fabric: DecisionFabric
    provider_id: str = "FA3-PROVIDER-SYSTEM-ONE-DECISION-001"

    def step(
        self,
        *,
        purpose: str,
        actions: list[str | dict[str, Any]],
        state: Any,
        final_policy_owner: str,
        constraints: dict[str, Any] | None = None,
        policy_context: dict[str, Any] | None = None,
        evidence_refs: list[str] | None = None,
        rollout: str = "SHADOW",
    ) -> dict[str, Any]:
        request = {
            "contract": "BOUNDED_ACTION",
            "purpose": purpose,
            "candidates": actions,
            "constraints": dict(constraints or {}),
            "policy_context": dict(policy_context or {}),
            "evidence_refs": list(evidence_refs or []),
            "state": state,
            "failure_policy": "NO_DECISION",
            "rollout": rollout,
            "final_policy_owner": final_policy_owner,
        }
        trace = self.fabric.decide(request, self.provider_id)
        result = trace.get("result") or {}
        provider_meta = trace.get("provider_meta") or {}
        handoff = provider_meta.get("handoff")

        if trace.get("status") == "DECIDED" and isinstance(result, dict) and result.get("selected"):
            runtime_status = "READY_FOR_AUTHORIZATION"
        elif trace.get("status") == "DECIDED" and result.get("terminal") == "FINISH":
            runtime_status = "FINISH_READY"
        else:
            runtime_status = "HANDOFF"

        return {
            "schema": "fa3.system-one-reflex-step.v1",
            "status": runtime_status,
            "authority": False,
            "confidence_is_authorization": False,
            "requires_external_policy_authorization": runtime_status == "READY_FOR_AUTHORIZATION",
            "execution_performed": False,
            "selected_action": result.get("selected") if isinstance(result, dict) else None,
            "parameters": result.get("parameters", {}) if isinstance(result, dict) else {},
            "handoff": handoff,
            "decision_trace": trace,
            "final_policy_owner": final_policy_owner,
            "global_promotion_claim": False,
        }
