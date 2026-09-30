#!/usr/bin/env python3
from __future__ import annotations
import fnmatch
import json
import os
import time
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("canonical/FA3-AUTHORITY-CONTRACT-REGISTRY-001.json")
LAYER_REGISTRY_REL = Path("canonical/FA3-LAYER-CONTRACT-REGISTRY-001.json")
ENVELOPE_SCHEMA = "fa3.task-authority-envelope.v1"
DIRECTOR_ID = "FA3-ORCHESTRATION-DIRECTOR-001"

class ScopeGuardError(ValueError):
    pass

def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ScopeGuardError(f"JSON object required: {path}")
    return value

def load_registry(root: Path | str) -> dict[str, Any]:
    reg = _load(Path(root) / REGISTRY_REL)
    if reg.get("schema") != "fa3.authority-contract-registry.v1" or reg.get("id") != "FA3-AUTHORITY-CONTRACT-REGISTRY-001":
        raise ScopeGuardError("unexpected authority contract registry")
    if reg.get("default_policy") != "DENY" or reg.get("new_architectural_authorities") != 0:
        raise ScopeGuardError("authority registry must be fail-closed and non-authoritative")
    actors = reg.get("actors")
    if not isinstance(actors, list) or not actors:
        raise ScopeGuardError("authority registry actors missing")
    ids = [x.get("actor_id") for x in actors]
    if len(ids) != len(set(ids)) or any(not isinstance(x, str) or not x for x in ids):
        raise ScopeGuardError("authority registry actor ids invalid")
    return reg

def load_layer_registry(root: Path | str) -> dict[str, Any]:
    reg = _load(Path(root) / LAYER_REGISTRY_REL)
    if reg.get("schema") != "fa3.layer-contract-registry.v1" or reg.get("id") != "FA3-LAYER-CONTRACT-REGISTRY-001":
        raise ScopeGuardError("unexpected layer contract registry")
    if reg.get("default_policy") != "DENY" or reg.get("new_architectural_authorities") != 0:
        raise ScopeGuardError("layer registry must be fail-closed and non-authoritative")
    layers = reg.get("layers")
    if not isinstance(layers, list) or not layers:
        raise ScopeGuardError("layer registry layers missing")
    keys = [x.get("layer_key") for x in layers]
    if len(keys) != len(set(keys)) or any(not isinstance(x, str) or not x for x in keys):
        raise ScopeGuardError("layer registry keys invalid")
    return reg

def _layer_contract(reg: dict[str, Any], layer_key: str) -> dict[str, Any] | None:
    return next((x for x in reg["layers"] if x.get("layer_key") == layer_key), None)

def _contract(reg: dict[str, Any], actor_id: str) -> dict[str, Any] | None:
    return next((x for x in reg["actors"] if x.get("actor_id") == actor_id), None)

def _strings(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value) or len(value) != len(set(value)):
        raise ScopeGuardError(f"{label} must be a unique string list")
    return list(value)

def _target_allowed(target: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(target, pattern) for pattern in patterns)

def make_envelope(*, task_id: str, actor_id: str, intent: str,
                  requested_authorities: list[str] | None = None,
                  target_actor: str | None = None,
                  parent_scope: list[str] | None = None,
                  side_effect_class: str = "NONE",
                  objective_id: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": ENVELOPE_SCHEMA, "task_id": task_id, "actor_id": actor_id,
        "intent": intent, "requested_authorities": list(requested_authorities or []),
        "side_effect_class": side_effect_class,
    }
    if target_actor is not None:
        out["target_actor"] = target_actor
    if parent_scope is not None:
        out["parent_scope"] = list(parent_scope)
    if objective_id is not None:
        out["objective_id"] = objective_id
    return out

def evaluate(root: Path | str, envelope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, dict) or envelope.get("schema") != ENVELOPE_SCHEMA:
        return _decision(envelope, "DENY", "INVALID_ENVELOPE_SCHEMA")
    task_id = envelope.get("task_id")
    actor_id = envelope.get("actor_id")
    intent = envelope.get("intent")
    if not all(isinstance(x, str) and x for x in (task_id, actor_id, intent)):
        return _decision(envelope, "DENY", "INVALID_REQUIRED_IDENTITY")
    try:
        requested = set(_strings(envelope.get("requested_authorities", []), "requested_authorities"))
        parent = None if "parent_scope" not in envelope else set(_strings(envelope.get("parent_scope"), "parent_scope"))
    except ScopeGuardError as exc:
        return _decision(envelope, "DENY", str(exc))
    side_effect = envelope.get("side_effect_class")
    if side_effect not in {"NONE", "READ", "WRITE", "DESTRUCTIVE"}:
        return _decision(envelope, "DENY", "INVALID_SIDE_EFFECT_CLASS")
    reg = load_registry(root)
    contract = _contract(reg, actor_id)
    if contract is None:
        return _decision(envelope, "DENY", "UNKNOWN_ACTOR")
    if intent in set(contract.get("forbidden_intents", [])):
        return _decision(envelope, "DENY", "FORBIDDEN_INTENT")
    if intent not in set(contract.get("allowed_intents", [])):
        return _decision(envelope, "DENY", "INTENT_OUTSIDE_ACTOR_CONTRACT")
    if side_effect != "NONE" and contract.get("may_execute_side_effects") is not True:
        return _decision(envelope, "DENY", "SIDE_EFFECT_OUTSIDE_ACTOR_CONTRACT")
    if parent is not None and not requested.issubset(parent):
        return _decision(envelope, "DENY", "PARENT_SCOPE_EXPANSION")
    target = envelope.get("target_actor")
    if target is not None:
        if not isinstance(target, str) or not target:
            return _decision(envelope, "DENY", "INVALID_TARGET_ACTOR")
        patterns = _strings(contract.get("allowed_delegation_targets", []), "allowed_delegation_targets")
        if not _target_allowed(target, patterns):
            return _decision(envelope, "DENY", "DELEGATION_TARGET_OUTSIDE_CONTRACT")
        delegable = set(_strings(contract.get("delegable_authorities", []), "delegable_authorities"))
        if not requested.issubset(delegable):
            return _decision(envelope, "DENY", "DELEGATION_AUTHORITY_EXPANSION")
        return _decision(envelope, "DELEGATE", "CONTRACT_MATCH")
    owned = set(_strings(contract.get("owned_authorities", []), "owned_authorities"))
    if requested and not requested.issubset(owned):
        return _decision(envelope, "DENY", "OWNED_AUTHORITY_SCOPE_MISMATCH")
    return _decision(envelope, "ALLOW", "CONTRACT_MATCH")

def _decision(envelope: Any, result: str, reason: str) -> dict[str, Any]:
    env = envelope if isinstance(envelope, dict) else {}
    return {
        "schema": "fa3.scope-authority-guard-decision.v1",
        "task_id": env.get("task_id"), "actor_id": env.get("actor_id"),
        "intent": env.get("intent"), "target_actor": env.get("target_actor"),
        "result": result, "reason": reason, "execution_authority": False,
        "authority_expansion": False,
    }

def monitor_event_path() -> Path:
    configured = os.environ.get("FA3_SCOPE_GUARD_EVENT_LOG", "").strip()
    if configured and configured != "AUTO":
        return Path(configured).expanduser()
    state_home = os.environ.get("XDG_STATE_HOME", "").strip()
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return base / "fa3" / "scope-authority-guard" / "decisions.jsonl"

def record_monitor_decision(decision: dict[str, Any], *, event_kind: str) -> dict[str, Any]:
    row = {
        "schema": "fa3.scope-authority-guard-event.v1",
        "event_id": f"{int(time.time_ns())}-{os.getpid()}",
        "epoch_ns": time.time_ns(),
        "event_kind": event_kind,
        "task_id": decision.get("task_id"),
        "actor_id": decision.get("actor_id"),
        "target_actor": decision.get("target_actor"),
        "intent": decision.get("intent"),
        "result": decision.get("result"),
        "reason": decision.get("reason"),
        "execution_authority": False,
        "authority_expansion": False,
    }
    path = monitor_event_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError:
        return {**decision, "monitor_event_recorded": False}
    return {**decision, "monitor_event_recorded": True, "monitor_event_id": row["event_id"]}

def evaluate_layer_task(root: Path | str, *, task_id: str, target_layer: str,
                        canonical_capability_ids: list[str], record_event: bool = True) -> dict[str, Any]:
    def emit(decision: dict[str, Any]) -> dict[str, Any]:
        return record_monitor_decision(decision, event_kind="LAYER_INGRESS") if record_event else decision
    try:
        required = set(_strings(canonical_capability_ids, "canonical_capability_ids"))
    except ScopeGuardError as exc:
        return emit(_decision({"task_id": task_id, "target_actor": target_layer, "intent": "layer.task"}, "DENY", str(exc))
    if not required:
        return emit(_decision({"task_id": task_id, "target_actor": target_layer, "intent": "layer.task"}, "DENY", "CANONICAL_CAPABILITY_IDS_REQUIRED"))\n    reg = load_layer_registry(root)
    target = _layer_contract(reg, target_layer)
    if target is None:
        return emit(_decision({"task_id": task_id, "target_actor": target_layer, "intent": "layer.task"}, "DENY", "UNKNOWN_LAYER"))\n    all_known = set()
    for layer in reg["layers"]:
        all_known.update(_strings(layer.get("allowed_capabilities", []), "allowed_capabilities"))
    unknown = sorted(required - all_known)
    if unknown:
        decision = _decision({"task_id": task_id, "target_actor": target_layer, "intent": "layer.task"}, "DENY", "UNKNOWN_CANONICAL_CAPABILITY")
        decision["unknown_capabilities"] = unknown
        return emit(decision)
    allowed = set(_strings(target.get("allowed_capabilities", []), "allowed_capabilities"))
    if required.issubset(allowed):
        decision = _decision({"task_id": task_id, "target_actor": target_layer, "intent": "layer.task"}, "ALLOW", "LAYER_CONTRACT_MATCH")
        decision["layer_key"] = target_layer
        decision["canonical_capability_ids"] = sorted(required)
        return emit(decision)
    exact_targets = []
    per_capability: dict[str, list[str]] = {}
    for layer in reg["layers"]:
        layer_caps = set(_strings(layer.get("allowed_capabilities", []), "allowed_capabilities"))
        if required.issubset(layer_caps):
            exact_targets.append(layer["layer_key"])
        for cap in required:
            if cap in layer_caps:
                per_capability.setdefault(cap, []).append(layer["layer_key"])
    if exact_targets:
        decision = _decision({"task_id": task_id, "target_actor": target_layer, "intent": "layer.task"}, "DELEGATE", "WRONG_LAYER")
        decision["recommended_layers"] = sorted(exact_targets)
        decision["canonical_capability_ids"] = sorted(required)
        return emit(decision)
    decision = _decision({"task_id": task_id, "target_actor": target_layer, "intent": "layer.task"}, "SPLIT", "CROSS_LAYER_TASK")
    decision["capability_layer_candidates"] = {key: sorted(value) for key, value in sorted(per_capability.items())}
    decision["canonical_capability_ids"] = sorted(required)
    return emit(decision)

def require_layer_permitted(root: Path | str, *, task_id: str, target_layer: str,
                            canonical_capability_ids: list[str]) -> dict[str, Any]:
    decision = evaluate_layer_task(root, task_id=task_id, target_layer=target_layer,
                                   canonical_capability_ids=canonical_capability_ids)
    if decision["result"] != "ALLOW":
        raise ScopeGuardError(f"{decision['result']}:{decision['reason']}")
    return decision

def require_permitted(root: Path | str, envelope: dict[str, Any]) -> dict[str, Any]:
    decision = evaluate(root, envelope)
    if decision["result"] not in {"ALLOW", "DELEGATE"}:
        raise ScopeGuardError(f"{decision['result']}:{decision['reason']}")
    return decision

def guard_transition(root: Path | str, *, actor_id: str, transition: str,
                     previous_scope: list[str], requested_scope: list[str],
                     task_id: str = "transition") -> dict[str, Any]:
    previous = set(_strings(previous_scope, "previous_scope"))
    requested = set(_strings(requested_scope, "requested_scope"))
    if not requested.issubset(previous):
        return _decision({"task_id": task_id, "actor_id": actor_id, "intent": transition}, "DENY", "STATE_TRANSITION_SCOPE_EXPANSION")
    intent = transition if "." in transition else f"orchestration.{transition}"
    return evaluate(root, make_envelope(task_id=task_id, actor_id=actor_id, intent=intent,
                                        requested_authorities=list(requested), parent_scope=list(previous)))

def guard_orchestration_delegation(root: Path | str, task: dict[str, Any],
                                   specialist: dict[str, Any]) -> dict[str, Any]:
    required = set(_strings(task.get("required_capabilities", []), "required_capabilities"))
    required_auth = set(_strings(task.get("required_authorities", []), "required_authorities"))
    if task.get("domain") not in set(specialist.get("domains", [])):
        return _decision({"task_id": task.get("task_id"), "actor_id": DIRECTOR_ID, "intent": "orchestration.delegate",
                          "target_actor": specialist.get("id")}, "DENY", "SPECIALIST_DOMAIN_MISMATCH")
    anti = required & set(specialist.get("anti_capabilities", []))
    if anti:
        return _decision({"task_id": task.get("task_id"), "actor_id": DIRECTOR_ID, "intent": "orchestration.delegate",
                          "target_actor": specialist.get("id")}, "DENY", "SPECIALIST_ANTI_CAPABILITY")
    caps = set(specialist.get("strong_capabilities", [])) | set(specialist.get("supported_capabilities", []))
    if not required.issubset(caps):
        return _decision({"task_id": task.get("task_id"), "actor_id": DIRECTOR_ID, "intent": "orchestration.delegate",
                          "target_actor": specialist.get("id")}, "DENY", "SPECIALIST_CAPABILITY_MISMATCH")
    if not required_auth.issubset(set(specialist.get("authority_scope", []))):
        return _decision({"task_id": task.get("task_id"), "actor_id": DIRECTOR_ID, "intent": "orchestration.delegate",
                          "target_actor": specialist.get("id")}, "DENY", "SPECIALIST_AUTHORITY_SCOPE_MISMATCH")
    envelope = make_envelope(
        task_id=str(task.get("task_id")), actor_id=DIRECTOR_ID, intent="orchestration.delegate",
        requested_authorities=sorted(required_auth), target_actor=str(specialist.get("id")),
        parent_scope=sorted(required_auth), side_effect_class="NONE",
    )
    return evaluate(root, envelope)
