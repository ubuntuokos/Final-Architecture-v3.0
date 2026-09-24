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
