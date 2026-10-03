"""Shared Interactive Workspace static materialization regressions."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "canonical/profiles/FA3-SHARED-INTERACTIVE-WORKSPACE-001.json"
CONTRACTS = ROOT / "canonical/contracts/FA3-SHARED-INTERACTIVE-WORKSPACE-CONTRACTS-001.json"
ASSESSMENT = ROOT / "canonical/assessments/FA3-SHARED-INTERACTIVE-WORKSPACE-REUSE-ASSESSMENT-2026-10-03.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-SHARED-INTERACTIVE-WORKSPACE-2026-10-03.json"
PLAN = ROOT / "docs/FA3-SHARED-INTERACTIVE-WORKSPACE-PLAN-2026-10-03.md"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
IMPACT = ROOT / "canonical/FA3-SHARED-INTERACTIVE-WORKSPACE-CURRENT-HOST-IMPACT-001.json"

class SharedInteractiveWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        cls.contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
        cls.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.impact = json.loads(IMPACT.read_text(encoding="utf-8"))

    def test_fixed_baseline_and_no_new_authority(self):
        self.assertEqual(self.profile["capability_count"], 175)
        self.assertFalse(self.profile["new_capability"])
        self.assertFalse(self.profile["new_architectural_authority"])
        self.assertEqual(self.assessment["capability_count_after"], 175)
        self.assertEqual(self.assessment["new_capabilities"], 0)
        self.assertEqual(self.assessment["new_architectural_authorities"], 0)

    def test_existing_authorities_and_mmg_ir_are_reused(self):
        a = self.profile["authority_bindings"]
        self.assertEqual(a["model_routing"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertEqual(a["tool_mediation"], "FA3-AUTH-MCP-GATEWAY-001")
        self.assertEqual(a["generation_context_ir"], "FA3-MMG-CONTEXT-IR-001")
        self.assertIn("EVAL_MODEL_OUTPUT", self.contracts["forbidden"])
        self.assertIn("LOADSTRING_MODEL_OUTPUT", self.contracts["forbidden"])
        self.assertEqual(
            self.contracts["required_semantics"]["generation_context"],
            "FA3-MMG-CONTEXT-IR-001_ONLY",
        )

    def test_published_main_donor_snapshot_only(self):
        snap = self.assessment["donor_planning_snapshot"]
        self.assertEqual(
            snap["published_main_commit"],
            "5d99e09b674877bcf4c057ec7af82e5d819ee616",
        )
        self.assertEqual(
            snap["donor_registry_blob_sha"],
            "6fcd9a7f5b3e3c5c54b1ae1b5227b37a9bb6a951",
        )
        self.assertEqual(
            snap["donor_registry_sha256"],
            "7dfe58f105a0100948ae19f58925a9deba0b4036544b883b1b63740f3791c7ac",
        )
        self.assertEqual(snap["donor_registry_entry_count"], 1422)
        self.assertEqual(self.assessment["donor_review"], "REVIEWED_MATCH")
        self.assertEqual(self.assessment["adopted_donors"], [])
        self.assertFalse(self.assessment["pending_or_unmerged_donors_consumed"])
        self.assertEqual(self.assessment["donor_usage_edges_created"], 0)

    def test_owner_approval_binds_exact_plan(self):
        raw = PLAN.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            self.decision["approved_plan_sha256"],
        )
        self.assertTrue(self.decision["explicit_user_approval"])
        self.assertEqual(self.decision["status"], "APPROVED")

    def test_shared_consumer_map_and_profiles(self):
        row = next(
            x for x in self.links["shared_capabilities"]
            if x["id"] == "FA3-SHARED-INTERACTIVE-WORKSPACE-001"
        )
        self.assertEqual(row["status"], "MATERIALIZED_STATIC")
        self.assertFalse(row["authority"])
        self.assertEqual(len(row["consumer_applications"]), 17)
        self.assertEqual(
            self.profile["initial_consumer_profiles"]["fa3.video-editor"], "G4"
        )
        self.assertEqual(
            self.profile["initial_consumer_profiles"]["studio.mautic"], "G2"
        )

    def test_static_current_host_boundary(self):
        self.assertEqual(self.impact["status"], "NO_RUNTIME_IMPACT")
        self.assertFalse(self.impact["runtime_change"])
        self.assertFalse(self.impact["physical_application_binding"])
        self.assertFalse(self.impact["physical_current_host_pass_claimed"])
        self.assertFalse(self.impact["host_requalification_required_now"])

if __name__ == "__main__":
    unittest.main()
