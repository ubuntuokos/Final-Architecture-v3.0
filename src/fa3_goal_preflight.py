#!/usr/bin/env python3
"""FA3 source-bound goal design preflight. No runtime, authorization or evidence authority."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_agent_workload import validate_task
from fa3_application_donor_index import build_index
from fa3_goal_execution import GoalContractError, compile_plan, digest, validate_goal
from fa3_reuse_assessment import assess_intent
from fa3_uaf import ActionRegistry, UafError

SCHEMA = "fa3.goal-source-preflight.v1"
PLAN_SCHEMA = "fa3.goal-source-bound-plan.v1"
CANONICAL_INTENT_ROOT = Path("canonical/intents")
DONOR_REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
AGENT_REGISTRY = "canonical/FA3-AGENT-DEFINITION-REGISTRY-001.json"
ACTION_REGISTRY = "canonical/actions"
REFERENCE_FILES = (
    DONOR_REGISTRY,
    AGENT_REGISTRY,
    "canonical/FA3-REUSE-CATALOG-001.json",
    "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json",
    "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
    "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
)
REQUIRED_HARDWARE = {
    "vendor_neutral": True,
    "cpu_only_viable": True,
    "accelerator_cardinality": "0..N",
    "global_accelerator_requirement": False,
}
REQUIRED_SECURITY = {
    "authentication": "required",
    "authorization": "required",
    "audit": "required",
}


class GoalPreflightError(GoalContractError):
    pass


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise GoalPreflightError(f"invalid {label}")
    return value


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, check=False,
    )
    if result.returncode:
        raise GoalPreflightError("immutable repository source not available")
    return result.stdout


def _tracked_source(root: Path, rel: str) -> tuple[bytes, str]:
    """Require exact committed bytes; no dirty, symlink or untracked canonical input."""
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel:
        raise GoalPreflightError("canonical source path invalid")
    path = Path(rel)
    if ".." in path.parts or path.as_posix() != rel:
        raise GoalPreflightError("canonical path traversal forbidden")
    location = (root / rel).resolve()
    try:
        location.relative_to(root.resolve())
    except ValueError as exc:
        raise GoalPreflightError("canonical input outside repository") from exc
    if not location.is_file() or location.is_symlink():
        raise GoalPreflightError("missing or symlinked canonical input")
    committed = _git(root, "show", "HEAD:" + rel)
    current = location.read_bytes()
    if current != committed:
        raise GoalPreflightError("canonical source differs from immutable HEAD")
    return current, hashlib.sha256(committed).hexdigest()


def _load_committed_json(root: Path, rel: str) -> tuple[dict[str, Any], str]:
    raw, sha = _tracked_source(root, rel)
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise GoalPreflightError("canonical source is not valid JSON") from exc
    if not isinstance(data, dict):
        raise GoalPreflightError("canonical record must be object")
    return data, sha


def _intent_rel(path: str) -> str:
    _text(path, "intent path")
    p = Path(path)
    if p.suffix != ".json" or p.parent != CANONICAL_INTENT_ROOT or p.name.startswith("."):
        raise GoalPreflightError("goal intent must be a committed canonical/intents JSON file")
    return p.as_posix()


def _topological_steps(steps: list[dict[str, Any]], max_depth: int) -> dict[str, Any]:
    if not isinstance(steps, list) or not steps:
        raise GoalPreflightError("at least one step required")
    by_id: dict[str, dict[str, Any]] = {}
    for step in steps:
        if not isinstance(step, dict):
            raise GoalPreflightError("step must be an object")
        sid = _text(step.get("task_id"), "task_id")
        if sid in by_id:
            raise GoalPreflightError("duplicate goal task ID")
        dependencies = step.get("depends_on", [])
        if not isinstance(dependencies, list) or len(dependencies) != len(set(map(str, dependencies))):
            raise GoalPreflightError("duplicate or malformed dependency set")
        if any(not isinstance(dep, str) or not dep or dep.strip() != dep for dep in dependencies):
            raise GoalPreflightError("invalid dependency ID")
        by_id[sid] = step

    graph: dict[str, list[str]] = {}
    for sid, step in by_id.items():
        deps = list(step.get("depends_on", []))
        if sid in deps or any(dep not in by_id for dep in deps):
            raise GoalPreflightError("self-dependency or missing task dependency")
        graph[sid] = deps

    ordered: list[str] = []
    depth: dict[str, int] = {}
    marks: dict[str, int] = {}

    def visit(sid: str) -> int:
        state = marks.get(sid, 0)
        if state == 1:
            raise GoalPreflightError("cycle in goal task graph")
        if state == 2:
            return depth[sid]
        marks[sid] = 1
        predecessors = graph[sid]
        d = 1 + max((visit(dep) for dep in predecessors), default=0)
        if d > max_depth:
            raise GoalPreflightError("task dependency depth exceeds approved budget")
        depth[sid] = d
        marks[sid] = 2
        ordered.append(sid)
        return d

    for task_id in by_id:
        visit(task_id)
    return {
        "order": ordered,
        "dependencies": {sid: list(graph[sid]) for sid in ordered},
        "max_depth": max(depth.values()),
        "candidate_set_expanded": False,
        "executed": False,
    }


def design_preflight(root: Path | str, goal_value: dict[str, Any], intent_path: str,
                     steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Check committed source identities and actual existing design registries.

    This reads real committed FA3 metadata; it does NOT authenticate current-host
    Security/HRB/model/provider receipts or grant admission. The final runtime
    must revalidate current scope and collect real authority attestations.
    """
    root = Path(root).resolve()
    goal = validate_goal(goal_value)
    rel = _intent_rel(intent_path)
    snapshot_sha = _git(root, "rev-parse", "HEAD").decode().strip()
    if len(snapshot_sha) != 40:
        raise GoalPreflightError("repository must have immutable SHA-1 snapshot")

    sources: dict[str, str] = {}
    intent, sources[rel] = _load_committed_json(root, rel)
    if intent.get("schema") != "fa3.application-intent.v1":
        raise GoalPreflightError("unexpected ApplicationIntent schema")
    for k in ("id", "project_id"):
        _text(intent.get(k), k)
    for source in REFERENCE_FILES:
        record, sources[source] = _load_committed_json(root, source)
        if source == DONOR_REGISTRY:
            if record.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
                raise GoalPreflightError("donor source identity mismatch")
            entries = record.get("entries")
            if not isinstance(entries, list) or record.get("backfill", {}).get("entry_count") != len(entries):
                raise GoalPreflightError("donor registry source is incomplete")

    audit = intent.get("hardware_audit")
    if not isinstance(audit, dict) or any(audit.get(key) != value
                                          for key, value in REQUIRED_HARDWARE.items()):
        raise GoalPreflightError("mandatory portable Hardware Audit invalid")
    if audit.get("resource_authority") not in (None, "FA3-AUTH-HOST-RESOURCE-BROKER-001"):
        raise GoalPreflightError("hardware intent attempts different resource authority")
    if audit.get("model_route_authority") not in (None, "FA3-AUTH-MODEL-ROUTER-001"):
        raise GoalPreflightError("hardware intent attempts different route authority")

    reuse = assess_intent(root, intent)
    if reuse.get("result") != "PASS" or reuse.get("candidate_set_expansion") is not False:
        raise GoalPreflightError("existing Reuse Discovery blocks goal preflight")
    mandatory = reuse.get("mandatory_source_reviews", [])
    if not isinstance(mandatory, list) or not all(
        r.get("review_status") in {"MATCHED", "REVIEWED_NO_MATCH"}
        and r.get("authority") is False and r.get("automatic_selection") is False
        for r in mandatory if isinstance(r, dict)
    ) or any(not isinstance(r, dict) for r in mandatory):
        raise GoalPreflightError("mandatory source review incomplete")

    donor_index = build_index(root)
    if (donor_index.get("validation", {}).get("result") != "PASS"
            or donor_index.get("authority") is not False
            or donor_index.get("runtime_promotion") is not False):
        raise GoalPreflightError("application donor inventory failed")
    if (donor_index.get("counts", {}).get("donor_records") !=
            len(_load_committed_json(root, DONOR_REGISTRY)[0]["entries"])):
        raise GoalPreflightError("donor inventory cardinality mismatch")

    allowed_actions = set(goal["execution_policy"]["allowed_action_ids"])
    approved_roles = set(goal["execution_policy"]["authorized_ai_participants"])
    agent_registry, _ = _load_committed_json(root, AGENT_REGISTRY)
    if agent_registry.get("id") != "FA3-AGENT-DEFINITION-REGISTRY-001":
        raise GoalPreflightError("agent registry identity mismatch")
    definitions = {a["definition_id"]: a for a in agent_registry.get("definitions", [])
                   if isinstance(a, dict) and isinstance(a.get("definition_id"), str)}
    if len(definitions) != len(agent_registry.get("definitions", [])):
        raise GoalPreflightError("duplicate or invalid canonical agent definitions")

    actions = ActionRegistry.from_directory(root / ACTION_REGISTRY)
    graph = _topological_steps(steps, goal["execution_policy"]["limits"]["max_depth"])
    if len(steps) > goal["execution_policy"]["limits"]["max_children"]:
        raise GoalPreflightError("goal fanout exceeds approved child budget")
    audit_actions = []
    used_roles = set()
    for step in steps:
        action_id = _text(step.get("action_id"), "step.action_id")
        if action_id not in allowed_actions:
            raise GoalPreflightError("step action not in user's permitted set")
        try:
            action = actions.get(action_id)
        except UafError as exc:
            raise GoalPreflightError("unregistered UAF action") from exc
        if not action.source_path:
            raise GoalPreflightError("UAF action has no canonical source")
        action_rel = Path(action.source_path).resolve().relative_to(root).as_posix()
        _, sources[action_rel] = _load_committed_json(root, action_rel)
        if any(action.security.get(k) != value for k, value in REQUIRED_SECURITY.items()):
            raise GoalPreflightError("UAF action does not enforce authentication, authorization and audit")
        if action.evidence.get("required") is not True or action.exposure.get("agent") is not True:
            raise GoalPreflightError("UAF action missing agent-exposure or mandatory evidence")
        if type(action.semantics.get("mutating")) is not bool:
            raise GoalPreflightError("UAF action mutation semantics unspecified")
        actual_mutating = action.semantics["mutating"]
        effect = step.get("effect")
        if effect not in ({"WRITE", "DESTRUCTIVE"} if actual_mutating else {"READ"}):
            raise GoalPreflightError("declared action effect inconsistent with canonical UAF semantics")
        role = _text(step.get("agent_definition_ref"), "agent_definition_ref")
        if role not in approved_roles or role not in definitions:
            raise GoalPreflightError("agent role not in canonical and user-approved participant set")
        desc = definitions[role]
        if desc.get("direct_provider_execution") is not False or desc.get("authority_grants") != []:
            raise GoalPreflightError("agent definition exceeds non-authoritative projection")
        if desc.get("execution_runtime_claim") is not False:
            raise GoalPreflightError("agent metadata attempts unsupported runtime admission")
        used_roles.add(role)
        audit_actions.append({
            "task_id": step["task_id"],
            "action_id": action_id,
            "canonical_action_source": action_rel,
            "effect": effect,
            "agent_definition_ref": role,
            "requires_fresh_effect_authorization": True,
            "runtime_admission": "PENDING_INDEPENDENT_EXISTING_AUTHORITIES",
        })
    if not used_roles.issubset(approved_roles):
        raise GoalPreflightError("agent participant expansion forbidden")

    return {
        "schema": SCHEMA,
        "goal_id": goal["goal_id"], "goal_revision": goal["revision"],
        "goal_digest": digest(goal),
        "application_intent": rel, "application_intent_id": intent["id"],
        "application_project_id": intent["project_id"],
        "immutable_repository_commit": snapshot_sha,
        "source_sha256": dict(sorted(sources.items())),
        "reuse": {
            "profile_id": "FA3-REUSE-DISCOVERY-001",
            "result": reuse["result"],
            "implementation_readiness": reuse["implementation_readiness"],
            "gaps": list(reuse["gaps"]),
            "mandatory_source_reviews": copy.deepcopy(mandatory),
            "candidate_set_expanded": False,
            "automatic_activation": False,
        },
        "application_donor_index": {
            "source_catalogs": list(donor_index["source_catalogs"]),
            "donor_records": donor_index["counts"]["donor_records"],
            "validation": "PASS",
            "automatic_selection": False,
        },
        "hardware_audit": {
            **REQUIRED_HARDWARE,
            "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "model_route_authority": "FA3-AUTH-MODEL-ROUTER-001",
            "runtime_host_observation": "PENDING_CURRENT_HOST",
            "host_mutation": False,
            "display_gpu_task_model_assignment": "EXISTING_FA3_POLICY_ONLY",
        },
        "dag": graph,
        "actions": audit_actions,
        "external_admission": {
            "security_approval": "REQUIRES_EXISTING_AUTHORITY",
            "hrb_lease": "REQUIRES_FRESH_HRB_ADMISSION",
            "live_model_route": "REQUIRES_CURRENT_ROUTER_DISCOVERY",
            "runner": "REQUIRES_SCOPE_BOUND_CURRENT_HOST_EVIDENCE",
            "canonical_acceptance": "REQUIRES_INDEPENDENT_EVIDENCE_GATE",
        },
        "status": ("DESIGN_PREFLIGHT_COMPLETE_ADMISSION_PENDING"
                   if reuse["implementation_readiness"] == "READY_FOR_NORMAL_ADMISSION"
                   else "REUSE_GAPS_REQUIRE_HUMAN_REVIEW"),
        "authority": False,
        "runtime_admission": False,
        "execution_performed": False,
    }


def compile_source_bound_plan(root: Path | str, goal_value: dict[str, Any],
                              intent_path: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Join existing design-only GoalPlan with committed-source preflight and DAG."""
    preflight = design_preflight(root, goal_value, intent_path, steps)
    if preflight["status"] != "DESIGN_PREFLIGHT_COMPLETE_ADMISSION_PENDING":
        raise GoalPreflightError("reuse gaps or unresolved source reviews block plan compilation")
    goal = validate_goal(goal_value)
    refs = {
        "reuse_profile": "FA3-REUSE-DISCOVERY-001",
        "reuse_assessment_ref": "sha256:" + digest(preflight["reuse"]),
        "hardware_resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "hardware_audit_ref": "sha256:" + digest(preflight["hardware_audit"]),
        "model_route_authority": "FA3-AUTH-MODEL-ROUTER-001",
        "security_policy_ref": goal["execution_policy"]["policy_ref"],
    }
    plan = compile_plan(root, goal, steps, refs)
    for row in plan["steps"]:
        validate_task(row["workload_candidate"])
    return {
        "schema": PLAN_SCHEMA,
        "goal_digest": preflight["goal_digest"],
        "preflight": preflight,
        "goal_plan": plan,
        "dependency_graph": preflight["dag"],
        "status": "SOURCE_BOUND_DESIGN_ONLY",
        "requires_real_external_authority_admission": True,
        "canonical_evidence_verified": False,
        "runtime_admitted": False,
        "execution_performed": False,
        "authority": False,
    }
