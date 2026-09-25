from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_reuse_assessment import assess_intent
from fa3_reuse_catalog import build_catalog
from fa3_reuse_resolver import bounded_rank, resolve


class ReuseDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.intent = json.loads((ROOT / "canonical/intents/FA3-EMBEDDING-FABRIC-APPLICATION-INTENT-001.json").read_text(encoding="utf-8"))

    def test_catalog_discovers_existing_fa3_assets(self):
        ids = {row["candidate_id"] for row in build_catalog(ROOT)["entries"]}
        self.assertIn("FA3-HIERARCHICAL-HYBRID-RETRIEVAL-001", ids)
        self.assertIn("FA3-INFERENCE-PORTABILITY-001", ids)
        self.assertIn("FA3-HARDWARE-BASELINE-001", ids)
        self.assertIn("fa3.document.retrieve", ids)

    def test_golden_embedding_intent_reuses_document_retrieval(self):
        result = assess_intent(ROOT, self.intent)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["implementation_readiness"], "PENDING_GAPS")
        ids = {row["id"] for row in result["selected_reuse"]}
        self.assertIn("fa3.document.retrieve", ids)

    def test_catalog_federates_admitted_skills_and_external_skill_sources(self):
        rows = build_catalog(ROOT)["entries"]
        by_id = {row["candidate_id"]: row for row in rows}
        self.assertIn("fa3-quality-code", by_id)
        skill = by_id["fa3-quality-code"]
        self.assertEqual(skill["candidate_class"], "SKILL")
        self.assertEqual(skill["admission_status"], "ADMITTED")
        self.assertTrue(skill["task_scoped"])
        self.assertFalse(skill["authority"])
        external = [row for row in rows if row["candidate_class"] == "EXTERNAL_SKILL_SOURCE"]
        self.assertGreaterEqual(len(external), 8)
        self.assertTrue(all(row["distribution_class"] == "REFERENCE_ONLY" for row in external))
        self.assertTrue(all(row["authority"] is False for row in external))
        self.assertTrue(all(row["automatic_install"] is False for row in external))

    def test_task_class_selects_only_admitted_skill_context(self):
        intent = copy.deepcopy(self.intent)
        intent["required_capabilities"] = []
        intent["optional_capabilities"] = []
        intent["problem_classes"] = ["code"]
        intent["task_classes"] = ["code"]
        intent["skill_triggers"] = ["quality.code"]
        intent["declared_gaps"] = []
        resolution = resolve(ROOT, intent)
        skills = [row for row in resolution["candidates"] if row["candidate_class"] == "SKILL"]
        code = next(row for row in skills if row["candidate_id"] == "fa3-quality-code")
        self.assertEqual(code["reuse_mode"], "ADMITTED_SKILL_REUSE")
        self.assertTrue(code["activation_candidate"])
        self.assertEqual(code["status"], "ADMITTED")
        self.assertFalse(code["authority"])
        self.assertFalse(resolution["skill_activation_authority"])

    def test_external_skill_sources_never_gain_install_or_activation_authority(self):
        resolution = resolve(ROOT, self.intent)
        self.assertFalse(resolution["external_skill_source_install_authority"])
        rows = build_catalog(ROOT)["entries"]
        external = [row for row in rows if row["candidate_class"] == "EXTERNAL_SKILL_SOURCE"]
        self.assertTrue(external)
        self.assertTrue(all(row["status"] == "REFERENCE_ONLY" for row in external))
        self.assertTrue(all(row["automatic_activation"] is False for row in external))

    def test_existing_authority_collision_fails(self):
        intent = copy.deepcopy(self.intent)
        intent["proposed_authority_roles"] = ["model_routing"]
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("AUTHORITY_COLLISION", result["blocking_findings"])

    def test_upstream_uninstall_requirement_fails_coexistence(self):
        intent = copy.deepcopy(self.intent)
        intent["namespace_claims"]["requires_upstream_uninstall"] = True
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("COEXISTENCE_INVALID", result["blocking_findings"])

    def test_hardware_vendor_pin_fails(self):
        intent = copy.deepcopy(self.intent)
        intent["hardware_audit"]["vendor_neutral"] = False
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("HARDWARE_AUDIT_INVALID", result["blocking_findings"])

    def test_duplicate_capability_declaration_fails(self):
        intent = copy.deepcopy(self.intent)
        intent["declared_new_capabilities"] = ["fa3.document.retrieve"]
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("DUPLICATE_CAPABILITY_DECLARATION", result["blocking_findings"])

    def test_decision_fabric_cannot_expand_candidate_set(self):
        self.assertEqual(bounded_rank(["a", "b"], ["b", "a"]), ["b", "a"])
        with self.assertRaises(ValueError):
            bounded_rank(["a", "b"], ["a", "c"])

    def test_resolver_records_space_for_real_gaps_without_inventing_authority(self):
        resolution = resolve(ROOT, self.intent)
        self.assertEqual(resolution["authority_collisions"], [])
        self.assertEqual(resolution["decision_fabric_candidate_expansion"], "DENY")
        self.assertEqual(resolution["agent_native_output"], "PROPOSAL_ONLY")


if __name__ == "__main__":
    unittest.main()
