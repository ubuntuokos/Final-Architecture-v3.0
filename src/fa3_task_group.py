#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

REGISTRY_REL = Path("canonical/FA3-TASK-GROUP-REGISTRY-001.json")
CONTRACT_REL = Path("canonical/contracts/FA3-TASK-GROUP-CONTRACTS-001.json")
EXPECTED_IDS = {f"F{i:02d}" for i in range(1, 32)}
AUTHORITY_BOUND_IDS = {"F09", "F10", "F11", "F12", "F13", "F17"}


class TaskGroupContractError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def canonical_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _expanded_record(registry: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    defaults = registry.get("defaults", {})
    if not isinstance(defaults, dict):
        raise TaskGroupContractError("task-group defaults must be an object")
    return _deep_merge(defaults, row)


def validate_registry(root: Path | str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root)
    reg = registry if registry is not None else _load(root / REGISTRY_REL)
    contract = _load(root / CONTRACT_REL)
    baseline = load_active_release_baseline(root).capability_count

    if reg.get("schema") != "fa3.task-group-registry.v1" or reg.get("id") != "FA3-TASK-GROUP-REGISTRY-001":
        raise TaskGroupContractError("unexpected task-group registry")
    if contract.get("id") != "FA3-TASK-GROUP-CONTRACTS-001":
        raise TaskGroupContractError("unexpected task-group contract")
    if reg.get("capability_count") != baseline or contract.get("capability_count") != baseline:
        raise TaskGroupContractError("task-group capability baseline drift")
    if reg.get("new_capability") is not False or reg.get("new_architectural_authority") is not False:
        raise TaskGroupContractError("task-group registry must not create capability or authority")

    groups = reg.get("groups")
    if not isinstance(groups, list):
        raise TaskGroupContractError("task-group groups must be a list")
    ids = [row.get("task_group_id") for row in groups if isinstance(row, dict)]
    if len(groups) != 31 or set(ids) != EXPECTED_IDS or len(ids) != len(set(ids)):
        raise TaskGroupContractError("canonical task-group registry must contain exactly unique F01..F31")
    if reg.get("first_level_group_count") != 31:
        raise TaskGroupContractError("first_level_group_count must be 31")

    aliases: dict[str, str] = {}
    expanded: dict[str, dict[str, Any]] = {}
    for raw in groups:
        if not isinstance(raw, dict):
            raise TaskGroupContractError("task-group record must be an object")
        group = _expanded_record(reg, raw)
        gid = group["task_group_id"]
        revision = group.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise TaskGroupContractError(f"{gid}: revision must be positive")
        if group.get("classification") not in {"ORCHESTRATED", "TEMPORAL_EXCLUSIVE", "AUTHORITY_BOUND"}:
            raise TaskGroupContractError(f"{gid}: invalid classification")

        alias_values = group.get("aliases", [])
        if not isinstance(alias_values, list) or not all(isinstance(x, str) and x for x in alias_values):
            raise TaskGroupContractError(f"{gid}: aliases must be strings")
        for alias in alias_values:
            if alias in EXPECTED_IDS or alias in aliases:
                raise TaskGroupContractError(f"{gid}: duplicate/colliding alias {alias}")
            aliases[alias] = gid

        authority = group.get("authority_policy", {})
        if authority.get("may_grant_authority") is not False:
            raise TaskGroupContractError(f"{gid}: task group may not grant authority")

        workflow = group.get("workflow_policy", {})
        if workflow.get("durable_lifecycle_owner", "Temporal") != "Temporal":
            raise TaskGroupContractError(f"{gid}: Temporal durable lifecycle drift")

        execution = group.get("execution_policy", {})
        if execution.get("direct_provider_execution") is not False:
            raise TaskGroupContractError(f"{gid}: direct provider execution forbidden")
        if execution.get("direct_model_selection") is not False:
            raise TaskGroupContractError(f"{gid}: direct model selection forbidden")
        if execution.get("direct_resource_admission") is not False:
            raise TaskGroupContractError(f"{gid}: direct resource admission forbidden")

        resource = group.get("resource_policy", {})
        if resource.get("cpu_only_valid") is not True:
            raise TaskGroupContractError(f"{gid}: CPU-only viability required")
        if resource.get("hrb_required_for_physical_resource_admission") is not True:
            raise TaskGroupContractError(f"{gid}: HRB admission boundary required")
        if resource.get("display_gpu_auto_recruitment") is not False:
            raise TaskGroupContractError(f"{gid}: display GPU auto recruitment forbidden")

        mode = group.get("workload_mode_policy", {})
        if mode.get("may_mutate_physical_resources") is not False:
            raise TaskGroupContractError(f"{gid}: Workload Mode intent may not mutate physical resources")

        evidence = group.get("evidence_policy", {})
        if evidence.get("worker_output_is_verified") is not False:
            raise TaskGroupContractError(f"{gid}: worker output may not self-verify")
        if evidence.get("evidence_authority") != "FA3-AUTH-OBS-EVIDENCE-001":
            raise TaskGroupContractError(f"{gid}: evidence authority drift")

        expanded[gid] = group

    f07 = expanded["F07"]
    if f07.get("classification") != "TEMPORAL_EXCLUSIVE":
        raise TaskGroupContractError("F07 must be TEMPORAL_EXCLUSIVE")
    if f07.get("workflow_policy", {}).get("conductor_allowed") is not False:
        raise TaskGroupContractError("F07 must not allow Conductor")
    if f07.get("profile_policy", {}).get("permitted_profiles", []):
        raise TaskGroupContractError("F07 must not be owned by a control profile")

    for gid in AUTHORITY_BOUND_IDS:
        group = expanded[gid]
        if group.get("classification") != "AUTHORITY_BOUND":
            raise TaskGroupContractError(f"{gid} must remain AUTHORITY_BOUND")
        if group.get("profile_policy", {}).get("permitted_profiles", []):
            raise TaskGroupContractError(f"{gid}: horizontal authority group must not become specialist-owned")

    f17 = expanded["F17"]
    review = f17.get("review_policy", {})
    if review.get("independent_review_required") is not True or review.get("self_review_allowed") is not False:
        raise TaskGroupContractError("F17 independent verification required")

    return {
        "registry": reg,
        "expanded": expanded,
        "aliases": aliases,
        "capability_count": baseline,
    }


def load_registry(root: Path | str) -> dict[str, Any]:
    return validate_registry(root)["registry"]


def resolve_task_group(root: Path | str, task_group_id: str) -> dict[str, Any]:
    if not isinstance(task_group_id, str) or not task_group_id.strip():
        raise TaskGroupContractError("task_group_id must be a non-empty string")
    state = validate_registry(root)
    key = task_group_id.strip()
    canonical_id = key if key in state["expanded"] else state["aliases"].get(key)
    if canonical_id is None:
        raise TaskGroupContractError(f"unknown task_group_id: {key}")
    record = deepcopy(state["expanded"][canonical_id])
    return {
        "schema": "fa3.task-group-policy-snapshot.v1",
        "registry_id": "FA3-TASK-GROUP-REGISTRY-001",
        "registry_revision": state["registry"].get("registry_revision"),
        "submitted_task_group_id": key,
        "task_group_id": canonical_id,
        "revision": record["revision"],
        "digest": canonical_digest(record),
        "record": record,
        "architectural_authority": False,
        "capability_delta": 0,
    }


def task_group_key_from_task(task: dict[str, Any]) -> str | None:
    direct = task.get("task_group_id")
    if isinstance(direct, str) and direct:
        return direct
    meta = task.get("metadata", {})
    if not isinstance(meta, dict):
        return None
    direct_meta = meta.get("task_group_id")
    if isinstance(direct_meta, str) and direct_meta:
        return direct_meta
    blueprint = meta.get("agent_application_blueprint", {})
    if isinstance(blueprint, dict):
        value = blueprint.get("task_group_id")
        if isinstance(value, str) and value:
            return value
    return None


def bind_task_group(root: Path | str, task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    key = task_group_key_from_task(task)
    if key is None:
        return deepcopy(task), None
    snapshot = resolve_task_group(root, key)
    out = deepcopy(task)
    metadata = deepcopy(out.get("metadata", {}))
    metadata["task_group_policy"] = {
        "registry_id": snapshot["registry_id"],
        "registry_revision": snapshot["registry_revision"],
        "submitted_task_group_id": snapshot["submitted_task_group_id"],
        "task_group_id": snapshot["task_group_id"],
        "revision": snapshot["revision"],
        "digest": snapshot["digest"],
    }
    out["task_group_id"] = snapshot["task_group_id"]
    out["metadata"] = metadata
    return out, snapshot
