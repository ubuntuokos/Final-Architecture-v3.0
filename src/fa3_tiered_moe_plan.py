#!/usr/bin/env python3
"""FA3 provider-neutral tiered MoE placement planner.

Independent FA3 implementation. NO_UPSTREAM_STRATA_SOURCE_COPIED.
The planner encodes FA3 policy concepts only; it does not import or translate
Niko1221/Strata source code.

Input is JSON on stdin or via --input. Output is a deterministic placement
proposal that still requires HRB admission before execution.
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

SCHEMA = "fa3.tiered-moe-placement-request.v1"
RESULT_SCHEMA = "fa3.tiered-moe-placement-plan.v1"


class PlanError(ValueError):
    pass


def _n(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PlanError(f"{name} must be a non-negative integer")
    return value


def _alloc(amount: int, pools: list[dict[str, Any]], field: str = "usable") -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    remaining = amount
    for pool in pools:
        if remaining <= 0:
            break
        take = min(remaining, pool[field])
        if take:
            out.append({"id": pool["id"], "bytes": take})
            pool[field] -= take
            remaining -= take
    return out, remaining


def plan(req: dict[str, Any]) -> dict[str, Any]:
    if req.get("schema") != SCHEMA:
        raise PlanError(f"schema must be {SCHEMA}")

    model = req.get("model") or {}
    hw = deepcopy(req.get("hardware") or {})
    policy = req.get("policy") or {}

    expert = _n(model.get("expert_bytes"), "model.expert_bytes")
    dense = _n(model.get("dense_bytes"), "model.dense_bytes")
    kv = _n(model.get("kv_bytes"), "model.kv_bytes")
    aux = _n(model.get("auxiliary_bytes"), "model.auxiliary_bytes")
    host_reserve = _n(policy.get("host_reserve_bytes", 0), "policy.host_reserve_bytes")
    accel_reserve = _n(policy.get("accelerator_reserve_bytes", 0), "policy.accelerator_reserve_bytes")
    allow_kv_host = bool(policy.get("allow_kv_host_spill", True))

    nodes = []
    for raw in hw.get("numa_nodes", []):
        free = _n(raw.get("free_bytes"), "numa_nodes[].free_bytes")
        nodes.append({
            "id": str(raw.get("id")),
            "free": free,
            "usable": free,
            "distance": _n(raw.get("distance", 0), "numa_nodes[].distance"),
        })
    nodes.sort(key=lambda x: (x["distance"], x["id"]))

    if not nodes:
        return {
            "schema": RESULT_SCHEMA,
            "result": "UNSATISFIABLE",
            "reason": "NO_HOST_MEMORY_TIER",
            "receipts": {"hrb_admission": "REQUIRED_AT_RUNTIME", "model_router_selection": "REQUIRED_IF_PROVIDER_USED"},
        }

    # Keep the requested host reserve untouched, deterministically from the least-preferred nodes first.
    reserve_left = host_reserve
    for node in reversed(nodes):
        take = min(reserve_left, node["usable"])
        node["usable"] -= take
        reserve_left -= take
    if reserve_left:
        return {
            "schema": RESULT_SCHEMA,
            "result": "UNSATISFIABLE",
            "reason": "HOST_RESERVE_EXCEEDS_AVAILABLE_MEMORY",
            "receipts": {"hrb_admission": "REQUIRED_AT_RUNTIME", "model_router_selection": "REQUIRED_IF_PROVIDER_USED"},
        }

    accelerators = []
    for raw in hw.get("accelerators", []):
        if raw.get("admitted") is not True:
            continue
        free = _n(raw.get("free_bytes"), "accelerators[].free_bytes")
        usable = max(0, free - accel_reserve)
        accelerators.append({
            "id": str(raw.get("id")),
            "numa_node": str(raw.get("numa_node", "")),
            "usable": usable,
        })
    accelerators.sort(key=lambda x: (-x["usable"], x["id"]))

    storage = []
    for raw in hw.get("storage_tiers", []):
        if raw.get("admitted") is not True:
            continue
        storage.append({
            "id": str(raw.get("id")),
            "usable": _n(raw.get("free_bytes"), "storage_tiers[].free_bytes"),
        })
    storage.sort(key=lambda x: (-x["usable"], x["id"]))

    # Dense weights prefer accelerator memory, but CPU-only remains valid.
    dense_place, dense_left = _alloc(dense, accelerators)
    if dense_left:
        host_dense, dense_left = _alloc(dense_left, nodes)
        dense_place.extend({"id": x["id"], "bytes": x["bytes"], "tier": "NUMA_HOST_MEMORY"} for x in host_dense)
    for x in dense_place:
        x.setdefault("tier", "ACCELERATOR_RESIDENT")
    if dense_left:
        return {
            "schema": RESULT_SCHEMA,
            "result": "UNSATISFIABLE",
            "reason": "DENSE_WEIGHTS_DO_NOT_FIT_ADMITTED_MEMORY",
            "receipts": {"hrb_admission": "REQUIRED_AT_RUNTIME", "model_router_selection": "REQUIRED_IF_PROVIDER_USED"},
        }

    # Authoritative experts must fit host memory. Accelerator residency is a rebuildable cache only.
    expert_host, expert_left = _alloc(expert, nodes)
    if expert_left:
        return {
            "schema": RESULT_SCHEMA,
            "result": "UNSATISFIABLE",
            "reason": "AUTHORITATIVE_EXPERT_SET_DOES_NOT_FIT_HOST_MEMORY",
            "receipts": {"hrb_admission": "REQUIRED_AT_RUNTIME", "model_router_selection": "REQUIRED_IF_PROVIDER_USED"},
        }

    cache_capacity = sum(a["usable"] for a in accelerators)
    cache_target = min(expert, cache_capacity)
    accel_cache, cache_left = _alloc(cache_target, accelerators)
    assert cache_left == 0

    kv_accel, kv_left = _alloc(kv, accelerators)
    kv_host: list[dict[str, Any]] = []
    if kv_left and allow_kv_host:
        kv_host, kv_left = _alloc(kv_left, nodes)
    if kv_left:
        return {
            "schema": RESULT_SCHEMA,
            "result": "UNSATISFIABLE",
            "reason": "KV_CACHE_DOES_NOT_FIT_ALLOWED_TIERS",
            "receipts": {"hrb_admission": "REQUIRED_AT_RUNTIME", "model_router_selection": "REQUIRED_IF_PROVIDER_USED"},
        }

    aux_place: list[dict[str, Any]] = []
    aux_left = aux
    if aux:
        aux_place, aux_left = _alloc(aux, storage)
    if aux_left:
        return {
            "schema": RESULT_SCHEMA,
            "result": "UNSATISFIABLE",
            "reason": "AUXILIARY_ARTIFACTS_DO_NOT_FIT_ADMITTED_STORAGE",
            "receipts": {"hrb_admission": "REQUIRED_AT_RUNTIME", "model_router_selection": "REQUIRED_IF_PROVIDER_USED"},
        }

    return {
        "schema": RESULT_SCHEMA,
        "result": "PASS",
        "dense_placement": dense_place,
        "expert_host_residency": [{"id": x["id"], "bytes": x["bytes"], "tier": "NUMA_HOST_MEMORY"} for x in expert_host],
        "accelerator_cache": [{"id": x["id"], "bytes": x["bytes"], "tier": "ACCELERATOR_RESIDENT", "authoritative": False} for x in accel_cache],
        "kv_placement": {
            "accelerator": [{"id": x["id"], "bytes": x["bytes"]} for x in kv_accel],
            "host": [{"id": x["id"], "bytes": x["bytes"]} for x in kv_host],
        },
        "auxiliary_storage": [{"id": x["id"], "bytes": x["bytes"], "tier": "PERSISTENT_STORAGE"} for x in aux_place],
        "invariants": {
            "authoritative_experts_on_storage": False,
            "accelerator_cache_rebuildable": True,
            "silent_fallback": False,
            "hrb_admission_required": True,
        },
        "receipts": {
            "hrb_admission": "REQUIRED_AT_RUNTIME",
            "model_router_selection": "REQUIRED_IF_PROVIDER_USED",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path)
    args = ap.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read())
    try:
        result = plan(data)
    except PlanError as exc:
        result = {"schema": RESULT_SCHEMA, "result": "UNSATISFIABLE", "reason": f"INVALID_REQUEST:{exc}"}
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
