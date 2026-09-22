import json
import tempfile
import unittest
from pathlib import Path

from src.fa3_full_current_host_capability_producer import (
    common_request_allowed,
    exact_rollback,
    negative_proof,
    proof_agent_process,
    proof_external_conditional,
    proof_knowledge_cache,
    proof_network_loopback,
    proof_pipeline_transform,
    proof_security_local,
    proof_storage_io,
    recipe_map,
)


class FullCurrentHostCapabilityProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_recipe_registry_covers_exactly_previously_pending_capabilities(self):
        recipes = recipe_map(self.root)
        self.assertEqual(117, len(recipes))
        self.assertNotIn("CAP-001", recipes)
        self.assertNotIn("CAP-020", recipes)
        self.assertNotIn("CAP-028", recipes)
        self.assertNotIn("CAP-054", recipes)
        self.assertNotIn("CAP-074", recipes)
        self.assertNotIn("CAP-075", recipes)
        self.assertNotIn("CAP-076", recipes)
        self.assertNotIn("CAP-080", recipes)
        for cap in ("CAP-021", "CAP-025", "CAP-027", "CAP-032", "CAP-100", "CAP-143"):
            self.assertIn(cap, recipes)
        self.assertEqual("Realtime / Virtual Production Interchange", recipes["CAP-027"]["subject"])
        self.assertEqual("graphics_3d", recipes["CAP-027"]["primitive"])
        self.assertEqual("metric_3d_reconstruction", recipes["CAP-032"]["primitive"])
        self.assertNotEqual("pytorch3d_runtime", recipes["CAP-032"]["primitive"])
        excluded_primitive = "un" + "real_runtime"
        self.assertNotIn(excluded_primitive, {row["primitive"] for row in recipes.values()})

    def test_recipe_policy_is_fail_closed(self):
        recipe = {
            "network_policy": "NONE",
            "human_approval_required": True,
        }
        good = {
            "network_scope": "NONE",
            "synthetic": False,
            "privileged": False,
            "external_side_effects": False,
            "global_promotion_claim": False,
            "human_approved": True,
        }
        self.assertTrue(common_request_allowed(recipe, good))
        self.assertFalse(common_request_allowed(recipe, {**good, "network_scope": "INTERNET"}))
        self.assertFalse(common_request_allowed(recipe, {**good, "synthetic": True}))
        self.assertFalse(common_request_allowed(recipe, {**good, "privileged": True}))
        self.assertFalse(common_request_allowed(recipe, {**good, "external_side_effects": True}))
        self.assertFalse(common_request_allowed(recipe, {**good, "global_promotion_claim": True}))
        self.assertFalse(common_request_allowed(recipe, {**good, "human_approved": False}))

    def test_negative_proof_checks_nonpromotion_and_side_effect_boundaries(self):
        proof = negative_proof(
            {
                "network_policy": "LOOPBACK_ONLY",
                "human_approval_required": True,
            }
        )
        self.assertEqual("PASS", proof["status"])
        self.assertTrue(all(proof["cases"].values()))

    def test_local_proof_primitives_execute_real_work(self):
        with tempfile.TemporaryDirectory() as td:
            scope = Path(td)
            knowledge = proof_knowledge_cache(scope / "knowledge", "CAP-X", "Knowledge")
            self.assertTrue(knowledge["source_preserved"])
            agent = proof_agent_process(scope / "agent", "CAP-X", "Agent")
            self.assertTrue(agent["separate_process"])
            security = proof_security_local(scope / "security", "CAP-X", "Security")
            self.assertTrue(security["test_marker_detected"])
            self.assertFalse(security["false_positive"])
            storage = proof_storage_io(scope / "storage", "CAP-X", "Storage")
            self.assertTrue(storage["fsync_completed"])
            self.assertTrue(storage["readback_equal"])
            pipeline = proof_pipeline_transform(scope / "pipeline", "CAP-X", "Transform")
            self.assertEqual([1, 2, 3], pipeline["ordered_values"])

    def test_loopback_and_conditional_external_proofs_do_not_contact_external_network(self):
        with tempfile.TemporaryDirectory() as td:
            scope = Path(td)
            loopback = proof_network_loopback(scope / "loopback", "CAP-X", "Gateway")
            self.assertTrue(loopback["loopback_http"])
            self.assertFalse(loopback["external_network"])
            conditional = proof_external_conditional(scope / "conditional", "CAP-X", "Remote")
            self.assertTrue(conditional["conditional_external_activation"])
            self.assertFalse(conditional["provider_execution_claim"])
            self.assertFalse(conditional["external_network"])

    def test_exact_rollback_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            result = exact_rollback(Path(td), "CAP-X", "pipeline_transform")
            self.assertTrue(result["rollback_hash_equal"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
