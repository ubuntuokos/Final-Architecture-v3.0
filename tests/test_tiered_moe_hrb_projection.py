from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

spec = importlib.util.spec_from_file_location("fa3_tiered_moe_hrb_projection", SRC / "fa3_tiered_moe_hrb_projection.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def receipt(*, accelerator: bool = False, storage: bool = True):
    classes = ["memory", "numa"]
    if storage:
        classes.append("storage")
    if accelerator:
        classes.append("accelerator")
    payload = {
        "host_attestation_sha256": "1" * 64,
        "compute_profile": {"metrics": {"memory.total_gib": 64}},
        "requested_resource_classes": sorted(classes),
        "accelerator_required": accelerator,
        "workload_resource_envelope": {"workload_id": "strata-workload"},
        "hrb_authorization": {
            "authority": mod.HRB_AUTHORITY,
            "authorization_id": "auth-1",
        },
    }
    if accelerator:
        payload["hrb_lease_identity"] = {
            "accelerator_uuid": "GPU-1",
            "memory_max_bytes": 24 * mod.GIB,
        }
    return {"payload": payload}


def grant(*, accelerator: bool = False, storage: bool = True):
    resources = {
        "numa_nodes": [
            {"id": "node0", "memory_max_bytes": 20 * mod.GIB, "distance": 0},
            {"id": "node1", "memory_max_bytes": 20 * mod.GIB, "distance": 1},
        ],
        "accelerators": [],
        "storage_tiers": [{"id": "nvme0", "bytes_max": 80 * mod.GIB}] if storage else [],
    }
    if accelerator:
        resources["accelerators"] = [
            {"id": "GPU-1", "memory_max_bytes": 20 * mod.GIB, "numa_node": "node0"}
        ]
    return {
        "schema": mod.GRANT_SCHEMA,
        "authority": mod.HRB_AUTHORITY,
        "status": "VALID",
        "broker_validation": True,
        "grant_id": "grant-1",
        "authorization_id": "auth-1",
        "workload_id": "strata-workload",
        "host_attestation_sha256": "1" * 64,
        "admitted_resources": resources,
    }


class TieredMoEHrbProjectionTests(unittest.TestCase):
    def valid(self, _receipt):
        return []

    def test_cpu_only_projection_is_bounded_by_hrb_grant(self):
        out = mod.project(
            receipt(),
            grant(),
            {"expert_bytes": 10 * mod.GIB, "dense_bytes": 4 * mod.GIB,
             "kv_bytes": 2 * mod.GIB, "auxiliary_bytes": 8 * mod.GIB},
            {"host_reserve_bytes": 2 * mod.GIB, "accelerator_reserve_bytes": 0,
             "allow_kv_host_spill": True},
            receipt_validator=self.valid,
        )
        self.assertEqual(out["result"], "PASS")
        self.assertEqual(out["accelerator_cache"], [])
        child = out["hrb_child_projection"]
        self.assertFalse(child["placement_authoritative"])
        self.assertFalse(child["may_expand_resources"])
        self.assertFalse(out["current_host_runtime_promotion_claim"])

    def test_parent_receipt_is_mandatory_and_fail_closed(self):
        with self.assertRaises(mod.ProjectionError):
            mod.project({}, grant(), {}, {}, receipt_validator=lambda _r: [{"code": "invalid"}])

    def test_grant_must_match_parent_authorization(self):
        bad = grant()
        bad["authorization_id"] = "other"
        with self.assertRaises(mod.ProjectionError):
            mod.project(receipt(), bad, {}, {}, receipt_validator=self.valid)

    def test_accelerator_grant_cannot_exceed_parent_lease(self):
        bad = grant(accelerator=True)
        bad["admitted_resources"]["accelerators"][0]["memory_max_bytes"] = 25 * mod.GIB
        with self.assertRaises(mod.ProjectionError):
            mod.project(receipt(accelerator=True), bad, {}, {}, receipt_validator=self.valid)

    def test_storage_cannot_appear_outside_requested_resource_classes(self):
        with self.assertRaises(mod.ProjectionError):
            mod.project(receipt(storage=False), grant(storage=True), {}, {}, receipt_validator=self.valid)

    def test_planner_cannot_silently_exceed_hrb_host_grant(self):
        out = mod.project(
            receipt(storage=False),
            grant(storage=False),
            {"expert_bytes": 50 * mod.GIB, "dense_bytes": 0, "kv_bytes": 0, "auxiliary_bytes": 0},
            {"host_reserve_bytes": 0, "accelerator_reserve_bytes": 0, "allow_kv_host_spill": True},
            receipt_validator=self.valid,
        )
        self.assertEqual(out["result"], "UNSATISFIABLE")
        self.assertEqual(out["reason"], "AUTHORITATIVE_EXPERT_SET_DOES_NOT_FIT_HOST_MEMORY")
        self.assertFalse(out["hrb_child_projection"]["may_admit_resources"])


if __name__ == "__main__":
    unittest.main()
