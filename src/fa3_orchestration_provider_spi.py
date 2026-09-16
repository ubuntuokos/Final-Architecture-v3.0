#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fa3_orchestration_workforce import RUNTIME_PASS_STATES, WorkforceContractError, load_registry

SPI_REL = Path("canonical/contracts/FA3-ORCHESTRATION-PROVIDER-SPI-001.json")


class ProviderAdapterError(WorkforceContractError):
    """Raised when a specialist route cannot be projected into a provider adapter envelope."""


class ProviderRuntimeNotPromoted(ProviderAdapterError):
    """Raised when a provider adapter is requested for runtime without current-host promotion."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_spi_contract(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    contract = _load_json(root / SPI_REL)
    if contract.get("schema") != "fa3.provider-spi-contract.v1":
        raise ProviderAdapterError("unexpected provider SPI schema")
    if contract.get("id") != "FA3-ORCHESTRATION-PROVIDER-SPI-001":
        raise ProviderAdapterError("unexpected provider SPI id")
    return contract


def _specialist_by_id(registry: dict[str, Any], specialist_id: str) -> dict[str, Any]:
    for specialist in registry.get("specialists", []):
        if specialist.get("id") == specialist_id:
            return specialist
    raise ProviderAdapterError(f"unknown specialist: {specialist_id}")


def _authority_names(registry: dict[str, Any]) -> list[str]:
    return [entry["authority"] for entry in registry.get("horizontal_authorities", []) if entry.get("authority")]


def compile_provider_envelope(
    root: Path | str,
    task: dict[str, Any],
    route_decision: dict[str, Any],
    *,
    runtime_execution: bool = False,
) -> dict[str, Any]:
    """Compile a routed FA3 task into a non-canonical provider invocation envelope.

    This function intentionally does not import provider SDKs. It proves the adapter seam,
    authority inheritance and fail-closed promotion rules. Actual runtime connectors remain
    separate provider materializations and require executable current-host evidence.
    """
    if route_decision.get("schema") != "fa3.orchestration-route-decision.v1":
        raise ProviderAdapterError("route decision schema mismatch")
    if route_decision.get("status") != "ROUTED":
        raise ProviderAdapterError("only ROUTED decisions may be compiled")
    if route_decision.get("task_id") != task.get("task_id"):
        raise ProviderAdapterError("task_id mismatch between task and route decision")

    registry = load_registry(root)
    spi = load_spi_contract(root)
    specialist = _specialist_by_id(registry, route_decision["specialist_id"])
    provider_id = specialist.get("provider_id")
    adapter_kind = spi.get("adapter_kinds", {}).get(provider_id)
    if not adapter_kind:
        raise ProviderAdapterError(f"no adapter kind registered for provider: {provider_id}")

    route_scope = set(route_decision.get("authority_scope", []))
    specialist_scope = set(specialist.get("authority_scope", []))
    if not route_scope.issubset(specialist_scope):
        raise ProviderAdapterError("route decision attempted to expand specialist authority scope")

    if runtime_execution and specialist.get("runtime_promotion_status") not in RUNTIME_PASS_STATES:
        raise ProviderRuntimeNotPromoted(
            f"provider {provider_id} is not promoted for current-host runtime: "
            f"{specialist.get('runtime_promotion_status')}"
        )

    required_capabilities = list(task.get("required_capabilities", []))
    required_authorities = list(task.get("required_authorities", []))
    canonical_authorities = _authority_names(registry)

    return {
        "schema": "fa3.provider-invocation-envelope.v1",
        "canonical": False,
        "task_id": task["task_id"],
        "specialist_id": specialist["id"],
        "provider": specialist["provider"],
        "provider_id": provider_id,
        "adapter_kind": adapter_kind,
        "mode": "runtime" if runtime_execution else "design",
        "provider_promotion_status": specialist.get("runtime_promotion_status"),
        "delegated_capabilities": required_capabilities,
        "delegated_authority_scope": sorted(route_scope),
        "required_authorities": required_authorities,
        "horizontal_authorities": canonical_authorities,
        "provider_payload": {
            "domain": task["domain"],
            "objective": task.get("objective") or task.get("description") or task["task_id"],
            "capabilities": required_capabilities,
            "metadata": task.get("metadata", {}),
        },
        "constraints": {
            "provider_native_schema_is_canonical": False,
            "may_expand_authority": False,
            "must_return_evidence_to_fa3": True,
            "must_reenter_horizontal_gates_for_consequential_actions": True,
        },
    }


def compile_plan_envelopes(
    root: Path | str,
    request: dict[str, Any],
    plan: dict[str, Any],
    *,
    runtime_execution: bool = False,
) -> dict[str, Any]:
    if plan.get("schema") != "fa3.cross-domain-work-plan.v1":
        raise ProviderAdapterError("cross-domain plan schema mismatch")
    tasks = {task["task_id"]: task for task in request.get("tasks", [])}
    envelopes = []
    for decision in plan.get("decisions", []):
        if decision.get("status") != "ROUTED":
            raise ProviderAdapterError(
                f"plan contains unresolved decision for task {decision.get('task_id')}"
            )
        task = tasks.get(decision.get("task_id"))
        if task is None:
            raise ProviderAdapterError(f"plan decision references unknown task: {decision.get('task_id')}")
        envelopes.append(
            compile_provider_envelope(
                root,
                task,
                decision,
                runtime_execution=runtime_execution,
            )
        )
    return {
        "schema": "fa3.provider-adapter-plan.v1",
        "canonical": False,
        "source_plan_schema": plan["schema"],
        "mode": "runtime" if runtime_execution else "design",
        "envelopes": envelopes,
    }
