#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
from typing import Any
from urllib.parse import urlparse

from fa3_agent_workload import validate_network_envelope, validate_task, validate_workspace
from fa3_google_ax_provider import AxProviderBridgeError, UPSTREAM_COMMIT, validate_binding

PLAN_SCHEMA = "fa3.google-ax-custom-runner-plan.v1"
PROVIDER_ID = "FA3-PROVIDER-GOOGLE-AX-001"
HEX_COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class AxCustomRunnerError(ValueError):
    pass


def _repo_host(repo: str) -> str:
    parsed = urlparse(repo)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise AxCustomRunnerError("AX_RUNNER_GIT_REPO_MUST_BE_HTTPS_WITHOUT_EMBEDDED_CREDENTIALS")
    return parsed.hostname.lower()


def _allowed_egress(envelope: dict[str, Any]) -> set[tuple[str, int]]:
    checked = validate_network_envelope(envelope)
    return {(str(x["host"]).lower(), int(x["port"])) for x in checked.get("egress", [])}


def compile_custom_runner_plan(
    task: dict[str, Any],
    workspaces: list[dict[str, Any]],
    envelope: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    checked_task = validate_task(task)
    checked_binding = validate_binding(binding)
    checked_envelope = validate_network_envelope(envelope)

    if checked_binding["network_envelope_ref"] != checked_task["network_envelope_ref"]:
        raise AxCustomRunnerError("AX_RUNNER_NETWORK_BINDING_REF_MISMATCH")
    if checked_envelope.get("ingress"):
        raise AxCustomRunnerError("AX_RUNNER_INGRESS_NOT_MATERIALIZED")
    if checked_envelope.get("direct_model_provider_access") is not False:
        raise AxCustomRunnerError("AX_RUNNER_DIRECT_MODEL_PROVIDER_BYPASS_FORBIDDEN")
    if checked_envelope.get("direct_external_tool_access") is not False:
        raise AxCustomRunnerError("AX_RUNNER_DIRECT_EXTERNAL_TOOL_BYPASS_FORBIDDEN")

    checked_workspaces = [validate_workspace(w) for w in workspaces]
    ids = [w["workspace_id"] for w in checked_workspaces]
    if ids != checked_binding["workspace_order"] or checked_task.get("workspace_refs", []) != ids:
        raise AxCustomRunnerError("AX_RUNNER_WORKSPACE_BINDING_MISMATCH")

    allowed = _allowed_egress(checked_envelope)
    materializations: list[dict[str, Any]] = []
    for workspace in checked_workspaces:
        wid = workspace["workspace_id"]
        target = checked_binding["workspace_paths"][wid]
        sources = workspace.get("sources", [])
        if len(sources) > 1:
            raise AxCustomRunnerError("AX_RUNNER_MULTISOURCE_WORKSPACE_NOT_MATERIALIZED")
        if not sources:
            materializations.append({
                "workspace_id": wid,
                "target_path": target,
                "mode": "EMPTY",
                "steps": [],
            })
            continue

        source = sources[0]
        if source.get("kind") != "GIT":
            raise AxCustomRunnerError(f"AX_RUNNER_WORKSPACE_SOURCE_FORBIDDEN:{source.get('kind')}")
        repo = str(source.get("repo", ""))
        commit = str(source.get("commit", "")).lower()
        if not HEX_COMMIT_RE.fullmatch(commit):
            raise AxCustomRunnerError("AX_RUNNER_IMMUTABLE_GIT_COMMIT_INVALID")
        host = _repo_host(repo)
        if (host, 443) not in allowed:
            raise AxCustomRunnerError("AX_RUNNER_GIT_HOST_NOT_IN_NETWORK_ENVELOPE")

        materializations.append({
            "workspace_id": wid,
            "target_path": target,
            "mode": "IMMUTABLE_GIT_COMMIT",
            "repository": repo,
            "commit": commit,
            "detached_checkout": True,
            "steps": [
                {"op": "git_init", "path": target},
                {"op": "git_remote_add", "path": target, "name": "origin", "repository": repo},
                {"op": "git_fetch_commit", "path": target, "remote": "origin", "commit": commit, "depth": 1},
                {"op": "git_checkout_detached", "path": target, "commit": commit},
                {"op": "git_verify_head", "path": target, "expected_commit": commit},
            ],
        })

    return {
        "schema": PLAN_SCHEMA,
        "provider_id": PROVIDER_ID,
        "upstream_commit": UPSTREAM_COMMIT,
        "canonical_ir": False,
        "architectural_authority": False,
        "task_id": checked_task["task_id"],
        "runner_image": checked_binding["runner_image"],
        "runner_command": copy.deepcopy(checked_binding["command"]),
        "workspace_materializations": materializations,
        "authority_bindings": {
            "resources": checked_binding["resource_authority"],
            "hrb_admission_ref": checked_binding["hrb_admission_ref"],
            "model_routing": checked_binding["model_router_authority"],
            "model_router_binding_ref": checked_binding["model_router_binding_ref"],
            "tool_mediation": checked_binding["mcp_gateway_authority"],
            "mcp_gateway_binding_ref": checked_binding["mcp_gateway_binding_ref"],
        },
        "network": {
            "envelope_ref": checked_binding["network_envelope_ref"],
            "default": "DENY",
            "direct_model_provider_access": False,
            "direct_external_tool_access": False,
        },
        "secret_material_embedded": False,
        "cluster_apply_ready": False,
        "runner_image_build_evidence_required": True,
        "scope_bound_cluster_e2e_required": True,
        "google_ax_runtime_promotion_claim": False,
        "global_promotion_claim": False,
    }
