#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("canonical/FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001.json")
RUNTIME_PASS_STATES = {"PASS", "PROMOTED", "EXISTING_CANONICAL_AUTHORITY"}


class WorkforceContractError(ValueError):
    """Raised when a work request or workforce registry violates the canonical contract."""


@dataclass(frozen=True)
class Rejection:
    specialist_id: str
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"specialist_id": self.specialist_id, "reasons": list(self.reasons)}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    registry = _load_json(root / REGISTRY_REL)
    if registry.get("schema") != "fa3.orchestration-workforce-registry.v1":
        raise WorkforceContractError("unexpected workforce registry schema")
    if registry.get("id") != "FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001":
        raise WorkforceContractError("unexpected workforce registry id")
    if not isinstance(registry.get("specialists"), list) or not registry["specialists"]:
        raise WorkforceContractError("workforce registry must contain specialists")
    return registry


def _require_task_shape(task: dict[str, Any]) -> None:
    for key in ("task_id", "domain", "required_capabilities"):
        if key not in task:
            raise WorkforceContractError(f"work request missing required field: {key}")
    if not isinstance(task["task_id"], str) or not task["task_id"].strip():
        raise WorkforceContractError("task_id must be a non-empty string")
    if not isinstance(task["domain"], str) or not task["domain"].strip():
        raise WorkforceContractError("domain must be a non-empty string")
    if not isinstance(task["required_capabilities"], list) or not all(
        isinstance(v, str) and v for v in task["required_capabilities"]
    ):
        raise WorkforceContractError("required_capabilities must be a list of non-empty strings")
    auth = task.get("required_authorities", [])
    if not isinstance(auth, list) or not all(isinstance(v, str) and v for v in auth):
        raise WorkforceContractError("required_authorities must be a list of non-empty strings")
    forbidden = task.get("forbidden_specialists", [])
    if not isinstance(forbidden, list) or not all(isinstance(v, str) and v for v in forbidden):
        raise WorkforceContractError("forbidden_specialists must be a list of non-empty strings")


def _capability_set(specialist: dict[str, Any]) -> set[str]:
    return set(specialist.get("strong_capabilities", [])) | set(
        specialist.get("supported_capabilities", [])
    )


def _rejection_reasons(
    specialist: dict[str, Any],
    task: dict[str, Any],
    *,
    runtime_execution: bool,
) -> list[str]:
    reasons: list[str] = []
    sid = specialist.get("id", "")
    domain = task["domain"]
    required = set(task["required_capabilities"])
    required_authorities = set(task.get("required_authorities", []))
    forbidden_specialists = set(task.get("forbidden_specialists", []))

    if sid in forbidden_specialists:
        reasons.append("SPECIALIST_EXPLICITLY_FORBIDDEN")
    if not specialist.get("enabled_for_design", False):
        reasons.append("SPECIALIST_DISABLED")
    if domain not in set(specialist.get("domains", [])):
        reasons.append("DOMAIN_MISMATCH")

    anti = set(specialist.get("anti_capabilities", []))
    anti_collision = sorted(required & anti)
    if anti_collision:
        reasons.append("ANTI_CAPABILITY:" + ",".join(anti_collision))

    missing = sorted(required - _capability_set(specialist))
    if missing:
        reasons.append("MISSING_CAPABILITY:" + ",".join(missing))

    authority_scope = set(specialist.get("authority_scope", []))
    missing_authority = sorted(required_authorities - authority_scope)
    if missing_authority:
        reasons.append("MISSING_AUTHORITY_SCOPE:" + ",".join(missing_authority))

    if runtime_execution and specialist.get("runtime_promotion_status") not in RUNTIME_PASS_STATES:
        reasons.append("CURRENT_HOST_NOT_PROMOTED")

    return reasons


def _score(specialist: dict[str, Any], task: dict[str, Any]) -> tuple[int, str]:
    required = set(task["required_capabilities"])
    strong = set(specialist.get("strong_capabilities", []))
    supported = set(specialist.get("supported_capabilities", []))
    score = int(specialist.get("rank_bias", 0))
    score += len(required & strong) * 30
    score += len(required & supported) * 12
    priority = specialist.get("priority")
    score += {"P0": 12, "P1": 6, "P2": 0}.get(priority, 0)
    return score, specialist.get("id", "")


def route_task(
    root: Path | str,
    task: dict[str, Any],
    *,
    runtime_execution: bool | None = None,
) -> dict[str, Any]:
    """Route one provider-neutral FA3 task through hard filters then deterministic scoring."""
    _require_task_shape(task)
    registry = load_registry(root)
    runtime = bool(task.get("runtime_execution", False)) if runtime_execution is None else runtime_execution

    accepted: list[dict[str, Any]] = []
    rejected: list[Rejection] = []
    for specialist in registry["specialists"]:
        reasons = _rejection_reasons(specialist, task, runtime_execution=runtime)
        if reasons:
            rejected.append(Rejection(specialist["id"], tuple(reasons)))
        else:
            accepted.append(specialist)

    horizontal = registry.get("horizontal_authorities", [])
    if not accepted:
        return {
            "schema": "fa3.orchestration-route-decision.v1",
            "task_id": task["task_id"],
            "status": "HUMAN_ESCALATION",
            "reason": "NO_ELIGIBLE_SPECIALIST_AFTER_HARD_FILTERS",
            "runtime_execution": runtime,
            "horizontal_gates": horizontal,
            "rejected": [r.as_dict() for r in rejected],
        }

    ranked = sorted(accepted, key=lambda s: (-_score(s, task)[0], _score(s, task)[1]))
    winner = ranked[0]
    winner_score = _score(winner, task)[0]
    ties = [s for s in ranked if _score(s, task)[0] == winner_score]
    if len(ties) > 1 and task.get("require_unambiguous", False):
        return {
            "schema": "fa3.orchestration-route-decision.v1",
            "task_id": task["task_id"],
            "status": "HUMAN_ESCALATION",
            "reason": "AMBIGUOUS_TOP_SPECIALIST",
            "runtime_execution": runtime,
            "horizontal_gates": horizontal,
            "top_candidates": [
                {"specialist_id": s["id"], "provider": s["provider"], "score": winner_score}
                for s in ties
            ],
            "rejected": [r.as_dict() for r in rejected],
        }

    return {
        "schema": "fa3.orchestration-route-decision.v1",
        "task_id": task["task_id"],
        "status": "ROUTED",
        "runtime_execution": runtime,
        "specialist_id": winner["id"],
        "specialist_name": winner["name"],
        "provider": winner["provider"],
        "provider_id": winner["provider_id"],
        "score": winner_score,
        "authority_scope": winner.get("authority_scope", []),
        "horizontal_gates": horizontal,
        "fallback_candidates": [
            {"specialist_id": s["id"], "provider": s["provider"], "score": _score(s, task)[0]}
            for s in ranked[1:]
        ],
        "rejected": [r.as_dict() for r in rejected],
    }


def compile_cross_domain_plan(
    root: Path | str,
    request: dict[str, Any],
    *,
    runtime_execution: bool | None = None,
) -> dict[str, Any]:
    """Compile a provider-neutral work request into specialist route decisions."""
    tasks = request.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise WorkforceContractError("cross-domain request requires a non-empty tasks list")
    seen: set[str] = set()
    decisions = []
    for task in tasks:
        _require_task_shape(task)
        if task["task_id"] in seen:
            raise WorkforceContractError(f"duplicate task_id: {task['task_id']}")
        seen.add(task["task_id"])
        decisions.append(route_task(root, task, runtime_execution=runtime_execution))

    status = "READY" if all(d["status"] == "ROUTED" for d in decisions) else "HUMAN_REQUIRED"
    return {
        "schema": "fa3.cross-domain-work-plan.v1",
        "goal": request.get("goal", ""),
        "status": status,
        "director": "FA3-ORCHESTRATION-DIRECTOR-001",
        "provider_neutral": True,
        "decisions": decisions,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description="FA3 competency-driven orchestration workforce router")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--request", required=True, help="JSON work request containing tasks")
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="Require current-host-promoted specialists; pending providers are fail-closed",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    request = _load_json(Path(args.request))
    plan = compile_cross_domain_plan(root, request, runtime_execution=args.runtime)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(_main())
