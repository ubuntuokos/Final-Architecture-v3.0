import json
import tempfile
import unittest
from pathlib import Path

from src.fa3_full_current_host_capability_producer import (
    common_request_allowed,
    desktop_wayland_scoped_admission,
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
        self.assertEqual(149, len(recipes))
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

    def test_desktop_wayland_recipe_scope_excludes_secret_authority(self):
        recipes = recipe_map(self.root)
        registry = json.loads(
            (self.root / "evidence/evidence-registry.json").read_text(encoding="utf-8")
        )
        records = {row["subject_id"]: row for row in registry["records"]}
        desktop_caps = sorted(
            cap for cap, row in recipes.items() if row["primitive"] == "desktop_wayland"
        )
        self.assertEqual(
            [
                "CAP-044",
                "CAP-057",
                "CAP-062",
                "CAP-090",
                "CAP-093",
                "CAP-096",
                "CAP-101",
                "CAP-105",
                "CAP-142",
            ],
            desktop_caps,
        )
        for cap in desktop_caps:
            self.assertNotIn("AUTH-SECRETS", records[cap]["authority_owners"], cap)

    def test_desktop_wayland_scoped_admission_ignores_only_secret_backend_failure(self):
        report = {
            "result": "FAIL",
            "desktop": {"desktop": "KDE_PLASMA"},
            "session": {"type": "wayland"},
            "capabilities": {
                "linux_host": "PASS",
                "xdg_runtime": "PASS",
                "dbus_session": "PASS",
                "uri_open": "PASS",
                "secret_backend": "FAIL",
                "local_gui_session": "PASS",
                "xdg_desktop_portal": "PASS",
            },
        }
        session_evidence = {
            "active_local_graphical_session_proven": True,
            "wayland_socket_proven": True,
            "kde_bus_identity_proven": True,
            "portal_bus_identity_proven": True,
        }
        scoped = desktop_wayland_scoped_admission(report, session_evidence)
        self.assertEqual("PASS", scoped["result"])
        self.assertEqual(["secret_backend"], scoped["full_desktop_required_failures"])
        self.assertEqual("FAIL", scoped["secret_backend_status"])
        self.assertFalse(scoped["secret_backend_used_for_desktop_wayland_admission"])

    def test_desktop_wayland_scoped_admission_remains_fail_closed_for_session_failure(self):
        report = {
            "result": "FAIL",
            "desktop": {"desktop": "KDE_PLASMA"},
            "session": {"type": "wayland"},
            "capabilities": {
                "linux_host": "PASS",
                "xdg_runtime": "PASS",
                "dbus_session": "FAIL",
                "uri_open": "PASS",
                "secret_backend": "FAIL",
                "local_gui_session": "PASS",
                "xdg_desktop_portal": "PASS",
            },
        }
        session_evidence = {
            "active_local_graphical_session_proven": True,
            "wayland_socket_proven": True,
            "kde_bus_identity_proven": True,
            "portal_bus_identity_proven": True,
        }
        scoped = desktop_wayland_scoped_admission(report, session_evidence)
        self.assertEqual("FAIL", scoped["result"])
        self.assertIn("dbus_session", scoped["failed_checks"])
        self.assertIn("full_desktop_failure:dbus_session", scoped["failed_checks"])

    def test_exact_rollback_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            result = exact_rollback(Path(td), "CAP-X", "pipeline_transform")
            self.assertTrue(result["rollback_hash_equal"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
