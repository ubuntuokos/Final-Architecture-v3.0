#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from typing import Any

CAPABILITY_COUNT = 175
MODEL_ROUTER = "FA3-AUTH-MODEL-ROUTER-001"
HRB = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
SECRET_BROKER = "FA3-AUTH-SECRETS-001"
LICENSE_RIGHTS = "FA3-LICENSE-RIGHTS-001"
KDENLIVE = "FA3-KDENLIVE-EDITORIAL-001"

OPERATIONS = {
    "motion_graphics.render",
    "generated_media.attach",
    "digital_human.attach",
    "vision.track.attach",
    "vision.mask.attach",
    "neural_media.refine",
    "caption.attach",
    "dubbing.attach",
    "lipsync.attach",
    "translation.attach",
    "color.transform.attach",
    "external_render.attach",
}

RAW_SECRET_KEYS = {"api_key", "apikey", "token", "access_token", "secret", "password"}

class MediaPlanError(ValueError):
    pass

def _walk_raw_secret(value: Any, path: str = "") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key.lower() in RAW_SECRET_KEYS and child not in (None, "", False):
                return child_path
            found = _walk_raw_secret(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found = _walk_raw_secret(child, f"{path}[{i}]")
            if found:
                return found
    return None

def _base_plan(request: dict[str, Any]) -> dict[str, Any]:
    operation = str(request.get("operation", "")).strip()
    if operation not in OPERATIONS:
        raise MediaPlanError(f"unsupported operation: {operation}")
    if request.get("execute") is True or request.get("execution_requested") is True:
        raise MediaPlanError("reference planner never executes media/provider jobs")
    raw = _walk_raw_secret(request)
    if raw:
        raise MediaPlanError(f"raw secret forbidden at {raw}")
    project_id = str(request.get("project_id", "")).strip()
    if not project_id:
        raise MediaPlanError("project_id is required")
    return {
        "schema": "fa3.mlt-extended-media-plan.v1",
        "operation": operation,
        "project_id": project_id,
        "execution_requested": False,
        "canonical_timeline_ir": "OpenTimelineIO",
        "direct_native_project_mutation": False,
        "editorial_state_authority": KDENLIVE,
        "provider_model_routing_authority": MODEL_ROUTER,
        "host_resource_authority": HRB,
        "secret_authority": SECRET_BROKER,
        "license_rights_authority": LICENSE_RIGHTS,
        "silent_fallback": False,
        "capability_count": CAPABILITY_COUNT,
    }

def plan_hyperframes(request: dict[str, Any]) -> dict[str, Any]:
    plan = _base_plan({**request, "operation": "motion_graphics.render"})
    source = deepcopy(request.get("composition") or {})
    if not source.get("source_revision") or not source.get("source_hash"):
        raise MediaPlanError("HyperFrames composition requires immutable revision and source hash")
    plan.update({
        "engine_id": "FA3-ENGINE-HYPERFRAMES-001",
        "donor_id": "FA3-DONOR-HYPERFRAMES-001",
        "usage_edge": "FA3-USAGE-HYPERFRAMES-MLT-EXTENDED-MEDIA-001",
        "adapter_form": "ISOLATED_SIDECAR_WORKER",
        "editable_source_preserved": True,
        "preview_projection": "FRAME_OR_ASSET",
        "final_projection": "MATERIALIZED_CONTENT_ADDRESSED_MEDIA",
        "runtime_admission_required": True,
        "status": "STATIC_PLAN_RUNTIME_NOT_ADMITTED",
        "composition": source,
    })
    return plan

def plan_heygen(request: dict[str, Any]) -> dict[str, Any]:
    operation = str(request.get("operation", "digital_human.attach"))
    plan = _base_plan({**request, "operation": operation})
    if operation not in {
        "digital_human.attach", "dubbing.attach", "lipsync.attach", "translation.attach",
        "generated_media.attach"
    }:
        raise MediaPlanError("operation is not supported by the HeyGen provider projection")
    if not request.get("rights_decision_ref"):
        raise MediaPlanError("rights_decision_ref is required for digital-human media")
    if not request.get("secret_ref"):
        raise MediaPlanError("Secret Broker reference is required for remote provider planning")
    plan.update({
        "engine_id": "FA3-ENGINE-HEYGEN-001",
        "provider_id": "FA3-PROVIDER-HEYGEN-001",
        "execution_mode": "CLOUD",
        "cloud_execution_approved": bool(request.get("cloud_execution_approved", False)),
        "billable_execution_approved": bool(request.get("billable_execution_approved", False)),
        "secret_ref": request["secret_ref"],
        "rights_decision_ref": request["rights_decision_ref"],
        "provider_runtime_admitted": False,
        "status": "BLOCKED_RUNTIME_NOT_ADMITTED",
        "next_gate": "PROVIDER_RUNTIME_ADMISSION_AND_EXPLICIT_REMOTE_JOB_APPROVAL",
    })
    return plan

def timeline_binding(artifact: dict[str, Any], *, project_id: str, track_id: str) -> dict[str, Any]:
    if not artifact.get("sha256"):
        raise MediaPlanError("derived artifact sha256 is required")
    return {
        "schema": "fa3.generated-media-timeline-binding.v1",
        "project_id": project_id,
        "track_id": track_id,
        "artifact_sha256": artifact["sha256"],
        "timeline_contract": "FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001",
        "mutation_path": "TYPED_TIMELINE_OPERATION_DRY_RUN_DIFF_APPROVAL",
        "direct_kdenlive_project_xml_mutation": False,
        "source_artifact": deepcopy(artifact),
    }
