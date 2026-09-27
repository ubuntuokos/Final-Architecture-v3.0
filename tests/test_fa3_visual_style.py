import copy
import unittest

import fa3_visual_style
import fa3_visual_style_gate


class Fa3VisualStyleTests(unittest.TestCase):
    def sample(self):
        return {
            "style_name": "Synthetic Editorial",
            "style_slug": "synthetic-editorial",
            "style_version": "1",
            "prompt_template": "Create {SUBJECT}",
            "style_fidelity_anchors": ["high contrast"],
            "source_content_to_avoid": ["copied identity"],
            "negative_prompt": "watermark",
            "camera_language": "editorial",
            "temporal_consistency": "locked",
        }

    def recipe(self):
        return fa3_visual_style.normalize_recipe(
            self.sample(),
            source_project="VigoZhao/AI-Visual-Prompt-Cookbook",
            source_revision="d320e7a99819a54da6ff56abbc19a83fb6741772",
            source_license="CC-BY-4.0",
            attribution="@VigoCreativeAI",
        )

    def test_materialization_gate(self):
        self.assertEqual([], fa3_visual_style_gate.validate())

    def test_import_preserves_provenance_and_constraints(self):
        recipe = self.recipe()
        self.assertEqual("fa3.visual-style-recipe.v1", recipe["schema"])
        self.assertTrue(recipe["provider_neutral"])
        self.assertEqual("CC-BY-4.0", recipe["provenance"]["license"])
        self.assertEqual("@VigoCreativeAI", recipe["provenance"]["attribution"])
        self.assertEqual(["copied identity"], recipe["source_content_to_avoid"])
        self.assertEqual("editorial", recipe["fa3_extensions"]["camera_language"])

    def test_visual_intent_is_router_bound_and_unpinned(self):
        ir = fa3_visual_style.build_visual_intent(self.recipe(), scope="SHOT")
        route = ir["route_request"]
        self.assertEqual("FA3-AUTH-MODEL-ROUTER-001", route["authority"])
        self.assertEqual("FA3-AUTH-HOST-RESOURCE-BROKER-001", route["resource_authority"])
        self.assertIsNone(route["provider"])
        self.assertIsNone(route["model"])
        self.assertIsNone(route["runtime"])
        self.assertFalse(route["silent_fallback_allowed"])
        self.assertFalse(ir["current_host_runtime_promotion_claim"])

    def test_style_dna_is_normalized(self):
        dna = fa3_visual_style.build_style_dna([
            {"recipe_id": "fa3.visual-style.a", "weight": 2},
            {"recipe_id": "fa3.visual-style.b", "weight": 1},
        ])
        self.assertAlmostEqual(1.0, sum(row["weight"] for row in dna["components"]))

    def test_fixed_provider_is_fail_closed(self):
        recipe = self.recipe()
        recipe = copy.deepcopy(recipe)
        recipe["runtime"]["fixed_provider"] = "not-allowed"
        with self.assertRaises(fa3_visual_style.VisualStyleDenied):
            fa3_visual_style.build_visual_intent(recipe)

    def test_invalid_recipe_and_scope_are_rejected(self):
        bad = self.sample()
        del bad["prompt_template"]
        with self.assertRaises(fa3_visual_style.VisualStyleDenied):
            fa3_visual_style.normalize_recipe(
                bad,
                source_project="x",
                source_revision="y",
                source_license="MIT",
                attribution="z",
            )
        with self.assertRaises(fa3_visual_style.VisualStyleDenied):
            fa3_visual_style.build_visual_intent(self.recipe(), scope="GLOBAL")


if __name__ == "__main__":
    unittest.main()
