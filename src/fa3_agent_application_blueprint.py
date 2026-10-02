#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fa3_orchestration_governance import DEPENDENCY_TYPES, validate_dependency_graph
from fa3_orchestration_workforce import WorkforceContractError, compile_cross_domain_plan

BLUEPRINT_SCHEMA = "fa3.agent-application-blueprint.v1"
CONTRACT_ID = "FA3-AGENT-APPLICATION-BLUEPRINT-CONTRACTS-001"
ROLE_KINDS = {"PLANNER", "ROUTER", "WORKER", "REVIEWER", "VERIFIER", "OPERATOR"}
REVIEW_KINDS = {"REVIEWER", "VERIFIER"}
CONDUCTOR_MODES = {"FA3_NATIVE_ADAPTIVE", "OPTIONAL_EXTERNAL_ADMITTED", "NONE"}


class BlueprintContractError(ValueError):
    pass


def _strings(value: Any, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        raise BlueprintContractError(f"{name} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise BlueprintContractError(f"{name} must contain unique values")
    if not allow_empty and not value:
        raise BlueprintContractError(f"{name} must not be empty")
    return list(value)


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BlueprintContractError(f"{name} must be a non-empty string")
    return value.strip()


def canonical_digest(blueprint: dict[str, Any]) -> str:
    payload = json.dumps(blueprint, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(blueprint, dict) or blueprint.get("schema") != BLUEPRINT_SCHEMA:
        raise BlueprintContractError("unexpected blueprint schema")

    for field in ("blueprint_id", "application_id", "task_group_id", "objective"):
        _nonempty(blueprint.get(field), field)
    revision = blueprint.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise BlueprintContractError("revision must be a positive integer")

    roles = blueprint.get("roles")
    if not isinstance(roles, list) or not roles:
        raise BlueprintContractError("roles must be a non-empty list")
    role_map: dict[str, dict[str, Any]] = {}
    for role in roles:
        if not isinstance(role, dict):
            raise BlueprintContractError("role must be an object")
        role_id = _nonempty(role.get("role_id"), "role_id")
        if role_id in role_map:
            raise BlueprintContractError("duplicate role_id")
        kind = role.get("kind")
        if kind not in ROLE_KINDS:
            raise BlueprintContractError("unsupported role kind")
        allowed = _strings(role.get("allowed_capabilities", []), "allowed_capabilities")
        forbidden = _strings(role.get("forbidden_capabilities", []), "forbidden_capabilities")
        authority = _strings(role.get("authority_scope", []), "authority_scope")
        if authority:
            raise BlueprintContractError("blueprint role authority_scope must remain empty")
        if set(allowed) & set(forbidden):
            raise BlueprintContractError("role capability cannot be both allowed and forbidden")
        role_map[role_id] = {**role, "allowed_capabilities": allowed, "forbidden_capabilities": forbidden, "authority_scope": []}

    tasks = blueprint.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise BlueprintContractError("tasks must be a non-empty list")
    task_map: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise BlueprintContractError("task must be an object")
        task_id = _nonempty(task.get("task_id"), "task_id")
        if task_id in task_map:
            raise BlueprintContractError("duplicate task_id")
        _nonempty(task.get("domain"), "domain")
        role_id = _nonempty(task.get("role_id"), "role_id")
        if role_id not in role_map:
            raise BlueprintContractError("task references unknown role")
        required = _strings(task.get("required_capabilities", []), "required_capabilities", allow_empty=False)
        role = role_map[role_id]
        allowed = set(role["allowed_capabilities"])
        forbidden = set(role["forbidden_capabilities"])
        if not set(required).issubset(allowed):
            raise BlueprintContractError("task capability is not declared by assigned role")
        if set(required) & forbidden:
            raise BlueprintContractError("task requests capability forbidden by assigned role")
        task_map[task_id] = task

    handoffs = blueprint.get("handoffs")
    if not isinstance(handoffs, list):
        raise BlueprintContractError("handoffs must be a list")
    normalized_edges: list[dict[str, str]] = []
    handoff_meta: list[dict[str, Any]] = []
    for handoff in handoffs:
        if not isinstance(handoff, dict):
            raise BlueprintContractError("handoff must be an object")
        source = _nonempty(handoff.get("from_task_id"), "from_task_id")
        target = _nonempty(handoff.get("to_task_id"), "to_task_id")
        relation = handoff.get("type")
        if relation not in DEPENDENCY_TYPES:
            raise BlueprintContractError("unsupported handoff relation type")
        artifacts = _strings(handoff.get("required_artifacts", []), "required_artifacts")
        normalized_edges.append({"from_task_id": source, "to_task_id": target, "type": relation})
        handoff_meta.append({
            "from_task_id": source,
            "to_task_id": target,
            "type": relation,
            "required_artifacts": artifacts,
            "digest_required": bool(handoff.get("digest_required", True)),
        })
    normalized_edges = validate_dependency_graph(list(task_map), normalized_edges)

    reviews = blueprint.get("reviews")
    if not isinstance(reviews, list):
        raise BlueprintContractError("reviews must be a list")
    review_bindings: list[dict[str, str]] = []
    reviewed_targets: set[str] = set()
    for review in reviews:
        if not isinstance(review, dict):
            raise BlueprintContractError("review must be an object")
        target_task_id = _nonempty(review.get("target_task_id"), "target_task_id")
        review_task_id = _nonempty(review.get("review_task_id"), "review_task_id")
        if target_task_id not in task_map or review_task_id not in task_map or target_task_id == review_task_id:
            raise BlueprintContractError("review references invalid tasks")
        target_role = role_map[task_map[target_task_id]["role_id"]]
        review_role = role_map[task_map[review_task_id]["role_id"]]
        if review_role.get("kind") not in REVIEW_KINDS:
            raise BlueprintContractError("review task must use REVIEWER or VERIFIER role")
        if task_map[target_task_id]["role_id"] == task_map[review_task_id]["role_id"]:
            raise BlueprintContractError("independent review cannot reuse target task role")
        if target_task_id in reviewed_targets:
            raise BlueprintContractError("duplicate review target")
        reviewed_targets.add(target_task_id)
        review_bindings.append({"target_task_id": target_task_id, "review_task_id": review_task_id})

    policy = blueprint.get("execution_policy")
    if not isinstance(policy, dict):
        raise BlueprintContractError("execution_policy must be an object")
    if policy.get("durable_lifecycle_authority") != "Temporal":
        raise BlueprintContractError("Temporal must remain durable lifecycle authority")
    if policy.get("conductor_mode") not in CONDUCTOR_MODES:
        raise BlueprintContractError("unsupported conductor_mode")
    if policy.get("execution_fabric") != "FA3-UNIFIED-ACTION-FABRIC-001":
        raise BlueprintContractError("UAF must remain execution fabric")
    if policy.get("direct_provider_invocation") is not False:
        raise BlueprintContractError("direct provider invocation must be false")
    if policy.get("independent_review_required") is True and not reviews:
        raise BlueprintContractError("independent review policy requires review binding")

    return {
        "roles": role_map,
        "tasks": task_map,
        "dependency_edges": normalized_edges,
        "handoffs": handoff_meta,
        "reviews": review_bindings,
        "execution_policy": deepcopy(policy),
    }


def compile_blueprint(root: Path | str, blueprint: dict[str, Any], *, runtime_execution: bool = False) -> dict[str, Any]:
    normalized = validate_blueprint(blueprint)
    digest = canonical_digest(blueprint)
    edge_by_source: dict[str, list[dict[str, str]]] = {task_id: [] for task_id in normalized["tasks"]}
    for edge in normalized["dependency_edges"]:
        edge_by_source[edge["from_task_id"]].append(edge)

    review_targets = {r["target_task_id"]: r["review_task_id"] for r in normalized["reviews"]}
    tasks: list[dict[str, Any]] = []
    for task_id, raw in normalized["tasks"].items():
        role = normalized["roles"][raw["role_id"]]
        metadata = deepcopy(raw.get("metadata", {}))
        metadata["agent_application_blueprint"] = {
            "contract_id": CONTRACT_ID,
            "blueprint_id": blueprint["blueprint_id"],
            "revision": blueprint["revision"],
            "digest": digest,
            "application_id": blueprint["application_id"],
            "task_group_id": blueprint["task_group_id"],
            "role_id": raw["role_id"],
            "role_kind": role["kind"],
            "review_task_id": review_targets.get(task_id),
        }
        task = {
            "task_id": task_id,
            "domain": raw["domain"],
            "required_capabilities": list(raw["required_capabilities"]),
            "authorized_ai_participants": list(raw.get("authorized_ai_participants", [])),
            "resource_requirements": deepcopy(raw.get("resource_requirements", {})),
            "metadata": metadata,
            "objective_ancestry": list(raw.get("objective_ancestry", [
                blueprint["application_id"], blueprint["task_group_id"], blueprint["blueprint_id"], task_id
            ])),
            "dependency_edges": edge_by_source[task_id],
            "runtime_execution": bool(runtime_execution),
        }
        for key in ("parent_task_id", "split_reasons", "budget_envelope", "required_authorities", "forbidden_specialists", "approval_required", "liveness_state"):
            if key in raw:
                task[key] = deepcopy(raw[key])
        tasks.append(task)

    try:
        work_plan = compile_cross_domain_plan(
            root,
            {
                "goal": blueprint["objective"],
                "tasks": tasks,
                "runtime_admission_receipts": deepcopy(blueprint.get("runtime_admission_receipts", {})),
                "decision_advisories": deepcopy(blueprint.get("decision_advisories", {})),
            },
            runtime_execution=runtime_execution,
        )
    except WorkforceContractError as exc:
        raise BlueprintContractError(str(exc)) from exc

    reviewed = {r["target_task_id"] for r in normalized["reviews"]}
    return {
        "schema": "fa3.agent-application-blueprint-compile.v1",
        "contract_id": CONTRACT_ID,
        "blueprint_id": blueprint["blueprint_id"],
        "revision": blueprint["revision"],
        "digest": digest,
        "application_id": blueprint["application_id"],
        "task_group_id": blueprint["task_group_id"],
        "provider_neutral": True,
        "architectural_authority": False,
        "capability_delta": 0,
        "durable_lifecycle_authority": "Temporal",
        "conductor_mode": normalized["execution_policy"]["conductor_mode"],
        "execution_fabric": "FA3-UNIFIED-ACTION-FABRIC-001",
        "model_router": "FA3-AUTH-MODEL-ROUTER-001",
        "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "review_bindings": normalized["reviews"],
        "reviewed_task_ids": sorted(reviewed),
        "handoffs": normalized["handoffs"],
        "compiled_tasks": tasks,
        "work_plan": work_plan,
        "runtime_promotion_claim": False,
    }


def load_and_compile(root: Path | str, path: Path | str, *, runtime_execution: bool = False) -> dict[str, Any]:
    blueprint = json.loads(Path(path).read_text(encoding="utf-8"))
    return compile_blueprint(root, blueprint, runtime_execution=runtime_execution)
