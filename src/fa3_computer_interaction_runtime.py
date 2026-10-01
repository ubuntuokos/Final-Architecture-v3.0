#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

TRUST_CLASS = "UNTRUSTED_DESKTOP_CONTENT"
EXECUTION_AUTHORITY = "FA3-UNIFIED-ACTION-FABRIC-001"
MODEL_ROUTER_AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
TELEMETRY_DEFAULT = "DISABLED"
TARGET_OPERATIONS = {"CLICK", "TYPE_TEXT", "SELECT", "PRESS_KEY", "SCROLL"}
MUTATING_OPERATIONS = {"CLICK", "TYPE_TEXT", "SELECT", "PRESS_KEY", "SCROLL"}
CONTROL_OPERATIONS = {"WAIT", "REOBSERVE", "ABSTAIN", "BLOCKED"}
ALLOWED_KEYS = {
    "Enter", "Tab", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
    "Backspace", "Delete", "Home", "End", "PageUp", "PageDown",
}


class ComputerInteractionDenied(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComputerInteractionDenied("COMPUTER-OBSERVATION-INVALID", f"{name} required")
    return value.strip()


def normalize_observation(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ComputerInteractionDenied("COMPUTER-OBSERVATION-INVALID", "object required")
    revision = raw.get("revision")
    if not isinstance(revision, int) or revision < 0:
        raise ComputerInteractionDenied("COMPUTER-OBSERVATION-INVALID", "non-negative revision required")
    targets = raw.get("targets")
    if not isinstance(targets, list):
        raise ComputerInteractionDenied("COMPUTER-OBSERVATION-INVALID", "targets list required")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in targets:
        if not isinstance(item, dict):
            raise ComputerInteractionDenied("COMPUTER-OBSERVATION-INVALID", "target object required")
        target_id = _text(item.get("target_id"), "target_id")
        if target_id in seen:
            raise ComputerInteractionDenied("COMPUTER-OBSERVATION-INVALID", "duplicate target_id")
        seen.add(target_id)
        actions = item.get("supported_actions", [])
        if not isinstance(actions, list) or any(action not in TARGET_OPERATIONS for action in actions):
            raise ComputerInteractionDenied("COMPUTER-OBSERVATION-INVALID", "invalid supported_actions")
        rows.append({
            "target_id": target_id,
            "role": str(item.get("role", "")),
            "label": str(item.get("label", "")),
            "value": item.get("value"),
            "visible": item.get("visible") is True,
            "enabled": item.get("enabled") is not False,
            "occluded": item.get("occluded") is True,
            "visual_region": item.get("visual_region") is True,
            "supported_actions": sorted(set(actions)),
            "metadata": item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {},
        })
    return {
        "schema": "fa3.computer-interaction-observation.v1",
        "session_id": _text(raw.get("session_id"), "session_id"),
        "observation_id": _text(raw.get("observation_id"), "observation_id"),
        "revision": revision,
        "application_id": _text(raw.get("application_id"), "application_id"),
        "window_id": _text(raw.get("window_id"), "window_id"),
        "window_fingerprint": _text(raw.get("window_fingerprint"), "window_fingerprint"),
        "capture_id": _text(raw.get("capture_id"), "capture_id"),
        "trust_class": TRUST_CLASS,
        "targets": sorted(rows, key=lambda row: row["target_id"]),
        "provenance": raw.get("provenance", {}) if isinstance(raw.get("provenance", {}), dict) else {},
    }


def build_action_space(raw: dict[str, Any]) -> dict[str, Any]:
    obs = normalize_observation(raw)
    candidates: list[dict[str, Any]] = []
    idx = 0
    for target in obs["targets"]:
        for operation in target["supported_actions"]:
            candidates.append({
                "id": str(idx),
                "action_id": f"{operation}:{target['target_id']}",
                "operation": operation,
                "target_id": target["target_id"],
                "description": f"{operation} role={target['role']} label={target['label']}".strip(),
                "metadata": {
                    "role": target["role"],
                    "label": target["label"],
                    "visual_region": target["visual_region"],
                    "trust_class": TRUST_CLASS,
                },
            })
            idx += 1
    for operation in ("WAIT", "REOBSERVE", "ABSTAIN", "BLOCKED"):
        candidates.append({
            "id": str(idx),
            "action_id": operation,
            "operation": operation,
            "target_id": None,
            "description": operation,
            "metadata": {"trust_class": "FA3_RUNTIME_CONTROL"},
        })
        idx += 1
    body = {
        "schema": "fa3.computer-interaction-action-space.v1",
        "session_id": obs["session_id"],
        "observation_id": obs["observation_id"],
        "revision": obs["revision"],
        "application_id": obs["application_id"],
        "window_id": obs["window_id"],
        "window_fingerprint": obs["window_fingerprint"],
        "capture_id": obs["capture_id"],
        "candidates": candidates,
        "candidate_set_source": "FA3_COMPUTER_INTERACTION_RUNTIME_ONLY",
        "candidate_set_expansion": "DENY",
        "raw_coordinate_only_action": "DENY_BY_DEFAULT",
    }
    body["action_space_hash"] = _digest(body)
    return body


def decision_request(
    space: dict[str, Any], *, purpose: str, state: Any = None, rollout: str = "SHADOW"
) -> dict[str, Any]:
    return {
        "contract": "SELECT_ONE",
        "purpose": purpose,
        "candidates": [
            {
                "id": row["id"],
                "description": row["description"],
                "metadata": {
                    **row["metadata"],
                    "operation": row["operation"],
                    "target_id": row["target_id"],
                    "action_id": row["action_id"],
                },
            }
            for row in space["candidates"]
        ],
        "constraints": {
            "candidate_set_expansion": "DENY",
            "executable_code_generation": "DENY",
            "unobserved_target": "DENY",
        },
        "policy_context": {
            "execution_authority": EXECUTION_AUTHORITY,
            "consumer": "FA3-COMPUTER-INTERACTION-RUNTIME-001",
            "session_id": space["session_id"],
            "observation_id": space["observation_id"],
            "revision": space["revision"],
            "application_id": space["application_id"],
            "window_id": space["window_id"],
            "capture_id": space["capture_id"],
            "action_space_hash": space["action_space_hash"],
            "desktop_content_trust": TRUST_CLASS,
        },
        "evidence_refs": [],
        "state": state,
        "failure_policy": "FAIL_CLOSED",
        "rollout": rollout,
        "final_policy_owner": EXECUTION_AUTHORITY,
    }


def bind_selected_action(space: dict[str, Any], selected_candidate_id: str) -> dict[str, Any]:
    row = next((item for item in space["candidates"] if item["id"] == str(selected_candidate_id)), None)
    if row is None:
        raise ComputerInteractionDenied(
            "COMPUTER-CANDIDATE-ESCAPE", "candidate outside bounded action space"
        )
    return {
        "schema": "fa3.computer-interaction-decision-binding.v1",
        "session_id": space["session_id"],
        "observation_id": space["observation_id"],
        "revision": space["revision"],
        "application_id": space["application_id"],
        "window_id": space["window_id"],
        "window_fingerprint": space["window_fingerprint"],
        "capture_id": space["capture_id"],
        "action_space_hash": space["action_space_hash"],
        "selected_candidate": row,
    }


def attach_execution_parameters(
    binding: dict[str, Any], parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not isinstance(binding, dict):
        raise ComputerInteractionDenied("COMPUTER-PARAMETERS-INVALID", "binding object required")
    params = {} if parameters is None else parameters
    if not isinstance(params, dict):
        raise ComputerInteractionDenied("COMPUTER-PARAMETERS-INVALID", "parameters object required")
    candidate = binding.get("selected_candidate")
    if not isinstance(candidate, dict):
        raise ComputerInteractionDenied("COMPUTER-PARAMETERS-INVALID", "selected candidate missing")
    operation = candidate.get("operation")
    if operation == "TYPE_TEXT":
        allowed = {"text"}
        value = params.get("text")
        if not isinstance(value, str) or len(value) > 32768:
            raise ComputerInteractionDenied(
                "COMPUTER-PARAMETERS-INVALID", "TYPE_TEXT requires bounded text"
            )
    elif operation == "SELECT":
        allowed = {"value"}
        value = params.get("value")
        if not isinstance(value, str) or len(value) > 4096:
            raise ComputerInteractionDenied(
                "COMPUTER-PARAMETERS-INVALID", "SELECT requires bounded value"
            )
    elif operation == "PRESS_KEY":
        allowed = {"key"}
        if params.get("key") not in ALLOWED_KEYS:
            raise ComputerInteractionDenied(
                "COMPUTER-PARAMETERS-INVALID", "PRESS_KEY key is not allowlisted"
            )
    elif operation == "SCROLL":
        allowed = {"delta_y"}
        delta = params.get("delta_y")
        if not isinstance(delta, int) or not -20 <= delta <= 20:
            raise ComputerInteractionDenied(
                "COMPUTER-PARAMETERS-INVALID", "SCROLL delta_y outside -20..20"
            )
    elif operation == "WAIT":
        allowed = {"milliseconds"}
        milliseconds = params.get("milliseconds", 250)
        if not isinstance(milliseconds, int) or not 0 <= milliseconds <= 5000:
            raise ComputerInteractionDenied(
                "COMPUTER-PARAMETERS-INVALID", "WAIT milliseconds outside 0..5000"
            )
        params = {**params, "milliseconds": milliseconds}
    else:
        allowed = set()
    if set(params) - allowed:
        raise ComputerInteractionDenied(
            "COMPUTER-PARAMETERS-INVALID", "unexpected execution parameter"
        )
    out = dict(binding)
    out["execution_parameters"] = dict(params)
    return out


def revalidate(binding: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    obs = normalize_observation(raw)
    fresh = build_action_space(obs)
    for key in (
        "session_id",
        "observation_id",
        "revision",
        "application_id",
        "window_id",
        "window_fingerprint",
        "capture_id",
        "action_space_hash",
    ):
        if fresh.get(key) != binding.get(key):
            raise ComputerInteractionDenied("STALE_OBSERVATION", f"binding mismatch: {key}")
    wanted = binding.get("selected_candidate", {})
    current = next(
        (
            row
            for row in fresh["candidates"]
            if row["id"] == wanted.get("id") and row["action_id"] == wanted.get("action_id")
        ),
        None,
    )
    if current is None:
        raise ComputerInteractionDenied("STALE_OBSERVATION", "selected action disappeared")
    guards = [
        "SESSION_MATCH",
        "OBSERVATION_CURRENT",
        "APPLICATION_MATCH",
        "WINDOW_MATCH",
        "WINDOW_FINGERPRINT_MATCH",
        "CAPTURE_MATCH",
        "ACTION_SPACE_MATCH",
    ]
    if current["target_id"] is not None:
        target = next(
            (row for row in obs["targets"] if row["target_id"] == current["target_id"]), None
        )
        if target is None:
            raise ComputerInteractionDenied("TARGET_MISSING", "target missing")
        if not target["visible"]:
            raise ComputerInteractionDenied("TARGET_NOT_VISIBLE", "target not visible")
        guards.append("VISIBLE")
        if current["operation"] in MUTATING_OPERATIONS:
            if not target["enabled"]:
                raise ComputerInteractionDenied("TARGET_DISABLED", "target disabled")
            guards.append("ENABLED")
        if current["operation"] == "CLICK":
            if target["occluded"]:
                raise ComputerInteractionDenied("TARGET_OCCLUDED", "target occluded")
            guards.append("NOT_OCCLUDED")
        if target["visual_region"]:
            guards.append("VISUAL_REGION_SAME_CAPTURE")
    return {
        "schema": "fa3.computer-interaction-execution-guard.v1",
        "result": "PASS",
        "guards": guards,
        "candidate": current,
        "observation_id": obs["observation_id"],
        "capture_id": obs["capture_id"],
        "revision": obs["revision"],
    }


@dataclass
class MutationLedger:
    attempted: set[str] = field(default_factory=set)

    def begin(self, binding: dict[str, Any]) -> str:
        candidate = binding["selected_candidate"]
        token = _digest({
            "session_id": binding["session_id"],
            "observation_id": binding["observation_id"],
            "revision": binding["revision"],
            "capture_id": binding["capture_id"],
            "action_id": candidate["action_id"],
        })
        if candidate["operation"] in MUTATING_OPERATIONS and token in self.attempted:
            raise ComputerInteractionDenied(
                "BLIND_MUTATION_RETRY_DENIED", "mutation cannot be blindly retried"
            )
        if candidate["operation"] in MUTATING_OPERATIONS:
            self.attempted.add(token)
        return token


def execute_interaction(
    binding: dict[str, Any],
    current: dict[str, Any],
    executor: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    authorization_ref: str | None = None,
    ledger: MutationLedger | None = None,
) -> dict[str, Any]:
    guard = revalidate(binding, current)
    candidate = guard["candidate"]
    operation = candidate["operation"]
    if operation == "REOBSERVE":
        return {
            "schema": "fa3.computer-interaction-effect-receipt.v1",
            "status": "REOBSERVE_REQUIRED",
            "verified_success": False,
            "candidate": candidate,
            "guard_result": guard,
            "global_promotion_claim": False,
        }
    if operation == "ABSTAIN":
        return {
            "schema": "fa3.computer-interaction-effect-receipt.v1",
            "status": "ABSTAINED",
            "verified_success": False,
            "candidate": candidate,
            "guard_result": guard,
            "global_promotion_claim": False,
        }
    if operation == "BLOCKED":
        return {
            "schema": "fa3.computer-interaction-effect-receipt.v1",
            "status": "BLOCKED_CLAIM",
            "verified_success": False,
            "candidate": candidate,
            "guard_result": guard,
            "global_promotion_claim": False,
        }
    if operation in MUTATING_OPERATIONS and (
        not isinstance(authorization_ref, str) or not authorization_ref.strip()
    ):
        raise ComputerInteractionDenied(
            "AUTHORIZATION_REQUIRED", "mutating interaction requires authorization reference"
        )
    ledger = ledger or MutationLedger()
    token = ledger.begin(binding)
    parameters = binding.get("execution_parameters", {})
    output = executor(candidate, normalize_observation(current), parameters)
    if not isinstance(output, dict):
        raise ComputerInteractionDenied("COMPUTER-EXECUTION-INVALID", "executor object required")
    return {
        "schema": "fa3.computer-interaction-effect-receipt.v1",
        "status": "EXECUTED",
        "verified_success": False,
        "candidate": candidate,
        "guard_result": guard,
        "attempt_token": token,
        "authorization_ref": authorization_ref,
        "provider_output_digest": _digest(output),
        "reobserve_required": operation in MUTATING_OPERATIONS,
        "global_promotion_claim": False,
    }


def verify_outcome(
    expected_postconditions: Iterable[dict[str, Any]], raw_post: dict[str, Any]
) -> dict[str, Any]:
    obs = normalize_observation(raw_post)
    conditions = list(expected_postconditions)
    if not conditions:
        return {
            "schema": "fa3.computer-interaction-outcome-verification.v1",
            "result": "INDETERMINATE",
            "checks": [],
            "global_promotion_claim": False,
        }
    by_id = {row["target_id"]: row for row in obs["targets"]}
    checks: list[dict[str, Any]] = []
    for condition in conditions:
        kind = condition.get("type")
        passed: bool | None = None
        if kind == "target_present":
            passed = condition.get("target_id") in by_id
        elif kind == "target_absent":
            passed = condition.get("target_id") not in by_id
        elif kind == "target_value_equals":
            target = by_id.get(condition.get("target_id"))
            passed = target is not None and target.get("value") == condition.get("value")
        elif kind == "window_fingerprint_equals":
            passed = obs["window_fingerprint"] == condition.get("value")
        elif kind == "application_equals":
            passed = obs["application_id"] == condition.get("value")
        checks.append({"condition": condition, "passed": passed})
    result = (
        "VERIFIED_FAILURE"
        if any(row["passed"] is False for row in checks)
        else "VERIFIED_SUCCESS"
        if all(row["passed"] is True for row in checks)
        else "INDETERMINATE"
    )
    return {
        "schema": "fa3.computer-interaction-outcome-verification.v1",
        "result": result,
        "checks": checks,
        "observation_id": obs["observation_id"],
        "capture_id": obs["capture_id"],
        "revision": obs["revision"],
        "global_promotion_claim": False,
    }


def make_trajectory_event(
    binding: dict[str, Any], receipt: dict[str, Any], verification: dict[str, Any] | None = None
) -> dict[str, Any]:
    candidate = binding.get("selected_candidate", {})
    event = {
        "schema": "fa3.computer-interaction-trajectory-event.v1",
        "session_id": binding.get("session_id"),
        "observation_id": binding.get("observation_id"),
        "revision": binding.get("revision"),
        "application_id": binding.get("application_id"),
        "window_id": binding.get("window_id"),
        "capture_id": binding.get("capture_id"),
        "action_space_hash": binding.get("action_space_hash"),
        "candidate_id": candidate.get("id"),
        "action_id": candidate.get("action_id"),
        "effect_status": receipt.get("status"),
        "attempt_token": receipt.get("attempt_token"),
        "verification_result": (verification or {}).get("result"),
        "privacy_profile": "METADATA_MINIMAL",
        "forbidden_payloads_absent": True,
    }
    event["event_digest"] = _digest(event)
    return event
