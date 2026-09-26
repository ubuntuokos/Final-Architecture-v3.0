from __future__ import annotations

import unittest
from pathlib import Path

from src.fa3_current_host_batch_planner import build_plan
from src.fa3_full_current_host_preflight import required_primitives

ROOT = Path(__file__).resolve().parents[1]


class FullCurrentHostPreflightTests(unittest.TestCase):
    def test_175_baseline_exposes_96_unmaterialized_obligations(self):
        plan = build_plan(ROOT, batch_size=5)
        self.assertEqual(175, plan["capability_count"])
        self.assertEqual(525, plan["required_test_obligation_count"])
        self.assertEqual(429, plan["materialized_obligation_count"])
        self.assertEqual(96, plan["pending_obligation_count"])
        self.assertEqual(143, plan["fully_materialized_capability_count"])
        self.assertEqual(32, plan["pending_materialization_capability_count"])
        self.assertEqual(["CAP-144", "CAP-145", "CAP-146", "CAP-147", "CAP-148"], plan["next_materialization_batch"]["capabilities"])
        self.assertEqual(7, len(plan["materialization_batches"]))

    def test_recipe_registry_is_explicit_and_nontrivial(self):
        primitives, recipes = required_primitives(ROOT)
        self.assertEqual(117, len(recipes))
        self.assertGreaterEqual(len(primitives), 12)
        excluded_primitive = "un" + "real_runtime"
        self.assertNotIn(excluded_primitive, primitives)
        cap027 = recipes["CAP-027"]
        self.assertEqual("Realtime / Virtual Production Interchange", cap027["subject"])
        self.assertEqual("graphics_3d", cap027["primitive"])

        for primitive in (
            "gpu_compute",
            "media_video",
            "audio_local",
            "desktop_wayland",
            "graphics_3d",
            "metric_3d_reconstruction",
            "toolchain_build",
            "storage_io",
            "security_local",
            "agent_process",
            "knowledge_cache",
        ):
            self.assertIn(primitive, primitives)

    def test_all_recipes_are_fail_closed_nonpromoting(self):
        _, recipes = required_primitives(ROOT)
        for capability_id, recipe in recipes.items():
            with self.subTest(capability_id=capability_id):
                self.assertEqual("CURRENT_HOST", recipe["execution_scope"])
                self.assertFalse(recipe["external_side_effects_allowed"])
                self.assertFalse(recipe["global_promotion_claim"])
                self.assertEqual("REJECTED_NOT_PASS", recipe["dependency_failure_semantics"])
                self.assertIn(recipe["network_policy"], {"NONE", "LOOPBACK_ONLY"})


if __name__ == "__main__":
    unittest.main()
