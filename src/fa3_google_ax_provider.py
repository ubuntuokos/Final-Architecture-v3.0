#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
from typing import Any

from fa3_agent_workload import WorkloadContractError, validate_network_envelope, validate_task, validate_workspace

API_VERSION = "ax.io/v1alpha1"
UPSTREAM_COMMIT = "e6211f84a9e30dd309304167b8f1d51cbdaf8dab"
PROVIDER_ID = "FA3-PROVIDER-GOOGLE-AX-001"
BINDING_SCHEMA = "fa3.google-ax-provider-binding.v1"
PROJECTION_SCHEMA = "fa3.google-ax-provider-projection.v1"
AX_NAME_RE = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")
IMAGE_DIGEST_RE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
HOST_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$")
WORKSPACE_PATH_RE = re.compile(r"^/workspace(?:/[A-Za-z0-9._-]+)*$")
FORBIDDEN_BINDING_KEYS = {
    "api_key", "apikey", "password", "secret", "secret_value", "token", "bearer_token",
    "direct_model_provider", "provider_endpoint", "model_id", "physical_model_id",
}


class AxProviderBridgeError(ValueError):
    pass


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_BINDING_KEYS:
                raise AxProviderBridgeError(f"AX_BINDING_FORBIDDEN_FIELD:{path}.{key}")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")


def _ax_name(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not AX_NAME_RE.fullmatch(text):
        raise AxProviderBridgeError(f"AX_V1ALPHA1_NAME_UNREPRESENTABLE:{field}")
    return text


def validate_binding(binding: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        raise AxProviderBridgeError("AX_BINDING_SCHEMA_MISMATCH")
    if binding.get("provider_id") != PROVIDER_ID:
        raise AxProviderBridgeError("AX_BINDING_PROVIDER_MISMATCH")
    _ax_name(binding.get("atespace"), "atespace")
    _ax_name(binding.get("gateway_name"), "gateway_name")
    image = str(binding.get("runner_image", "")).strip()
    if not IMAGE_DIGEST_RE.fullmatch(image):
        raise AxProviderBridgeError("AX_RUNNER_IMAGE_MUST_BE_IMMUTABLE_DIGEST")
    command = binding.get("command")
    if not isinstance(command, list) or not command or any(not _nonempty(x) for x in command):
        raise AxProviderBridgeError("AX_COMMAND_INVALID")
    if binding.get("debug") is not False:
        raise AxProviderBridgeError("AX_DEBUG_REQUIRES_SEPARATE_UAF_SECURITY_APPROVAL")
    for key, expected in (
        ("resource_authority", "FA3-AUTH-HOST-RESOURCE-BROKER-001"),
        ("model_router_authority", "FA3-AUTH-MODEL-ROUTER-001"),
        ("mcp_gateway_authority", "FA3-AUTH-MCP-GATEWAY-001"),
    ):
        if binding.get(key) != expected:
            raise AxProviderBridgeError(f"AX_AUTHORITY_BINDING_MISMATCH:{key}")
    for key in ("hrb_admission_ref", "model_router_binding_ref", "mcp_gateway_binding_ref", "network_envelope_ref"):
        if not _nonempty(binding.get(key)):
            raise AxProviderBridgeError(f"AX_BINDING_REFERENCE_MISSING:{key}")
    order = binding.get("workspace_order")
    paths = binding.get("workspace_paths")
    if not isinstance(order, list) or any(not _nonempty(x) for x in order):
        raise AxProviderBridgeError("AX_WORKSPACE_ORDER_INVALID")
    if not isinstance(paths, dict) or set(paths) != set(order):
        raise AxProviderBridgeError("AX_WORKSPACE_PATH_BINDING_MISMATCH")
    seen_paths: set[str] = set()
    for wid in order:
        path = paths.get(wid)
        if not isinstance(path, str) or not WORKSPACE_PATH_RE.fullmatch(path):
            raise AxProviderBridgeError("AX_WORKSPACE_PATH_INVALID")
        if path in seen_paths:
            raise AxProviderBridgeError("AX_WORKSPACE_PATH_DUPLICATE")
        seen_paths.add(path)
    resources = binding.get("resources", {})
    if not isinstance(resources, dict) or set(resources) - {"requests", "limits"}:
        raise AxProviderBridgeError("AX_RESOURCE_PROJECTION_INVALID")
    for section in ("requests", "limits"):
        value = resources.get(section, {})
        if not isinstance(value, dict) or set(value) - {"cpu", "memory"}:
            raise AxProviderBridgeError("AX_RESOURCE_PROJECTION_INVALID")
        if any(not _nonempty(v) for v in value.values()):
            raise AxProviderBridgeError("AX_RESOURCE_PROJECTION_INVALID")
    _walk_forbidden(binding)
    return copy.deepcopy(binding)


def _validate_workspace_subset(workspace: dict[str, Any]) -> dict[str, Any]:
    checked = validate_workspace(workspace)
    if checked.get("bootstrap_goal"):
        raise AxProviderBridgeError("AX_WORKSPACE_GOAL_EXECUTION_AUTHORITY_FORBIDDEN")
    for source in checked.get("sources", []):
        kind = source.get("kind")
        if kind == "GIT":
            raise AxProviderBridgeError("AX_V1ALPHA1_IMMUTABLE_GIT_COMMIT_UNREPRESENTABLE")
        if kind == "SKILL":
            raise AxProviderBridgeError("AX_NATIVE_SKILL_REGISTRY_BYPASSES_FA3_SKILL_FABRIC")
        if kind == "MCP_CAPABILITY":
            raise AxProviderBridgeError("AX_NATIVE_MCP_CONFIG_BYPASSES_FA3_MCP_GATEWAY")
        raise AxProviderBridgeError(f"AX_WORKSPACE_SOURCE_NOT_REPRESENTABLE:{kind}")
    return checked


def _gateway_hosts(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    checked = validate_network_envelope(envelope)
    if checked.get("ingress"):
        raise AxProviderBridgeError("AX_INGRESS_PROJECTION_REQUIRES_SEPARATE_AUTHORIZATION")
    hosts: list[dict[str, Any]] = []
    for item in checked.get("egress", []):
        if not isinstance(item, dict) or set(item) != {"host", "port"}:
            raise AxProviderBridgeError("AX_EGRESS_RULE_UNREPRESENTABLE")
        host = str(item.get("host", "")).strip()
        port = item.get("port")
        if host == "*" or not HOST_RE.fullmatch(host):
            raise AxProviderBridgeError("AX_EGRESS_WILDCARD_OR_INVALID_HOST_FORBIDDEN")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise AxProviderBridgeError("AX_EGRESS_PORT_INVALID")
        hosts.append({"host": host, "port": port})
    return hosts


def compile_ax_provider_bridge(
    task: dict[str, Any],
    workspaces: list[dict[str, Any]],
    envelope: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    checked_task = validate_task(task)
    checked_binding = validate_binding(binding)
    if checked_binding["network_envelope_ref"] != checked_task["network_envelope_ref"]:
        raise AxProviderBridgeError("AX_NETWORK_BINDING_REF_MISMATCH")
    for key in checked_task.get("resource_requirements", {}):
        k = str(key).lower()
        if k.startswith(("gpu", "npu", "accelerator")):
            raise AxProviderBridgeError("AX_V1ALPHA1_ACCELERATOR_RESOURCE_UNREPRESENTABLE")
    checked_workspaces = [_validate_workspace_subset(w) for w in workspaces]
    ids = [w["workspace_id"] for w in checked_workspaces]
    if ids != checked_binding["workspace_order"]:
        raise AxProviderBridgeError("AX_WORKSPACE_ORDER_DOES_NOT_MATCH_INPUT")
    if checked_task.get("workspace_refs", []) != ids:
        raise AxProviderBridgeError("AX_TASK_WORKSPACE_REFS_DO_NOT_MATCH_PROVIDER_BINDING")

    manifests: list[dict[str, Any]] = []
    for workspace in checked_workspaces:
        wid = _ax_name(workspace["workspace_id"], "workspace_id")
        manifests.append({
            "apiVersion": API_VERSION,
            "kind": "Workspace",
            "metadata": {"name": wid, "atespace": checked_binding["atespace"]},
            "spec": {},
        })

    gateway_name = checked_binding["gateway_name"]
    manifests.append({
        "apiVersion": API_VERSION,
        "kind": "Gateway",
        "metadata": {"name": gateway_name, "atespace": checked_binding["atespace"]},
        "spec": {"egress": {"allowlist": {"hosts": _gateway_hosts(envelope)}}},
    })

    task_name = _ax_name(checked_task["task_id"], "task_id")
    spec: dict[str, Any] = {
        "image": checked_binding["runner_image"],
        "command": list(checked_binding["command"]),
        "workspaces": [
            {"name": wid, "path": checked_binding["workspace_paths"][wid]}
            for wid in checked_binding["workspace_order"]
        ],
        "gateway": {"name": gateway_name},
        "debug": False,
    }
    if checked_binding.get("resources"):
        spec["resources"] = copy.deepcopy(checked_binding["resources"])
    manifests.append({
        "apiVersion": API_VERSION,
        "kind": "Task",
        "metadata": {"name": task_name, "atespace": checked_binding["atespace"]},
        "spec": spec,
    })

    return {
        "schema": PROJECTION_SCHEMA,
        "provider_id": PROVIDER_ID,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_api_version": API_VERSION,
        "canonical_ir": False,
        "architectural_authority": False,
        "cluster_apply_ready": False,
        "cluster_apply_blocker": "FA3_CUSTOM_AX_RUNNER_AND_SCOPE_BOUND_CLUSTER_E2E_NOT_YET_MATERIALIZED",
        "manifests": manifests,
        "authority_bindings": {
            "resources": checked_binding["resource_authority"],
            "model_routing": checked_binding["model_router_authority"],
            "tool_mediation": checked_binding["mcp_gateway_authority"],
            "hrb_admission_ref": checked_binding["hrb_admission_ref"],
            "model_router_binding_ref": checked_binding["model_router_binding_ref"],
            "mcp_gateway_binding_ref": checked_binding["mcp_gateway_binding_ref"],
        },
        "non_emitted_resources": {
            "Model": "FORBIDDEN_FA3_MODEL_ROUTER_REMAINS_AUTHORITY",
            "Workspace.git": "FORBIDDEN_UNTIL_AX_CAN_REPRESENT_IMMUTABLE_COMMIT_OR_FA3_CUSTOM_RUNNER_MATERIALIZES_IT",
            "Workspace.mcp": "FORBIDDEN_CENTRAL_MCP_GATEWAY_REMAINS_AUTHORITY",
            "Workspace.skills": "FORBIDDEN_SKILL_FABRIC_REMAINS_ADMISSION_BOUNDARY",
            "Task.debug": "FORBIDDEN_WITHOUT_SEPARATE_EXPLICIT_UAF_SECURITY_APPROVAL",
        },
        "global_promotion_claim": False,
        "google_ax_runtime_promotion_claim": False,
    }
