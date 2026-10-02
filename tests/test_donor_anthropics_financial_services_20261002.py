"""Anthropic financial-services explicit owner-marked donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-ANTHROPICS-FINANCIAL-SERVICES-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

KEY = "github:anthropics/financial-services"
DONOR_ID = "FA3-DONOR-ANTHROPICS-FINANCIAL-SERVICES-001"
URL = "https://github.com/anthropics/financial-services"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class AnthropicFinancialServicesDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(len(self.entries), 1340)
        self.assertEqual(self.registry["backfill"]["entry_count"], 1340)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1339)
        self.assertEqual(self.delta["proposed_entry_count"], 1340)
        self.assertEqual(self.delta["source_count"], 1)
        self.assertEqual(self.delta["unique_source_key_count"], 1)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_source_is_reference_only(self):
        row = self.by_key[KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["locator"], URL)
        self.assertEqual(row["source"]["kind"], "GITHUB_REPOSITORY")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
        self.assertFalse(row["submission_review"]["second_registry_approval_required"])
        self.assertEqual(row["license"]["declared"], "Apache-2.0")
        self.assertTrue(row["discoverable_for_planning"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))
        self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_intake_creates_no_usage_edge_or_runtime_admission(self):
        self.assertNotIn(DONOR_ID, json.dumps(self.links, sort_keys=True))
        boundaries = self.delta["boundaries"]
        for field in (
            "automatic_fetch", "automatic_install", "automatic_activation",
            "automatic_code_import", "automatic_dependency",
            "automatic_provider_admission", "automatic_model_selection",
            "mcp_connector_admission", "hosted_service_activation",
            "partner_component_auto_registration", "usage_edge_created",
            "capability_count_change", "authority_change",
        ):
            self.assertFalse(boundaries[field])

if __name__ == "__main__":
    unittest.main()
