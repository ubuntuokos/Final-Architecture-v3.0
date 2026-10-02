import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = ROOT / "canonical/assessments/FA3-APIFY-ECOSYSTEM-DONOR-ASSESSMENT-2026-10-02.json"

EXPECTED = {
    "apify/crawlee": "438e3419626bd070f8984566bfb86ab9355f55d6",
    "apify/crawlee-python": "ccdb72cdffd2dee93828c7cf420b7634b965f354",
    "apify/crawlee-storage": "5bea28ede93f81ee27cc6ee4298dd2a608aa4472",
    "apify/apify-mcp-server": "1b8d4e0236e3b4e17a51c42ebdfcb60d2d4956de",
    "apify/agent-skills": "f5e84aa961e0ff2e890efebff64b0c5d04de1f1a",
    "apify/apify-sdk-python": "d1de6546b39cd213b816990373b6472c379d281b",
    "apify/browser-pool": "80ab2c57934648aaf08ee9d0d3fed8c69b413ac4",
    "apify/fingerprint-suite": "67866a6196658076a7b61ecbe2c590a2ff3f4057",
}

class ApifyEcosystemAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        cls.sources = {row["repository"]: row for row in cls.a["sources"]}

    def test_zero_runtime_authority_and_capability_delta(self):
        self.assertEqual(self.a["capability_baseline"], 175)
        self.assertEqual(self.a["capability_delta"], 0)
        self.assertEqual(self.a["architectural_authority_delta"], 0)
        self.assertFalse(self.a["current_host_runtime_claim"])
        self.assertFalse(self.a["automatic_provider_admission"])
        self.assertFalse(self.a["automatic_mcp_registration"])
        self.assertFalse(self.a["automatic_skill_admission"])
        self.assertFalse(self.a["apify_cloud_activation"])
        self.assertFalse(self.a["actor_store_admission"])

    def test_exact_child_snapshots_are_analysis_only(self):
        self.assertEqual(set(self.sources), set(EXPECTED))
        for repo, sha in EXPECTED.items():
            row = self.sources[repo]
            self.assertEqual(row["immutable_revision"], sha)
            self.assertFalse(row["material_adoption_authorized"])
            self.assertNotIn("donor_id", row)

    def test_special_boundaries(self):
        self.assertEqual(
            self.sources["apify/browser-pool"]["disposition"],
            "SUPERSEDED_HISTORICAL_REFERENCE_ONLY",
        )
        self.assertEqual(
            self.sources["apify/fingerprint-suite"]["disposition"],
            "SECURITY_RESTRICTED_REFERENCE_ONLY",
        )
        self.assertEqual(
            self.sources["apify/agent-skills"]["disposition"],
            "REFERENCE_ONLY_PENDING_LICENSE_PROVENANCE_RESOLUTION",
        )
        self.assertIn(
            "ROOT_LICENSE_FILE_NOT_OBSERVED",
            self.sources["apify/agent-skills"]["license_observation"],
        )

    def test_openclaw_dependency_is_analysis_not_runtime(self):
        o = self.a["openclaw_reconciliation"]
        self.assertEqual(o["prerequisite_kind"], "SOURCE_CLASSIFICATION_NOT_RUNTIME_ADMISSION")
        self.assertTrue(o["apify_analysis_prerequisite_satisfied_when_this_assessment_is_published_on_main"])
        self.assertTrue(o["openclaw_materialization_remains_blocked_until_publication"])
        self.assertFalse(o["affiliate_parameters_are_canonical_identity"])
        self.assertFalse(o["actor_listing_is_provider_admission"])
        self.assertEqual(
            self.a["conclusion"],
            "APIFY_ECOSYSTEM_ANALYSIS_COMPLETE_FOR_OPENCLAW_SOURCE_RECONCILIATION_ONLY",
        )

if __name__ == "__main__":
    unittest.main()
