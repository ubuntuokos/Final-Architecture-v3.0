from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_display_gpu_admission import evaluate_display_gpu_admission
from fa3_hrb_composite_lease import evaluate_reservation_plan, RESOURCE_ORDER, HRB_AUTHORITY_ID


def inventory(*others):
    return {
        "schema": "fa3.hrb-live-accelerator-inventory.v1",
        "verified_by": HRB_AUTHORITY_ID,
        "topology_revalidated": True,
        "devices": [{"stable_id": "display-uuid", "kind": "GPU", "display_active": True, "present": True}, *others],
    }


def workload():
    return {
        "application_id": "app.video", "task_id": "shot-inference-1",
        "model_id": "model-selected-by-router", "display_reserve_confirmed": True,
        "router_binding": {
            "authority_id": "FA3-AUTH-MODEL-ROUTER-001",
            "selection_receipt_verified": True,
            "route_id": "video-frame-analysis", "provider_id": "admitted-provider",
            "runtime_id": "admitted-runtime", "model_id": "model-selected-by-router",
        },
    }


def selection():
    return {
        "source": "APPLICATION_USER_SELECTION", "approved": True,
        "automatic": False, "allow_fallback": False,
        "intent_id": "intent-9", "reason": "specific frame model needs this GPU",
        "application_id": "app.video", "task_id": "shot-inference-1",
        "model_id": "model-selected-by-router", "accelerator_id": "display-uuid",
    }


def assess(inv, sel=None, job=None):
    return evaluate_display_gpu_admission(
        inventory=inv, accelerator_id="display-uuid",
        workload=workload() if job is None else job, application_selection=sel,
    )


class DisplayGpuAdmissionTests(unittest.TestCase):
    def test_sole_gpu_without_npu_may_compute(self):
        decision = assess(inventory())
        self.assertEqual(decision["result"], "PASS")
        self.assertEqual(decision["mode"], "SOLE_GPU_NO_NPU")
        self.assertTrue(decision["hrb_lease_required"])

    def test_second_gpu_even_unavailable_requires_selection(self):
        inv = inventory({"stable_id": "compute-uuid", "kind": "GPU",
                         "display_active": False, "present": True, "health": "OFFLINE"})
        self.assertEqual(assess(inv)["result"], "FAIL")
        self.assertEqual(assess(inv, selection())["mode"], "EXPLICIT_APPLICATION_SELECTION")

    def test_npu_requires_opt_in(self):
        inv = inventory({"stable_id": "npu-a", "kind": "NPU", "present": True})
        self.assertEqual(assess(inv)["result"], "FAIL")
        self.assertEqual(assess(inv, selection())["result"], "PASS")

    def test_absent_second_device_does_not_block_solo_path(self):
        inv = inventory({"stable_id": "removed", "kind": "GPU",
                         "display_active": False, "present": False})
        self.assertEqual(assess(inv)["result"], "PASS")

    def test_missing_gpu_or_unverified_topology_fails_closed(self):
        inv = inventory()
        inv["devices"] = []
        self.assertEqual(assess(inv)["result"], "FAIL")
        inv = inventory()
        inv["topology_revalidated"] = False
        self.assertEqual(assess(inv)["result"], "FAIL")

    def test_unknown_device_kind_or_duplicate_stable_id_fails_closed(self):
        inv = inventory({"stable_id": "unknown", "kind": "UNVERIFIED", "present": True})
        self.assertEqual(assess(inv)["result"], "FAIL")
        inv = inventory({"stable_id": "display-uuid", "kind": "GPU", "display_active": False})
        self.assertEqual(assess(inv)["result"], "FAIL")

    def test_display_reserve_is_mandatory(self):
        job = workload()
        job["display_reserve_confirmed"] = False
        self.assertIn("HRB_DISPLAY_SAFETY_RESERVE_NOT_CONFIRMED", assess(inventory(), job=job)["findings"])

    def test_physical_router_model_must_match_selected_model(self):
        job = workload()
        job["router_binding"]["model_id"] = "unexpected-model"
        self.assertIn("MODEL_ROUTER_BINDING_MISMATCH", assess(inventory(), job=job)["findings"])

    def test_explicit_selection_is_scoped_and_never_automatic(self):
        inv = inventory({"stable_id": "compute-uuid", "kind": "GPU", "display_active": False})
        for key, value in (("model_id", "other"), ("accelerator_id", "compute-uuid"),
                           ("task_id", "elsewhere"), ("application_id", "other-app"),
                           ("automatic", True), ("allow_fallback", True),
                           ("approved", False), ("source", "AUTO_BROKER")):
            with self.subTest(key=key):
                chosen = selection()
                chosen[key] = value
                self.assertEqual(assess(inv, chosen)["result"], "FAIL")

    def test_hrb_reservation_checks_actual_display_role_even_if_mislabelled(self):
        plan = {
            "schema": "fa3.resource-reservation-plan.v1", "authority_id": HRB_AUTHORITY_ID,
            "atomic_admission": True, "hold_and_wait": False,
            "acquisition_order": list(RESOURCE_ORDER),
            "queue_policy": {"max_waiters": 1, "deadline_seconds": 15},
            "workloads": [{"id": "w1", "resources": {"cpu_threads": 1}}],
            "accelerators": [{
                "stable_id": "display-uuid", "role": "COMPUTE",
                "runtime_ordinal_is_identity": False, "workload_binding": workload(),
            }],
        }
        capacity = {"cpu_threads": 2, "ram_bytes": 0, "vram_bytes": 0,
                    "io_bytes_per_second": 0, "network_bytes_per_second": 0}
        inv = inventory({"stable_id": "npu-a", "kind": "NPU", "present": True})
        result = evaluate_reservation_plan(plan, capacity, trusted_hardware_inventory=inv)
        self.assertEqual(result["result"], "FAIL")
        plan["accelerators"][0]["role"] = "DISPLAY"
        plan["accelerators"][0]["application_selection"] = selection()
        self.assertEqual(evaluate_reservation_plan(plan, capacity, trusted_hardware_inventory=inv)["result"], "PASS")
        missing = evaluate_reservation_plan(plan, capacity)
        self.assertEqual(missing["result"], "FAIL")
        self.assertTrue(any("display GPU" in x for x in missing["findings"]))


if __name__ == "__main__":
    unittest.main()
