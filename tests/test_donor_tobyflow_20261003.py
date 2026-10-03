"""Owner-marked TobyFlow donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-TOBYFLOW-2026-10-03.json"

SOURCE_KEY = "https://labs.toby.vn/tobyflow"
DONOR_ID = "FA3-DONOR-TOBYFLOW-001"
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class TobyFlowDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_delta(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 1425)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1424)
        self.assertEqual(self.delta["proposed_entry_count"], 1425)
        self.assertEqual(self.delta["source_count"], 1)
        self.assertEqual(self.delta["unique_source_key_count"], 1)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_tobyflow_source_is_reference_only(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["kind"], "WEBSITE")
        self.assertEqual(row["source"]["locator"], "https://labs.toby.vn/tobyflow")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
        self.assertTrue(row["discoverable_for_planning"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_workflow_pattern_scope_and_license_boundary(self):
        row = self.by_key[SOURCE_KEY]
        self.assertEqual(row["license"]["declared"], "UNKNOWN")
        self.assertFalse(row["selection_scope"]["runtime_adoption"])
        self.assertFalse(row["selection_scope"]["code_copy"])
        self.assertIn("WORKFLOW_PATTERN", row["donor_modes"])
        self.assertIn("UI_WORKFLOW_PATTERN", row["donor_modes"])
        self.assertIn("visual-dag-workflow-builder", row["capability_hints"])
        self.assertIn("mcp-agent-trigger-pattern", row["capability_hints"])

    def test_no_runtime_provider_account_or_usage_edge_admission(self):
        b = self.delta["boundaries"]
        self.assertFalse(b["runtime_admission"])
        self.assertFalse(b["automatic_provider_admission"])
        self.assertFalse(b["browser_extension_runtime_admission"])
        self.assertFalse(b["third_party_account_admission"])
        self.assertFalse(b["credential_or_cookie_access_admission"])
        self.assertFalse(b["paid_service_dependency_admission"])
        self.assertFalse(b["remote_command_channel_admission"])
        self.assertFalse(b["usage_edge_created"])
        self.assertFalse(b["current_host_pass_claimed"])

if __name__ == "__main__":
    unittest.main()
