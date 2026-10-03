"""Exact owner-marked GitHub workflow-topic donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-WORKFLOW-TOPIC-2026-10-03.json"

KEY = "github:topics/workflow"
URL = "https://github.com/topics/workflow"
DONOR_ID = "FA3-DONOR-WORKFLOW-TOPIC-001"

FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class WorkflowTopicDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1421)
        self.assertEqual(self.delta["proposed_entry_count"], 1422)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_owner_marked_topic_is_reference_only(self):
        row = self.by_key[KEY]
        self.assertEqual(row["donor_id"], DONOR_ID)
        self.assertEqual(row["source"]["locator"], URL)
        self.assertEqual(row["source"]["kind"], "GITHUB_TOPIC")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
        self.assertFalse(row["submission_review"]["second_registry_approval_required"])
        self.assertIn("DISCOVERY_INDEX", row["donor_modes"])
        self.assertEqual(row["license"], {"declared": "NOT_APPLICABLE", "status": "COLLECTION_INDEX"})
        self.assertTrue(all(row[flag] is False for flag in FLAGS))
        self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))
        self.assertTrue(row["discoverable_for_planning"])

    def test_topic_does_not_recursively_admit_children_or_authority(self):
        self.assertEqual(self.delta["source_count"], 1)
        self.assertEqual(self.delta["unique_source_key_count"], 1)
        self.assertEqual(self.delta["sources"][0]["normalized_key"], KEY)
        self.assertFalse(self.delta["boundaries"]["child_repository_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])
        self.assertFalse(self.delta["boundaries"]["authority_change"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])
        self.assertIn("VISUAL_WORKFLOW_AUTHORING", self.delta["discovery_classes"])
        self.assertIn("HUMAN_PROCESS_WORKFLOW", self.delta["discovery_classes"])
        self.assertIn("AGENT_AI_WORKFLOW", self.delta["discovery_classes"])

if __name__ == "__main__":
    unittest.main()
