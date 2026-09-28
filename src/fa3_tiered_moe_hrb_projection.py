#!/usr/bin/env python3
"""Bind the FA3 tiered-MoE planner to an already-authorized HRB resource grant.

This is a child projection of FA3-AUTH-HOST-RESOURCE-BROKER-001. It cannot
admit, reserve, lease, discover, or expand resources. The parent current-host
resource-admission receipt is validated first; the placement planner sees only
the resource ceilings explicitly granted by HRB.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_resource_admission_current_host_gate import canonical_sha256, validate_receipt
from fa3_tiered_moe_plan import plan as tiered_plan

HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
GRANT_SCHEMA = "fa3.tiered-moe-hrb-placement-grant.v1"
PROJECTION_SCHEMA = "fa3.tiered-moe-hrb-child-projection.v1"
GIB = 1024 ** 3


class ProjectionError(RuntimeError):
    pass


def _nonneg(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProjectionError(f"{name} must be a non-negative integer")
    return value


def _require_grant(grant: dict[str, Any], receipt: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if grant.get("schema") != GRANT_SCHEMA:
        raise ProjectionError("HRB placement grant schema mismatch")
    if grant.get("authority") != HRB_AUTHORITY or grant.get("status") != "VALID":
        raise ProjectionError("HRB placement grant authority/status invalid")
    if grant.get("broker_validation") is not True:
        raise ProjectionError("HRB placement grant lacks broker validation")
    if not str(grant.get("grant_id", "")).strip():
        raise ProjectionError("HRB placement grant id missing")

    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        raise ProjectionError("validated receipt payload missing")
    auth = payload.get("hrb_authorization")
    if not isinstance(auth, dict) or auth.get("authority") != HRB_AUTHORITY:
        raise ProjectionError("validated receipt HRB authorization missing")

    workload = payload.get("workload_resource_envelope")
    if not isinstance(workload, dict):
        raise ProjectionError("validated receipt workload envelope missing")

    if grant.get("authorization_id") != auth.get("authorization_id"):
        raise ProjectionError("HRB placement grant authorization binding mismatch")
    if grant.get("workload_id") != workload.get("workload_id"):
        raise ProjectionError("HRB placement grant workload binding mismatch")
    if grant.get("host_attestation_sha256") != payload.get("host_attestation_sha256"):
        raise ProjectionError("HRB placement grant host binding mismatch")
    return payload, auth


def _hardware_from_grant(grant: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    resources = grant.get("admitted_resources")
    if not isinstance(resources, dict):
        raise ProjectionError("HRB placement grant admitted_resources missing")

    classes = set(payload.get("requested_resource_classes") or [])
    accelerator_required = payload.get("accelerator_required") is True

    raw_nodes = resources.get("numa_nodes", [])
    raw_accels = resources.get("accelerators", [])
    raw_storage = resources.get("storage_tiers", [])
    if not all(isinstance(x, list) for x in (raw_nodes, raw_accels, raw_storage)):
        raise ProjectionError("HRB placement grant resource lists invalid")

    if raw_nodes and not ({"memory", "numa"} & classes):
        raise ProjectionError("HRB grant contains host-memory placement outside requested classes")
    if raw_storage and "storage" not in classes:
        raise ProjectionError("HRB grant contains storage outside requested classes")
    if raw_accels and ("accelerator" not in classes or not accelerator_required):
        raise ProjectionError("HRB grant contains accelerator outside requested classes")
    if accelerator_required and not raw_accels:
        raise ProjectionError("accelerator workload lacks accelerator placement grant")
    if not accelerator_required and raw_accels:
        raise ProjectionError("CPU-only workload unexpectedly received accelerator placement")

    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_nodes:
        if not isinstance(item, dict):
            raise ProjectionError("NUMA grant entry invalid")
        node_id = str(item.get("id", "")).strip()
        if not node_id or node_id in seen:
            raise ProjectionError("NUMA grant id missing or duplicated")
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "free_bytes": _nonneg(item.get("memory_max_bytes"), "numa_nodes[].memory_max_bytes"),
            "distance": _nonneg(item.get("distance", 0), "numa_nodes[].distance"),
        })

    metrics = payload.get("compute_profile", {}).get("metrics", {})
    memory_gib = metrics.get("memory.total_gib") if isinstance(metrics, dict) else None
    if nodes:
        try:
            physical_memory_bytes = int(float(memory_gib) * GIB)
        except (TypeError, ValueError):
            raise ProjectionError("validated compute profile lacks memory.total_gib for NUMA projection")
        if sum(x["free_bytes"] for x in nodes) > physical_memory_bytes:
            raise ProjectionError("HRB NUMA grant exceeds validated host memory")

    accels: list[dict[str, Any]] = []
    if raw_accels:
        # The current FA3 resource-admission receipt binds one accelerator lease.
        # Global FA3 remains 0..N; a future multi-lease receipt can extend this adapter.
        if len(raw_accels) != 1:
            raise ProjectionError("current HRB receipt supports one accelerator lease per workload")
        lease = payload.get("hrb_lease_identity")
        if not isinstance(lease, dict):
            raise ProjectionError("accelerator grant lacks parent HRB lease")
        item = raw_accels[0]
        if not isinstance(item, dict):
            raise ProjectionError("accelerator grant entry invalid")
        accelerator_id = str(item.get("id", "")).strip()
        if accelerator_id != str(lease.get("accelerator_uuid", "")).strip():
            raise ProjectionError("accelerator grant does not match HRB lease identity")
        granted = _nonneg(item.get("memory_max_bytes"), "accelerators[].memory_max_bytes")
        leased = _nonneg(lease.get("memory_max_bytes"), "hrb_lease_identity.memory_max_bytes")
        if granted > leased:
            raise ProjectionError("accelerator placement grant exceeds HRB lease memory budget")
        accels.append({
            "id": accelerator_id,
            "free_bytes": granted,
            "numa_node": str(item.get("numa_node", "")),
            "admitted": True,
        })

    storage: list[dict[str, Any]] = []
    seen_storage: set[str] = set()
    for item in raw_storage:
        if not isinstance(item, dict):
            raise ProjectionError("storage grant entry invalid")
        storage_id = str(item.get("id", "")).strip()
        if not storage_id or storage_id in seen_storage:
            raise ProjectionError("storage grant id missing or duplicated")
        seen_storage.add(storage_id)
        storage.append({
            "id": storage_id,
            "free_bytes": _nonneg(item.get("bytes_max"), "storage_tiers[].bytes_max"),
            "admitted": True,
        })

    return {"numa_nodes": nodes, "accelerators": accels, "storage_tiers": storage}


def project(
    receipt: dict[str, Any],
    grant: dict[str, Any],
    model: dict[str, Any],
    policy: dict[str, Any],
    *,
    receipt_validator: Callable[[dict[str, Any]], list[dict[str, Any]]] = validate_receipt,
) -> dict[str, Any]:
    findings = receipt_validator(receipt)
    if findings:
        raise ProjectionError("parent HRB current-host receipt is not valid")

    payload, _auth = _require_grant(grant, receipt)
    hardware = _hardware_from_grant(grant, payload)
    request = {
        "schema": "fa3.tiered-moe-placement-request.v1",
        "model": model,
        "hardware": hardware,
        "policy": policy,
    }
    result = tiered_plan(request)
    result["hrb_child_projection"] = {
        "schema": PROJECTION_SCHEMA,
        "authority": HRB_AUTHORITY,
        "parent_receipt_sha256": canonical_sha256(receipt),
        "authorization_id": grant["authorization_id"],
        "grant_id": grant["grant_id"],
        "workload_id": grant["workload_id"],
        "placement_authoritative": False,
        "may_admit_resources": False,
        "may_expand_resources": False,
        "may_create_lease": False,
        "requires_parent_hrb_authority": True,
    }
    result["current_host_runtime_promotion_claim"] = False
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 HRB-bound tiered MoE placement child projection")
    ap.add_argument("--input", type=Path, required=True)
    args = ap.parse_args()
    bundle = json.loads(args.input.read_text(encoding="utf-8"))
    try:
        out = project(
            bundle.get("resource_admission_receipt", {}),
            bundle.get("hrb_placement_grant", {}),
            bundle.get("model", {}),
            bundle.get("policy", {}),
        )
    except ProjectionError as exc:
        out = {
            "schema": PROJECTION_SCHEMA,
            "result": "BLOCKED",
            "reason": str(exc),
            "authority": HRB_AUTHORITY,
            "current_host_runtime_promotion_claim": False,
        }
        print(json.dumps(out, indent=2, sort_keys=True))
        return 2
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
