import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_generative_media_mesh_gate import run

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class GenerativeMediaMeshTests(unittest.TestCase):
    def test_gate(self):
        self.assertEqual(run(), [])

    def test_baseline_and_authorities(self):
        p = load("canonical/profiles/FA3-GENERATIVE-MEDIA-MESH-001.json")
        c = load("canonical/contracts/FA3-GENERATIVE-MEDIA-MESH-CONTRACTS-001.json")
        self.assertEqual(p["capability_count"], 175)
        self.assertEqual(c["capability_count"], 175)
        self.assertFalse(p["new_capability"])
        self.assertFalse(p["new_architectural_authority"])
        self.assertEqual(c["authority_boundaries"]["provider_model_routing"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertEqual(c["authority_boundaries"]["host_resource_placement"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")

    def test_hidream_children_fail_closed(self):
        p = load("canonical/profiles/FA3-GENERATIVE-MEDIA-MESH-001.json")
        child = p["hidream_children"]
        self.assertFalse(child["automatic_execution"])
        self.assertFalse(child["automatic_registration"])
        self.assertFalse(child["canonical_child_queue"])
        self.assertFalse(child["child_sources_canonicalized"])
        self.assertEqual(child["admission_state"], "BLOCKED_PENDING_EXPLICIT_CHILD_DONOR_MARKERS_AND_INDIVIDUAL_GATES")

    def test_no_physical_pass_claim(self):
        d = load("canonical/decisions/FA3-DEC-HIDREAM-GENERATIVE-MEDIA-MESH-2026-10-04.json")
        self.assertFalse(d["runtime_promotion_claim"])
        self.assertFalse(d["current_host_pass_claimed"])
        self.assertFalse(d["approval_binding"]["exact_head_repository_owner_approved_review_observed"])
        self.assertTrue(d["approval_binding"]["finalization_fail_closed_until_owner_review"])

if __name__ == "__main__":
    unittest.main()