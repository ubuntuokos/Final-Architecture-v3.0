"""Paperclip canonical donor usage-edge and provenance reconciliation regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
ASSESSMENT = ROOT / "canonical/assessments/FA3-ORCHESTRATION-GOVERNANCE-PAPERCLIP-REUSE-ASSESSMENT-2026-10-02.json"
HISTORICAL_ASSESSMENT = ROOT / "canonical/assessments/FA3-ORCHESTRATION-GOVERNANCE-REUSE-ASSESSMENT-2026-09-30.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-ORCHESTRATION-GOVERNANCE-2026-09-30.json"
CONTRACT = ROOT / "canonical/contracts/FA3-ORCHESTRATION-GOVERNANCE-CONTRACTS-001.json"

DONOR_ID = "FA3-DONOR-PAPERCLIPAI-PAPERCLIP-001"
USAGE_ID = "FA3-USAGE-PAPERCLIP-ORCHESTRATION-GOVERNANCE-001"
PROFILE_ID = "FA3-ORCHESTRATION-WORKFORCE-001"
ASSESSMENT_ID = "FA3-ORCHESTRATION-GOVERNANCE-PAPERCLIP-REUSE-ASSESSMENT-2026-10-02"


class PaperclipCanonicalUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
        cls.historical = json.loads(HISTORICAL_ASSESSMENT.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_donor_is_published_canonical_reference(self):
        donor = next(row for row in self.registry["entries"] if row.get("donor_id") == DONOR_ID)
        self.assertEqual(donor["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(donor["source"]["normalized_key"], "github:paperclipai/paperclip")
        self.assertFalse(donor["selection_scope"]["runtime_adoption"])
        self.assertFalse(donor["selection_scope"]["control_plane_adoption"])
        self.assertFalse(donor["selection_scope"]["code_copy"])

    def test_exact_architecture_pattern_usage_edge(self):
        usage = next(row for row in self.links["donor_usage_records"] if row.get("id") == USAGE_ID)
        self.assertEqual(usage["donor_id"], DONOR_ID)
        self.assertEqual(usage["usage_kind"], "ARCHITECTURE_PATTERN")
        self.assertEqual(usage["status"], "ACTIVE")
        self.assertEqual(usage["primary_consumer"]["kind"], "PROFILE")
        self.assertEqual(usage["primary_consumer"]["id"], PROFILE_ID)
        self.assertEqual(usage["current_host_impact"]["classification"], "NO_RUNTIME_IMPACT")
        self.assertEqual(
            usage["provenance"]["evidence_classification"],
            "EXPLICIT_CANONICAL_DONOR_PATTERN_USE_NO_CODE_COPY",
        )

    def test_reuse_assessment_is_bound_to_published_paperclip_snapshot(self):
        row = self.assessment
        self.assertEqual(row["id"], ASSESSMENT_ID)
        self.assertEqual(row["result"], "PASS")
        self.assertEqual(row["published_main_registry"]["entry_count"], 1355)
        self.assertTrue(row["published_main_registry"]["paperclip_present"])
        self.assertEqual(row["published_main_registry"]["paperclip_donor_id"], DONOR_ID)
        self.assertEqual(row["paperclip_analysis"]["usage_edge_id"], USAGE_ID)
        self.assertTrue(row["paperclip_analysis"]["canonical_donor_registered"])
        self.assertFalse(row["paperclip_analysis"]["runtime_dependency"])
        self.assertFalse(row["paperclip_analysis"]["control_plane_adoption"])
        self.assertFalse(row["paperclip_analysis"]["code_copy"])
        self.assertEqual(row["capability_count_after"], 175)
        self.assertEqual(row["new_capabilities"], 0)
        self.assertEqual(row["new_architectural_authorities"], 0)
        self.assertFalse(row["current_host_runtime_promotion_claim"])

    def test_historical_assessment_is_preserved_and_linked(self):
        self.assertFalse(self.historical["published_main_registry"]["paperclip_present"])
        reconciliation = self.historical["post_publication_reconciliation"]
        self.assertTrue(reconciliation["historical_snapshot_preserved"])
        self.assertEqual(reconciliation["donor_id"], DONOR_ID)
        self.assertEqual(reconciliation["usage_edge_id"], USAGE_ID)
        self.assertEqual(reconciliation["reconciliation_assessment_id"], ASSESSMENT_ID)

    def test_571_boundary_records_are_canonical_donor_aware_without_new_authority(self):
        boundary = self.decision["paperclip_boundary"]
        self.assertEqual(boundary["registry_status"], "CANONICAL_DONOR_ACCEPTED_REFERENCE")
        self.assertEqual(boundary["donor_id"], DONOR_ID)
        self.assertEqual(boundary["usage_edge_id"], USAGE_ID)
        self.assertTrue(boundary["canonical_provenance_reconciled"])
        self.assertFalse(boundary["code_copied"])
        self.assertFalse(boundary["runtime_adopted"])
        self.assertFalse(boundary["control_plane_adopted"])

        contract = self.contract["paperclip_reference_boundary"]
        self.assertTrue(contract["canonical_donor_registered"])
        self.assertEqual(contract["donor_id"], DONOR_ID)
        self.assertEqual(contract["usage_edge_id"], USAGE_ID)
        self.assertEqual(contract["usage_kind"], "ARCHITECTURE_PATTERN")
        self.assertFalse(contract["source_copy"])
        self.assertFalse(contract["runtime_dependency"])
        self.assertFalse(contract["control_plane_admission"])
        self.assertTrue(contract["temporal_sole_global_durable_lifecycle"])


if __name__ == "__main__":
    unittest.main()
