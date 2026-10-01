#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from typing import Any

PLUGIN_ID = "FA3-SHARED-REAL2SIM-3D-001"
REQUEST_SCHEMA = "fa3.shared-real2sim-3d.request.v1"
PLAN_SCHEMA = "fa3.shared-real2sim-3d.plan.v1"
HANDOFF_SCHEMA = "fa3.shared-real2sim-3d.dcc-handoff.v1"

CAPABILITY_BINDINGS = ("CAP-032", "CAP-163", "CAP-164", "CAP-166", "CAP-167")

ALLOWED_FEATURES = {
    "ROOM_GEOMETRY",
    "CAMERA_RECOVERY",
    "ACTOR_RECONSTRUCTION",
    "CONTACT_REFINEMENT",
    "MOTION_TRANSFER",
    "SCENE_VARIANTS",
    "PLACEMENT_VALIDATION",
    "PREVIEW_REVIEW",
}

HOSTS = {
    "BFORARTISTS": {
        "role": "PRIMARY_DCC_HOST",
        "compatibility": "BLENDER_ENGINE_COMPATIBLE",
        "direct_host_mutation": False,
    },
    "BLENDER": {
        "role": "COMPATIBILITY_DCC_HOST",
        "compatibility": "BLENDER_NATIVE_COMPATIBILITY_ADAPTER",
        "direct_host_mutation": False,
    },
}

STAGE_SPECS = {
    "SOURCE_ANALYSIS": {
        "features": ALLOWED_FEATURES,
        "capabilities": ("CAP-167",),
        "profile": "FA3-SHARED-MULTIMODAL-SOURCE-001",
    },
    "ROOM_RECONSTRUCTION": {
        "features": {"ROOM_GEOMETRY", "PLACEMENT_VALIDATION", "SCENE_VARIANTS"},
        "capabilities": ("CAP-032",),
        "profile": "FA3-DIFFERENTIABLE-3D-001",
    },
    "CAMERA_RECOVERY": {
        "features": {"CAMERA_RECOVERY"},
        "capabilities": ("CAP-032", "CAP-166"),
        "profile": "FA3-DIFFERENTIABLE-3D-001",
    },
    "ACTOR_RECONSTRUCTION": {
        "features": {"ACTOR_RECONSTRUCTION", "CONTACT_REFINEMENT", "MOTION_TRANSFER"},
        "capabilities": ("CAP-164", "CAP-166"),
        "profile": "FA3-HUMAN-MOTION-001",
    },
    "CONTACT_REFINEMENT": {
        "features": {"CONTACT_REFINEMENT"},
        "capabilities": ("CAP-164", "CAP-166"),
        "profile": "FA3-HUMAN-MOTION-001",
    },
    "MOTION_TRANSFER": {
        "features": {"MOTION_TRANSFER"},
        "capabilities": ("CAP-164",),
        "profile": "FA3-HUMAN-MOTION-001",
    },
    "SCENE_ASSEMBLY": {
        "features": ALLOWED_FEATURES,
        "capabilities": ("CAP-166",),
        "profile": "FA3-DCC-RT3D-001",
    },
    "PLACEMENT_VALIDATION": {
        "features": {"PLACEMENT_VALIDATION", "CONTACT_REFINEMENT"},
        "capabilities": ("CAP-032", "CAP-166"),
        "profile": "FA3-3D-GEOM-001",
    },
    "PREVIEW_REVIEW": {
        "features": {"PREVIEW_REVIEW"},
        "capabilities": ("CAP-163", "CAP-166"),
        "profile": "FA3-DCC-RT3D-001",
    },
}


class Real2Sim3DError(ValueError):
    pass


def _require_nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Real2Sim3DError(f"{name} must be a non-empty string")
    return value.strip()


def _normalize_features(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise Real2Sim3DError("features must be a non-empty list")
    if not all(isinstance(item, str) for item in value):
        raise Real2Sim3DError("features must contain strings only")
    unknown = sorted(set(value) - ALLOWED_FEATURES)
    if unknown:
        raise Real2Sim3DError(f"unsupported features: {unknown}")
    return sorted(set(value))


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise Real2Sim3DError("request must be an object")
    if request.get("schema") != REQUEST_SCHEMA:
        raise Real2Sim3DError("request schema mismatch")
    _require_nonempty_string(request.get("project_id"), "project_id")
    _require_nonempty_string(request.get("source_asset_ref"), "source_asset_ref")
    features = _normalize_features(request.get("features"))
    host = request.get("dcc_host", "BFORARTISTS")
    if host not in HOSTS:
        raise Real2Sim3DError(f"unsupported dcc_host: {host}")
    if request.get("ai_enabled") not in (True, False):
        raise Real2Sim3DError("ai_enabled must be an explicit boolean")
    if request.get("allow_network") not in (True, False):
        raise Real2Sim3DError("allow_network must be an explicit boolean")
    if request.get("commit_to_dcc") not in (True, False):
        raise Real2Sim3DError("commit_to_dcc must be an explicit boolean")
    if request.get("commit_to_dcc") and not request.get("approval_ref"):
        raise Real2Sim3DError("commit_to_dcc requires approval_ref")
    return {
        "result": "PASS",
        "project_id": request["project_id"],
        "feature_count": len(features),
        "dcc_host": host,
    }


def _stage_enabled(name: str, requested: set[str]) -> bool:
    if name in {"SOURCE_ANALYSIS", "SCENE_ASSEMBLY"}:
        return True
    return bool(STAGE_SPECS[name]["features"] & requested)


def build_plan(request: dict[str, Any]) -> dict[str, Any]:
    validate_request(request)
    features = set(_normalize_features(request["features"]))
    host = request.get("dcc_host", "BFORARTISTS")
    stages: list[dict[str, Any]] = []
    for name, spec in STAGE_SPECS.items():
        if not _stage_enabled(name, features):
            continue
        stages.append({
            "stage": name,
            "profile": spec["profile"],
            "capability_bindings": list(spec["capabilities"]),
            "provider_selection": "FA3-AUTH-MODEL-ROUTER-001",
            "resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "action_execution": "FA3-UNIFIED-ACTION-FABRIC-001",
            "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
            "status": "PLANNED_NOT_EXECUTED",
        })
    return {
        "schema": PLAN_SCHEMA,
        "plugin_id": PLUGIN_ID,
        "project_id": request["project_id"],
        "source_asset_ref": request["source_asset_ref"],
        "features": sorted(features),
        "dcc_host": deepcopy(HOSTS[host]),
        "dcc_host_id": host,
        "stages": stages,
        "capability_bindings": list(CAPABILITY_BINDINGS),
        "geometry_authority": "FA3-3D-GEOM-001",
        "dcc_scene_and_final_asset_authority": "FA3-DCC-RT3D-001",
        "workflow_authority": "FA3-AUTH-DURABLE-ORCHESTRATION-001",
        "model_provider_selection": "FA3-AUTH-MODEL-ROUTER-001",
        "host_resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "action_execution": "FA3-UNIFIED-ACTION-FABRIC-001",
        "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
        "ai_enabled": request["ai_enabled"],
        "network_requested": request["allow_network"],
        "network_authorized_by_plan": False,
        "execution_authorized": False,
        "direct_dcc_mutation_authorized": False,
        "human_review_required_before_dcc_commit": True,
        "approval_ref": request.get("approval_ref"),
        "commit_requested": request["commit_to_dcc"],
        "cpu_only_control_path_valid": True,
        "compute_stage_without_compatible_provider": "UNAVAILABLE_NO_SILENT_FALLBACK",
        "display_gpu_implicit_enlistment": False,
        "hardware_mutation": False,
        "new_service": False,
        "new_daemon": False,
        "new_port": False,
        "global_environment_mutation": False,
        "upstream_aha3d_runtime_dependency": False,
        "upstream_code_copied": False,
        "current_host_runtime_promotion_claim": False,
    }


def build_dcc_handoff(plan: dict[str, Any], approval_receipt: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise Real2Sim3DError("plan schema mismatch")
    if not isinstance(approval_receipt, dict):
        raise Real2Sim3DError("approval_receipt must be an object")
    approval_id = _require_nonempty_string(approval_receipt.get("id"), "approval_receipt.id")
    if approval_receipt.get("approved") is not True:
        raise Real2Sim3DError("DCC handoff requires explicit approved receipt")
    if approval_receipt.get("project_id") != plan.get("project_id"):
        raise Real2Sim3DError("approval project_id does not match plan")
    return {
        "schema": HANDOFF_SCHEMA,
        "plugin_id": PLUGIN_ID,
        "project_id": plan["project_id"],
        "dcc_host_id": plan["dcc_host_id"],
        "approval_ref": approval_id,
        "scene_authority": "FA3-DCC-RT3D-001",
        "action_execution": "FA3-UNIFIED-ACTION-FABRIC-001",
        "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
        "direct_host_mutation": False,
        "adapter_commit_requested": True,
        "execution_authorized_by_this_handoff": False,
        "native_project_preservation_required": True,
        "blender_compatible_interchange_required": True,
    }


def plugin_manifest() -> dict[str, Any]:
    return {
        "id": PLUGIN_ID,
        "kind": "SHARED_3D_PLUGIN_CORE",
        "provider_neutral": True,
        "new_capability": False,
        "new_architectural_authority": False,
        "capability_count": 175,
        "capability_bindings": list(CAPABILITY_BINDINGS),
        "hosts": deepcopy(HOSTS),
        "authority": False,
        "runtime_dependency_on_aha3d": False,
        "upstream_bridge_status": "ANALYSIS_ONLY_NOT_ADMITTED",
        "current_host_runtime_promotion_claim": False,
    }
