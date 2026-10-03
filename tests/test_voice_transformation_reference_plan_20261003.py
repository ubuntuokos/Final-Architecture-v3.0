"""FA3 Voice transformation plan closure regressions."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
APPS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
INTENT = ROOT / "canonical/intents/FA3-VOICE-TRANSFORMATION-APPLICATION-INTENT-2026-10-03.json"
ASSESSMENT = ROOT / "canonical/assessments/FA3-VOICE-TRANSFORMATION-REUSE-ASSESSMENT-2026-10-03.json"
PLAN = ROOT / "canonical/plans/FA3-VOICE-TRANSFORMATION-PLAN-2026-10-03.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-VOICE-TRANSFORMATION-PLAN-APPROVAL-2026-10-03.json"
DONOR_ID = "FA3-DONOR-0XDEVALIAS-AI-VOICE-CLONING-GIST-001"

class VoiceTransformationPlanClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.apps = json.loads(APPS.read_text(encoding="utf-8"))
        cls.intent = json.loads(INTENT.read_text(encoding="utf-8"))
        cls.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.by_donor = {row["donor_id"]: row for row in cls.registry["entries"]}

    def test_published_donor_and_fixed_baseline(self):
        donor = self.by_donor[DONOR_ID]
        self.assertEqual(donor["status"], "ACCEPTED_REFERENCE")
        self.assertIn("DISCOVERY_INDEX", donor["donor_modes"])
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.plan["capability_baseline"], 175)
        self.assertEqual(self.plan["capability_delta"], 0)
        self.assertEqual(self.plan["authority_delta"], 0)
        self.assertEqual(self.assessment["capability_count_after"], 175)
        self.assertEqual(self.assessment["new_capabilities"], 0)
        self.assertEqual(self.assessment["new_architectural_authorities"], 0)

    def test_reuse_assessment_is_bound_to_published_main_snapshot(self):
        snap = self.assessment["donor_planning_snapshot"]
        self.assertEqual(snap["published_main_commit"], "fd8adf5ab2ef12882c47250ecb5d5f22ff8e796b")
        self.assertEqual(snap["donor_registry_blob_sha"], "6ca92f89dba92910b202d51e607b68cfee0cb488")
        self.assertEqual(snap["donor_registry_entry_count"], 1423)
        self.assertEqual(snap["donor_registry_sha256"], "f20260dc85bf9bf78f6456a2f2fbce426991832412a82cb8c66e8c347819488f")
        self.assertEqual(self.assessment["donor_review"], "REVIEWED_MATCH")
        self.assertEqual(self.assessment["adopted_donors"], [])
        self.assertFalse(self.assessment["pending_or_unmerged_donors_consumed"])

    def test_shared_consumers_are_canonical_applications(self):
        canonical = {row["application_id"] for row in self.apps["applications"]}
        consumers = set(self.plan["canonical_consumers"])
        self.assertTrue(consumers)
        self.assertTrue(consumers <= canonical)
        self.assertEqual(consumers, set(self.assessment["shared_capability_placement"]["consumer_application_ids"]))
        self.assertFalse(self.assessment["shared_capability_placement"]["local_duplicate_created"])

    def test_child_sources_remain_discovery_only(self):
        policy = self.plan["child_source_policy"]
        self.assertTrue(policy["explicit_owner_donornak_required"])
        self.assertFalse(policy["recursive_registration"])
        self.assertFalse(policy["provider_admission_from_discovery_index"])
        detail = self.assessment["donor_review_detail"]
        self.assertFalse(detail["usage_edge_created"])
        self.assertFalse(detail["runtime_dependency"])
        self.assertFalse(detail["provider_admission"])
        self.assertFalse(detail["model_admission"])

    def test_plan_approval_is_exact_and_non_promoting(self):
        raw = PLAN.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.decision["approved_plan_sha256"])
        self.assertEqual(self.decision["approved_plan_id"], self.plan["id"])
        self.assertEqual(self.decision["status"], "APPROVED")
        self.assertTrue(self.decision["explicit_user_approval"])
        self.assertFalse(self.decision["invariants"]["provider_model_runtime_admission_from_this_decision"])
        self.assertFalse(self.decision["invariants"]["current_host_runtime_promotion_claim"])
        self.assertFalse(self.plan["closure"]["current_host_promotion_claim"])

    def test_existing_authorities_remain_exclusive(self):
        inv = self.plan["hard_invariants"]
        self.assertEqual(inv["model_router_authority"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertEqual(inv["host_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertEqual(inv["license_rights_authority"], "FA3-LICENSE-RIGHTS-001")
        self.assertEqual(inv["evidence_authority"], "FA3-AUTH-OBS-EVIDENCE-001")
        self.assertTrue(inv["cpu_only_path_required"])
        self.assertTrue(inv["silent_fallback_forbidden"])
        self.assertTrue(inv["display_gpu_auto_ai_forbidden"])
        self.assertTrue(inv["child_donor_auto_admission_forbidden"])
        self.assertTrue(inv["current_host_simulated_pass_forbidden"])

if __name__ == "__main__":
    unittest.main()
