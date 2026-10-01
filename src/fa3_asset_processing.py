"""FA3-native deterministic asset identity and processing-plan core.

WP1 is metadata/planning only. It does not read or write asset bytes, spawn
processes, choose codecs/providers/models, access the network, or mutate host
configuration.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict, deque
from typing import Any

PLAN_SCHEMA = "fa3.asset-processing-plan.v1"
INVALIDATION_SCHEMA = "fa3.asset-invalidation-plan.v1"
RIGHTS_STATES = ("CLEARED", "REFERENCE_ONLY", "PENDING", "RESTRICTED")
DEPENDENCY_KINDS = ("BUILD", "REFERENCE", "OPTIONAL")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BANNED_EXEC_KEYS = {
    "argv", "command", "commands", "code", "executable", "python",
    "script", "shell", "subprocess",
}


class AssetPlanError(ValueError):
    """Fail-closed asset planning error."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise AssetPlanError(f"{field} must be a non-empty canonical string")
    return value


def _content_digest(value: Any, field: str = "content_digest") -> str:
    value = _token(value, field)
    if not _DIGEST_RE.fullmatch(value):
        raise AssetPlanError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def logical_asset_id(project_namespace: str, asset_key: str) -> str:
    project_namespace = _token(project_namespace, "project_namespace")
    asset_key = _token(asset_key, "asset_key")
    raw = f"fa3.asset.logical.v1\0{project_namespace}\0{asset_key}".encode("utf-8")
    return "fa3asset:v1:" + hashlib.sha256(raw).hexdigest()


def source_version_id(logical_id: str, content_digest: str) -> str:
    logical_id = _token(logical_id, "logical_id")
    content_digest = _content_digest(content_digest)
    return "fa3assetver:v1:" + stable_digest({
        "logical_id": logical_id,
        "content_digest": content_digest,
        "role": "SOURCE",
    }).split(":", 1)[1]


def _reject_executable_payload(value: Any, path: str = "recipe") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _BANNED_EXEC_KEYS:
                raise AssetPlanError(f"arbitrary executable payload forbidden at {path}.{key}")
            _reject_executable_payload(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_executable_payload(child, f"{path}[{index}]")


def _toposort(nodes: set[str], build_edges: list[tuple[str, str]]) -> list[str]:
    # edge semantics: consumer depends on dependency
    indegree = {node: 0 for node in nodes}
    forward: dict[str, set[str]] = defaultdict(set)
    for consumer, dependency in build_edges:
        if consumer == dependency:
            raise AssetPlanError(f"BUILD self-dependency forbidden: {consumer}")
        if consumer not in nodes or dependency not in nodes:
            raise AssetPlanError(f"BUILD dependency references unknown asset: {consumer}->{dependency}")
        if consumer not in forward[dependency]:
            forward[dependency].add(consumer)
            indegree[consumer] += 1
    ready = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while ready:
        node = ready.popleft()
        ordered.append(node)
        for consumer in sorted(forward.get(node, ())):
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                # Preserve deterministic lexical ordering of the ready set.
                ready.append(consumer)
                ready = deque(sorted(ready))
    if len(ordered) != len(nodes):
        cyclic = sorted(node for node, degree in indegree.items() if degree)
        raise AssetPlanError("BUILD dependency cycle: " + ",".join(cyclic))
    return ordered


def _rights_max(states: list[str]) -> str:
    order = {state: index for index, state in enumerate(RIGHTS_STATES)}
    return max(states, key=lambda state: order[state]) if states else "PENDING"


def _normalize_sources(project_namespace: str, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise AssetPlanError("source_assets must be a non-empty list")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise AssetPlanError("source asset must be an object")
        key = _token(row.get("asset_key"), "source.asset_key")
        if key in out:
            raise AssetPlanError(f"duplicate source asset_key: {key}")
        rights = _token(row.get("rights_state"), f"{key}.rights_state")
        if rights not in RIGHTS_STATES:
            raise AssetPlanError(f"invalid rights_state for {key}: {rights}")
        provenance = _token(row.get("provenance_ref"), f"{key}.provenance_ref")
        media_type = _token(row.get("media_type"), f"{key}.media_type")
        digest = _content_digest(row.get("content_digest"), f"{key}.content_digest")
        logical_id = logical_asset_id(project_namespace, key)
        out[key] = {
            "asset_key": key,
            "role": "SOURCE",
            "logical_id": logical_id,
            "version_id": source_version_id(logical_id, digest),
            "content_digest": digest,
            "media_type": media_type,
            "rights_state": rights,
            "provenance_ref": provenance,
            "source_locator": row.get("source_locator"),
        }
    return out


def _normalize_jobs(rows: list[dict[str, Any]], known_source_keys: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if not isinstance(rows, list):
        raise AssetPlanError("jobs must be a list")
    jobs: dict[str, dict[str, Any]] = {}
    producer: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise AssetPlanError("job must be an object")
        job_key = _token(row.get("job_key"), "job.job_key")
        if job_key in jobs:
            raise AssetPlanError(f"duplicate job_key: {job_key}")
        recipe = row.get("recipe")
        if not isinstance(recipe, dict):
            raise AssetPlanError(f"{job_key}.recipe must be an object")
        _reject_executable_payload(recipe)
        recipe_id = _token(recipe.get("id"), f"{job_key}.recipe.id")
        recipe_version = _token(recipe.get("version"), f"{job_key}.recipe.version")
        inputs = row.get("input_keys")
        if not isinstance(inputs, list) or not inputs:
            raise AssetPlanError(f"{job_key}.input_keys must be non-empty")
        input_keys = sorted({_token(x, f"{job_key}.input_key") for x in inputs})
        outputs = row.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            raise AssetPlanError(f"{job_key}.outputs must be non-empty")
        normalized_outputs = []
        for output in outputs:
            if not isinstance(output, dict):
                raise AssetPlanError(f"{job_key}.output must be object")
            key = _token(output.get("asset_key"), f"{job_key}.output.asset_key")
            if key in known_source_keys or key in producer:
                raise AssetPlanError(f"duplicate asset key across source/product: {key}")
            producer[key] = job_key
            normalized_outputs.append({
                "asset_key": key,
                "media_type": _token(output.get("media_type"), f"{key}.media_type"),
                "variant": str(output.get("variant", "default")),
            })
        recipe_normalized = {
            "id": recipe_id,
            "version": recipe_version,
            "parameters": recipe.get("parameters", {}),
        }
        jobs[job_key] = {
            "job_key": job_key,
            "input_keys": input_keys,
            "outputs": sorted(normalized_outputs, key=lambda x: x["asset_key"]),
            "recipe": recipe_normalized,
            "recipe_digest": stable_digest(recipe_normalized),
        }
    return jobs, producer


def compile_processing_plan(
    *,
    project_namespace: str,
    source_assets: list[dict[str, Any]],
    dependency_edges: list[dict[str, Any]] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compile a deterministic, non-executing asset processing plan."""
    project_namespace = _token(project_namespace, "project_namespace")
    sources = _normalize_sources(project_namespace, source_assets)
    normalized_jobs, producer = _normalize_jobs(jobs or [], set(sources))
    all_keys = set(sources) | set(producer)

    edges_by_kind: dict[str, list[tuple[str, str]]] = {kind: [] for kind in DEPENDENCY_KINDS}
    unresolved_optional: list[dict[str, str]] = []
    for row in dependency_edges or []:
        if not isinstance(row, dict):
            raise AssetPlanError("dependency edge must be an object")
        consumer = _token(row.get("consumer_key"), "dependency.consumer_key")
        dependency = _token(row.get("dependency_key"), "dependency.dependency_key")
        kind = _token(row.get("kind"), "dependency.kind")
        if kind not in DEPENDENCY_KINDS:
            raise AssetPlanError(f"invalid dependency kind: {kind}")
        if consumer not in all_keys:
            raise AssetPlanError(f"dependency consumer unknown: {consumer}")
        if dependency not in all_keys:
            if kind == "OPTIONAL":
                unresolved_optional.append({
                    "consumer_key": consumer,
                    "dependency_key": dependency,
                    "kind": kind,
                })
                continue
            raise AssetPlanError(f"required dependency unknown: {consumer}->{dependency}")
        edges_by_kind[kind].append((consumer, dependency))

    # Job inputs are mandatory BUILD edges for each output.
    for job in normalized_jobs.values():
        for input_key in job["input_keys"]:
            if input_key not in all_keys:
                raise AssetPlanError(f"job input unknown: {job['job_key']}:{input_key}")
        for output in job["outputs"]:
            for input_key in job["input_keys"]:
                edges_by_kind["BUILD"].append((output["asset_key"], input_key))

    # Deduplicate deterministically.
    for kind in DEPENDENCY_KINDS:
        edges_by_kind[kind] = sorted(set(edges_by_kind[kind]))

    asset_order = _toposort(all_keys, edges_by_kind["BUILD"])

    # A job depends on any job producing one of its inputs.
    job_edges: list[tuple[str, str]] = []
    for job in normalized_jobs.values():
        for input_key in job["input_keys"]:
            parent_job = producer.get(input_key)
            if parent_job:
                job_edges.append((job["job_key"], parent_job))
    job_order = _toposort(set(normalized_jobs), sorted(set(job_edges))) if normalized_jobs else []

    build_deps: dict[str, list[str]] = defaultdict(list)
    for consumer, dependency in edges_by_kind["BUILD"]:
        build_deps[consumer].append(dependency)

    assets: dict[str, dict[str, Any]] = dict(sources)
    job_by_output = {output["asset_key"]: job for job in normalized_jobs.values() for output in job["outputs"]}
    for asset_key in asset_order:
        if asset_key in assets:
            continue
        job = job_by_output[asset_key]
        deps = sorted(set(build_deps.get(asset_key, [])))
        if not deps:
            raise AssetPlanError(f"product has no BUILD inputs: {asset_key}")
        dep_rows = [assets[key] for key in deps]
        rights = _rights_max([row["rights_state"] for row in dep_rows])
        logical_id = logical_asset_id(project_namespace, asset_key)
        output_decl = next(row for row in job["outputs"] if row["asset_key"] == asset_key)
        version_basis = {
            "logical_id": logical_id,
            "recipe_digest": job["recipe_digest"],
            "dependencies": [
                {"logical_id": row["logical_id"], "version_id": row["version_id"]}
                for row in dep_rows
            ],
            "output": output_decl,
        }
        assets[asset_key] = {
            "asset_key": asset_key,
            "role": "PRODUCT",
            "logical_id": logical_id,
            "version_id": "fa3assetver:v1:" + stable_digest(version_basis).split(":", 1)[1],
            "content_digest": None,
            "media_type": output_decl["media_type"],
            "rights_state": rights,
            "provenance_ref": f"job:{job['job_key']}",
            "source_locator": None,
            "recipe_digest": job["recipe_digest"],
            "input_asset_keys": deps,
        }

    ordered_jobs = []
    for job_key in job_order:
        job = normalized_jobs[job_key]
        input_rows = [assets[key] for key in job["input_keys"]]
        eligible = all(row["rights_state"] == "CLEARED" for row in input_rows)
        ordered_jobs.append({
            **job,
            "execution_eligible_if_executor_admitted": eligible,
            "execution_authorized_by_wp1": False,
            "output_logical_ids": {
                row["asset_key"]: assets[row["asset_key"]]["logical_id"]
                for row in job["outputs"]
            },
            "predicted_output_version_ids": {
                row["asset_key"]: assets[row["asset_key"]]["version_id"]
                for row in job["outputs"]
            },
        })

    def edge_rows(kind: str) -> list[dict[str, str]]:
        return [
            {"consumer_key": consumer, "dependency_key": dependency, "kind": kind}
            for consumer, dependency in edges_by_kind[kind]
        ]

    plan = {
        "schema": PLAN_SCHEMA,
        "project_namespace": project_namespace,
        "execution_authorized": False,
        "network_access_required": False,
        "file_transform_execution": False,
        "assets": [assets[key] for key in sorted(assets)],
        "asset_build_order": asset_order,
        "jobs": ordered_jobs,
        "job_build_order": job_order,
        "build_dependencies": edge_rows("BUILD"),
        "reference_dependencies": edge_rows("REFERENCE"),
        "optional_dependencies": edge_rows("OPTIONAL"),
        "unresolved_optional_dependencies": sorted(
            unresolved_optional,
            key=lambda x: (x["consumer_key"], x["dependency_key"]),
        ),
    }
    plan["plan_digest"] = stable_digest(plan)
    return plan


def compile_invalidation_plan(plan: dict[str, Any], changed_asset_keys: list[str]) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise AssetPlanError("invalid processing plan")
    known = {row["asset_key"] for row in plan.get("assets", [])}
    changed = sorted({_token(key, "changed_asset_key") for key in changed_asset_keys})
    unknown = sorted(set(changed) - known)
    if unknown:
        raise AssetPlanError("changed asset unknown: " + ",".join(unknown))

    reverse: dict[str, set[str]] = defaultdict(set)
    for edge in plan.get("build_dependencies", []):
        reverse[edge["dependency_key"]].add(edge["consumer_key"])

    affected = set(changed)
    queue = deque(changed)
    while queue:
        key = queue.popleft()
        for consumer in sorted(reverse.get(key, ())):
            if consumer not in affected:
                affected.add(consumer)
                queue.append(consumer)

    affected_jobs = sorted({
        job["job_key"]
        for job in plan.get("jobs", [])
        if any(output["asset_key"] in affected for output in job["outputs"])
    })
    result = {
        "schema": INVALIDATION_SCHEMA,
        "source_plan_digest": plan["plan_digest"],
        "changed_asset_keys": changed,
        "affected_asset_keys": sorted(affected),
        "affected_job_keys": affected_jobs,
        "automatic_rebuild_authorized": False,
    }
    result["invalidation_digest"] = stable_digest(result)
    return result
