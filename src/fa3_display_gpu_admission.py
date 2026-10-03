#!/usr/bin/env python3
"""Fail-closed, provider-neutral display GPU AI admission policy.

The HRB must supply trusted live inventory and verified display headroom.
The central Model Router must separately verify the model selection receipt.
This structural checker must never authenticate application-provided claims.
"""
from __future__ import annotations
from typing import Any

POLICY_ID = "FA3-DISPLAY-GPU-ADMISSION-001"
HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
ROUTER_AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
INVENTORY_SCHEMA = "fa3.hrb-live-accelerator-inventory.v1"


def _filled(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _result(errors: list[str], *, mode: str = "DENIED") -> dict[str, Any]:
    return {
        "schema": "fa3.display-gpu-admission-decision.v1",
        "policy_id": POLICY_ID,
        "result": "PASS" if not errors else "FAIL",
        "mode": mode,
        "new_resource_authority": False,
        "hrb_lease_required": True,
        "silent_device_or_model_fallback": False,
        "findings": errors,
    }


def evaluate_display_gpu_admission(
    *,
    inventory: Any,
    accelerator_id: str,
    workload: Any,
    application_selection: Any = None,
) -> dict[str, Any]:
    """Evaluate one selected display GPU, without placing or leasing devices.

    Inventory, display headroom and router binding must come exclusively from
    trusted HRB/Router integration, not application or provider-origin JSON.
    """
    errors: list[str] = []
    if not isinstance(inventory, dict) or inventory.get("schema") != INVENTORY_SCHEMA:
        return _result(["LIVE_HRB_INVENTORY_REQUIRED"])
    if inventory.get("verified_by") != HRB_AUTHORITY or inventory.get("topology_revalidated") is not True:
        errors.append("LIVE_HRB_TOPOLOGY_ATTESTATION_REQUIRED")
    devices = inventory.get("devices")
    if not isinstance(devices, list):
        return _result(errors + ["DEVICE_INVENTORY_INVALID"])
    seen: set[str] = set()
    present: list[dict[str, Any]] = []
    for row in devices:
        if not isinstance(row, dict) or not _filled(row.get("stable_id")):
            errors.append("DEVICE_IDENTITY_INVALID")
            continue
        device_id = row["stable_id"]
        if device_id in seen:
            errors.append("DUPLICATE_DEVICE_IDENTITY")
        seen.add(device_id)
        if row.get("present") is False:
            continue
        kind = str(row.get("kind", "")).upper()
        if kind not in {"GPU", "NPU", "OTHER"}:
            errors.append("DEVICE_KIND_UNVERIFIED")
        if kind == "GPU" and not isinstance(row.get("display_active"), bool):
            errors.append("DISPLAY_ROLE_UNVERIFIED")
        present.append(row)

    selected = [row for row in present if row.get("stable_id") == accelerator_id]
    if not _filled(accelerator_id) or len(selected) != 1:
        errors.append("SELECTED_GPU_NOT_IN_LIVE_INVENTORY")
    elif str(selected[0].get("kind", "")).upper() != "GPU" or selected[0].get("display_active") is not True:
        errors.append("SELECTED_DEVICE_IS_NOT_VERIFIED_DISPLAY_GPU")
    other_accelerators = [
        row for row in present
        if row.get("stable_id") != accelerator_id and str(row.get("kind", "")).upper() in {"GPU", "NPU"}
    ]
    explicit_required = bool(other_accelerators)

    if not isinstance(workload, dict):
        errors.append("MODEL_TASK_APPLICATION_BINDING_REQUIRED")
        workload = {}
    for field in ("application_id", "task_id", "model_id"):
        if not _filled(workload.get(field)):
            errors.append("WORKLOAD_" + field.upper() + "_MISSING")
    if workload.get("display_reserve_confirmed") is not True:
        errors.append("HRB_DISPLAY_SAFETY_RESERVE_NOT_CONFIRMED")
    router = workload.get("router_binding")
    if not isinstance(router, dict):
        errors.append("CENTRAL_MODEL_ROUTER_BINDING_REQUIRED")
    elif not (
        router.get("authority_id") == ROUTER_AUTHORITY
        and router.get("selection_receipt_verified") is True
        and _filled(router.get("route_id"))
        and _filled(router.get("provider_id"))
        and _filled(router.get("runtime_id"))
        and _filled(router.get("model_id"))
        and router.get("model_id") == workload.get("model_id")
    ):
        errors.append("MODEL_ROUTER_BINDING_MISMATCH")

    if explicit_required:
        selection = application_selection if isinstance(application_selection, dict) else {}
        if not (
            selection.get("source") == "APPLICATION_USER_SELECTION"
            and selection.get("approved") is True
            and selection.get("automatic") is False
            and selection.get("allow_fallback") is False
            and _filled(selection.get("intent_id"))
            and _filled(selection.get("reason"))
            and selection.get("application_id") == workload.get("application_id")
            and selection.get("task_id") == workload.get("task_id")
            and selection.get("model_id") == workload.get("model_id")
            and selection.get("accelerator_id") == accelerator_id
        ):
            errors.append("EXPLICIT_APPLICATION_MODEL_TASK_GPU_SELECTION_REQUIRED")
    mode = "EXPLICIT_APPLICATION_SELECTION" if explicit_required else "SOLE_GPU_NO_NPU"
    return _result(errors, mode=mode if not errors else "DENIED")
