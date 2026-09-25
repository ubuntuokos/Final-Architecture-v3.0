#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
from typing import Any

from fa3_google_ax_custom_runner import PLAN_SCHEMA, PROVIDER_ID
from fa3_google_ax_provider import PROJECTION_SCHEMA, UPSTREAM_COMMIT

APPLY_PLAN_SCHEMA = "fa3.google-ax-cluster-apply-plan.v1"
RUNNER_EVIDENCE_SCHEMA = "fa3.google-ax-runner-image-evidence.v1"
CLUSTER_BINDING_SCHEMA = "fa3.google-ax-cluster-binding.v1"
IMAGE_DIGEST_RE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$")
NAMESPACE_RE = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")


class AxClusterApplyError(ValueError):
    pass


def _nonempty_ref(value: Any, code: str) -> str:
    text = str(value or "").strip()
    if not REF_RE.fullmatch(text):
        raise AxClusterApplyError(code)
    return text


def validate_runner_image_evidence(evidence: dict[str, Any], expected_image: str) -> dict[str, Any]:
    if not isinstance(evidence, dict) or evidence.get("schema") != RUNNER_EVIDENCE_SCHEMA:
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_EVIDENCE_SCHEMA_MISMATCH")
    image = str(evidence.get("runner_image", "")).strip()
    if image != expected_image or not IMAGE_DIGEST_RE.fullmatch(image):
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_IMAGE_EVIDENCE_MISMATCH")
    if evidence.get("build_verified") is not True or evidence.get("digest_verified") is not True:
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_IMAGE_EVIDENCE_NOT_VERIFIED")
    _nonempty_ref(evidence.get("evidence_ref"), "AX_CLUSTER_RUNNER_EVIDENCE_REF_INVALID")
    if evidence.get("current_host_runtime_promotion_claim") is not False:
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_EVIDENCE_PROMOTION_CLAIM_FORBIDDEN")
    return copy.deepcopy(evidence)


def validate_cluster_binding(binding: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(binding, dict) or binding.get("schema") != CLUSTER_BINDING_SCHEMA:
        raise AxClusterApplyError("AX_CLUSTER_BINDING_SCHEMA_MISMATCH")
    namespace = str(binding.get("namespace", "")).strip()
    if not NAMESPACE_RE.fullmatch(namespace):
        raise AxClusterApplyError("AX_CLUSTER_NAMESPACE_INVALID")
    for key, code in (
        ("cluster_scope_ref", "AX_CLUSTER_SCOPE_REF_INVALID"),
        ("kubernetes_context_ref", "AX_CLUSTER_CONTEXT_REF_INVALID"),
        ("agent_substrate_ref", "AX_CLUSTER_SUBSTRATE_REF_INVALID"),
        ("security_approval_ref", "AX_CLUSTER_SECURITY_APPROVAL_REF_INVALID"),
    ):
        _nonempty_ref(binding.get(key), code)
    if binding.get("scope_bound") is not True:
        raise AxClusterApplyError("AX_CLUSTER_SCOPE_MUST_BE_BOUND")
    if binding.get("debug_guest_services_authorized") is not False:
        raise AxClusterApplyError("AX_CLUSTER_DEBUG_GUEST_SERVICES_FORBIDDEN")
    forbidden = {"kubeconfig", "token", "password", "client_key", "client_certificate_data"}
    if forbidden.intersection(binding):
        raise AxClusterApplyError("AX_CLUSTER_RAW_CREDENTIAL_MATERIAL_FORBIDDEN")
    return copy.deepcopy(binding)


def compile_cluster_apply_plan(
    provider_projection: dict[str, Any],
    runner_plan: dict[str, Any],
    runner_image_evidence: dict[str, Any],
    cluster_binding: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(provider_projection, dict) or provider_projection.get("schema") != PROJECTION_SCHEMA:
        raise AxClusterApplyError("AX_CLUSTER_PROVIDER_PROJECTION_SCHEMA_MISMATCH")
    if provider_projection.get("provider_id") != PROVIDER_ID or provider_projection.get("upstream_commit") != UPSTREAM_COMMIT:
        raise AxClusterApplyError("AX_CLUSTER_PROVIDER_PROJECTION_IDENTITY_MISMATCH")
    if provider_projection.get("google_ax_runtime_promotion_claim") is not False:
        raise AxClusterApplyError("AX_CLUSTER_PROVIDER_PROJECTION_PROMOTION_CLAIM_FORBIDDEN")
    manifests = provider_projection.get("manifests")
    if not isinstance(manifests, list) or [m.get("kind") for m in manifests] != ["Workspace", "Gateway", "Task"]:
        raise AxClusterApplyError("AX_CLUSTER_MANIFEST_SET_INVALID")
    if any(m.get("apiVersion") != "ax.io/v1alpha1" for m in manifests) or any(m.get("kind") == "Model" for m in manifests):
        raise AxClusterApplyError("AX_CLUSTER_MANIFEST_AUTHORITY_BYPASS_FORBIDDEN")

    if not isinstance(runner_plan, dict) or runner_plan.get("schema") != PLAN_SCHEMA:
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_PLAN_SCHEMA_MISMATCH")
    if runner_plan.get("provider_id") != PROVIDER_ID or runner_plan.get("upstream_commit") != UPSTREAM_COMMIT:
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_PLAN_IDENTITY_MISMATCH")
    if runner_plan.get("google_ax_runtime_promotion_claim") is not False:
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_PLAN_PROMOTION_CLAIM_FORBIDDEN")

    task_manifest = manifests[-1]
    image = str(task_manifest.get("spec", {}).get("image", "")).strip()
    if image != runner_plan.get("runner_image"):
        raise AxClusterApplyError("AX_CLUSTER_RUNNER_IMAGE_BINDING_MISMATCH")
    evidence = validate_runner_image_evidence(runner_image_evidence, image)
    cluster = validate_cluster_binding(cluster_binding)

    provider_authority = provider_projection.get("authority_bindings", {})
    runner_authority = runner_plan.get("authority_bindings", {})
    required = {
        "resources": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "model_routing": "FA3-AUTH-MODEL-ROUTER-001",
        "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
    }
    for key, expected in required.items():
        if provider_authority.get(key) != expected or runner_authority.get(key) != expected:
            raise AxClusterApplyError(f"AX_CLUSTER_AUTHORITY_BINDING_MISMATCH:{key}")

    return {
        "schema": APPLY_PLAN_SCHEMA,
        "provider_id": PROVIDER_ID,
        "upstream_commit": UPSTREAM_COMMIT,
        "canonical_ir": False,
        "architectural_authority": False,
        "cluster_scope_ref": cluster["cluster_scope_ref"],
        "kubernetes_context_ref": cluster["kubernetes_context_ref"],
        "agent_substrate_ref": cluster["agent_substrate_ref"],
        "security_approval_ref": cluster["security_approval_ref"],
        "namespace": cluster["namespace"],
        "runner_image": image,
        "runner_image_evidence_ref": evidence["evidence_ref"],
        "apply_order": ["Workspace", "Gateway", "Task"],
        "manifests": copy.deepcopy(manifests),
        "server_side_apply": True,
        "force_conflicts": False,
        "dry_run_required_before_apply": True,
        "scope_bound_cluster_e2e_required": True,
        "cluster_apply_adapter_materialized": True,
        "runtime_promotion_eligible": False,
        "google_ax_runtime_promotion_claim": False,
        "global_promotion_claim": False,
    }
