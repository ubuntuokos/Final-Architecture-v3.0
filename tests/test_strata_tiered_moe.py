from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("fa3_tiered_moe_plan", ROOT / "src/fa3_tiered_moe_plan.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class TieredMoEPlannerTests(unittest.TestCase):
    def test_gpu_numa_storage_plan(self):
        req = {
            "schema": mod.SCHEMA,
            "model": {
                "expert_bytes": 80,
                "dense_bytes": 20,
                "kv_bytes": 30,
                "auxiliary_bytes": 40,
            },
            "hardware": {
                "numa_nodes": [
                    {"id": "node0", "free_bytes": 100, "distance": 0},
                    {"id": "node1", "free_bytes": 100, "distance": 1},
                ],
                "accelerators": [
                    {"id": "gpu0", "free_bytes": 90, "numa_node": "node0", "admitted": True}
                ],
                "storage_tiers": [
                    {"id": "nvme0", "free_bytes": 1000, "admitted": True}
                ],
            },
            "policy": {
                "host_reserve_bytes": 20,
                "accelerator_reserve_bytes": 10,
                "allow_kv_host_spill": True,
            },
        }
        out = mod.plan(req)
        self.assertEqual(out["result"], "PASS")
        self.assertEqual(sum(x["bytes"] for x in out["expert_host_residency"]), 80)
        self.assertLessEqual(sum(x["bytes"] for x in out["accelerator_cache"]), 60)
        self.assertTrue(all(x["authoritative"] is False for x in out["accelerator_cache"]))
        self.assertEqual(sum(x["bytes"] for x in out["auxiliary_storage"]), 40)
        self.assertTrue(out["invariants"]["hrb_admission_required"])

    def test_cpu_only_remains_valid(self):
        req = {
            "schema": mod.SCHEMA,
            "model": {
                "expert_bytes": 60,
                "dense_bytes": 20,
                "kv_bytes": 10,
                "auxiliary_bytes": 0,
            },
            "hardware": {
                "numa_nodes": [{"id": "node0", "free_bytes": 128, "distance": 0}],
                "accelerators": [],
                "storage_tiers": [],
            },
            "policy": {
                "host_reserve_bytes": 16,
                "accelerator_reserve_bytes": 0,
                "allow_kv_host_spill": True,
            },
        }
        out = mod.plan(req)
        self.assertEqual(out["result"], "PASS")
        self.assertEqual(out["accelerator_cache"], [])
        self.assertEqual(sum(x["bytes"] for x in out["kv_placement"]["host"]), 10)

    def test_expert_master_cannot_silently_spill_to_storage(self):
        req = {
            "schema": mod.SCHEMA,
            "model": {
                "expert_bytes": 200,
                "dense_bytes": 0,
                "kv_bytes": 0,
                "auxiliary_bytes": 0,
            },
            "hardware": {
                "numa_nodes": [{"id": "node0", "free_bytes": 100, "distance": 0}],
                "accelerators": [{"id": "gpu0", "free_bytes": 1000, "admitted": True}],
                "storage_tiers": [{"id": "nvme0", "free_bytes": 10000, "admitted": True}],
            },
            "policy": {
                "host_reserve_bytes": 0,
                "accelerator_reserve_bytes": 0,
                "allow_kv_host_spill": True,
            },
        }
        out = mod.plan(req)
        self.assertEqual(out["result"], "UNSATISFIABLE")
        self.assertEqual(out["reason"], "AUTHORITATIVE_EXPERT_SET_DOES_NOT_FIT_HOST_MEMORY")

    def test_kv_host_spill_can_be_forbidden(self):
        req = {
            "schema": mod.SCHEMA,
            "model": {
                "expert_bytes": 20,
                "dense_bytes": 40,
                "kv_bytes": 40,
                "auxiliary_bytes": 0,
            },
            "hardware": {
                "numa_nodes": [{"id": "node0", "free_bytes": 200, "distance": 0}],
                "accelerators": [{"id": "gpu0", "free_bytes": 60, "admitted": True}],
                "storage_tiers": [],
            },
            "policy": {
                "host_reserve_bytes": 0,
                "accelerator_reserve_bytes": 0,
                "allow_kv_host_spill": False,
            },
        }
        out = mod.plan(req)
        self.assertEqual(out["result"], "UNSATISFIABLE")
        self.assertEqual(out["reason"], "KV_CACHE_DOES_NOT_FIT_ALLOWED_TIERS")


class StaticGateTests(unittest.TestCase):
    def test_static_gate(self):
        gate_spec = importlib.util.spec_from_file_location("fa3_strata_gate", ROOT / "src/fa3_strata_tiered_moe_gate.py")
        gate = importlib.util.module_from_spec(gate_spec)
        assert gate_spec.loader is not None
        gate_spec.loader.exec_module(gate)
        gate.check()


if __name__ == "__main__":
    unittest.main()
