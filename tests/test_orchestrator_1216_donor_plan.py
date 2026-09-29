"""Source-bound design checks only; NEVER physical current-host runtime evidence."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
INTENT = ROOT / "canonical/intents/FA3-ORCHESTRATOR-DONOR-EXPANSION-APPLICATION-INTENT-2026-09-30.json"
ASSESSMENT = ROOT / "canonical/assessments/FA3-ORCHESTRATOR-DONOR-EXPANSION-REUSE-ASSESSMENT-2026-09-30.json"
PLAN = ROOT / "docs/FA3-ORCHESTRATOR-1216-DONOR-EXPANSION-2026-09-30.md"

class OrchestratorSourceBoundPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text())
        cls.intent = json.loads(INTENT.read_text())
        cls.assessment = json.loads(ASSESSMENT.read_text())
        cls.plan = PLAN.read_text()

    def test_registry_integrity_and_release_count(self):
        entries = self.registry["entries"]
        self.assertEqual(len(entries), self.registry["backfill"]["entry_count"])
        self.assertEqual(len(entries), len({e["source"]["normalized_key"] for e in entries}))
        self.assertEqual(len(entries), len({e["donor_id"] for e in entries}))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.intent["capability_count"], 175)
        self.assertEqual(self.assessment["capability_count_after"], 175)

    def test_exact_published_source_identity_tied_between_records(self):
        source = self.intent["source_snapshot"]
        checked = self.assessment["assessment_provenance"]
        self.assertEqual(source["published_main_sha"], checked["source_main_sha"])
        self.assertEqual(source["donor_registry_blob_sha"], checked["donor_registry_blob_sha"])
        self.assertEqual(source["registry_entry_count"], checked["published_count"])
        self.assertEqual(source["registry_unique_normalized_keys"], checked["unique_keys_verified"])
        self.assertTrue(source["pending_donor_prs_excluded"])
        self.assertEqual(len(source["published_main_sha"]), 40)
        self.assertEqual(len(source["donor_registry_blob_sha"]), 40)
        self.assertIn(source["donor_registry_blob_sha"], self.plan)

    def test_pattern_donors_exist_in_published_registry_without_admission(self):
        ids = {e["donor_id"]: e for e in self.registry["entries"]}
        patterns = self.assessment["pattern_reuse"]
        self.assertEqual(len(patterns), 20)
        self.assertEqual(len({p["id"] for p in patterns}), 20)
        for p in patterns:
            with self.subTest(donor=p["id"]):
                self.assertIn(p["id"], ids)
                self.assertIn(ids[p["id"]]["status"], ("CANDIDATE", "ACCEPTED_REFERENCE", "ANALYZED"))
                self.assertEqual(p["status"], "NON_AUTHORITATIVE_PATTERN_ONLY")
                self.assertFalse(p["automatic_install"])
                self.assertFalse(p["automatic_activation"])

    def test_no_unauthorized_scope_or_premature_closure(self):
        self.assertEqual(self.intent["proposed_authority_roles"], [])
        self.assertEqual(self.intent["declared_new_capabilities"], [])
        self.assertTrue(self.assessment["approval_required_before_implementation"])
        self.assertEqual(self.assessment["implementation_readiness"], "PENDING_GAPS")
        self.assertEqual(self.assessment["owner_approved_final_plan_receipt"], "PENDING")
        self.assertFalse(self.assessment["current_host_runtime_promotion_claim"])
        self.assertFalse(self.assessment["global_promotion_claim"])
        self.assertTrue(self.intent["hardware_audit"]["cpu_only_viable"])
        self.assertFalse(self.intent["hardware_audit"]["display_gpu_auto_extra_use"])
        self.assertFalse(self.intent["hardware_audit"]["hardware_mutation"])
        self.assertFalse(self.intent["namespace_claims"]["claims_default_port"])

    def test_archived_prs_not_treated_as_current_implementation(self):
        self.assertIn("OBJECTIVE_COORDINATION_392_CLOSED_UNMERGED", self.intent["declared_gaps"])
        self.assertIn("AGENT_COLLABORATION_427_CLOSED_UNMERGED", self.intent["declared_gaps"])
        self.assertIn("#392", self.plan)
        self.assertIn("#427", self.plan)
        self.assertIn("CLOSED", self.plan)
        self.assertIn("UNMERGED", self.plan)

    def test_feature_and_negative_case_coverage(self):
        for i in range(1, 19):
            with self.subTest(feature=i):
                self.assertIn(f"F{i}", self.plan)
        for i in range(17, 31):
            with self.subTest(case=i):
                self.assertIn(f"T{i}", self.plan)
        for token in ("Temporal", "UAF", "HRB", "Model Router", "MCP Gateway",
                      "Software Coexistence", "two *distinct physical hosts*",
                      "Wayland", "X11", "owner-approved"):
            with self.subTest(boundary=token):
                self.assertIn(token, self.plan)

if __name__ == "__main__":
    unittest.main()
